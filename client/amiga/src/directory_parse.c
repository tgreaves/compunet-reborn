/*
 * directory_parse.c — parse a directory frame into the directory page (reconstructed).
 *
 *   parse_directory_frame (FUN_00109a5e, 1924 bytes) — read an RLE-decompressed
 *       directory frame from the transport and populate the directory page struct:
 *       the header text, up to 8 clickable "link" gadgets, the info line, the page
 *       number table, and the row table (name / number / date / type columns), then
 *       hand off to dir_select() to draw the initial selection highlight.
 *
 * This is what navigate.c's goto_page / link_follow call after a successful nav ack
 * (the earlier reconstruction exposed it as "directory_refresh" and approximated it
 * with a plain repaint — wrong; it is a full frame parser that also (re)builds the
 * gadget list).
 *
 * TRANSCRIPTION: faithful to the recon. The control flow is from the Ghidra decompile
 * (FUN_00109a5e); every structure offset and loop bound was confirmed against the raw
 * m68k listing of $109a5e..$10a1e0. Byte source is frame_rle_getchar (FUN_00108086),
 * installed here to read from the transport via read_frame_byte (LAB_0010a5ac ==
 * FUN_0010800c). Text is emitted through render_char / frame_write_string, with the
 * cursor/pen leaf helpers in frame.c. The link gadgets use the standard Intuition
 * Gadget layout; their handler is link_follow (FUN_001098e8) and their +0x30 field
 * back-points to the page.
 *
 * Directory page field offsets (from the page base = param_1):
 *   +0x006  WORD   render "column base" used by frame_write_string paging
 *   +0x790  8 x 7-byte link-code table  (row*7 + i)
 *   +0x7c8  page-number table: rows of 9 bytes (row*9 + i), 8 chars + NUL
 *   +0x810  row table, stride 0x66:  +0x810 col A (6+NUL), +0x817 col B (16+NUL),
 *           +0x828 col C (5+NUL), +0x82e sub-rows (8 x 9 bytes)
 *   +0xc72  WORD  number of page-number rows
 *   +0xc74  WORD  currently-selected row (init 0)
 *   +0xc76  WORD  number of body rows
 *   +0xc78  WORD  current page number (set to 0xffff = "none" at end)
 *   +0xc7a  LONG  head of the gadget list (RemoveGList/AddGList target)
 *   +0x1022 gadget array base, stride 0x34 (Gadget struct); +0x104e handler,
 *           +0x1052 page back-pointer, +0x1048(+0x26) GadgetID = link index
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/intuition_protos.h>

#include "compunet.h"

/* Byte source + text rendering (frame.c). */
extern char  frame_rle_getchar(void);              /* FUN_00108086 */
extern UBYTE read_frame_byte(void);                /* FUN_0010800c — installed as getbyte */
extern UBYTE (*g_frame_getbyte)(void);             /* DAT_001203b6 */
extern UWORD g_frame_pos;                          /* DAT_001203a0 */
extern UWORD g_frame_len;                           /* DAT_001203a4 */
extern UBYTE g_frame_eof;                           /* DAT_001203ac */
extern UBYTE *g_frame_capture;                      /* DAT_001203ae */
extern UBYTE g_rle_run;                             /* DAT_001203bb */

extern void render_char(UBYTE ch, APTR page);       /* FUN_001054f8 */
extern void frame_write_string(APTR text, APTR page); /* FUN_0010565e */
extern void frame_clear_region(int r0, int c0, int r1, int c1, APTR page); /* FUN_0010544e */
extern void frame_home(APTR page);                  /* FUN_00105180 */
extern void frame_set_cursor(WORD row, WORD col, APTR page); /* FUN_001056aa */
extern void frame_pen_lower(APTR page);             /* FUN_00105022 */
extern void frame_pen_upper(APTR page);             /* FUN_0010506a */
extern void frame_row_newline(APTR page);           /* FUN_00105250 */
extern void frame_advance_cursor(APTR page);        /* FUN_001051de */

extern LONG link_follow(APTR gadget);               /* FUN_001098e8 — gadget handler */
extern LONG dir_select(APTR sel_field, LONG mode);  /* FUN_0010935a — draw selection */

/* Page-field byte cursor. */
#define PB(p, off)   ((UBYTE *)(p) + (off))
#define PW(p, off)   (*(WORD *)((UBYTE *)(p) + (off)))

void parse_directory_frame(APTR page)
{
    UBYTE *p = (UBYTE *)page;
    UBYTE  c, prev;
    struct Gadget *prev_gad = NULL;   /* local_c — link back-patch of NextGadget */
    WORD   crlf;                       /* local_4 — CR counter / generic index    */
    WORD   ngad;                       /* local_6 — link gadget count / col index */
    WORD   row;                        /* local_8 — body row index                */
    WORD   idx;                        /* local_4 reused as sub index             */

    /* Install the transport byte source and reset the RLE / frame-read state. */
    g_frame_getbyte = read_frame_byte;
    g_frame_pos     = 0;
    g_frame_len     = 0;
    g_frame_capture = NULL;
    g_frame_eof     = 0;
    g_rle_run       = 0;

    /* --- Section 1: header text (drawn in region rows 0..5) --------------- */
    c = frame_rle_getchar();
    if (c != '\0') {
        frame_clear_region(0, 0, 5, 0x27, page);
        frame_home(page);
        do {
            render_char(c, page);
            c = frame_rle_getchar();
        } while (c != '\0');
    }

    /* Clear the two body regions (rows 0x1d..0x14 and 0x26..0x1f columns). */
    frame_clear_region(10, 1, 0x14, 0x1d, page);
    frame_clear_region(10, 0x1f, 0x14, 0x26, page);

    /* --- Section 2: the numbered link menu + its gadgets ----------------- */
    c = frame_rle_getchar();
    if (c != 0) {
        /* Clear the 8 link-code slots. */
        for (row = 0; row < 8; row++)
            *PB(page, row * 7 + 0x790) = 0;

        /* Remove any gadget list left from the previous page. */
        if (*(APTR *)PB(page, 0xc7a) != NULL)
            RemoveGList(*(struct Window **)p, *(struct Gadget **)PB(page, 0xc7a), -1);
        prev_gad = NULL;

        frame_clear_region(0x16, 0, 0x17, 0x27, page);
        frame_set_cursor(0x16, 0, page);

        prev = 0;
        row  = 0;      /* CR counter (local_4) */
        ngad = 0;      /* link gadget count (local_6) */
        do {
            /* When the previous char was 'F' (0x46) and this char is a digit
             * '1'..'8', start a new link gadget for that slot. */
            if (prev == 0x46 && c > 0x30 && c < 0x39) {
                struct Gadget *g = (struct Gadget *)PB(page, ngad * 0x34 + 0x1022);
                if (prev_gad != NULL)
                    prev_gad->NextGadget = g;
                g->NextGadget    = NULL;
                g->LeftEdge      = (WORD)((PW(page, 6) - 1) * 8 + 4);
                g->TopEdge       = (WORD)(PW(page, 4) * 8 + 10);
                g->Width         = 0x10;
                g->Height        = 8;
                g->Flags         = 3;        /* GADGHCOMP | GADGHBOX-ish (recon literal) */
                g->Activation    = 0x102;    /* RELVERIFY | GADGIMMEDIATE (recon literal)*/
                g->GadgetType    = 1;        /* BOOLGADGET (recon literal) */
                g->GadgetRender  = NULL;
                g->SelectRender  = NULL;
                g->GadgetText    = NULL;
                g->MutualExclude = 0;
                g->SpecialInfo   = NULL;
                g->GadgetID      = (WORD)(c - 0x31);   /* link slot index */
                g->UserData      = NULL;
                /* +0x2c handler = link_follow; +0x30 = page back-pointer. */
                *(APTR *)((UBYTE *)g + 0x2c) = (APTR)link_follow;
                *(APTR *)((UBYTE *)g + 0x30) = page;
                ngad++;
                prev_gad = g;
            }
            render_char(c, page);
            if (c == 0x0d)
                row++;
            prev = c;
            if (row >= 2)          /* two CRs end the menu section */
                break;
            c = frame_rle_getchar();
        } while (c != 0);

        if (ngad != 0)
            AddGList(*(struct Window **)p, (struct Gadget *)PB(page, 0x1022), -1, -1, NULL);

        /* --- Section 2b: link-code assignments ("<digit>=<code>") -------- */
        while (c != 0) {
            WORD slot;
            c = frame_rle_getchar();
            if (c == 0)
                goto info_line;
            slot = (WORD)(c - 0x31);
            if (slot >= 0 && slot < 8) {
                c = frame_rle_getchar();
                if (c == 0x3d) {           /* '=' : read up to 6 code chars */
                    idx = 0;
                    for (;;) {
                        c = frame_rle_getchar();
                        if (c == 0 || c == 0x0d)
                            break;
                        if (idx < 6) {
                            *PB(page, idx + slot * 7 + 0x790) = c;
                            idx++;
                        }
                    }
                    *PB(page, idx + slot * 7 + 0x790) = 0;
                    continue;
                }
            }
            /* Not an assignment — skip to end of line. */
            while (c != 0 && c != 0x0d)
                c = frame_rle_getchar();
        }
    }

info_line:
    /* --- Section 3: the info line (rows 8..0x1d, pen 1) ------------------ */
    c = frame_rle_getchar();
    if (c != '\0') {
        frame_clear_region(7, 1, 8, 0x1d, page);
        frame_set_cursor(7, 1, page);
        frame_pen_upper(page);
        do {
            render_char(c, page);
            if (c == '\r')
                frame_advance_cursor(page);
            c = frame_rle_getchar();
        } while (c != '\0');
    }

    /* --- Section 4: page-number table (+0x7c8, rows of 9 bytes) ---------- */
    c = frame_rle_getchar();
    if (c != '\0') {
        row = 0;
        do {
            ngad = 0;   /* column index (local_6) */
            do {
                if (ngad < 8) {
                    *PB(page, ngad + row * 9 + 0x7c8) = c;
                    ngad++;
                }
                c = frame_rle_getchar();
            } while (c != '\0' && c != '\r' && c != ',');
            for (; ngad < 8; ngad++)
                *PB(page, ngad + row * 9 + 0x7c8) = 0x20;
            *PB(page, ngad + row * 9 + 0x7c8) = 0;
            if (c == '\0' || c == '\r')
                break;
            c = frame_rle_getchar();
            row++;
        } while (c != '\0');
        PW(page, 0xc72) = row + 1;
        while (c != '\0')
            c = frame_rle_getchar();
    }

    /* --- Reset selection, draw the number column, then the body rows ----- */
    PW(page, 0xc74) = 0;
    frame_set_cursor(7, 0x1f, page);
    frame_pen_upper(page);
    frame_write_string(PB(page, 0x7c8), page);

    /* --- Section 5: body rows (+0x810, stride 0x66) --------------------- */
    c = frame_rle_getchar();
    if (c != '\0') {
        frame_set_cursor(10, 1, page);
        frame_pen_lower(page);
        row = 0;
        do {
            /* col A: 6 chars + NUL (+0x810) */
            for (ngad = 0; ngad < 6; ngad++) {
                *PB(page, ngad + row * 0x66 + 0x810) = c;
                c = frame_rle_getchar();
            }
            *PB(page, ngad + row * 0x66 + 0x810) = 0;
            /* col B: 16 chars + NUL (+0x817) */
            for (ngad = 0; ngad < 0x10; ngad++) {
                *PB(page, ngad + row * 0x66 + 0x817) = frame_rle_getchar();
            }
            *PB(page, ngad + row * 0x66 + 0x817) = 0;
            /* skip one separator */
            frame_rle_getchar();
            /* col C: up to ',' then pad to 5 + NUL (+0x828) */
            ngad = 0;
            for (;;) {
                c = frame_rle_getchar();
                if (c == ',')
                    break;
                *PB(page, ngad + row * 0x66 + 0x828) = c;
                ngad++;
            }
            for (; ngad < 5; ngad++)
                *PB(page, ngad + row * 0x66 + 0x828) = 0x20;
            *PB(page, ngad + row * 0x66 + 0x828) = 0;
            /* sub-rows: 8 fields of 9 bytes, comma/CR separated (+0x82e) */
            ngad = 0;   /* sub-row (local_6) */
            crlf = 0;   /* col within sub-row (local_8) */
            do {
                c = frame_rle_getchar();
                if (c == '\r' || c == ',') {
                    for (; crlf < 8; crlf++)
                        *PB(page, crlf + ngad * 9 + row * 0x66 + 0x82e) = 0x20;
                    *PB(page, crlf + ngad * 9 + row * 0x66 + 0x82e) = 0;
                    ngad++;
                    crlf = 0;
                } else if (crlf < 8) {
                    *PB(page, crlf + ngad * 9 + row * 0x66 + 0x82e) = c;
                    crlf++;
                }
            } while (c != '\r');

            /* Draw the four columns of this row (recon toggles +6 between them). */
            PW(page, 6) = 1;
            frame_write_string(PB(page, row * 0x66 + 0x810), page);
            PW(page, 6)++;
            frame_write_string(PB(page, row * 0x66 + 0x817), page);
            PW(page, 6)++;
            frame_write_string(PB(page, row * 0x66 + 0x828), page);
            PW(page, 6) = 0x1f;
            frame_write_string(PB(page, row * 0x66 + 0x82e), page);
            frame_row_newline(page);
            frame_pen_upper(page);
            row++;
            c = frame_rle_getchar();
        } while (c != '\0');
        PW(page, 0xc76) = row;
    }

    /* Mark "no current page", then draw the initial selection highlight. */
    PW(page, 0xc78) = (WORD)0xffff;
    dir_select((APTR)PB(page, 0xc7a), 0);
}
