/*
 * directory_select.c — directory row selection + highlight (reconstructed).
 *
 *   dir_select       (FUN_0010935a) — the directory selection gadget's handler.
 *       Installed as the handler for the page's selection gadget (page+0xca6). On a
 *       plain move (mode 0) it un-highlights the previously selected row and
 *       highlights the target row (the gadget's GadgetID). When invoked with a click
 *       count (mode 1/2) AND the connection is in a navigable state, it instead runs
 *       the row's action (goto page / download / validate login) with a lock/unlock
 *       highlight around it.
 *   directory_repaint(FUN_001096c8) — redraw the selected number/name columns,
 *       toggling the highlight box on the current row. (The earlier reconstruction
 *       in ui.c approximated this with a full frame_redraw.)
 *
 * TRANSCRIPTION: control flow from the Ghidra decompile (FUN_0010935a / FUN_001096c8),
 * with every structure offset and the RectFill/SetDrMd coordinates confirmed against
 * the raw m68k listing of $10935a..$10951e and $1096c8. The RastPort is the page's
 * window's RPort: rp = ((Window*)page[0])->RPort, i.e. *(*(APTR*)page + 0x32).
 *
 * Highlight geometry (COMPLEMENT-mode RectFill on rp):
 *   number column: x 0x0c..0xf3,  name column: x 0xfc..0x13b
 *   y = row*8 + 0x5a .. row*8 + 0x61
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/graphics_protos.h>
#include <clib/intuition_protos.h>

#include "compunet.h"

extern APTR GfxBase;
extern LONG g_state;           /* DAT_0011d070 */

extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

/* Row actions dispatched on a click while navigable (recon FUN_0010956c/963c/a484). */
extern LONG goto_page(void);       /* FUN_0010a1e2 — state 2/3, click 1 */
extern LONG download_check(void);  /* FUN_0010b730 — state 2/3, click 2 */
extern LONG hook_dir_0963c(APTR gadget);   /* dispatch.c — the Dnld action hook */
/* ⚠ FUN_0010e0fc is mail_download, not "validate_login" — state 5 is COURIER
 * (ui_state.c maps 5/6 to "Compunet - courier"). It was reconstructed TWICE under
 * two names; the duplicate in login.c is gone. See #131. */
extern LONG mail_download(void);   /* FUN_0010e0fc — state 5 (Courier), click 2 */
extern void link_lock(APTR dir_page, int row);   /* FUN_00109520 — toggle row box */

/* Frame text primitives (frame.c). */
extern void frame_set_cursor(WORD row, WORD col, APTR page); /* FUN_001056aa */
extern void frame_pen_upper(APTR page);                      /* FUN_0010506a */
extern void frame_pen_lower(APTR page);                      /* FUN_00105022 */
extern void frame_write_string(UBYTE *text, APTR page);        /* FUN_0010565e */

#define PAGE_OF(gad)   (*(APTR  *)((UBYTE *)(gad) + 0x30))
#define GAD_ROW(gad)   (*(WORD  *)((UBYTE *)(gad) + 0x26))
#define WIN_RP(page)   (*(struct RastPort **)((UBYTE *)*(APTR *)(page) + 0x32))
#define PW(p, off)     (*(WORD *)((UBYTE *)(p) + (off)))
#define PB(p, off)     ((UBYTE *)(p) + (off))

/* Draw (COMPLEMENT) the two highlight boxes for row 'r' on the page's RastPort. */
static void hilite_row(APTR page, WORD r)
{
    struct RastPort *rp = WIN_RP(page);
    LONG y0 = r * 8 + 0x5a;
    LONG y1 = r * 8 + 0x61;
    SetDrMd(rp, COMPLEMENT);
    RectFill(rp, 0x0c, y0, 0xf3, y1);   /* number column */
    RectFill(rp, 0xfc, y0, 0x13b, y1);  /* name column   */
}

/*
 * dir_select — recon FUN_0010935a. param is the selection gadget; mode is the click
 * count from the event loop (0 = programmatic move). Returns 1 on a highlight move,
 * the action's result on a click dispatch, 0 if the target row is out of range.
 */
LONG dir_select(APTR gadget, LONG mode)
{
    WORD  target = GAD_ROW(gadget);          /* -$2 : the gadget's GadgetID = row  */
    APTR  page   = PAGE_OF(gadget);          /* -$8 : the directory page           */
    WORD  old;

    if (target >= PW(page, 0xc76))           /* beyond the last body row -> nothing */
        return 0;

    /* A real click while navigable: run the row's action, not a highlight move. */
    if (mode != 0 && g_state >= 2) {
        switch (g_state) {
        case 2:
        case 3:
            /* ⚠ THROUGH THE ROW'S ACTION GADGET, not straight to the handler. The
             * original passes the gadget at page+0xf52 to the Dnld hook, which wraps the
             * call in link_lock() either side — that is what shows the busy state while
             * the download runs. Calling download_check() bare skipped the lock:
             *   1093ba  movea.l -$8(a5), a0     ; the directory page
             *   1093be  adda.w  #$f52, a0       ; its Dnld action gadget
             *   1093c4  move.l  a0, -(a7)
             *   1093c6  bsr.w   $10963c         ; hook_dir_0963c -> download_check
             * Note the original dispatches BEFORE updating the highlight, so a
             * double-click acts on the row that was already selected — a real quirk,
             * preserved. */
            if (mode == 2) return hook_dir_0963c((UBYTE *)page + 0xf52);
            if (mode == 1) return goto_page();
            break;
        case 5:
            if (mode == 2) return mail_download();
            break;
        case 8:
            if (mode == 1) return goto_page();
            break;
        default:
            break;
        }
        /* Other state/click combinations fall through to a plain highlight move. */
    }

    /* Un-highlight the previously selected row (if any), then highlight the new. */
    old = PW(page, 0xc78);
    if (old >= 0)
        hilite_row(page, old);
    PW(page, 0xc78) = target;
    hilite_row(page, target);
    return 1;
}

/*
 * directory_repaint — recon FUN_001096c8. Redraw the highlighted row's number and
 * name/sub-row columns and re-stroke the highlight box. Uses page fields +0xc74
 * (selected row, "31d"), +0xc76 (row count), and +0xc78/"31e" (highlight row).
 */
void directory_repaint(APTR page)
{
    WORD sel   = PW(page, 0xc74);   /* param_1[0x31d] — selected row      */
    WORD nrows = PW(page, 0xc76);   /* row count                          */
    WORD hi    = PW(page, 0xc78);   /* param_1[0x31e] — highlight row      */
    struct RastPort *rp = WIN_RP(page);
    WORD i;

    /* Clear the old highlight box on the name column. */
    SetDrMd(rp, COMPLEMENT);
    RectFill(rp, 0xfc, hi * 8 + 0x5a, 0x13b, hi * 8 + 0x61);

    /* Redraw the selected page number (row 7) and its first sub-row (row 10). */
    frame_set_cursor(7, 0x1f, page);
    frame_pen_upper(page);
    frame_write_string(PB(page, sel * 9 + 0x7c8), page);
    frame_set_cursor(10, 0x1f, page);
    frame_pen_lower(page);
    frame_write_string(PB(page, sel * 9 + 0x82e), page);
    frame_pen_upper(page);
    for (i = 1; i < nrows; i++) {
        frame_set_cursor(i + 10, 0x1f, page);
        frame_write_string(PB(page, sel * 9 + i * 0x66 + 0x82e), page);
    }

    /* Re-stroke the highlight box. */
    SetDrMd(rp, COMPLEMENT);
    RectFill(rp, 0xfc, hi * 8 + 0x5a, 0x13b, hi * 8 + 0x61);
}

/* The action-gadget handlers are C functions in dispatch.c, so the +0x2c handler slot must
 * point at OUR hooks, not the blob's original code addresses (the 0x11e376/0x11e3da and
 * 0x11e2da/0x11e33e tables). The IntuiText LABELS stay in the blob (they are data); only the
 * code pointers are substituted. Mail row order: Done/ID/More/Dnld/Upld; directory row order:
 * Dir/Back/Goto/Dnld/Upld. */
extern LONG hook_nav_0a3d0(APTR), hook_nav_0a3f8(APTR), hook_nav_0a43e(APTR),
            hook_nav_0a484(APTR), hook_nav_0a4ca(APTR);   /* mail: Done/ID/More/Dnld/Upld */
extern LONG hook_dir_0956c(APTR), hook_dir_095b0(APTR), hook_dir_095f6(APTR),
            hook_dir_0963c(APTR), hook_dir_09682(APTR);   /* dir:  Dir/Back/Goto/Dnld/Upld */

static APTR const g_mail_gadget_handlers[5] = {
    (APTR)hook_nav_0a3d0, (APTR)hook_nav_0a3f8, (APTR)hook_nav_0a43e,
    (APTR)hook_nav_0a484, (APTR)hook_nav_0a4ca,
};
static APTR const g_dir_gadget_handlers[5] = {
    (APTR)hook_dir_0956c, (APTR)hook_dir_095b0, (APTR)hook_dir_095f6,
    (APTR)hook_dir_0963c, (APTR)hook_dir_09682,
};

/* mail_relabel — shared body of mail_state_enter/exit: RemoveGList the 5 action gadgets, set
 * each one's GadgetText (+0x1a) from the label blob table and its handler (+0x2c) from the C
 * hook table, then AddGList + RefreshGList. */
static void mail_relabel(APTR dir, ULONG label_tbl, APTR const *handlers)
{
    struct Window *win  = *(struct Window **)dir;
    struct Gadget *list = (struct Gadget *)((UBYTE *)dir + 0xf86);
    UWORD pos;
    int   row;

    pos = RemoveGList(win, list, 5);
    for (row = 0; row < 5; row++) {
        struct Gadget *g = (struct Gadget *)((UBYTE *)dir + row * 0x34 + 0xeb6);
        g->GadgetText = (struct IntuiText *)DATA(label_tbl + row * 0x14);
        *(APTR *)((UBYTE *)g + 0x2c) = handlers[row];
    }
    AddGList(win, list, pos, 5, NULL);
    RefreshGList(list, win, NULL, 5);
}

/*
 * mail_state_enter — recon FUN_001091f2. Re-label the 5 directory action gadgets for
 * mail/courier mode: labels from the blob mail table (0x11e376, stride 0x14 = Done/ID/More/
 * Dnld/Upld), handlers to our mail hooks. (The original binds the 0x11e3da code table; we
 * substitute the reconstructed C hooks — see mail_relabel.)
 */
void mail_state_enter(APTR dir)
{
    mail_relabel(dir, 0x11e376, g_mail_gadget_handlers);
}

/*
 * mail_state_exit — recon FUN_001092a6. Restore the directory action gadgets when leaving
 * Courier (called by mail_done): labels from the blob directory table (0x11e2da = Dir/Back/
 * Goto/Dnld/Upld), handlers back to our directory hooks.
 */
void mail_state_exit(APTR dir)
{
    mail_relabel(dir, 0x11e2da, g_dir_gadget_handlers);
}
