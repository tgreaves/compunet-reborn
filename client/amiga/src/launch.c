/*
 * launch.c — subprocess launch + top-level UI bring-up (reconstructed).
 *
 *   launch_editor (FUN_001025de) — LoadSeg + run the "CnetEditor" frame editor as a
 *                 child process, passing it a shared message-port + font pointer,
 *                 and wait for its ready reply.
 *   launch_tty    (FUN_001026ae) — the client's main bring-up: open intuition +
 *                 graphics libraries, open the screen/window, build the C64 font,
 *                 launch the editor, load config, and prepare the "CnetTty" viewer.
 *
 * These sit at the top of the program (launch_tty is effectively the client's
 * init). The window/gadget plumbing is UI-layer and delegated to helpers; the
 * control flow and the "open X or bail with error 0x14" pattern are preserved.
 */
#include <exec/types.h>
#include <clib/exec_protos.h>

#include "compunet.h"

/* Library bases (defined in globals.c). */
extern APTR IntuitionBase;
extern APTR GfxBase;

/* Helpers into the OS/UI layer (LoadSeg, CreateProc, OpenScreen/Window, etc). */
extern APTR  open_library_checked(const char *name, ULONG ver); /* FUN_0011a290 */
extern APTR  load_seg_tracked(const char *name);      /* thunk FUN_0011a868 */
extern APTR  create_proc(const char *name, LONG pri, APTR seg, ULONG stack); /* FUN_001280b4 */
extern APTR  open_screen_tracked(APTR ns);            /* thunk FUN_0011a4e0 */
extern APTR  open_window_tracked(APTR nw);            /* thunk FUN_0011a534 */
extern void  fatal_exit(ULONG code);                  /* thunk FUN_0011a11e */
extern void  put_msg(APTR port, APTR msg);            /* thunk FUN_001290f4 */

extern APTR  g_editor_port;   /* DAT_00120142 — editor reply port  */
extern APTR  g_screen;        /* DAT_001200f8 */
extern APTR  g_window;        /* DAT_001200fc */
extern APTR  g_editor_seg;    /* DAT_0011d06c — LoadSeg of CnetEditor */
extern UBYTE g_editor_status; /* DAT_0012015b — editor's ready/fail byte */

/*
 * launch_editor — recon FUN_001025de. Create a reply port, LoadSeg "CnetEditor",
 * CreateProc it with a 4000-byte stack, hand it a startup message (our port + the
 * shared screen + font), and wait for its reply. Returns 1 if the editor reports
 * ready (status byte 0), else 0. All allocations are resource-tracked so a failure
 * unwinds cleanly.
 */
LONG launch_editor(void)
{
    APTR proc;

    resource_mark();

    g_editor_port = create_port_tracked(0, 0);
    if (g_editor_port == NULL) {
        cleanup_resources();
        return 0;
    }

    g_editor_seg = load_seg_tracked("CnetEditor");
    if (g_editor_seg == NULL) {
        cleanup_resources();
        return 0;
    }

    proc = create_proc("CnetEditor", 0, g_editor_seg, 4000);
    if (proc == NULL) {
        cleanup_resources();
        return 0;
    }

    /* Post the startup message (our port + shared screen + font base) and wait. */
    put_msg(proc, &g_editor_port);
    WaitPort(g_editor_port);
    GetMsg(g_editor_port);

    if (g_editor_status == '\0') {
        resource_commit();      /* editor ready — keep its resources */
        return 1;
    }
    cleanup_resources();
    return 0;
}

/*
 * launch_tty — recon FUN_001026ae. Top-level init. Opens the libraries and UI,
 * builds the font, launches the editor, loads config. Any failure calls
 * fatal_exit(0x14). (The screen/window NewScreen/NewWindow structures and gadget
 * lists are UI-layer data; here we show the ordered bring-up and the guards.)
 */
/* CLI progress trace (temporary, for bring-up debugging). Writes to the shell's
 * stdout while it's still visible — the LAST line printed pins which init step
 * faulted. Remove once bring-up is stable. */
#include <clib/dos_protos.h>
static ULONG dbg_len(const char *s){ const char *p=s; while(*p)p++; return (ULONG)(p-s); }
static void dbg(const char *s)
{
    BPTR out = Output();
    if (out) { Write(out, (APTR)s, (LONG)dbg_len(s)); Write(out, (APTR)"\n", 1); }
}

/* Faithful transcription of recon FUN_001026ae. Every step and its order matches
 * the disassembly; data-blob structure addresses are the recon's &DAT_ values.
 * Extra externs for the steps the earlier draft omitted: */
extern APTR g_data[];
#define L_DATA_BASE 0x11d000
#define LDATA(off) ((APTR)(g_data + ((off) - L_DATA_BASE)))

extern void  load_screen_palette(APTR viewport, APTR coltable, ULONG n); /* GfxBase.LoadRGB4 (FUN_0012a01c) */
extern APTR  find_task(APTR name);                    /* SysBase.FindTask (FUN_0012907c) */
extern void  set_menu_strip_tracked(APTR win, APTR menu); /* FUN_0011a588 -> SetMenuStrip + track */
extern APTR  build_menu_strip(APTR spec);             /* FUN_0011b000 — build Menu/MenuItem tree */
extern void  set_wait_pointer(void);                  /* FUN_001020ae */

extern APTR  g_main_uport;    /* DAT_00120100 — main window UserPort   */
extern ULONG g_extra_sig;     /* DAT_00120104 — its signal mask        */
extern APTR  g_menu_strip;    /* DAT_001201ae — built Menu list        */
extern ULONG g_menu_extra;    /* DAT_001201b2 */
extern APTR  g_proc;          /* DAT_001200f0 — our Process            */
extern APTR  g_saved_windowptr;/* DAT_001200f4 — saved pr_WindowPtr    */
extern APTR  g_screen_copy;   /* DAT_0011d100 — screen ptr copy        */
extern ULONG g_tty_seg_bptr;  /* DAT_0012016c — CnetTty seg (BPTR*4+4) */

void launch_tty(void)
{
    APTR *sprite;
    APTR  seg;

    IntuitionBase = open_library_checked("intuition.library", 0x21);
    if (IntuitionBase == NULL) fatal_exit(0x14);

    GfxBase = open_library_checked("graphics.library", 0x21);
    if (GfxBase == NULL) fatal_exit(0x14);

    /* Open the custom screen (NewScreen = DAT_0011d098+10). */
    g_screen = open_screen_tracked(0);
    if (g_screen == NULL) fatal_exit(0x14);

    /* Load the screen's 16-colour palette into its ViewPort (screen+0x2c).
     * recon: LoadRGB4(&screen->ViewPort, &DAT_0011d0c2, 16). */
    load_screen_palette((UBYTE *)g_screen + 0x2c, LDATA(0x11d0c2), 0x10);
    g_screen_copy = g_screen;

    /* Open the main window (NewWindow = DAT_0011d0e2). */
    g_window = open_window_tracked(0);
    if (g_window == NULL) fatal_exit(0x14);

    /* Set the busy pointer on all windows. */
    set_wait_pointer();

    /* Cache the window's UserPort (window+0x56) and its signal mask. */
    g_main_uport = *(APTR *)((UBYTE *)g_window + 0x56);
    g_extra_sig  = 1UL << (*(UBYTE *)((UBYTE *)g_main_uport + 0x0f) & 0x3f);

    /* Build the menu strip from its spec (&PTR_DAT_0011d172) and attach it to the
     * window. recon: FUN_0011b000 builds a Menu/MenuItem tree and returns a 2-word
     * result [menu, extra]; SetMenuStrip(window, menu) via FUN_0011a588. */
    sprite = (APTR *)build_menu_strip(LDATA(0x11d172));
    g_menu_strip = sprite[0];
    g_menu_extra = (ULONG)sprite[1];
    if (g_menu_strip == NULL) fatal_exit(0x14);
    set_menu_strip_tracked(g_window, g_menu_strip);

    /* Build the C64 font from the embedded charset. */
    if (build_font() == 0) fatal_exit(0x14);

    /* Point our Process's pr_WindowPtr (+0xb8) at our window so system requesters
     * appear on our screen; save the old value to restore on editor-launch failure. */
    g_proc = find_task(NULL);
    g_saved_windowptr = *(APTR *)((UBYTE *)g_proc + 0xb8);
    *(APTR *)((UBYTE *)g_proc + 0xb8) = g_window;

    if (launch_editor() == 0) {
        *(APTR *)((UBYTE *)g_proc + 0xb8) = g_saved_windowptr;
        fatal_exit(0x14);
    }

    load_config();

    /* LoadSeg the CnetTty viewer; keep its seg (as BPTR*4+4, recon DAT_0012016c). */
    seg = load_seg_tracked("CnetTty");
    if (seg == NULL) fatal_exit(0x14);
    g_tty_seg_bptr = (ULONG)seg * 4 + 4;
}
