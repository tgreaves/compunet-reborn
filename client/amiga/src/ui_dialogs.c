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

/* status_ok_dialog — recon FUN_00110472. Modal OK requester (two text lines). The
 * original takes 5 args: (line1, line2, screen, p4, p5) where p4 -> DAT_0011f0b7 and
 * p5 -> BOTH IntuiText FrontPens (DAT_0011f080 / DAT_0011f094). Callers vary the pen:
 * show_status_message passes p4=2,p5=1; account passes p4=1,p5=6. (screen is consumed
 * by the requester core via the blob NewWindow.Screen patch in run_requester.) */
void status_ok_dialog(const char *line1, const char *line2, UBYTE p4, UBYTE p5)
{
    *(UBYTE *)DATA(0x11f0b7) = p4;
    *(UBYTE *)DATA(0x11f094) = p5;   /* FrontPen of text-1 IntuiText */
    *(UBYTE *)DATA(0x11f080) = p5;   /* FrontPen of text-2 IntuiText */
    requester_2line(line1, line2, DATA(0x11f028 /*OK-only gadget list*/));
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

/*
 * number_prompt — recon FUN_00110306. Wire the caller's title, edit buffer, and field
 * width into the shared string gadget (all blob-resident), then open+run the requester.
 * Verified offsets: title -> 0x11eebc, StringInfo.Buffer -> 0x11f0bc, MaxChars = width+1
 * -> 0x11f0c6, gadget pixel width -> 0x11f0e8 (width>=0x10 ? 0x88 : (width+1)*8).
 * Returns 1 if OK (GadgetID 1). WITHOUT this wiring the user's input never reached the
 * caller's buffer (g_vote_choice / g_ul_name / g_goto_page_no / ...). */
static LONG number_prompt(const char *title, char *buf, int width)
{
    *(APTR  *)DATA(0x11eebc) = (APTR)title;         /* gadget title            */
    *(APTR  *)DATA(0x11f0bc) = (APTR)buf;           /* StringInfo.Buffer       */
    *(UWORD *)DATA(0x11f0c6) = (UWORD)(width + 1);  /* MaxChars                */
    *(UWORD *)DATA(0x11f0e8) = (UWORD)(width >= 0x10 ? 0x88 : (width + 1) * 8);
    return run_requester(DATA(0x11ee80), DATA(0x11f0e0)) == 1;
}

/* string_prompt — recon FUN_00110390: number_prompt with a fixed width of 0x20 (32). */
static LONG string_prompt(const char *title, char *buf)
{
    return number_prompt(title, buf, 0x20);
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

/* download_machine_prompt — recon FUN_0010b0ea: confirm the file's machine type via a
 * yes/no retry_dialog with a type-specific two-line message. type 1 (Amiga) auto-yes;
 * type 0 = "Commodore 64 file", type 2 = "Atart ST file" (original's typo), any other =
 * "Unrecognised machine type"; all titled "File download". Returns 1 if the user
 * confirms. (Was a bare textless OK/Cancel window handling only type 0/1/2.) */
LONG download_machine_prompt(char type)
{
    switch (type) {
    case 1:  return 1;                                                    /* Amiga */
    case 0:  return retry_dialog("File download", "Commodore 64 file");
    case 2:  return retry_dialog("File download", "Atart ST file");
    default: return retry_dialog("File download", "Unrecognised machine type");
    }
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

/* dir_action_cleanup — recon FUN_0010d0d0. Tear down the publish/upload requester
 * window: if g_courier_win (DAT_00121650) is open, close_window_tracked it and null
 * the handle. The verified disasm is `tst.l 0x121650(a4); beq; push; jsr close_window_
 * tracked(0x11a568); clr.l 0x121650`. (An earlier reconstruction wrongly made this a
 * clear_wait_pointer — it never touched the pointer.) */
extern APTR g_courier_win;                  /* DAT_00121650 */
extern void close_window_tracked(APTR win); /* FUN_0011a568 */
void dir_action_cleanup(void)
{
    if (g_courier_win) {
        close_window_tracked(g_courier_win);
        g_courier_win = NULL;
    }
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

/* download_filename_prompt — recon FUN_0010b06e: prompt for the local save filename
 * (pre-filled from the directory row's name). */
LONG download_filename_prompt(void)
{
    extern char g_dl_filename[];
    return string_prompt("Download filename", g_dl_filename);
}

/* ------------------------------------------------------------------ *
 *  Publish-frame requester — recon FUN_0010d000 / FUN_0010d0e6 / FUN_0010f1a4
 * ------------------------------------------------------------------ *
 * put_frame() (directory.c) calls put_frame_dialog() to collect the frame name, page
 * type, page.subpage and LIFE before publishing. This is a full requester subsystem
 * (~508 bytes across three functions) driven from the data blob:
 *   NewWindow   0x11e708  (Screen patch at +0x1e = 0x11e726; positioned off the dir win)
 *   gadget list 0x11e934  (6 gadgets: 4 string fields id 3/3/3/2, OK id 1, Cancel id 0)
 *   body Image  0x11e960 ; version/label IntuiText 0x11ea1c ; Border 0x11e9b8
 *   status Image 0x11ea30 (drawn on OK to show "sending")
 * The 4 string gadgets' StringInfo.Buffers point at the put_frame globals:
 *   g_put_name 0x1215f4, g_put_type 0x121605, g_put_type_str 0x121607, g_put_life_str
 *   0x12160e — so reading them back needs no copy, exactly as the original.
 */
extern APTR g_screen;
extern char g_put_name[];      /* DAT_001215f4 */
extern char g_put_type;        /* DAT_00121605 */
extern char g_put_type_str[];  /* DAT_00121607 */
extern char g_put_life_str[];  /* DAT_0012160e */

/* str_clean_upper — recon FUN_0010f1a4. In place: skip leading spaces, uppercase a-z,
 * trim trailing spaces, null-terminate. Applied to the name and type after editing. */
static void str_clean_upper(char *s)
{
    int i = 0, j = 0;
    char c;
    while ((c = s[i]) != '\0') {
        if (j != 0 || c != ' ') {           /* drop leading spaces */
            if (c >= 'a' && c <= 'z')
                c -= 0x20;
            s[j++] = c;
        }
        i++;
    }
    while (j != 0 && s[j - 1] == ' ')        /* trim trailing spaces */
        j--;
    s[j] = '\0';
}

/* put_frame_dialog_open — recon FUN_0010d000. Open the requester positioned relative to
 * the directory window (LeftEdge+0x3d, TopEdge+0x64), clear the four edit buffers, draw
 * the body/text/border, add the gadget list. Returns 1 on success, 0 if OpenWindow failed. */
extern APTR g_dir_page;    /* DAT_0011d07c — dir page; [0] = its Window */
static LONG put_frame_dialog_open(void)
{
    struct NewWindow *nw = (struct NewWindow *)DATA(0x11e708);
    struct Window    *dw = *(struct Window **)g_dir_page;
    struct Window    *w;

    *(APTR *)DATA(0x11e726) = g_screen;                /* NewWindow.Screen (+0x1e)  */
    nw->LeftEdge = dw->LeftEdge + 0x3d;
    nw->TopEdge  = dw->TopEdge  + 0x64;

    w = (struct Window *)open_window_tracked(nw);
    g_courier_win = (APTR)w;
    if (w == NULL)
        return 0;

    g_put_name[0]     = 0;                             /* recon clr.b 0x45f4/05/07/0e */
    g_put_type        = 0;
    g_put_type_str[0] = 0;
    g_put_life_str[0] = 0;

    DrawImage(w->RPort, (struct Image *)DATA(0x11e960), 0, 0);
    PrintIText(w->RPort, (struct IntuiText *)DATA(0x11ea1c), 0, 0);
    DrawBorder(w->RPort, (struct Border *)DATA(0x11e9b8), 0, 0);
    AddGList(w, (struct Gadget *)DATA(0x11e934), ~0, ~0, NULL);
    RefreshGList((struct Gadget *)DATA(0x11e934), w, NULL, ~0);
    return 1;
}

/* put_frame_dialog — recon FUN_0010d0e6. Open the requester, activate the first field,
 * then run the IDCMP loop: WaitPort, drain all messages keeping the last gadget's id
 * (+0x26). id 0 = Cancel (close via dir_action_cleanup, return 0); id 3 = a string field
 * hit (activate its NextGadget — tab to the next field — and keep looping); id 1/2 = OK.
 * The OK path detaches the 4 string gadgets and re-adds them (forcing Intuition to commit
 * the edited buffers) around cleaning the name + type, removes all 6 gadgets, draws the
 * "sending" status image, and returns 1. Buffers are read directly from the globals. */
LONG put_frame_dialog(void)
{
    struct Window       *w;
    struct IntuiMessage *msg;
    struct Gadget       *last;
    struct Gadget       *glist = (struct Gadget *)DATA(0x11e934);
    WORD                 pos;

    /* The original FUN_0010d0e6 calls the opener and then ActivateGadget without
     * checking the result (it relies on the requester always opening on the custom
     * screen). We guard the OpenWindow-failure path to avoid a NULL deref — the only
     * behavioural difference, and only when the window can't open. */
    if (!put_frame_dialog_open())
        return 0;
    w = (struct Window *)g_courier_win;

    ActivateGadget(glist, w, NULL);

    for (;;) {
        last = NULL;
        WaitPort(w->UserPort);
        while ((msg = (struct IntuiMessage *)GetMsg(w->UserPort)) != NULL) {
            last = (struct Gadget *)msg->IAddress;
            ReplyMsg((struct Message *)msg);
        }
        if (last == NULL || last->GadgetID >= 4)   /* recon: id>=4 ignored */
            continue;

        switch (last->GadgetID) {
        case 0:                                     /* Cancel */
            dir_action_cleanup();
            return 0;
        case 3:                                     /* string field -> tab to next */
            ActivateGadget(last->NextGadget, w, NULL);
            break;
        case 1:
        case 2:                                     /* OK */
            /* Detach the 4 string gadgets and re-add at the same position so Intuition
             * flushes their edit buffers, then clean name + type. */
            pos = RemoveGList(w, glist, 4);
            str_clean_upper(g_put_name);
            str_clean_upper(&g_put_type);
            AddGList(w, glist, pos, 4, NULL);
            RefreshGList(glist, w, NULL, 4);
            RemoveGList(w, glist, 6);               /* now detach all 6 */
            DrawImage(w->RPort, (struct Image *)DATA(0x11ea30), 0, 0);  /* status */
            return 1;
        }
    }
}
