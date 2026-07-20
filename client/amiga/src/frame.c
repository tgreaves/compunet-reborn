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

extern void frame_advance_cursor(APTR page);/* FUN_001051de — move to next cell */

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

    g_font_base = (UBYTE *)AllocMem(0x2000, MEMF_CHIP | MEMF_CLEAR);
    if (g_font_base == NULL)
        return 0;
    base = g_font_base;

    for (ch = 0; ch < 0x80; ch++) {
        for (y = 0; y < 8; y++) {
            UBYTE *cellrow = base + ch * 0x10 + y * 2;

            bits = c64_charset_upper[y + ch * 8];
            *(UWORD *)(cellrow)          = (UWORD)bits << 8;
            *(UWORD *)(cellrow + 0x800)  = ~((UWORD)bits << 8);

            bits = c64_charset_lower[y + ch * 8];
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
extern void   blt_font_to_rastport(void); /* GfxBase.BltBitMapRastPort() path      */

void blit_char_cell(WORD row, WORD col, APTR page)
{
    UBYTE *cell = PAGE_CELLS(page) + row * 0x50 + col * 2;
    UBYTE  code  = cell[0];
    UBYTE  colour = cell[1];
    UBYTE  attr  = *(UBYTE *)((UBYTE *)page + 0x0f);  /* background attr */
    WORD   plane;

    /* Select a font source for each of the 4 bitplanes. */
    for (plane = 0; plane < 4; plane++) {
        UBYTE mask = (UBYTE)(1 << plane);
        if ((mask & colour) == 0) {
            if ((mask & attr) == 0)
                g_plane_src[plane] = g_font_base + 0x200;             /* blank */
            else
                g_plane_src[plane] = g_font_base + ((code ^ 0x80) * 0x10);
        } else if ((mask & attr) == 0) {
            g_plane_src[plane] = g_font_base + (code * 0x10);         /* normal */
        } else {
            g_plane_src[plane] = g_font_base + 0xa00;                 /* solid */
        }
    }

    if (g_offscreen == 0) {
        blt_font_to_rastport();
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
