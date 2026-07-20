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
#include <intuition/intuition.h>
#include <clib/graphics_protos.h>

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
extern UBYTE g_editor_msg[];  /* DAT_00120146 — CnetEditor startup message */
extern APTR  g_edit_proc;     /* DAT_00120168 — editor semaphore owner (out) */
extern APTR  g_edit_msgport;  /* DAT_0012013e — editor message port (out)   */
extern UBYTE *g_font_base;    /* DAT_00120258 — the built C64 font          */
extern APTR  g_proc;          /* DAT_001200f0 — our Process (FindTask(NULL)) */

/* Editor startup-message field accessors (see globals.c for the layout). */
#define EMSG_REPLYPORT  (*(APTR *)(g_editor_msg + 0x0e))
#define EMSG_STATUS     (g_editor_msg[0x15])
#define EMSG_SCREEN     (*(APTR *)(g_editor_msg + 0x16))   /* in: screen / out: proc */
#define EMSG_FONT       (*(APTR *)(g_editor_msg + 0x1a))   /* in: font  / out: owner  */
#define EMSG_CURDIR     (*(APTR *)(g_editor_msg + 0x1e))

/*
 * launch_editor — recon FUN_001025de. Create a reply port, LoadSeg "CnetEditor",
 * CreateProc it with a 4000-byte stack, hand it a fully-populated startup MESSAGE
 * (reply port + shared screen + font + our current dir) via PutMsg, and wait for its
 * reply. Returns 1 if the editor reports ready (status byte 0), else 0. All
 * allocations are resource-tracked so a failure unwinds cleanly.
 *
 * NB: the message is the struct g_editor_msg (DAT_00120146), NOT &g_editor_port — an
 * earlier reconstruction passed the wrong pointer and left the message unfilled, so
 * the child read a garbage mn_ReplyPort and crashed with a Line-F guru (#0000000B).
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

    /* Populate the startup message (recon fills these fields at $102646-$102660). */
    EMSG_REPLYPORT = g_editor_port;
    EMSG_STATUS    = 0;
    EMSG_SCREEN    = g_screen;
    EMSG_FONT      = (APTR)g_font_base;
    EMSG_CURDIR    = *(APTR *)((UBYTE *)g_proc + 0x98);   /* pr_CurrentDir */

    put_msg(proc, g_editor_msg);
    WaitPort(g_editor_port);
    GetMsg(g_editor_port);

    if (EMSG_STATUS == '\0') {
        /* Editor ready (recon lines 1832-1835): it wrote its message port back into
         * the screen slot (msg+0x16) and its semaphore owner into the font slot
         * (msg+0x1a). Cache both: g_edit_msgport (DAT_0012013e) is the PutMsg target
         * for later editor commands (serial setup, frame display, quit teardown);
         * g_edit_proc (DAT_00120168) is the semaphore owner. */
        g_edit_msgport = EMSG_SCREEN;
        g_edit_proc    = EMSG_FONT;
        resource_commit();      /* keep its resources */
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
/* Faithful transcription of recon FUN_001026ae. Every step and its order matches
 * the disassembly (start $1026ae, a4 = 0x11d000 small-data base); the data-blob
 * structure addresses are the recon's &DAT_ values, verified against the raw
 * m68k listing. Extra externs for the steps the earlier draft omitted: */
/* NB: g_data MUST be UBYTE[] (as in every other module) — the LDATA macro does
 * byte arithmetic on it. An earlier APTR[] typing scaled the offset by 4, so every
 * blob address (menu spec, palette) landed 4x too far into/past the 12520-byte blob,
 * feeding build_menu_strip a garbage spec (nmenus=10851) -> wild allocs/writes -> a
 * boot guru that timing/scaffolding masked (cross-object type mismatch = UB). */
extern UBYTE g_data[];
#define L_DATA_BASE 0x11d000
#define LDATA(off) ((APTR)(g_data + ((off) - L_DATA_BASE)))

extern void  load_screen_palette(APTR viewport, APTR coltable, ULONG n); /* GfxBase.LoadRGB4 (FUN_0012a01c) */
extern APTR  find_task(APTR name);                    /* SysBase.FindTask (FUN_0012907c) */
extern void  set_menu_strip_tracked(APTR win, APTR menu); /* FUN_0011a588 -> SetMenuStrip + track */
extern APTR  build_menu_strip(APTR spec);             /* FUN_0011b000 — build Menu/MenuItem tree */
extern void  set_wait_pointer(void);                  /* FUN_001020ae */

extern APTR  g_main_uport;    /* DAT_00120100 — main window UserPort   */
extern ULONG g_extra_sig;     /* DAT_00120104 — its signal mask        */
extern APTR  g_menu_pair[2];  /* DAT_001201ae/b2 — [menu list, cmd map]*/
extern APTR  g_proc;          /* DAT_001200f0 — our Process            */
extern APTR  g_saved_windowptr;/* DAT_001200f4 — saved pr_WindowPtr    */
extern ULONG g_tty_seg_bptr;  /* DAT_0012016c — CnetTty seg (BPTR*4+4) */


void launch_tty(void)
{
    APTR *pair;
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

    /* Patch the main NewWindow's Screen field (NewWindow@0x11d0e2 + 0x1e = 0x11d100)
     * with our just-opened custom screen, so OpenWindow attaches to it. recon
     * FUN_001026ae line 1872: DAT_0011d100 = DAT_001200f8 — this is a WRITE INTO THE
     * BLOB, not a separate copy. (Writing a detached g_screen_copy left NewWindow.Screen
     * NULL, so the window opened without a proper UserPort and WaitPort faulted.) */
    *(APTR *)LDATA(0x11d100) = g_screen;

    /* Open the main window (NewWindow = DAT_0011d0e2). */
    g_window = open_window_tracked(0);
    if (g_window == NULL) fatal_exit(0x14);

    /* Set the busy pointer on all windows. */
    set_wait_pointer();

    /* Cache the window's UserPort (window+0x56) and its signal mask. The recon
     * computes 1 << UserPort->mp_SigBit (port+0x0f) with no mask (raw move.b +
     * asl.l at $10275a-$102766). */
    g_main_uport = *(APTR *)((UBYTE *)g_window + 0x56);
    g_extra_sig  = 1UL << *(UBYTE *)((UBYTE *)g_main_uport + 0x0f);

    /* Build the menu strip from its spec (&PTR_DAT_0011d172) and attach it to the
     * window. recon: FUN_0011b000 builds a Menu/MenuItem tree and returns a 2-long
     * result [menu list, command map] which is copied into DAT_001201ae/b2
     * (g_menu_pair). Bail if the menu list is NULL; SetMenuStrip via FUN_0011a588. */
    pair = (APTR *)build_menu_strip(LDATA(0x11d172));
    g_menu_pair[0] = pair[0];
    g_menu_pair[1] = pair[1];
    if (g_menu_pair[0] == NULL) fatal_exit(0x14);
    set_menu_strip_tracked(g_window, g_menu_pair[0]);

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
