/*
 * ui_state.c — connection-state UI update (reconstructed, faithful).
 *
 *   set_connection_state (FUN_001023ec) — when g_state or g_online changes, retitle
 *       every window, then enable/disable the main menu items and the directory- and
 *       frame-window gadgets appropriate to the new state. Called at the top of the
 *       event loop each pass.
 *   menu_enable      (FUN_0010227c) — walk a [menu-number, flag] table (stride 6,
 *       0xffff-terminated) calling OnMenu/OffMenu on the main window.
 *   dir_gadgets_enable  (FUN_001022bc) — for directory rows 0..4, OnGadget/OffGadget
 *       the row's gadget (dir_page + row*0x34 + 0xeb6) per an enable byte table,
 *       skipping any already in the desired state (GADGDISABLED bit at +0xec2 & 0x100).
 *   frame_gadgets_enable(FUN_00102354) — same for frame rows 0..5, gadgets at
 *       frame_page + row*0x34 + 0x790 (state bit at +0x79c).
 *
 * The title strings and the per-state enable tables all live in the extracted data
 * blob (their &DAT_0011d2xx..d4xx addresses); we drive them by blob offset. This
 * replaces the earlier title-only approximation in navigate.c.
 *
 * TRANSCRIPTION: control flow + the exact table addresses and gadget offsets are from
 * the recon (FUN_001023ec) and the raw m68k listing of the three helpers
 * ($10227c / $1022bc / $102354). OnMenu/OffMenu/OnGadget/OffGadget are the KS1.3
 * Intuition vectors the thunks resolve to.
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/intuition_protos.h>

#include "compunet.h"

extern APTR  g_window;       /* DAT_001200fc — main window            */
extern APTR  g_frame_page;   /* DAT_0011d078 — frame page (page[0]=win)*/
extern APTR  g_dir_page;     /* DAT_0011d07c — directory page          */
extern LONG g_state;        /* DAT_0011d070 */
extern LONG g_online;       /* DAT_0011d074 */
extern LONG g_state_shadow; /* DAT_0011d46e */
extern LONG g_online_shadow;/* DAT_0011d472 */

extern void  ui_set_title(const char *title);   /* FUN_0010217a (ui.c) */

extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

/* Title strings (in the blob). */
#define S_OFFLINE    "Compunet - offline"
#define S_LOGGING    "Compunet - logging on"
#define S_ONLINE     "Compunet - online"
#define S_COURIER    "Compunet - courier"
#define S_UPLOAD     "Send to upload, Done to finish"
#define S_NEWDIR     "Dir or Goto for new directory"

/*
 * menu_enable — recon FUN_0010227c. Each table entry is 6 bytes: a 32-bit menu
 * number at +0 followed by a 16-bit enable flag at +4; a number of 0xffff (as a
 * LONG) terminates. flag != 0 -> OnMenu, else OffMenu. (The disassembly reads the
 * number with move.l / cmpi.l #$ffff and the flag with tst.w $4(a0), stride 6 —
 * an earlier reconstruction wrongly read the number as a 16-bit word, which fed
 * garbage menu numbers to OnMenu and crashed on the first event-loop pass.)
 */
static void menu_enable(const UBYTE *tab)
{
    for (;;) {
        ULONG num  = *(ULONG *)(tab + 0);
        UWORD flag = *(UWORD *)(tab + 4);
        if (num == 0xffff)
            return;
        if (flag)
            OnMenu((struct Window *)g_window, num);
        else
            OffMenu((struct Window *)g_window, num);
        tab += 6;
    }
}

/*
 * dir_gadgets_enable — recon FUN_001022bc. For each of directory rows 0..4, an enable
 * byte in 'want' (want[row] != 0 => enabled). The row's gadget is at
 * dir + row*0x34 + 0xeb6; its current state is the GADGDISABLED bit (0x100) of the
 * Flags word at +0xec2. Only toggle when it differs from what we want.
 */
static void dir_gadgets_enable(APTR dir, const UBYTE *want)
{
    struct Window *win = *(struct Window **)dir;
    int row;
    for (row = 0; row < 5; row++) {
        struct Gadget *g = (struct Gadget *)((UBYTE *)dir + row * 0x34 + 0xeb6);
        UWORD flags = *(UWORD *)((UBYTE *)dir + row * 0x34 + 0xec2);
        if (want[row]) {
            if (flags & 0x100)                 /* currently disabled -> enable */
                OnGadget(g, win, NULL);
        } else {
            if (!(flags & 0x100))              /* currently enabled -> disable */
                OffGadget(g, win, NULL);
        }
    }
}

/*
 * frame_gadgets_enable — recon FUN_00102354. Same as above for frame rows 0..5,
 * gadgets at frame + row*0x34 + 0x790, state bit at +0x79c.
 */
static void frame_gadgets_enable(APTR frame, const UBYTE *want)
{
    struct Window *win = *(struct Window **)frame;
    int row;
    for (row = 0; row < 6; row++) {
        struct Gadget *g = (struct Gadget *)((UBYTE *)frame + row * 0x34 + 0x790);
        UWORD flags = *(UWORD *)((UBYTE *)frame + row * 0x34 + 0x79c);
        if (want[row]) {
            if (flags & 0x100)
                OnGadget(g, win, NULL);
        } else {
            if (!(flags & 0x100))
                OffGadget(g, win, NULL);
        }
    }
}

/*
 * set_connection_state — recon FUN_001023ec. Retitle + re-enable menus/gadgets when
 * the (state, online) pair changes. Table offsets are the recon's &DAT_ addresses.
 */
void set_connection_state(void)
{
    if (g_state_shadow == g_state && g_online_shadow == g_online)
        return;
    g_online_shadow = g_online;
    g_state_shadow  = g_state;

    /* Title + main-menu enable table, per state. */
    switch (g_state) {
    case 0:
        menu_enable((UBYTE *)DATA(0x11d236));
        ui_set_title(S_OFFLINE);
        break;
    case 1:
        ui_set_title(S_LOGGING);
        menu_enable((UBYTE *)DATA(0x11d26c));
        break;
    case 2:
    case 3:
        ui_set_title(S_ONLINE);
        menu_enable((UBYTE *)DATA(g_online == 0 ? 0x11d2a2 : 0x11d302));
        break;
    case 5:
    case 6:
        ui_set_title(S_COURIER);
        menu_enable((UBYTE *)DATA(0x11d3c6));
        break;
    case 4:  /* state 4 mirrors state 7 (recon jump table: both -> 0x1024c4) */
    case 7:
        ui_set_title(S_UPLOAD);
        menu_enable((UBYTE *)DATA(0x11d420));
        break;
    case 8:
        ui_set_title(S_NEWDIR);
        menu_enable((UBYTE *)DATA(0x11d356));
        break;
    default:
        break;
    }

    /* Directory-window gadget enable, per state. */
    if (g_dir_page != NULL) {
        switch (g_state) {
        case 2:
            dir_gadgets_enable(g_dir_page, (UBYTE *)DATA(g_online == 0 ? 0x11d2f6 : 0x11d3aa));
            break;
        case 3:
            dir_gadgets_enable(g_dir_page, (UBYTE *)DATA(0x11d3af));
            break;
        case 5:
        case 6:
            dir_gadgets_enable(g_dir_page, (UBYTE *)DATA(0x11d41a));
            break;
        case 4:  /* state 4 mirrors state 7 (recon jump table: both -> 0x102552) */
        case 7:
            dir_gadgets_enable(g_dir_page, (UBYTE *)DATA(0x11d450));
            break;
        case 8:
            dir_gadgets_enable(g_dir_page, (UBYTE *)DATA(0x11d3ba));
            break;
        default:
            break;                   /* cases 0/1: no dir gadget change */
        }
    }

    /* Frame-window gadget enable, per state. */
    if (g_frame_page != NULL) {
        switch (g_state) {
        case 0:
            frame_gadgets_enable(g_frame_page, (UBYTE *)DATA(0x11d266));
            break;
        case 1:
            frame_gadgets_enable(g_frame_page, (UBYTE *)DATA(0x11d29c));
            break;
        case 2:
        case 5:
        case 6:
        case 8:
            frame_gadgets_enable(g_frame_page, (UBYTE *)DATA(0x11d2fb));
            break;
        case 3:
            frame_gadgets_enable(g_frame_page, (UBYTE *)DATA(0x11d3b4));
            break;
        case 4:
        case 7:
            frame_gadgets_enable(g_frame_page, (UBYTE *)DATA(0x11d3bf));
            break;
        default:
            break;
        }
    }
}
