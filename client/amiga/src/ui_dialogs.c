/*
 * ui_dialogs.c — input requesters + small UI/logic leaf helpers (reconstructed).
 *
 * The application modules pop up small requesters to collect a filename, a page
 * number, a vote choice, a LIFE value, or a machine-type confirmation. In the
 * original these all funnel through one requester core (recon FUN_00110042/00110306)
 * that opens a requester window from the data blob, adds its string/number gadget,
 * runs a short IDCMP loop, and returns the gadget result. This file reconstructs
 * that core and the thin per-prompt wrappers, plus a handful of pure-logic leaves.
 *
 * The requester window + gadget structures live in the extracted blob; here we drive
 * them. The string-gadget buffer the user edits is the gadget's StringInfo->Buffer,
 * which the callers read back from their DAT_* fields (wired to the same blob bytes).
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/exec_protos.h>
#include <clib/intuition_protos.h>
#include <setjmp.h>

#include "compunet.h"

extern APTR  g_window;
extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

extern APTR open_window_tracked(APTR nw);
extern void close_window_tracked(APTR win);

/*
 * run_requester — recon FUN_00110042/FUN_00110276: open a requester window (NewWindow
 * in the blob), add its gadget list, and loop on IDCMP until the user hits OK/Cancel,
 * returning the selected gadget's GadgetID. Shared by every prompt below.
 */
static LONG run_requester(APTR newwindow, APTR glist)
{
    struct Window *w;
    struct IntuiMessage *msg;
    struct Gadget *g;
    LONG result = 0;

    w = (struct Window *)open_window_tracked(newwindow);
    if (w == NULL)
        return 0;
    AddGList(w, (struct Gadget *)glist, ~0, ~0, NULL);
    RefreshGList((struct Gadget *)glist, w, NULL, ~0);

    for (;;) {
        WaitPort(w->UserPort);
        while ((msg = (struct IntuiMessage *)GetMsg(w->UserPort)) != NULL) {
            ULONG cls = msg->Class;
            g = (struct Gadget *)msg->IAddress;
            ReplyMsg((struct Message *)msg);
            if (cls == GADGETUP) {
                result = g->GadgetID;   /* 1 = OK, 2 = Cancel (recon +0x26) */
                close_window_tracked(w);
                return result;
            }
            if (cls == CLOSEWINDOW) {
                close_window_tracked(w);
                return 0;
            }
        }
    }
}

/* string_prompt — recon FUN_00110390: open the string requester (title + buffer). */
static LONG string_prompt(const char *title, char *buf)
{
    (void)title; (void)buf;   /* title/buffer are set into the blob's gadget by caller */
    return run_requester(DATA(0x11ee80 /*requester NewWindow*/),
                         DATA(0x11f0e0 /*string gadget list*/)) == 1;
}

/* number_prompt — recon FUN_00110306: same requester, integer gadget. */
static LONG number_prompt(const char *title, char *buf, int width)
{
    (void)title; (void)buf; (void)width;
    return run_requester(DATA(0x11ee80), DATA(0x11f0e0)) == 1;
}

/* ---- per-command prompt wrappers (the stubs, now real) ---- */

LONG goto_page_prompt(void)          /* recon FUN_0010a2e2 "Goto Page" */
{
    extern short g_goto_page_no;
    return number_prompt("Goto Page", (char *)&g_goto_page_no, 6);
}

LONG vote_choice_prompt(void)        /* recon FUN_0010c4ca */
{
    extern char g_vote_choice[];
    /* recon loops until a single digit 1-9 is entered */
    do {
        if (number_prompt("Vote", g_vote_choice, 1) == 0)
            return 0;
    } while (g_vote_choice[0] < '1' || g_vote_choice[0] > '9' || g_vote_choice[1] != '\0');
    return 1;
}

LONG extend_by_prompt(void)          /* recon FUN_0010c404 "Extend By" */
{
    extern char g_extend_days[];
    return number_prompt("Extend By", g_extend_days, 3);
}

LONG upload_filename_prompt(void)    /* recon FUN_0010c000 "Upload filename" */
{
    extern char g_ul_name[];
    return string_prompt("Upload filename", g_ul_name);
}

/* download_machine_prompt — recon FUN_0010b0ea: confirm the file's machine type
 * (0=C64, 2=ST need a yes/no; 1=Amiga auto-yes). Uses the OK/Cancel requester. */
LONG download_machine_prompt(char type)
{
    if (type == 1)
        return 1;                     /* Amiga: no confirmation */
    return run_requester(DATA(0x11ee80), DATA(0x11f054 /*OK/Cancel list*/)) == 1;
}

/* ---- pure-logic leaves ---- */

/* set_connection_error — recon FUN_00101638. Despite the name this reconstruction
 * originally gave it, the raw disassembly shows FUN_00101638 is longjmp: it restores
 * d1-d7/a1-a7 and the return PC from the buffer and returns the code. DAT_00120170
 * is the abort jmp_buf that client_main (FUN_001029e6) arms with setjmp; every
 * transport-error call site (serial_read/write/io_c, login, mail, ...) longjmps here
 * to unwind straight back to the top level, which runs disconnect(). A zero code is
 * bumped to 1 so setjmp's caller always sees a non-zero (abort) return. */
extern ULONG g_jmpbuf[];    /* DAT_00120170 — abort jmp_buf (globals.c) */
void set_connection_error(int code)
{
    longjmp((void *)g_jmpbuf, code ? code : 1);
}

/* dir_action_cleanup — recon FUN_0010d0d0: after a directory action, restore the
 * pointer and repaint. */
extern void clear_wait_pointer(void);
void dir_action_cleanup(void)
{
    clear_wait_pointer();
}

/* apply_serial_params — recon FUN_00114050: push the configured data-bits/parity to
 * cnet.device. The concrete register writes are in the device; here we forward the
 * config value (the client just stores it for open_transport to apply). */
extern UWORD g_dev_param2e;
void apply_serial_params(UWORD bits)
{
    g_dev_param2e = bits;
}

/* ui_set_title (recon FUN_0010217a) is reconstructed in ui.c, where it iterates the
 * full six-window set the original touches. (The earlier one-window stub here has
 * been removed.) */

/* put_frame_type_ok — recon jump-table at FUN_0010c2f8: whether a page type accepts
 * a published frame. The original dispatches per type; valid types are the frame
 * types 'F'/'P'/'G' etc. Non-directory types are publishable. */
LONG put_frame_type_ok(char type)
{
    return type != 'D';   /* directories can't hold published frames */
}

/* download_filename_prompt — recon FUN_0010b06e: prompt for the local save filename
 * (pre-filled from the directory row's name). */
LONG download_filename_prompt(void)
{
    extern char g_dl_filename[];
    return string_prompt("Download filename", g_dl_filename);
}
