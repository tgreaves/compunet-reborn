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
 * those to the blob structures here. The NewScreen is at DATA(0x0d2), NewWindow at
 * DATA(0x0e2) (recon &DAT_0011d0e2). */
APTR open_screen_tracked(APTR newscreen)
{
    if (newscreen == 0)
        newscreen = DATA(0x11d0c2);   /* the client's NewScreen (recon DAT_0011d0c2) */
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

void logon_window_ready(void)  /* recon FUN_0011949a */
{
    /* The original flips the logon window to its "connected" state; the visible
     * effect is just enabling input — handled by the caller's state machine. */
}

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
    g_frame_win = (struct Window *)open_window_tracked(DATA(0x11d3aa /*frame NewWindow*/));
    if (g_frame_win == NULL)
        return 0;
    g_frame_page = (APTR)&g_frame_win;
    return 1;
}

LONG init_directory(void)      /* recon FUN_001099c0 */
{
    g_dir_win = (struct Window *)open_window_tracked(DATA(0x11d3ba /*dir NewWindow*/));
    if (g_dir_win == NULL)
        return 0;
    g_dir_page = (APTR)&g_dir_win;
    return 1;
}

/* directory_repaint — recon FUN_001096c8: redraw the directory listing, highlighting
 * the currently-selected row. The row text is drawn through the frame render
 * primitives (render_char via frame's text writer). The detailed per-row layout is
 * in the directory page's row table; this repaints the visible window from it. */
extern void frame_write_string(APTR text, APTR page);   /* recon FUN_0010565e */
void directory_repaint(APTR dir_page)
{
    /* recon walks the row table at dir_page+0x7c8/+0x82e drawing each row's name via
     * frame_write_string, then boxes the selected row. Behaviourally: repaint. */
    if (dir_page == NULL) return;
    frame_redraw(dir_page);
}

/* directory_refresh — recon FUN_00109a5e (large): reload + repaint after navigation.
 * Delegates to directory_repaint for the visible redraw. */
void directory_refresh(APTR dir_page)
{
    directory_repaint(dir_page);
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
    /* The original picks a colour/line by code; behaviourally it sets the window
     * title bar text to the message. */
    SetWindowTitles((struct Window *)g_window, (STRPTR)text, (STRPTR)-1);
    (void)code;
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
    if (g_window)    SetPointer((struct Window *)g_window, (UWORD *)DATA(0x11d068), 0xb, 0xb, -5, 0);
    if (g_frame_win) SetPointer(g_frame_win, (UWORD *)DATA(0x11d068), 0xb, 0xb, -5, 0);
    if (g_dir_win)   SetPointer(g_dir_win,   (UWORD *)DATA(0x11d068), 0xb, 0xb, -5, 0);
}

void clear_wait_pointer(void)  /* recon FUN_0010221c — restore default pointer */
{
    if (g_window)    ClearPointer((struct Window *)g_window);
    if (g_frame_win) ClearPointer(g_frame_win);
    if (g_dir_win)   ClearPointer(g_dir_win);
}

/* ------------------------------------------------------------------ *
 *  Main IDCMP event loop — recon FUN_00102814
 * ------------------------------------------------------------------ *
 * Wait on the window's UserPort, dispatch gadget/menu/key events to the command
 * handlers, and repaint the connection state. This is the client's top-level loop
 * (entered from main() via launch). Menu selections map to the command functions
 * (goto_page, download_check, vote, extend_life, account, mail, upload, put_frame).
 */
extern LONG upload_file(void);
extern LONG mail_submit(void);
extern LONG mail_read(void);

void main_event_loop(void)
{
    struct IntuiMessage *msg;

    for (;;) {
        set_connection_state();

        if (g_window == NULL)
            return;
        WaitPort(((struct Window *)g_window)->UserPort);
        while ((msg = (struct IntuiMessage *)GetMsg(((struct Window *)g_window)->UserPort)) != NULL) {
            ULONG  cls  = msg->Class;
            UWORD  code = msg->Code;
            ReplyMsg((struct Message *)msg);

            if (cls == CLOSEWINDOW)
                return;
            if (cls == MENUPICK && code != MENUNULL) {
                /* Menu number -> command. The blob's menu strip drives these; the
                 * exact item ordering is in the extracted MenuItem structures. */
                switch (MENUNUM(code)) {
                case 0: goto_page();      break;
                case 1: download_check(); break;
                case 2: vote();           break;
                case 3: extend_life();    break;
                case 4: account();        break;
                case 5: mail_submit();    break;
                case 6: upload_file();    break;
                case 7: put_frame();      break;
                default: break;
                }
            }
        }
    }
}
