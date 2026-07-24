/*
 * launch_helpers.c — the tiny OS-call helpers launch_tty() brings up (reconstructed).
 *
 *   load_screen_palette   (FUN_0012a01c thunk) — graphics.library LoadRGB4 into the
 *                         screen's ViewPort.
 *   find_task             (FUN_0012907c thunk) — exec.library FindTask.
 *   set_menu_strip_tracked(FUN_0011a588)       — SetMenuStrip(window, menu) and
 *                         register a tracked ClearMenuStrip(window) so cleanup
 *                         detaches the strip before the window closes.
 *
 * Each is a single library vector (plus, for the menu strip, a resource-tracker
 * registration), matching the original's amiga.lib-style thunks. Verified against
 * the recon disassembly: launch_tty ($10271e) calls LoadRGB4 with (&screen->ViewPort,
 * &DAT_0011d0c2, 16); FindTask is $1027b0 with a NULL arg; SetMenuStrip is $102796.
 */
#include <exec/types.h>
#include <exec/nodes.h>
#include <exec/lists.h>
#include <exec/ports.h>
#include <clib/exec_protos.h>
#include <clib/graphics_protos.h>
#include <clib/intuition_protos.h>
#include <intuition/intuition.h>

/* Registered ClearMenuStrip tracker (resources.c, recon FUN_0011a16c). */
extern void resource_register_free(void (*fn)(), APTR arg1, APTR arg2);

/* load_screen_palette — recon: LoadRGB4(viewport, colortable, count). */
void load_screen_palette(APTR viewport, APTR coltable, ULONG n)
{
    LoadRGB4((struct ViewPort *)viewport, (UWORD *)coltable, (WORD)n);
}

/* find_task — recon: FindTask(name); launch_tty passes NULL to get our own task. */
APTR find_task(APTR name)
{
    return (APTR)FindTask((STRPTR)name);
}

/*
 * set_menu_strip_tracked — recon FUN_0011a588: SetMenuStrip(win, menu), then register
 * a tracked ClearMenuStrip(win) (freefn = ClearMenuStrip, arg1 = win) so the resource
 * unwinder detaches the strip on cleanup/exit before the window is closed.
 */
void set_menu_strip_tracked(APTR win, APTR menu)
{
    SetMenuStrip((struct Window *)win, (struct Menu *)menu);
    resource_register_free((void (*)())ClearMenuStrip, win, 0);
}

/*
 * unshare_user_port — recon FUN_0011a5d0. Detach a window that had been sharing
 * another window's UserPort: under Forbid(), drain (Remove + ReplyMsg) any messages
 * on the shared port that were addressed to this window (IntuiMessage->IDCMPWindow
 * at msg+0x2c), clear the window's UserPort (win+0x56), and ModifyIDCMP(win, 0).
 * Registered as the cleanup for share_user_port.
 */
static void unshare_user_port(struct Window *win)
{
    struct MsgPort *port = *(struct MsgPort **)((UBYTE *)win + 0x56);
    struct Node *n, *next;

    Forbid();
    if (port != NULL) {
        n = port->mp_MsgList.lh_Head;
        while ((next = n->ln_Succ) != NULL) {
            /* IntuiMessage->IDCMPWindow is at +0x2c (== node[0xb] as longs). */
            if (*(struct Window **)((UBYTE *)n + 0x2c) == win) {
                Remove(n);
                ReplyMsg((struct Message *)n);
            }
            n = next;
        }
    }
    *(APTR *)((UBYTE *)win + 0x56) = NULL;
    ModifyIDCMP(win, 0);
    Permit();
}

/*
 * share_user_port — recon FUN_0011a636. Make 'win' share 'port' as its UserPort
 * (win+0x56) if it doesn't already have one, and register unshare_user_port as the
 * tracked cleanup. Returns the port now in use.
 */
APTR share_user_port(APTR win, APTR port)
{
    APTR *slot = (APTR *)((UBYTE *)win + 0x56);
    if (*slot == NULL) {
        *slot = port;
        resource_register_free((void (*)())unshare_user_port, win, port);
    } else {
        port = *slot;
    }
    return port;
}
