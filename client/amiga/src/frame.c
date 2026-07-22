/*
 * frame.c — PETSCII frame display (reconstructed).
 *
 * This is the answer to project goal #3 ("how does the Amiga handle PETSCII?"):
 * the Amiga client renders the SAME PETSCII frame format as the C64/server, using
 * an embedded copy of the C64 character ROM as an Amiga font. There is no separate
 * "Amiga frame format" and no translation table on the wire — the conversion from
 * PETSCII byte to screen-code happens here, in render_char, exactly as the C64
 * kernal does it.
 *
 *   read_frame_byte    (FUN_0010800c) — pull the next raw byte of a frame, topping
 *                       up from the transport in 0x8f-byte reads.
 *   frame_rle_getchar  (FUN_00108086) — de-RLE: 0x06 => run of spaces,
 *                       0x07 => run of an arbitrary char (same scheme as server SEQ).
 *   render_char        (FUN_001054f8) — PETSCII byte -> screen cell. Dispatches on
 *                       byte>>5: control ranges go through jump tables; printable
 *                       ranges map to screen-codes via the canonical PETSCII masks.
 *   build_font         (FUN_00106000) — build the 8x8 Amiga font (normal + reverse,
 *                       upper + lower case) from the embedded C64 charset.
 *   blit_char_cell     (FUN_00107000) — draw one 8x8 cell (4 colour planes) from the
 *                       font into the frame bitmap / rastport.
 *
 * See client/amiga/vintage/tools/re/petscii-frame-format.md for the byte>>5 map and
 * the (still-partly-unconfirmed) 0x00-0x1F / 0x80-0x9F control tables.
 */
#include <exec/types.h>
#include <clib/exec_protos.h>

#include "compunet.h"

/*
 * A frame "page" is a header followed by a 40x24 grid of (screencode, colour)
 * cell pairs. We access it through the same byte offsets the original used:
 *   +0x04 WORD  cursor row
 *   +0x06 WORD  cursor col
 *   +0x08 BYTE  current colour
 *   +0x09 BYTE  charset/case + reverse flags (OR'd into each screen code)
 *   +0x0a WORD  wrap flag
 *   +0x0c WORD  lowercase/mode flag
 *   +0x0e BYTE  border colour
 *   +0x0f BYTE  background colour
 *   +0x10 ...   the 40x24 cell array: cell = 2 bytes (screencode, colour)
 */
#define PAGE_ROW(p)     (*(WORD  *)((UBYTE *)(p) + 0x04))
#define PAGE_COL(p)     (*(WORD  *)((UBYTE *)(p) + 0x06))
#define PAGE_COLOUR(p)  (*(UBYTE *)((UBYTE *)(p) + 0x08))
#define PAGE_ATTR(p)    (*(UBYTE *)((UBYTE *)(p) + 0x09))
#define PAGE_WRAP(p)    (*(WORD  *)((UBYTE *)(p) + 0x0a))
#define PAGE_CELLS(p)   ((UBYTE *)(p) + 0x10)

/* Control-code jump tables (recon PTR_FUN_0011d8a8 for 0x00-0x1F, PTR_FUN_0011d928
 * for 0x80-0x9F). These dispatch colour/cursor/RVS/charset PETSCII control codes.
 * TODO: the individual entries are not all confirmed — see petscii-frame-format.md.
 * They are declared here as arrays of handlers taking the page pointer. */
extern void (*g_ctrl_lo[32])(APTR page);   /* PTR_FUN_0011d8a8 — codes 0x00-0x1F */
extern void (*g_ctrl_hi[128])(APTR page);  /* PTR_FUN_0011d928 — codes 0x80-0xFF (& 0x7f) */

/* Rendering helpers reconstructed below (were extern/stub). */
void frame_advance_cursor(APTR page);   /* FUN_001051de */
void frame_redraw(APTR page);           /* FUN_00107156 — re-blit all 40x24 cells */
void frame_clear_region(int r0, int c0, int r1, int c1, APTR page); /* FUN_0010544e */
void frame_insert_char(APTR page);      /* FUN_0010527e */
void frame_delete_char(APTR page);      /* FUN_00105376 */
extern void frame_offscreen_begin(void);/* FUN_001060f6 — set up offscreen bitmap */
extern void frame_offscreen_end(APTR page);/* FUN_0010617c — blit offscreen to window */
extern void frame_border(int r0, int c0, int r1, int c1, APTR page); /* FUN_001061e8 */
extern void gfx_set_bpen(APTR rp, UBYTE pen);       /* GfxBase.SetBPen (FUN_0012a0a0) */
extern void gfx_scroll_raster(APTR rp, int dx, int dy, int x0, int y0, int x1, int y1); /* FUN_0012a0f0 */

/*
 * Frame byte source: a function pointer the frame parser installs to read either
 * from the transport (read_frame_byte) or from a memory buffer (upload path).
 * (recon DAT_001203b6.)
 */
extern UBYTE (*g_frame_getbyte)(void);

/* Transport-fed frame buffer state (recon DAT_001203a0..DAT_001203ae). */
extern UWORD  g_frame_pos;      /* DAT_001203a0 — read cursor into g_frame_buf   */
extern UWORD  g_frame_len;      /* DAT_001203a4 — valid bytes in g_frame_buf     */
extern UBYTE  g_frame_eof;      /* DAT_001203ac — end-of-frame flag from device  */
extern UBYTE *g_frame_capture;  /* DAT_001203ae — optional capture sink (or NULL)*/
extern UBYTE  g_frame_buf[];    /* DAT_00120310 — 0x8f-byte transport read buffer*/
extern UWORD  g_frame_hdr_more; /* DAT_001203b2 — top bit of first header byte   */

/* RLE de-compression state (recon DAT_001203ba/bb). */
extern UBYTE  g_rle_char;       /* DAT_001203ba — the char being emitted         */
extern UBYTE  g_rle_run;        /* DAT_001203bb — remaining repeat count         */

/*
 * read_frame_byte — next raw frame byte, refilling from the transport in
 * 0x8f-byte reads and honouring the optional capture sink (recon: FUN_0010800c).
 */
UBYTE read_frame_byte(void)
{
    UBYTE b;
    UBYTE ser_flags, status_hi;
    ULONG actual;

    if (g_frame_pos < g_frame_len) {
        b = g_frame_buf[g_frame_pos++];
    } else if (g_frame_eof == '\0') {
        serial_read(g_frame_buf, 0x8f, &g_frame_eof, &status_hi, &actual);
        g_frame_len = (UWORD)actual;
        g_frame_pos = 1;
        b = g_frame_buf[0];
    } else {
        b = 0;
    }

    if (g_frame_capture != NULL)
        *g_frame_capture++ = b;

    return b;
}

/*
 * frame_rle_getchar — de-RLE the frame stream (recon: FUN_00108086). 0x06 begins a
 * run of spaces; 0x07 begins a run of an arbitrary char. Identical to the server's
 * SEQ frame RLE.
 */
char frame_rle_getchar(void)
{
    if (g_rle_run == '\0') {
        g_rle_char = g_frame_getbyte();
        if (g_rle_char == 0x06) {              /* run of spaces */
            g_rle_char = ' ';
            g_rle_run  = g_frame_getbyte();
        } else if (g_rle_char == 0x07) {       /* run of a char */
            g_rle_char = g_frame_getbyte();
            g_rle_run  = g_frame_getbyte();
        }
    } else {
        g_rle_run--;
    }
    return (char)g_rle_char;
}

/* frame_has_more_pages — the first header byte's top bit (recon DAT_001203b2). */
LONG frame_has_more_pages(void)
{
    return g_frame_hdr_more != 0;
}

/*
 * render_char — convert one PETSCII byte to a screen-code and store it into the
 * current cell (recon: FUN_001054f8). The dispatch on byte>>5 is the canonical
 * PETSCII decode:
 *   0x00-0x1F : control codes  -> jump table g_ctrl_lo
 *   0x20-0x3F : screencode = byte              (punctuation/digits)
 *   0x40-0x5F : screencode = byte & 0x1f       (@A-Z)
 *   0x60-0x7F : screencode = (byte & 0x1f)|0x40
 *   0x80-0x9F : control codes  -> jump table g_ctrl_hi
 *   0xA0-0xBF : screencode = (byte & 0x1f)|0x60
 *   0xC0-0xDF : screencode = byte & 0x7f
 *   0xE0-0xFF : screencode = byte & 0x7f  (0xFF -> 0x5e special-case)
 */
void render_char(UBYTE ch, APTR page)
{
    UBYTE code;
    WORD  row, col;
    UBYTE *cell;
    UBYTE prev;

    switch (ch >> 5) {
    case 0:                                    /* 0x00-0x1F */
        g_ctrl_lo[ch](page);
        return;
    case 1:  code = ch;              break;    /* 0x20-0x3F */
    case 2:  code = ch & 0x1f;       break;    /* 0x40-0x5F */
    case 3:  code = (ch & 0x1f)|0x40;break;    /* 0x60-0x7F */
    case 4:                                    /* 0x80-0x9F */
        g_ctrl_hi[ch & 0x7f](page);
        return;
    case 5:  code = (ch & 0x1f)|0x60;break;    /* 0xA0-0xBF */
    case 6:  code = ch & 0x7f;       break;    /* 0xC0-0xDF */
    default:                                   /* 0xE0-0xFF */
        code = (ch == 0xff) ? 0x5e : (ch & 0x7f);
        break;
    }

    /* OR in the page's current attribute (charset/case + reverse) bits. */
    code |= PAGE_ATTR(page);

    row  = PAGE_ROW(page);
    col  = PAGE_COL(page);
    cell = PAGE_CELLS(page) + row * 0x50 + col * 2;
    prev = cell[0];
    cell[0] = code;
    cell[1] = PAGE_COLOUR(page);

    /* Only re-blit if the cell actually changed away from a blank. */
    if (code != 0x20 || prev != ' ')
        blit_char_cell(row, col, page);

    frame_advance_cursor(page);
    PAGE_WRAP(page) = (WORD)(PAGE_COL(page) == 0);
}

/*
 * build_font — construct the 8x8 Amiga font from the embedded C64 charset
 * (recon: FUN_00106000). Four 0x800-byte banks are built into one 0x2000 block:
 *   +0x0000 upper-case normal   +0x0800 upper-case reverse
 *   +0x1000 lower-case normal   +0x1800 lower-case reverse
 * Each C64 8-bit row becomes an Amiga 16-bit word (byte<<8); reverse = ~word.
 * Returns 1 on success, 0 if the allocation failed.
 */
LONG build_font(void)
{
    WORD ch, y;
    UBYTE bits;
    UBYTE *base;

    /* The C64 charset ROM lives in the extracted data blob (upper bank at 0x11d9c0,
     * lower at 0x11ddc0). The c64_charset_upper/lower globals were DECLARED but never
     * filled (a blob-vs-globals aliasing gap, like the credentials gadgets and the busy
     * pointer), so build_font was reading zeros -> an all-blank font: normal glyphs
     * rendered invisible (no text) while reverse/solid cells showed as coloured blocks
     * (the "graphics"). Read the charset from the blob instead. */
    extern UBYTE g_data[];
    const UBYTE *cs_upper = g_data + (0x11d9c0 - 0x11d000);
    const UBYTE *cs_lower = g_data + (0x11ddc0 - 0x11d000);

    g_font_base = (UBYTE *)AllocMem(0x2000, MEMF_CHIP | MEMF_CLEAR);
    if (g_font_base == NULL)
        return 0;
    base = g_font_base;

    for (ch = 0; ch < 0x80; ch++) {
        for (y = 0; y < 8; y++) {
            UBYTE *cellrow = base + ch * 0x10 + y * 2;

            bits = cs_upper[y + ch * 8];
            *(UWORD *)(cellrow)          = (UWORD)bits << 8;
            *(UWORD *)(cellrow + 0x800)  = ~((UWORD)bits << 8);

            bits = cs_lower[y + ch * 8];
            *(UWORD *)(cellrow + 0x1000) = (UWORD)bits << 8;
            *(UWORD *)(cellrow + 0x1800) = ~((UWORD)bits << 8);
        }
    }

    return 1;
}

/*
 * blit_char_cell — draw one 8x8 cell into the frame bitmap (recon: FUN_00107000).
 * The cell's screencode + attribute select one of four font sources per plane
 * (normal / reverse / blank / solid). When drawing to the offscreen bitmap
 * (g_offscreen set) the 8 rows are copied plane-by-plane; otherwise a
 * BltBitMapRastPort draws directly. The exact plane/source selection is preserved
 * from the original; only the pointer arithmetic is expressed via typed locals.
 *
 * NOTE: the four-way plane source selection and the offscreen row copy are the
 * literal transcription of the original's inner loop. The rendering is confirmed
 * to reproduce C64 frames; the plane-select constants (0x200/0xa00 blank/solid
 * banks) are as observed. See petscii-frame-format.md.
 */
extern UBYTE  g_offscreen;         /* DAT_0011d9a8 — 1 = draw to offscreen bitmap */
extern UBYTE *g_plane_src[4];      /* DAT_00120264 — per-plane font source ptrs   */
extern UBYTE *g_plane_dst[4];      /* DAT_0012028c — per-plane offscreen bases     */
extern void   blt_font_to_rastport(WORD row, WORD col, APTR page); /* direct-draw cell blit */

void blit_char_cell(WORD row, WORD col, APTR page)
{
    UBYTE *cell = PAGE_CELLS(page) + row * 0x50 + col * 2;
    UBYTE  colour = cell[1];
    UBYTE  attr  = *(UBYTE *)((UBYTE *)page + 0x0f);  /* background attr */
    WORD   plane;
    /* Font index = screencode OR (charset/lowercase-mode flag at page+0x0c) shifted
     * into bit 8 (recon 0x107032-0x10703e: move.w $c(a0); asl.l #8; or.l cell[0]).
     * So mode=1 selects the lowercase banks build_font lays down at +0x1000/+0x1800.
     * The reverse path XORs 0x80 into this (mode-extended) index (recon 0x10708c
     * eori.w #$80). Reading only cell[0] as a byte made the lowercase banks
     * unreachable — lowercase frames rendered in upper-case. */
    WORD   idx = (WORD)cell[0] | (WORD)(*(WORD *)((UBYTE *)page + 0x0c) << 8);

    /* Select a font source for each of the 4 bitplanes. */
    for (plane = 0; plane < 4; plane++) {
        UBYTE mask = (UBYTE)(1 << plane);
        if ((mask & colour) == 0) {
            if ((mask & attr) == 0)
                g_plane_src[plane] = g_font_base + 0x200;             /* blank */
            else
                g_plane_src[plane] = g_font_base + ((idx ^ 0x80) * 0x10);
        } else if ((mask & attr) == 0) {
            g_plane_src[plane] = g_font_base + (idx * 0x10);          /* normal */
        } else {
            g_plane_src[plane] = g_font_base + 0xa00;                 /* solid */
        }
    }

    if (g_offscreen == 0) {
        blt_font_to_rastport(row, col, page);
    } else {
        WORD base = col + row * 0x140;
        for (plane = 3; plane >= 0; plane--) {
            UBYTE *src = g_plane_src[plane];
            UBYTE *dst = g_plane_dst[plane] + base;
            int    r;
            for (r = 0; r < 8; r++)
                dst[r * 0x28] = src[r * 2];
        }
    }
}

/*
 * frame_advance_cursor — recon FUN_001051de. Advance the cursor one cell, wrapping
 * to the next row at column 40 (0x28) and clamping at row 24 (0x17).
 */
void frame_advance_cursor(APTR page)
{
    if (++PAGE_COL(page) == 0x28) {
        PAGE_COL(page) = 0;
        if (PAGE_ROW(page) < 0x17)
            PAGE_ROW(page)++;
    }
    PAGE_WRAP(page) = 0;
}

/*
 * frame_redraw — recon FUN_00107156. Re-blit the whole 40x24 grid (used after a
 * charset switch). Wraps the cell loop in the offscreen-bitmap begin/end pair.
 */
void frame_redraw(APTR page)
{
    WORD row, col;
    frame_offscreen_begin();
    for (row = 0; row < 0x18; row++)
        for (col = 0; col < 0x28; col++)
            blit_char_cell(row, col, page);
    frame_offscreen_end(page);
}

/*
 * frame_clear_region — recon FUN_0010544e. Fill a rectangular cell range with
 * spaces, then repaint that region's border.
 */
void frame_clear_region(int r0, int c0, int r1, int c1, APTR page)
{
    int r, c;
    for (r = r0; r <= r1; r++)
        for (c = c0; c <= c1; c++)
            PAGE_CELLS(page)[r * 0x50 + c * 2] = 0x20;
    frame_border(r0, c0, r1, c1, page);
}

/*
 * frame_insert_char — recon FUN_0010527e. Shift the current line right from the
 * cursor (insert a blank), then hardware-scroll the affected screen strip.
 */
void frame_insert_char(APTR page)
{
    short row = PAGE_ROW(page);
    short col = PAGE_COL(page);
    UBYTE *cells = PAGE_CELLS(page);
    short x;

    if (col > 0 || row > 0) {
        /* cursor_left (recon FUN_0010521e), inlined */
        if (--PAGE_COL(page) < 0) {
            PAGE_COL(page) = 0x27;
            if (PAGE_ROW(page) > 0) PAGE_ROW(page)--;
        }
        PAGE_WRAP(page) = 0;
        row = PAGE_ROW(page);
        col = PAGE_COL(page);
        for (x = col; x < 0x27; x++) {
            cells[row * 0x50 + x * 2]     = cells[row * 0x50 + (x + 1) * 2];
            cells[row * 0x50 + x * 2 + 1] = cells[row * 0x50 + (x + 1) * 2 + 1];
        }
        cells[row * 0x50 + 0x27 * 2] = 0x20;
        frame_redraw(page);   /* recon does a targeted SetBPen+ScrollRaster; redraw is behaviour-equivalent */
    }
}

/*
 * frame_delete_char — recon FUN_00105376. Shift the current line left into the
 * cursor cell (delete), blanking the last column.
 */
void frame_delete_char(APTR page)
{
    short row = PAGE_ROW(page);
    short col = PAGE_COL(page);
    UBYTE *cells = PAGE_CELLS(page);
    short x;

    for (x = 0x27; x > col; x--) {
        cells[row * 0x50 + x * 2]     = cells[row * 0x50 + (x - 1) * 2];
        cells[row * 0x50 + x * 2 + 1] = cells[row * 0x50 + (x - 1) * 2 + 1];
    }
    cells[row * 0x50 + col * 2] = 0x20;
    frame_redraw(page);
}

/* ------------------------------------------------------------------ *
 *  Frame parser — decode a received (or in-memory) frame into a page.
 * ------------------------------------------------------------------ *
 * A frame begins with a small header: byte 0 flags (top bit = more pages),
 * bytes 1-2 border/background colour nibbles (mapped through the 16-entry
 * PETSCII->Amiga colour table), byte 3 the initial charset. The body is the
 * RLE-compressed PETSCII cell stream, rendered a char at a time via render_char.
 */
extern UBYTE g_palette[16];   /* DAT_0011e1c0 — PETSCII colour -> Amiga pen map */

#define PAGE_MODE(p)  (*(short *)((UBYTE *)(p) + 0x0c))
#define PAGE_BORDER(p)(*(UBYTE *)((UBYTE *)(p) + 0x0e))
#define PAGE_BG(p)    (*(UBYTE *)((UBYTE *)(p) + 0x0f))

/* reset the page cursor/mode before rendering (recon FUN_0010568c). Sets mode (+0x0c)
 * = 1, clears attr (+9), then clear_screen (0x1054bc): frame_clear_region over the whole
 * grid AND homes the cursor (row/col/wrap = 0 at +4/+6/+0xa). The cursor-home was
 * previously omitted (frame_clear_region alone doesn't reset it). */
void frame_reset_page(APTR page)
{
    PAGE_MODE(page) = 1;
    *(UBYTE *)((UBYTE *)page + 9) = 0;   /* clear attribute */
    frame_clear_region(0, 0, 0x17, 0x27, page);
    PAGE_ROW(page)  = 0;                  /* clear_screen homes the cursor */
    PAGE_COL(page)  = 0;
    PAGE_WRAP(page) = 0;
}

/*
 * frame_display — recon FUN_0010818a. Parse a frame arriving from the transport
 * into 'page', capturing the raw bytes into 'out'. Returns the capture end pointer.
 */
APTR frame_display(APTR page, APTR out)
{
    UBYTE b;
    char  c;

    g_frame_getbyte = read_frame_byte;
    g_frame_pos = 0;
    g_frame_len = 0;
    g_frame_eof = 0;
    g_frame_capture = (UBYTE *)out;

    b = read_frame_byte();
    g_frame_hdr_more = b & 0x80;
    if (out) *(UBYTE *)out = 0;

    PAGE_BORDER(page) = g_palette[read_frame_byte() & 0x0f];
    PAGE_BG(page)     = g_palette[read_frame_byte() & 0x0f];
    frame_reset_page(page);
    c = (char)read_frame_byte();
    PAGE_MODE(page) = (c == 0x0e);   /* 0x0e -> lowercase mode */

    g_rle_run = 0;
    while ((c = frame_rle_getchar()) != '\0')
        render_char((UBYTE)c, page);

    return g_frame_capture;
}

/*
 * frame_display_mem — recon FUN_001080da. Same as frame_display but the byte source
 * is an in-memory buffer (used by the mail ID-check path), not the transport.
 */
extern UBYTE *g_mem_src;        /* DAT_001203a8 — memory read cursor */
static UBYTE mem_getbyte(void) { return *g_mem_src++; }

void frame_display_mem(APTR src, APTR page)
{
    UBYTE b;
    char  c;

    frame_offscreen_begin();
    g_mem_src = (UBYTE *)src;
    g_frame_getbyte = mem_getbyte;

    b = mem_getbyte();
    (void)b;
    PAGE_BORDER(page) = g_palette[mem_getbyte() & 0x0f];
    PAGE_BG(page)     = g_palette[mem_getbyte() & 0x0f];
    frame_reset_page(page);
    c = (char)mem_getbyte();
    PAGE_MODE(page) = (c == 0x0e);

    g_rle_run = 0;
    while ((c = frame_rle_getchar()) != '\0')
        render_char((UBYTE)c, page);
    frame_offscreen_end(page);
}

/*
 * frame_display_done — recon FUN_0011754e. Finalise a displayed frame: flush the
 * offscreen bitmap to the window. 'out'/'len' bound the captured raw frame.
 */
void frame_display_done(APTR out, APTR len)
{
    (void)out; (void)len;
    frame_offscreen_end(g_frame_page);
}

/*
 * frame_write_string — recon FUN_0010565e. Render a NUL-terminated string through
 * render_char (used by the directory renderer to draw row text).
 */
void frame_write_string(APTR text, APTR page)
{
    UBYTE *s = (UBYTE *)text;
    UBYTE c;
    while ((c = *s++) != '\0')
        render_char(c, page);
}

/* ------------------------------------------------------------------ *
 *  Cursor / pen setters used by the directory-frame parser
 * ------------------------------------------------------------------ *
 * Small leaf helpers that just poke the page struct's cursor (row/col at +4/+6),
 * wrap flag (+0xa) and pen/attr (+8/+9). Transcribed verbatim from the recon.
 */

/* frame_home — recon FUN_00105180. Reset cursor to (0,0) and clear the wrap flag. */
void frame_home(APTR page)
{
    PAGE_ROW(page)  = 0;
    PAGE_COL(page)  = 0;
    PAGE_WRAP(page) = 0;
}

/* frame_set_cursor — recon FUN_001056aa. Set cursor to (row,col), clear wrap. */
void frame_set_cursor(WORD row, WORD col, APTR page)
{
    PAGE_ROW(page)  = row;
    PAGE_COL(page)  = col;
    PAGE_WRAP(page) = 0;
}

/* frame_pen_lower — recon FUN_00105022. Select the "lower/normal" text pen (2). */
void frame_pen_lower(APTR page)
{
    PAGE_COLOUR(page) = 2;
}

/* frame_pen_upper — recon FUN_0010506a. Select the "upper/highlight" text pen (6). */
void frame_pen_upper(APTR page)
{
    PAGE_COLOUR(page) = 6;
}

/* frame_row_newline — recon FUN_00105250. Advance to the next row (unless wrapped or
 * already at the bottom row 0x17), reset column, clear wrap + attr. */
void frame_row_newline(APTR page)
{
    if (PAGE_WRAP(page) == 0 && PAGE_ROW(page) < 0x17)
        PAGE_ROW(page)++;
    PAGE_COL(page)  = 0;
    PAGE_WRAP(page) = 0;
    PAGE_ATTR(page) = 0;
}
