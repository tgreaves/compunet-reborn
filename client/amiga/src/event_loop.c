/*
 * event_loop.c — the client's top level: main, the Intuition IDCMP loop, and the
 * abort/disconnect teardown (reconstructed, faithful).
 *
 *   client_main (FUN_001029e6) — launch_tty(), save the resource level, arm the
 *               abort setjmp (a longjmp from a transport error lands here and runs
 *               disconnect()), then enter the event loop, which never returns.
 *   event_loop  (FUN_00102814) — the main IDCMP loop: on each pass update the
 *               connection-state UI, drain+reply any queued messages, restore the
 *               pointer, WaitPort, then dispatch one message:
 *                 CLOSEWINDOW (0x200 == $400 here) — the "quit" path; loops back to
 *                             the top of the outer loop, where a RAWKEY $5f + Amiga
 *                             qualifier while online triggers a longjmp abort.
 *                 GADGETDOWN  (0x20)  — hit-test the gadget, use Intuition
 *                             DoubleClick() on the message's seconds/micros vs the
 *                             remembered last click to pass 0/1/2 (none/single/
 *                             double) to the gadget's own handler at gadget+0x2c.
 *                 MENUPICK    (0x100) — walk the command map (menu_dispatch) for the
 *                             menu-number and call the matching command handler.
 *   disconnect  (FUN_00102968) — unwind tracked resources back to the saved level,
 *               release the frame-editor semaphore + clear the edit-in-progress bit
 *               if a frame was being published, then zero all the session window /
 *               state handles so the next connection starts clean.
 *
 * TRANSCRIPTION NOTES: control flow from the Ghidra decompile (FUN_00102814 /
 * FUN_001029e6 / FUN_00102968); the message-field offsets, the IDCMP class values,
 * and the DoubleClick / longjmp calls were confirmed from the raw m68k listing of
 * $102814..$102964 (a4 = 0x11d000 small-data base). The IntuiMessage fields read are
 * Class(+0x14), Code(+0x18), Qualifier(+0x1a), IAddress(+0x1c), Seconds(+0x24),
 * Micros(+0x28) — the standard KS1.3 IntuiMessage layout.
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/exec_protos.h>
#include <clib/intuition_protos.h>
#include <setjmp.h>

#include "compunet.h"

extern APTR IntuitionBase;

/* Shared UI/session state (globals.c / launch.c). */
extern APTR  g_window;          /* DAT_001200fc — main window            */
extern APTR  g_main_uport;      /* DAT_00120100 — its UserPort           */
extern APTR  g_menu_pair[2];    /* DAT_001201ae/b2 — [menu list, cmd map]*/
extern ULONG g_jmpbuf[];        /* DAT_00120170 — abort jmp_buf          */
extern BYTE  g_res_saved_level; /* DAT_001201ac — resource level to unwind to */
extern UWORD g_state;           /* DAT_0011d070 — connection state       */

/* Last-click state for DoubleClick() (globals.c, recon DAT_0011d548/54c/550). */
extern ULONG g_click_secs;      /* DAT_0011d548 */
extern ULONG g_click_micros;    /* DAT_0011d54c */
extern APTR  g_click_win;       /* DAT_0011d550 */

/* Busy/normal pointer + connection-state repaint (ui.c / navigate.c). */
extern void set_wait_pointer(void);    /* FUN_001020ae */
extern void clear_wait_pointer(void);  /* FUN_0010221c */

/*
 * client_main — recon FUN_001029e6. The program's real top level (the runtime
 * startup tail-calls it once SysBase/a4 are set). launch_tty() brings up the whole
 * UI; we then remember the current resource nesting level and arm the abort setjmp.
 * A transport failure calls set_connection_error(code) == longjmp(g_jmpbuf, code),
 * which returns here non-zero and runs disconnect() before re-entering the loop.
 */

void client_main(void)
{
    launch_tty();
    g_res_saved_level = resource_mark();
    if (setjmp((void *)g_jmpbuf) != 0)
        disconnect();
    event_loop();     /* never returns */
}

/* IDCMP class values (KS1.3), used as raw longs to match the recon's cmpi.l. */
#define CLS_GADGETDOWN  0x0020
#define CLS_MENUPICK    0x0100
#define CLS_RAWKEY      0x0400
#define MENU_NULL       0xffff

/*
 * event_loop — recon FUN_00102814. An infinite loop; there is no quit path. Each
 * pass: refresh the connection-state UI, drain+reply queued messages, drop the busy
 * pointer, WaitPort for the next message, then dispatch it by IDCMP class. The
 * last-click stamp (seconds/micros/window) is written to the shared globals at the
 * end of every pass and read back by the GADGETDOWN double-click test on the next.
 */
void event_loop(void)
{

    for (;;) {
        struct IntuiMessage *msg;
        ULONG  cls, secs, micros;
        UWORD  code, qual;
        APTR   iaddr;

        /* Drain any pending messages, then block until one arrives. */
        for (;;) {
            set_connection_state();
            while ((msg = (struct IntuiMessage *)GetMsg((struct MsgPort *)g_main_uport)) != NULL)
                ReplyMsg((struct Message *)msg);
            clear_wait_pointer();
            WaitPort((struct MsgPort *)g_main_uport);
            msg = (struct IntuiMessage *)GetMsg((struct MsgPort *)g_main_uport);
            if (msg != NULL)
                break;
        }

        /* Snapshot the message, reply it, and show the busy pointer while we work. */
        cls    = msg->Class;                                   /* +0x14 */
        code   = msg->Code;                                    /* +0x18 */
        qual   = msg->Qualifier;                               /* +0x1a */
        iaddr  = msg->IAddress;                                /* +0x1c */
        secs   = msg->Seconds;                                 /* +0x24 */
        micros = msg->Micros;                                  /* +0x28 */
        ReplyMsg((struct Message *)msg);
        set_wait_pointer();

        if (cls == CLS_RAWKEY) {
            /* Left-Amiga (qualifier bit 6) + HELP (raw key $5f) while online aborts
             * the current operation: longjmp back to client_main's setjmp. */
            if (code == 0x5f && (qual & 0x40) && g_state != 0)
                set_connection_error(1);   /* == longjmp(g_jmpbuf, 1); no return */
        } else if (cls == CLS_GADGETDOWN) {
            struct Gadget *g = (struct Gadget *)iaddr;
            LONG clicks = 0;
            /* Double-click iff this gadget is the same IAddress as the previous
             * message's AND Intuition's DoubleClick() says the interval qualifies.
             * (g_click_win holds the last message's IAddress; see the loop tail.) */
            if ((APTR)g == g_click_win &&
                DoubleClick(g_click_secs, g_click_micros, secs, micros)) {
                /* qualifier bit 0 (shift) set => 2, else => 1. */
                clicks = (qual & 1) ? 2 : 1;
            }
            /* Dispatch to the gadget's own handler (fn ptr at gadget+0x2c). */
            (*(LONG (**)(struct Gadget *, LONG))((UBYTE *)g + 0x2c))(g, clicks);
        } else if (cls == CLS_MENUPICK && code != MENU_NULL) {
            menu_dispatch(g_menu_pair, code);
        }

        /* Loop tail (recon $102952): remember this message's click stamp for the
         * next GADGETDOWN double-click test — done for every message class. */
        g_click_secs   = secs;
        g_click_micros = micros;
        g_click_win    = iaddr;
    }
}

/*
 * disconnect — recon FUN_00102968. Unwind every tracked resource opened since the
 * saved mark, then reset the session. If a frame was being published (g_edit_frame),
 * take its process semaphore, clear the in-progress bit (+0x11 & ~4), release it.
 * Finally zero all the per-connection window/state handles.
 */
extern APTR g_edit_frame;       /* DAT_0011d080 — frame being published */
extern APTR g_edit_proc;        /* DAT_00120168 — the editor process     */
extern APTR g_dir_page;         /* DAT_0011d07c */
extern APTR g_frame_page;       /* DAT_0011d078 */
extern UWORD g_online;          /* DAT_0011d074 */

/* Extra session handles zeroed on disconnect (defined in globals.c). */
extern APTR g_logon_win_h;      /* DAT_0011d570 */
extern APTR g_courier_win;      /* DAT_00121650 */
extern APTR g_dir2_win;         /* DAT_00121698 */
extern APTR g_party_win;        /* DAT_0011fd70 */
extern APTR g_sess_a;           /* DAT_0011f120 */
extern APTR g_sess_b;           /* DAT_0011f124 */
extern APTR g_sess_c;           /* DAT_0011f128 */

void disconnect(void)
{
    /* Unwind tracked resources level-by-level back to the saved mark. */
    while ((BYTE)g_res_saved_level <= cleanup_resources())
        ;
    resource_mark();   /* re-enter the saved level for the next connection */

    if (g_edit_frame != NULL) {
        ObtainSemaphore((struct SignalSemaphore *)((UBYTE *)g_edit_proc + 0xe));
        *((UBYTE *)g_edit_frame + 0x11) &= (UBYTE)~0x04;
        ReleaseSemaphore((struct SignalSemaphore *)((UBYTE *)g_edit_proc + 0xe));
        g_edit_frame = NULL;
    }

    g_online       = 0;
    g_dir_page     = NULL;
    g_logon_win_h  = NULL;
    g_frame_page   = NULL;
    g_courier_win  = NULL;
    g_dir2_win     = NULL;
    g_party_win    = NULL;
    g_sess_a       = NULL;
    g_sess_b       = NULL;
    g_sess_c       = NULL;
    g_state        = 0;
}
