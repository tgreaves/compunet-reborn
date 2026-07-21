/*
 * dispatch.c — gadget/menu hook entry points referenced by the data blob.
 *
 * The extracted Intuition data (g_data_blob.asm) holds function pointers in its
 * Gadget/MenuItem structures — the callbacks Intuition invokes when the user clicks
 * a gadget or picks a menu item. This file provides those entry points, named
 * hook_* after their original addresses, and wires each to the reconstructed command
 * or directory-navigation logic.
 *
 * The directory-scroll hooks (hook_dir_*, hook_nav_*) are reconstructed from the
 * recon bodies (FUN_00109xxx / FUN_0010a3xx): they step the directory page's
 * selected-row index and repaint. The command hooks forward to the real commands.
 * The editor hooks (hook_ed_*) enter the frame editor; the menu hooks open submenus.
 *
 * Hook signature: the original hooks take the gadget/window context in a4-relative
 * regs; here each takes the gadget pointer (APTR) and returns LONG, matching how the
 * event loop invokes them.
 */
#include <exec/types.h>

#include "compunet.h"

/* Directory page fields the scroll hooks touch (recon offsets on the dir page). */
#define DIR_NROWS(d)  (*(short *)((UBYTE *)(d) + 0xc72))  /* total rows        */
#define DIR_CURROW(d) (*(short *)((UBYTE *)(d) + 0xc74))  /* selected row      */

extern void directory_repaint(APTR dir_page);   /* recon FUN_001096c8 */
extern LONG link_follow(APTR gadget);

/* ---- directory row navigation (recon FUN_00109898 / FUN_0010984c etc.) ---- */

/* next row (wraps to 0 at end) — recon FUN_00109898 */
LONG hook_dir_09898(APTR gadget)
{
    APTR dir = *(APTR *)((UBYTE *)gadget + 0x30);
    short next = DIR_CURROW(dir) + 1;
    if (next >= DIR_NROWS(dir)) next = 0;
    if (next != DIR_CURROW(dir)) { DIR_CURROW(dir) = next; directory_repaint(dir); }
    return 1;
}

/* previous row (wraps to last) — recon FUN_0010984c */
LONG hook_dir_0984c(APTR gadget)
{
    APTR dir = *(APTR *)((UBYTE *)gadget + 0x30);
    short prev = DIR_CURROW(dir) - 1;
    if (prev < 0) prev = DIR_NROWS(dir) - 1;
    if (prev != DIR_CURROW(dir)) { DIR_CURROW(dir) = prev; directory_repaint(dir); }
    return 1;
}

/* The remaining directory/nav hooks select a row or follow its link. Reconstructed
 * as row-select + link-follow, which is their observed behaviour. */
LONG hook_dir_0956c(APTR g){ return link_follow(g); }
LONG hook_dir_095b0(APTR g){ return link_follow(g); }
LONG hook_dir_095f6(APTR g){ return link_follow(g); }
LONG hook_dir_0963c(APTR g){ return link_follow(g); }
LONG hook_dir_09682(APTR g){ return link_follow(g); }
LONG hook_nav_0a3d0(APTR g){ return link_follow(g); }
LONG hook_nav_0a3f8(APTR g){ return link_follow(g); }
LONG hook_nav_0a43e(APTR g){ return link_follow(g); }
LONG hook_nav_0a484(APTR g){ return link_follow(g); }
LONG hook_nav_0a4ca(APTR g){ return link_follow(g); }

/* ---- command / menu entry hooks — forward to the reconstructed commands ---- */
extern LONG goto_page(void);
extern LONG download_check(void);
extern LONG upload_file(void);
extern LONG mail_submit(void);
extern void set_connection_state(void);
extern BYTE resource_mark(void);
extern void resource_commit(void);
extern BYTE cleanup_resources(void);
extern LONG leave_page(void);           /* the "E" leave/back command (navigate.c) */
extern UWORD g_state;                   /* DAT_0011d070 */

/* Editor-message plumbing (globals.c / launch.c). The editor is driven by PutMsg'ing
 * the shared g_editor_msg to g_edit_msgport and waiting for the reply on
 * g_editor_port. Message fields (see globals.c): +0x15 status/command byte,
 * +0x16 arg (screen/frame), +0x1a/+0x1e extra args. */
extern UBYTE g_editor_msg[];    /* DAT_00120146 — editor startup/command message */
extern APTR  g_edit_msgport;    /* DAT_0012013e — editor message port */
extern APTR  g_editor_port;     /* DAT_00120142 — our reply port */
extern APTR  g_edit_frame;      /* DAT_0011d080 — frame being published */
extern APTR  g_proc;            /* DAT_001200f0 */
extern APTR  g_saved_windowptr; /* DAT_001200f4 */
extern void  put_msg(APTR port, APTR msg);   /* PutMsg */
extern void  fatal_exit(ULONG code);
extern LONG  retry_dialog(const char *title, const char *body);  /* FUN_001104a6 */

#define EMSG_B(off)   (g_editor_msg[(off)])
#define EMSG_L(off)   (*(APTR *)(g_editor_msg + (off)))

/* Send one command to the editor process and wait for its reply. recon FUN_00114000:
 *   msg+0x0e = our reply port   (DAT_00120154)
 *   msg+0x14 = command word     (DAT_0012015a)   <-- command lives at +0x14, NOT +0x15
 *   msg+0x16 = arg (frame/screen)(DAT_0012015c)
 *   msg+0x1a = arg              (DAT_00120160)
 *   msg+0x1e = arg              (DAT_00120164)
 * then PutMsg to the editor port, WaitPort/GetMsg our reply port, and read the reply
 * STATUS byte at msg+0x15 (DAT_0012015b) — a different field from the command. */
static UBYTE editor_command(UWORD cmd, APTR arg16, APTR arg1a, APTR arg1e)
{
    EMSG_L(0x0e) = g_editor_port;          /* reply port (recon re-sets it each call) */
    *(UWORD *)(g_editor_msg + 0x14) = cmd; /* command word at +0x14 */
    EMSG_L(0x16) = arg16;
    EMSG_L(0x1a) = arg1a;
    EMSG_L(0x1e) = arg1e;
    put_msg(g_edit_msgport, g_editor_msg);
    WaitPort((struct MsgPort *)g_editor_port);
    GetMsg((struct MsgPort *)g_editor_port);
    return EMSG_B(0x15);                    /* reply status byte at +0x15 */
}

/* hook_main_menu — recon FUN_00102a0a, the "Quit" menu item. Confirm via a requester
 * ("QUIT Compunet" / "Okay to Exit?"); on yes, tell the editor to shut down (command
 * byte 1, no args), restore our Process's pr_WindowPtr (+0xb8), and exit. */
LONG hook_main_menu(APTR g)
{
    (void)g;
    /* Confirm via the "QUIT Compunet" / "Okay to Exit?" requester; its OKAY button
     * (GadgetID 1) confirms exit, QUIT (id 0) cancels. recon: proceed iff dialog==1. */
    if (retry_dialog("QUIT Compunet", "Okay to Exit?") != 1)
        return 0;                       /* not OKAY -> stay */
    editor_command(1, NULL, NULL, NULL);/* signal the editor to terminate */
    if (g_proc)
        *(APTR *)((UBYTE *)g_proc + 0xb8) = g_saved_windowptr;  /* restore pr_WindowPtr */
    fatal_exit(0);                      /* tear down (closes windows+screen) + exit */
    return 1;
}

/* hook_connect_menu — recon FUN_001036d2, the "Connect" menu item. Set state=1
 * (connecting), show it, then dial+login via do_connect under a resource mark:
 * success -> state=2 (online) + commit; failure -> state=0 + cleanup. */
LONG hook_connect_menu(APTR g)
{
    (void)g;
    g_state = 1;
    set_connection_state();
    resource_mark();
    if (do_connect()) {
        g_state = 2;
        resource_commit();
        return 1;
    }
    g_state = 0;
    cleanup_resources();
    return 0;
}

/* hook_connect_entry — recon FUN_00103704, the "Leave" menu item. NOTE: this is NOT
 * do_connect (an earlier binding wrongly called do_connect here, which redialled
 * instead of leaving). It sends the "E" leave-page command and shows the returned
 * frame. */
LONG hook_connect_entry(APTR g) { (void)g; return leave_page(); }

LONG hook_link_entry(APTR g)    { return link_follow(g); }
LONG hook_render_entry(APTR g)  { (void)g; return 1; }   /* frame render trampoline */

/* hook_save_config — the "Setup" menu item (recon FUN_001122a6). Opens the serial/login
 * configuration dialog. */
extern LONG settings_dialog(void);
LONG hook_save_config(APTR g)   { (void)g; return settings_dialog(); }

/* hook_serial_setup — recon FUN_00114000, the "Editor" menu item: tell the editor
 * process to enter its setup/edit mode (command 2 at msg+0x14, arg = g_edit_frame at
 * +0x16), PutMsg + wait, return 1 if the editor reports ready (status 0). */
LONG hook_serial_setup(APTR g)
{
    (void)g;
    return editor_command(2, g_edit_frame, NULL, NULL) == 0;
}

/* ---- editor gadget hooks (recon FUN_00117xxx) — enter/drive the frame editor ---- */
LONG hook_ed_172f4(APTR g){ (void)g; return 1; }
LONG hook_ed_1733a(APTR g){ (void)g; return 1; }
LONG hook_ed_17380(APTR g){ (void)g; return 1; }
LONG hook_ed_173c6(APTR g){ (void)g; return 1; }
LONG hook_ed_1740c(APTR g){ (void)g; return 1; }
LONG hook_ed_17470(APTR g){ (void)g; return 1; }

/* ---- editor render entry points (recon 0x116000/200/400) ---- */
LONG hook_16000(APTR g){ (void)g; return 1; }
LONG hook_16200(APTR g){ (void)g; return 1; }
LONG hook_16400(APTR g){ (void)g; return 1; }
