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

/* ---- directory ACTION gadgets: "Dir / Back / Goto / Dnld / Upld" ---------------
 * recon FUN_0010956c / 95b0 / 95f6 / 963c / 09682. Each reads its dir page (gad+0x30)
 * and row (gad+0x26), toggles the row-highlight box (link_lock) around its command,
 * and returns the command's result. These are the on-screen navigation buttons in the
 * directory window; "Dir" is the top-directory request (goto_page -> "P00" while
 * offline), the Amiga equivalent of the C64's typed DIR.
 * NOTE: an earlier reconstruction wrongly stubbed all five as link_follow(). */
extern LONG goto_page(void);        /* FUN_0010a1e2 — "Dir":  P00 / P<n>            */
extern LONG back_dir(void);         /* FUN_0010a29a — "Back": send "B"              */
extern LONG link_goto(void);        /* FUN_0010a310 — "Goto": Goto-Page dialog + L  */
extern LONG download_check(void);   /* FUN_0010b730 — "Dnld"                        */
extern LONG put_frame(void);        /* FUN_0010c2f8 — "Upld": publish orchestrator   */
                                    /* (dialog collects name/type/page/life, then    */
                                    /* dispatches T->editor, P/A/S/F->upload_file)    */
extern void link_lock(APTR dir, int row);   /* FUN_00109520 — toggle row box */

#define GAD_DIR(g)  (*(APTR  *)((UBYTE *)(g) + 0x30))
#define GAD_ROW(g)  (*(short *)((UBYTE *)(g) + 0x26))

LONG hook_dir_0956c(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=goto_page();      link_lock(d,r); return x; } /* Dir  */
LONG hook_dir_095b0(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=back_dir();       link_lock(d,r); return x; } /* Back */
LONG hook_dir_095f6(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=link_goto();      link_lock(d,r); return x; } /* Goto */
LONG hook_dir_0963c(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=download_check(); link_lock(d,r); return x; } /* Dnld */
LONG hook_dir_09682(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=put_frame();      link_lock(d,r); return x; } /* Upld */
/* Mail/Courier action buttons (recon FUN_0010a3d0/3f8/43e/484/4ca): the same directory-
 * gadget lock wrapper, dispatching to the mail commands. mail_state_enter binds these to the
 * relabelled action gadgets (Done/ID/More/Dnld/Upld). Done takes a single lock (recon: no
 * trailing unlock — it tears the mail buttons down via mail_state_exit). */
extern LONG mail_done(void);      /* FUN_0010e058 — send "N", leave Courier   */
extern LONG mail_read(void);      /* FUN_0010e468 — "I" record: verify IDs     */
extern LONG mail_more(void);      /* FUN_0010e0b4 — send "M": next mail page   */
extern LONG mail_download(void);  /* FUN_0010e0fc — read the selected message  */
extern LONG mail_submit(void);    /* FUN_0010e188 — collect recipients + send  */

LONG hook_nav_0a3d0(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=mail_done();                     return x; } /* Done */
LONG hook_nav_0a3f8(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=mail_read();     link_lock(d,r); return x; } /* ID   */
LONG hook_nav_0a43e(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=mail_more();     link_lock(d,r); return x; } /* More */
LONG hook_nav_0a484(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=mail_download(); link_lock(d,r); return x; } /* Dnld */
LONG hook_nav_0a4ca(APTR g){ APTR d=GAD_DIR(g); short r=GAD_ROW(g); LONG x; link_lock(d,r); x=mail_submit();   link_lock(d,r); return x; } /* Upld */

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
 *   msg+0x14 = command OPCODE BYTE (DAT_0012015a) <-- a byte at +0x14, NOT +0x15
 *   msg+0x16 = arg (frame/screen)(DAT_0012015c)
 *   msg+0x1a = arg              (DAT_00120160)
 *   msg+0x1e = arg              (DAT_00120164)
 * then PutMsg to the editor port, WaitPort/GetMsg our reply port, and read the reply
 * STATUS byte at msg+0x15 (DAT_0012015b) — a different field from the command. */
static UBYTE editor_command(UWORD cmd, APTR arg16, APTR arg1a, APTR arg1e)
{
    EMSG_L(0x0e) = g_editor_port;          /* reply port (recon re-sets it each call) */
    g_editor_msg[0x14] = (UBYTE)cmd;       /* opcode BYTE at +0x14 (recon move.b #cmd).
                                            * A UWORD write here put 0x00 in the opcode
                                            * byte (+0x14) and the cmd in +0x15 (the reply
                                            * STATUS byte) — so the editor saw opcode 0
                                            * (idle) and the Editor menu did nothing. */
    EMSG_L(0x16) = arg16;
    EMSG_L(0x1a) = arg1a;
    EMSG_L(0x1e) = arg1e;
    put_msg(g_edit_msgport, g_editor_msg);
    WaitPort((struct MsgPort *)g_editor_port);
    GetMsg((struct MsgPort *)g_editor_port);
    return EMSG_B(0x15);                    /* reply status byte at +0x15 */
}

/*
 * editor_set_frame_count — recon FUN_00114050. Tell the editor how many frames its offline
 * ring should hold (the "Editor frames" Setup value, config+0x2a). Sends editor opcode 5 with
 * the count at msg+0x16. Called from load_config (startup, after launch_editor) and
 * settings_apply (after the user edits the field); both ignore the result.
 *
 * NOTE: the earlier reconstruction misread FUN_00114050 as a serial-parameter routine
 * ("apply_serial_params") and stubbed it to a dead write of g_dev_param2e, so the editor never
 * received the frame count. Verified byte-exact against $114050: move.b #5,msg+0x14;
 * msg+0x16 = arg; PutMsg + WaitPort/GetMsg; return (status==0).
 */
LONG editor_set_frame_count(UWORD count)
{
    return editor_command(5, (APTR)(ULONG)count, NULL, NULL) == 0;
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
/* ---- frame-window button bar: Next / Last / More / All / Send / Done -------------
 * recon FUN_001172f4 / 1733a / 17380 / 173c6 / 1740c / 17470. Each reads its frame page
 * (gad+0x30) and button row (gad+0x26) and wraps its action in the frame highlight lock.
 * "More" (FUN_00113062) sends "D" to fetch the next frame of a multi-frame page — the
 * multi-page reader control. Next/Last (in-frame scroll) and All/Send/Done (editor/
 * upload) call editor internals not yet reconstructed; stubbed to a no-op for now. */
extern void frame_lock(APTR frame_page, int row);   /* FUN_001170be */
extern LONG frame_more(void);                        /* FUN_00113062 — "D" MORE */
extern LONG put_frame_xfer(void);                    /* FUN_0010c270 — text-upload Send   */
extern LONG put_frame_done(void);                    /* FUN_0010c2de — text-upload Done   */
extern LONG mail_field_send(void);                   /* FUN_0010e398 — courier Send       */
extern LONG mail_field_next(void);                   /* FUN_0010e402 — courier Done       */
extern UWORD g_state;                                /* DAT_0011d070 */

#define FGAD_PAGE(g)  (*(APTR  *)((UBYTE *)(g) + 0x30))
#define FGAD_ROW(g)   (*(short *)((UBYTE *)(g) + 0x26))

extern LONG frame_next(void);   /* FUN_0011710a — list nav forward  */
extern LONG frame_last(void);   /* FUN_001171fc — list nav backward */
extern LONG frame_all(void);    /* FUN_0011763a — fetch all frames  */

LONG hook_ed_17380(APTR g){ APTR p=FGAD_PAGE(g); short r=FGAD_ROW(g); LONG x; frame_lock(p,r); x=frame_more(); frame_lock(p,r); return x; } /* More */
LONG hook_ed_172f4(APTR g){ APTR p=FGAD_PAGE(g); short r=FGAD_ROW(g); LONG x; frame_lock(p,r); x=frame_next(); frame_lock(p,r); return x; } /* Next */
LONG hook_ed_1733a(APTR g){ APTR p=FGAD_PAGE(g); short r=FGAD_ROW(g); LONG x; frame_lock(p,r); x=frame_last(); frame_lock(p,r); return x; } /* Last */
LONG hook_ed_173c6(APTR g){ APTR p=FGAD_PAGE(g); short r=FGAD_ROW(g); LONG x; frame_lock(p,r); x=frame_all();  frame_lock(p,r); return x; } /* All  */

/* Send / Done — recon FUN_0011740c / FUN_00117470. Both lock the frame highlight, then
 * dispatch on g_state: 4 = text ('T') upload, 7 = mail/courier body send. Verified: the
 * blob command buffers are "U" (0x11ea90) for Send and "N" (0x11ea94) for Done — the same
 * frame-ready / done keys mail_field_send / mail_field_next use. */
LONG hook_ed_1740c(APTR g){ APTR p=FGAD_PAGE(g); short r=FGAD_ROW(g); LONG x=1; frame_lock(p,r); if (g_state==4) x=put_frame_xfer(); else if (g_state==7) x=mail_field_send(); frame_lock(p,r); return x; } /* Send */
LONG hook_ed_17470(APTR g){ APTR p=FGAD_PAGE(g); short r=FGAD_ROW(g); LONG x=1; frame_lock(p,r); if (g_state==4) x=put_frame_done(); else if (g_state==7) x=mail_field_next(); frame_lock(p,r); return x; } /* Done */

/* ---- editor render entry points (recon 0x116000/200/400) ---- */
LONG hook_16000(APTR g){ (void)g; return 1; }
LONG hook_16200(APTR g){ (void)g; return 1; }
LONG hook_16400(APTR g){ (void)g; return 1; }
