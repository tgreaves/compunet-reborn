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
void launch_tty(void)
{
    IntuitionBase = open_library_checked("intuition.library", 0x21);
    if (IntuitionBase == NULL) fatal_exit(0x14);

    GfxBase = open_library_checked("graphics.library", 0x21);
    if (GfxBase == NULL) fatal_exit(0x14);

    g_screen = open_screen_tracked(0 /* NewScreen in globals */);
    if (g_screen == NULL) fatal_exit(0x14);

    g_window = open_window_tracked(0 /* NewWindow in globals */);
    if (g_window == NULL) fatal_exit(0x14);

    if (build_font() == 0) fatal_exit(0x14);

    if (launch_editor() == 0) fatal_exit(0x14);

    load_config();

    /* Prepare the CnetTty scroll viewer (LoadSeg; run lazily on demand). */
    if (load_seg_tracked("CnetTty") == NULL) fatal_exit(0x14);
}
