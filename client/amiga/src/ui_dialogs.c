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
#include <clib/graphics_protos.h>
#include <setjmp.h>

#include "compunet.h"

extern APTR  g_screen;
extern APTR  g_window;
extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

extern APTR open_window_tracked(APTR nw);
extern void close_window_tracked(APTR win);

/*
 * about_dialog — recon FUN_00104000. The "About..." menu handler. Opens the About
 * window (NewWindow in the blob at 0x11d6e4, whose Screen field at 0x11d702 we patch
 * with our custom screen just like the main window), draws its Image + border +
 * version IntuiText, adds its OK gadget, and runs a small IDCMP loop until the gadget
 * (GadgetID 1) is hit, then closes. Returns 1.
 *
 * NB: this was previously mis-bound in the data blob to the no-op stub hook_16000
 * (extract_data CODE_SYM[0x104000] wrongly named "hook_render_entry"), which is why
 * selecting About did nothing. It is now a real reconstruction; the blob binds
 * 0x104000 -> about_dialog.
 */
LONG about_dialog(void)
{
    struct Window *w;
    struct IntuiMessage *msg;
    LONG done = 0;

    /* Patch the About NewWindow's Screen field (NewWindow 0x11d6e4 + 0x1e = 0x11d702)
     * with our custom screen (recon: DAT_0011d702 = g_screen). */
    *(APTR *)DATA(0x11d702) = g_screen;

    w = (struct Window *)open_window_tracked(DATA(0x11d6e4));
    if (w == NULL)
        return 0;

    /* Body image, version text, border (recon DrawImage / PrintIText / DrawBorder). */
    DrawImage(w->RPort, (struct Image *)DATA(0x11d740), 0, 0);
    PrintIText(w->RPort, (struct IntuiText *)DATA(0x11d894), 0, 0);
    DrawBorder(w->RPort, (struct Border *)DATA(0x11d798), 0, 0);

    /* OK gadget list (recon &DAT_0011d714). */
    AddGList(w, (struct Gadget *)DATA(0x11d714), ~0, ~0, NULL);
    RefreshGList((struct Gadget *)DATA(0x11d714), w, NULL, ~0);

    /* Run until a message whose IAddress is the OK gadget (GadgetID at +0x26 == 1).
     * recon FUN_00104000 loop ($102... ): WaitPort, one GetMsg, read IAddress(+0x1c),
     * ReplyMsg, then exit when gadget->GadgetID == 1 — NO class filter (an earlier
     * GADGETUP-only check never matched, so OK didn't close the window). */
    do {
        WaitPort(w->UserPort);
        msg = (struct IntuiMessage *)GetMsg(w->UserPort);
        if (msg != NULL) {
            struct Gadget *g = (struct Gadget *)msg->IAddress;
            ReplyMsg((struct Message *)msg);
            if (g != NULL && g->GadgetID == 1)
                done = 1;
        }
    } while (!done);

    close_window_tracked(w);
    return 1;
}

/*
 * run_requester — recon FUN_00110042. Open the requester window (NewWindow in the
 * blob at 0x11ee80), add its gadget list, WaitPort ONCE, drain all queued messages
 * (keeping the last one's IAddress), close, and return that gadget's GadgetID (+0x26).
 *
 * IMPORTANT: the recon applies NO message-class filter — it just returns the last
 * message's gadget id. The OK/Cancel gadgets are GADGIMMEDIATE (they emit GADGETDOWN,
 * never GADGETUP), so an earlier `if (cls == GADGETUP)` check never matched and every
 * prompt hung forever at WaitPort. The window is CUSTOMSCREEN, so its NewWindow.Screen
 * (0x11ee80 + 0x1e = 0x11ee9e) must be patched with g_screen first, or OpenWindow
 * returns NULL (recon FUN_00110042 line 11292: DAT_0011ee9e = screen).
 */
/*
 * run_requester — faithful recon FUN_00110042. Open the requester window, draw its
 * body (box Image + the IntuiText chain + border), add the passed gadget list, then
 * WaitPort / drain / close. Returns the last message's IAddress->GadgetID.
 *
 * Blob structures driven:
 *   0x11ee80  NewWindow (Width=264, Height=50; Screen at +0x1e = 0x11ee9e)
 *   0x11f0a8  Image (the dialog box background)
 *   0x11f094  IntuiText (line 1 — NextText chains to 0x11f080 = line 2)
 *   0x11f018  Border (button outlines)
 *   0x11f028  Gadget list (OK only)
 *   0x11f054  Gadget list (OK + Cancel)
 */
static LONG run_requester(APTR newwindow, APTR glist)
{
    struct Window *w;
    struct IntuiMessage *msg;
    struct Gadget *last = NULL;

    /* Patch the NewWindow's Screen field into the blob so it opens on our screen. */
    *(APTR *)DATA(0x11ee9e) = g_screen;

    w = (struct Window *)open_window_tracked(newwindow);
    if (w == NULL)
        return 0;

    /* Draw the dialog body: box image, text (IntuiText chain at 0x11f094 renders
     * both lines since its NextText is 0x11f080), and the gadget border. These are
     * the three draw calls the recon makes before adding gadgets. */
    DrawImage(w->RPort, (struct Image *)DATA(0x11f0a8), 4, 2);
    PrintIText(w->RPort, (struct IntuiText *)DATA(0x11f094), 4, 2);
    DrawBorder(w->RPort, (struct Border *)DATA(0x11f018), 4, 2);

    AddGList(w, (struct Gadget *)glist, 0, ~0, NULL);
    RefreshGList((struct Gadget *)glist, w, NULL, ~0);

    /* Block until user clicks a gadget, then drain all queued messages and return
     * the last one's gadget id (recon: WaitPort + drain loop + read IAddress+0x26). */
    WaitPort(w->UserPort);
    while ((msg = (struct IntuiMessage *)GetMsg(w->UserPort)) != NULL) {
        last = (struct Gadget *)msg->IAddress;
        ReplyMsg((struct Message *)msg);
    }
    close_window_tracked(w);
    return (last != NULL) ? last->GadgetID : 0;
}

/*
 * requester_2line — the shared "two text lines + gadget list" requester used by the
 * OK-only (recon FUN_00110472) and yes/no (recon FUN_001104a6) dialogs. It patches
 * the two pre-built IntuiText structs in the blob (their .IText fields at 0x11f0a0
 * [line 1, top] and 0x11f08c [line 2]) with the caller's strings, then runs the
 * requester core with the chosen gadget list:
 *   glist 0x11f028 -> OK only ;  glist 0x11f054 -> OK(id 1) + Cancel(id 0).
 * Returns the clicked gadget's id (OK = 1, Cancel = 0).
 */
LONG requester_2line(const char *line1, const char *line2, APTR glist)
{
    *(const char **)DATA(0x11f0a0) = line1;   /* IntuiText@0x11f094 .IText */
    *(const char **)DATA(0x11f08c) = line2;   /* IntuiText@0x11f080 .IText */
    return run_requester(DATA(0x11ee80), glist);
}

/* status_ok_dialog — recon FUN_00110472: modal OK requester (two text lines).
 * Sets FrontPen of both IntuiText structs to param (recon param_5; for the status
 * dialog it's typically 1 = blue-on-black). */
void status_ok_dialog(const char *title, const char *body)
{
    *(UBYTE *)DATA(0x11f094) = 1;   /* FrontPen of text-1 IntuiText */
    *(UBYTE *)DATA(0x11f080) = 1;   /* FrontPen of text-2 IntuiText */
    requester_2line(title, body, DATA(0x11f028 /*OK-only gadget list*/));
}

/* retry_dialog — recon FUN_001104a6: yes/no requester. Returns 1 = OK, 0 = Cancel.
 * Sets FrontPen = 7 (white), DAT_0011f0b7 = 6. */
LONG retry_dialog(const char *title, const char *body)
{
    *(UBYTE *)DATA(0x11f0b7) = 6;
    *(UBYTE *)DATA(0x11f094) = 7;   /* FrontPen of text-1 IntuiText */
    *(UBYTE *)DATA(0x11f080) = 7;   /* FrontPen of text-2 IntuiText */
    return requester_2line(title, body, DATA(0x11f054 /*OK+Cancel list*/)) == 1;
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
