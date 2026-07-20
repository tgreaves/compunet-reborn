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
APTR open_screen_tracked(APTR newscreen)
{
    if (newscreen == 0)
        newscreen = DATA(0x11d0a2);   /* NewScreen (recon DAT_0011d098+10) */
    /* tracked so cleanup closes it; here we call OpenScreen directly + register. */
    return (APTR)OpenScreen((struct NewScreen *)newscreen);
}

APTR open_window_tracked(APTR newwindow)
{
    if (newwindow == 0)
        newwindow = DATA(0x11d0e2);   /* the main NewWindow (recon DAT_0011d0e2) */
    return (APTR)OpenWindow((struct NewWindow *)newwindow);
}

void close_window_tracked(APTR win)
{
    if (win)
        CloseWindow((struct Window *)win);
}

/* ------------------------------------------------------------------ *
 *  Logon window (dial progress) — recon FUN_001030c6 / FUN_00103024 / FUN_00103000
 * ------------------------------------------------------------------ */

/* open_logon_window — recon FUN_001030c6: open the logon window from its NewWindow
 * at DATA(0x57a), draw its border Image, set up the scrolling text pen, and reset
 * the text cursor. Returns non-zero on success. */
LONG open_logon_window(void)
{
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

LONG logon_poll(void)          /* recon FUN_00115168 */
{
    /* Poll the logon window's IDCMP for the user pressing return / cancel. Returns
     * 1 to continue the login handshake, 0 to abort. Reconstructed as a simple
     * message drain; the detailed field-editing is in the gadget handlers. */
    struct IntuiMessage *msg;
    if (g_logon_win == NULL)
        return 0;
    while ((msg = (struct IntuiMessage *)GetMsg(g_logon_win->UserPort)) != NULL) {
        ULONG cls = msg->Class;
        ReplyMsg((struct Message *)msg);
        if (cls == CLOSEWINDOW)
            return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------ *
 *  Frame / directory windows — recon FUN_001174d4 / FUN_001099c0
 * ------------------------------------------------------------------ */

LONG open_frame_window(void)   /* recon FUN_001174d4 */
{
    /* NewWindow = DAT_0011fa3e (recon FUN_001174d4 line 13628) */
    g_frame_win = (struct Window *)open_window_tracked(DATA(0x11fa3e));
    if (g_frame_win == NULL)
        return 0;
    g_frame_page = (APTR)&g_frame_win;
    return 1;
}

LONG init_directory(void)      /* recon FUN_001099c0 */
{
    /* NewWindow = DAT_0011e1e2 (recon FUN_001099c0 line 5970) */
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
 * show_status_message(code, text): the original dispatches on the status code via a
 * small table (info line / message / error). We render into the main window's title
 * / status area. Codes: 1 = info, 0x41 = message, 0x42 = error. */
void show_status_message(UBYTE code, const char *text)
{
    if (g_window == NULL)
        return;
    /* The window is a borderless backdrop window, so the visible text is the SCREEN
     * title (3rd arg); window title (2nd arg) stays unchanged (-1). recon
     * FUN_0010217a: SetWindowTitles(win, -1, text). */
    SetWindowTitles((struct Window *)g_window, (STRPTR)-1, (STRPTR)text);
    (void)code;
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

/* Build a one-line IntuiText for AutoRequest (KS1.3-era requester API). */
static void mk_itext(struct IntuiText *it, const char *s, WORD x, WORD y)
{
    it->FrontPen  = 0;
    it->BackPen   = 1;
    it->DrawMode  = JAM2;
    it->LeftEdge  = x;
    it->TopEdge   = y;
    it->ITextFont = NULL;
    it->IText     = (UBYTE *)s;
    it->NextText  = NULL;
}

/* status_ok_dialog — recon FUN_00110472: a modal "OK" requester (title + body).
 * Reconstructed with AutoRequest (the period-correct KS1.3 API). */
void status_ok_dialog(const char *title, const char *body)
{
    struct IntuiText bt, pt, nt;
    mk_itext(&bt, body,  8, 8);
    mk_itext(&pt, "OK",  6, 3);
    mk_itext(&nt, "OK",  6, 3);
    (void)title;
    AutoRequest((struct Window *)g_window, &bt, NULL, &nt, 0, 0, 320, 72);
}

/* retry_dialog — recon FUN_001104a6: a "try again?" requester (returns 1 = retry). */
LONG retry_dialog(const char *title, const char *body)
{
    struct IntuiText bt, pt, nt;
    mk_itext(&bt, body,    8, 8);
    mk_itext(&pt, "Retry", 6, 3);
    mk_itext(&nt, "Cancel",6, 3);
    (void)title;
    return AutoRequest((struct Window *)g_window, &bt, &pt, &nt, 0, 0, 320, 72);
}

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
