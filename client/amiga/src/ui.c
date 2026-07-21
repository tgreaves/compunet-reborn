/*
 * ui.c — Intuition UI layer (reconstructed).
 *
 * The window/screen/gadget/menu *data* lives in the extracted data blob
 * (g_data_blob.asm, HUNK 27, byte-identical to the original). This file
 * reconstructs the *behaviour* — opening screens and windows, drawing the Images
 * and gadget lists, running the IDCMP event loops, and the status-line dispatch —
 * as readable C that binds to those structures by their original offsets.
 *
 * Structures are addressed as DATA(off), where off = original_address - 0x11d000
 * (the data section's base in the flat image). So DATA(0x57a) is the logon window's
 * NewWindow, DATA(0x5aa) its border Image, etc. — exactly the &DAT_0011dXXX the
 * decompiler showed, now resolved against the real bytes.
 *
 * Everything here calls graphics.library / intuition.library. This is the last
 * layer above the reconstructed application logic; with it the client is complete.
 *
 * NOTE ON VERIFICATION: this layer compiles and links, and the data it drives is
 * byte-accurate. Full behavioural correctness (pixel layout, gadget hit-testing)
 * can only be confirmed by running under an Amiga (WinUAE/vAmiga) against a Reborn
 * server — that runtime test is the acceptance step this reconstruction enables.
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <intuition/screens.h>
#include <graphics/text.h>
#include <clib/exec_protos.h>
#include <clib/intuition_protos.h>
#include <clib/graphics_protos.h>
#include <string.h>

#include "compunet.h"

extern APTR SysBase;   /* supplied by the C runtime startup */

/* The extracted data section and its base in the original flat image. */
extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

/* Library bases + shared window/screen handles (globals.c / launch.c). */
extern APTR g_screen;      /* DAT_001200f8 — the custom screen  */
extern APTR g_window;      /* DAT_001200fc — the main window     */
extern APTR g_editor_port;
extern char g_login_userid[];   /* DAT_00120244 */
extern char g_login_scratch[];  /* DAT_0012024d */

/* Resource-tracked screen/window open+close (recon FUN_0011a4e0 / FUN_0011a534). */
extern APTR open_screen_tracked(APTR newscreen);   /* FUN_0011a4e0 -> OpenScreen */
extern APTR open_window_tracked(APTR newwindow);   /* FUN_0011a534 -> OpenWindow */
extern void close_window_tracked(APTR win);        /* FUN_0011a568 -> CloseWindow */

/* Window/menu-state handles (recon DAT_* in the blob/BSS). */
static struct Window *g_logon_win;   /* DAT_0011d570 */
static struct Window *g_frame_win;   /* *DAT_0011d078 */
static struct Window *g_dir_win;     /* *DAT_0011d07c */
static struct RastPort *g_logon_rp;  /* DAT_001201c0 */
static short  g_logon_x;             /* DAT_001201ee */
static short  g_logon_y;             /* DAT_001201f0 */

/* ------------------------------------------------------------------ *
 *  Screen / main window bring-up (called from launch_tty)
 * ------------------------------------------------------------------ */

/* open_screen_tracked / open_window_tracked are the tracked OpenScreen/OpenWindow.
 * launch_tty passes 0 (meaning "the NewScreen/NewWindow in the data blob"); resolve
 * those to the blob structures here. Offsets DERIVED FROM THE RECON (not guessed):
 *   NewScreen  = DAT_0011d098 + 10 = 0x11d0a2   (recon FUN_001026ae line 1867)
 *   NewWindow  = DAT_0011d0e2                    (recon FUN_001026ae line 1873) */
extern void resource_register_free(void (*fn)(), APTR arg1, APTR arg2); /* FUN_0011a16c */

APTR open_screen_tracked(APTR newscreen)
{
    struct Screen *s;
    if (newscreen == 0)
        newscreen = DATA(0x11d0a2);   /* NewScreen (recon DAT_0011d098+10) */
    s = OpenScreen((struct NewScreen *)newscreen);
    /* recon FUN_0011a4e0: on success register CloseScreen so cleanup closes it at exit
     * (this is why the screen was left on-screen after Quit — the close was missing). */
    if (s != NULL)
        resource_register_free((void (*)())CloseScreen, (APTR)s, 0);
    return (APTR)s;
}

APTR open_window_tracked(APTR newwindow)
{
    struct Window *w;
    if (newwindow == 0)
        newwindow = DATA(0x11d0e2);   /* the main NewWindow (recon DAT_0011d0e2) */
    w = OpenWindow((struct NewWindow *)newwindow);
    /* recon FUN_0011a534: on success register CloseWindow. */
    if (w != NULL)
        resource_register_free((void (*)())CloseWindow, (APTR)w, 0);
    return (APTR)w;
}

extern void resource_unregister(void (*fn)(), APTR arg1);   /* FUN_0011a19c */
void close_window_tracked(APTR win)
{
    /* recon FUN_0011a568: close the window AND remove its tracker node, so the
     * exit-time cleanup_all_resources doesn't try to close it a second time. */
    if (win) {
        CloseWindow((struct Window *)win);
        resource_unregister((void (*)())CloseWindow, win);
    }
}

/* ------------------------------------------------------------------ *
 *  Logon window (dial progress) — recon FUN_001030c6 / FUN_00103024 / FUN_00103000
 * ------------------------------------------------------------------ */

/* open_logon_window — recon FUN_001030c6: open the logon window from its NewWindow
 * at DATA(0x57a), draw its border Image, set up the scrolling text pen, and reset
 * the text cursor. Returns non-zero on success. */
LONG open_logon_window(void)
{
    /* Patch NewWindow.Screen (0x11d57a + 0x1e) with our custom screen before opening;
     * the window is CUSTOMSCREEN so OpenWindow returns NULL otherwise. recon
     * FUN_001030c6 line 2900: DAT_0011d598 = g_screen. */
    *(APTR *)DATA(0x11d598) = g_screen;
    g_logon_win = (struct Window *)open_window_tracked(DATA(0x11d57a));
    if (g_logon_win == NULL)
        return 0;
    g_logon_rp = g_logon_win->RPort;
    DrawImage(g_logon_rp, (struct Image *)DATA(0x11d5aa), 4, 0xb);
    SetAPen(g_logon_rp, 1);
    SetDrMd(g_logon_rp, JAM2);
    g_logon_x = 0;
    g_logon_y = 0xb;
    return 1;
}

void close_logon_window(void)   /* recon FUN_00119450 / FUN_0010314c */
{
    if (g_logon_win) {
        close_window_tracked(g_logon_win);
        g_logon_win = NULL;
    }
}

void close_connection_window(void)  /* recon FUN_0010314c (alias) */
{
    close_logon_window();
}

/* logon_text_append — recon FUN_00103024: print a string into the logon window's
 * scrolling text area, advancing the y position and scrolling when it fills. */
void logon_text_append(const char *s, int len)
{
    if (len == 0) { s = "\n"; len = 1; }
    if (g_logon_rp == NULL) return;
    Move(g_logon_rp, 4, g_logon_y + 6);
    Text(g_logon_rp, (STRPTR)s, len);
    if (g_logon_y < 0x9c)
        g_logon_y += 8;
    else
        ScrollRaster(g_logon_rp, 0, 8, 4, 0xb, 0x143, 0xaa);
}

/* logon_window_ready (recon FUN_0011949a) is reconstructed faithfully in
 * partyline.c: it optionally opens the partyline window and issues the device's
 * "login ready" command (io_Command 9). */

/* uppercase in place — recon FUN_0011513a (a..z -> A..Z). */
static void str_upper(char *p)
{
    for (; *p; p++)
        if (*p >= 'a' && *p <= 'z')
            *p -= 0x20;
}

/*
 * logon_poll — recon FUN_00115168, the login-CREDENTIALS dialog (not a mere poll).
 * Opens the credentials window (NewWindow 0x11f81c, Screen patched at +0x1e=0x11f83a),
 * draws its image/border/text + gadget list, then runs the IDCMP loop: drain all
 * messages keeping the last gadget, switch on GadgetID (+0x26) — 0 = cancel (return
 * 0), 1/2 = accept (uppercase userid + scratch, return 1), 3 = activate the next
 * string field and keep looping, default = keep looping. NO class filter (recon
 * FUN_00115168). Window credentials window handle is DAT_00121830.
 */
static struct Window *g_cred_win;   /* DAT_00121830 */
static UBYTE g_undo_scratch[16];    /* string-gadget undo buffer (see below) */

LONG logon_poll(void)
{
    struct IntuiMessage *msg;
    struct Gadget *last;

    /* FUN_00115080: open the credentials window with its Screen patched in. */
    *(APTR *)DATA(0x11f83a) = g_screen;
    g_cred_win = (struct Window *)open_window_tracked(DATA(0x11f81c));
    if (g_cred_win == NULL)
        return 0;

    /* The credentials string gadgets come from the extracted data blob, where their
     * StringInfo.Buffer pointers still hold the ORIGINAL absolute addresses
     * (0x120244 userid / 0x12024d password). Those are OUTSIDE the blob (which ends at
     * 0x1200e8) and were never relocated to the reconstruction's globals — so typed
     * input landed in stray memory and the login record used the stale config userid.
     * Re-point both buffers at the real g_login_userid / g_login_scratch, seed the
     * userid field's pre-filled length, and give each a valid undo buffer. Also widen
     * the password field, which the original data made only 8px (one character) wide. */
    {
        struct StringInfo *si_user = (struct StringInfo *)DATA(0x11f93c);
        struct StringInfo *si_pass = (struct StringInfo *)DATA(0x11f8c8);
        struct Gadget     *g_pass  = (struct Gadget *)DATA(0x11f8ec);
        UWORD ulen = (UWORD)strlen(g_login_userid);

        si_user->Buffer     = (UBYTE *)g_login_userid;
        si_user->UndoBuffer = g_undo_scratch;
        si_user->NumChars   = ulen;
        si_user->BufferPos  = ulen;
        si_user->DispPos    = 0;

        si_pass->Buffer     = (UBYTE *)g_login_scratch;
        si_pass->UndoBuffer = g_undo_scratch;
        si_pass->NumChars   = 0;
        si_pass->BufferPos  = 0;
        si_pass->DispPos    = 0;

        g_pass->Width = 56;   /* was 8 (one char); ~7 chars wide now */
    }

    g_login_scratch[0] = 0;
    DrawImage(g_cred_win->RPort, (struct Image *)DATA(0x11f98c), 0, 0);
    PrintIText(g_cred_win->RPort, (struct IntuiText *)DATA(0x11fa1a), 0, 0);
    DrawBorder(g_cred_win->RPort, (struct Border *)DATA(0x11f9e4), 0, 0);
    AddGList(g_cred_win, (struct Gadget *)DATA(0x11f960), ~0, ~0, NULL);
    RefreshGList((struct Gadget *)DATA(0x11f960), g_cred_win, NULL, ~0);
    ActivateGadget((struct Gadget *)DATA(0x11f960), g_cred_win, NULL);

    for (;;) {
        last = NULL;
        WaitPort(g_cred_win->UserPort);
        while ((msg = (struct IntuiMessage *)GetMsg(g_cred_win->UserPort)) != NULL) {
            last = (struct Gadget *)msg->IAddress;
            ReplyMsg((struct Message *)msg);
        }
        if (last == NULL)
            continue;
        switch (last->GadgetID) {
        case 0:                                 /* Cancel */
            close_window_tracked(g_cred_win);
            g_cred_win = NULL;
            return 0;
        case 1:
        case 2:                                 /* OK / accept */
            str_upper(g_login_userid);
            str_upper(g_login_scratch);
            close_window_tracked(g_cred_win);
            g_cred_win = NULL;
            return 1;
        case 3:                                 /* Enter/tab in userid -> next field */
            /* recon FUN_00115168 @0x1151f6: ActivateGadget(last->NextGadget, ...) — it
             * advances to the NEXT gadget (the password field). An earlier reconstruction
             * activated `last` (the same userid field), so focus never reached the
             * password gadget and the login was sent with an empty password. */
            ActivateGadget(last->NextGadget, g_cred_win, NULL);
            break;
        default:
            break;
        }
    }
}

/* ------------------------------------------------------------------ *
 *  Frame / directory windows — recon FUN_001174d4 / FUN_001099c0
 * ------------------------------------------------------------------ */

LONG open_frame_window(void)   /* recon FUN_001174d4 */
{
    /* NewWindow = DAT_0011fa3e; patch its Screen (+0x1e = 0x11fa5c) with g_screen
     * (CUSTOMSCREEN). recon FUN_001174d4 line 13637: DAT_0011fa5c = g_screen. */
    *(APTR *)DATA(0x11fa5c) = g_screen;
    g_frame_win = (struct Window *)open_window_tracked(DATA(0x11fa3e));
    if (g_frame_win == NULL)
        return 0;
    g_frame_page = (APTR)&g_frame_win;
    return 1;
}

LONG init_directory(void)      /* recon FUN_001099c0 */
{
    /* NewWindow = DAT_0011e1e2; patch its Screen (+0x1e = 0x11e200) with g_screen
     * (CUSTOMSCREEN). recon FUN_001099c0 line 5969: DAT_0011e200 = g_screen. */
    *(APTR *)DATA(0x11e200) = g_screen;
    g_dir_win = (struct Window *)open_window_tracked(DATA(0x11e1e2));
    if (g_dir_win == NULL)
        return 0;
    g_dir_page = (APTR)&g_dir_win;
    return 1;
}

/* directory_repaint (recon FUN_001096c8) now lives in directory_select.c, and
 * directory_refresh — which is really the full directory-frame PARSER
 * (recon FUN_00109a5e) — lives in directory_parse.c. The earlier approximations
 * that stood here (a plain frame_redraw) have been removed. */
extern void parse_directory_frame(APTR page);   /* directory_parse.c — FUN_00109a5e */

/* directory_refresh — the name navigate.c / mail.c call after a nav ack; it IS the
 * directory-frame parser (recon FUN_00109a5e). Thin alias to keep those call sites. */
void directory_refresh(APTR dir_page)
{
    parse_directory_frame(dir_page);
}

/* ------------------------------------------------------------------ *
 *  The window set every UI-state helper iterates (recon: a4-relative slots
 *  touched by FUN_001020ae / FUN_0010221c / FUN_0010217a in the same order).
 * ------------------------------------------------------------------ *
 * Six windows: the main window (DAT_001200fc, held directly), the frame page and
 * directory page (DAT_0011d078 / DAT_0011d07c — page structs whose first field is
 * the window), and the courier / secondary-directory / partyline windows
 * (DAT_00121650 / DAT_00121698 / DAT_0011fd70, held directly). ui_each_window()
 * yields each live window pointer in the recon's order. */
extern APTR g_frame_page;    /* DAT_0011d078 — frame page (page[0] = window)   */
extern APTR g_dir_page;      /* DAT_0011d07c — directory page (page[0]=window)  */
extern APTR g_courier_win;   /* DAT_00121650 */
extern APTR g_dir2_win;      /* DAT_00121698 */
extern APTR g_party_win;     /* DAT_0011fd70 */

static struct Window *ui_window(int i)
{
    switch (i) {
    case 0: return (struct Window *)g_window;
    case 1: return g_frame_page ? *(struct Window **)g_frame_page : NULL;
    case 2: return g_dir_page   ? *(struct Window **)g_dir_page   : NULL;
    case 3: return (struct Window *)g_courier_win;
    case 4: return (struct Window *)g_dir2_win;
    case 5: return (struct Window *)g_party_win;
    default: return NULL;
    }
}

/* ------------------------------------------------------------------ *
 *  Status line + simple dialogs — recon FUN_00115000 / FUN_00110042 / FUN_00110472
 * ------------------------------------------------------------------ *
 * show_status_message(code, text): recon FUN_00115000 selects an error-class PREFIX
 * string from the code and pops a modal OK requester (status_ok_dialog) with that
 * prefix as the title and the caller's text as the body. It is NOT a title-bar write.
 * The code->prefix table (verified from the relocated jump table at 0x11501a and the
 * blob strings): 0x41 = "Host error", 0x42 = "Fatal error", 0x01 = "Local error",
 * 0x02 = "Comms error"; any other code -> no prefix (plain requester). */
extern void status_ok_dialog(const char *line1, const char *line2, UBYTE p4, UBYTE p5); /* FUN_00110472 */
void show_status_message(UBYTE code, const char *text)
{
    const char *prefix;
    switch (code) {
    case 0x41: prefix = "Host error";  break;
    case 0x42: prefix = "Fatal error"; break;
    case 0x01: prefix = "Local error"; break;
    case 0x02: prefix = "Comms error"; break;
    default:   prefix = "";            break;   /* recon default: plain requester */
    }
    status_ok_dialog(prefix, text, 2, 1);   /* recon: p4=2, p5=1 (FrontPen 1) */
}

/* ui_set_title — recon FUN_0010217a: set the SCREEN title on every live window
 * (SetWindowTitles(win, -1, title): window title unchanged, screen title = text —
 * that's the text visible in the top bar of the backdrop screen). */
void ui_set_title(const char *title)
{
    int i;
    for (i = 0; i < 6; i++) {
        struct Window *w = ui_window(i);
        if (w)
            SetWindowTitles(w, (STRPTR)-1, (STRPTR)title);
    }
}

/* status_ok_dialog (recon FUN_00110472) and retry_dialog (recon FUN_001104a6) are
 * reconstructed in ui_dialogs.c as real requesters over the blob requester core
 * (FUN_00110042) with the proper OK / OK+Cancel gadget lists — not AutoRequest with
 * hardcoded "Retry/Cancel" labels (which rendered wrong buttons that did nothing). */

/* ------------------------------------------------------------------ *
 *  Pointer / gadget state helpers (recon FUN_001020ae / FUN_0010221c)
 * ------------------------------------------------------------------ */
void set_wait_pointer(void)    /* recon FUN_001020ae — busy pointer on all windows */
{
    int i;
    /* Busy pointer sprite at DATA(0x11d068), size 0xb x 0xb, hotspot (-5, 0). */
    for (i = 0; i < 6; i++) {
        struct Window *w = ui_window(i);
        if (w)
            SetPointer(w, (UWORD *)DATA(0x11d068), 0xb, 0xb, -5, 0);
    }
}

void clear_wait_pointer(void)  /* recon FUN_0010221c — restore default pointer */
{
    int i;
    for (i = 0; i < 6; i++) {
        struct Window *w = ui_window(i);
        if (w)
            ClearPointer(w);
    }
}

/* ------------------------------------------------------------------ *
 *  Main IDCMP event loop
 * ------------------------------------------------------------------ *
 * The client's top-level IDCMP loop (recon FUN_00102814) and its abort/disconnect
 * teardown now live in event_loop.c, faithfully transcribed with the real gadget
 * double-click dispatch, RAWKEY abort (longjmp), and menu command-map dispatch. The
 * earlier hand-rolled approximation that lived here has been removed.
 */
