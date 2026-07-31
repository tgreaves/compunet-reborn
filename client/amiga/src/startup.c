/*
 * startup.c — program entry (reconstructed intent).
 *
 * The original binary's `start` (recon FUN_00100000) and `exit` (FUN_0010012e) are
 * the SAS/Lattice C runtime startup: BCPL argv unpacking, small-data (a4) base
 * setup, library-base zeroing, and the cleanup epilogue that closes DOSBase and
 * frees the resource list. In a real SAS/C (or vbcc) build that code is supplied by
 * the compiler's own startup object (c.o / startup.o) — it is NOT application logic,
 * and hand-porting the decompiled register arithmetic would be both inaccurate and
 * pointless. So here we provide the idiomatic C entry point that the runtime would
 * call into, and let the toolchain supply the true startup/teardown.
 *
 * The application's real init is launch_tty() (recon FUN_001026ae), which opens the
 * libraries, screen, window and font and launches the editor; the main event loop
 * is FUN_00102814. main() below expresses that top-level sequence.
 */
#include <exec/types.h>

#include "compunet.h"

extern APTR SysBase;
extern APTR AbsExecBase;             /* set by the runtime startup */
extern void open_dos_library(void);  /* recon FUN_001001c4 */

/* #129 TEMPORARY diagnostic trace (download.c). Not part of the reconstruction —
 * remove with the rest of the instrumentation once the IFF display defect is found. */
extern void cnet_log_open(void);
extern void cnet_log(const char *s);

int main(void)
{
    /* The runtime (vbcc minstart.o) has set SysBase and the a4 small-data base and
     * called us. Open DOS, then hand off to the reconstructed top level (recon
     * FUN_001029e6): launch_tty() brings up the UI, an abort setjmp is armed, and the
     * Intuition event loop runs forever. client_main() does not return. */
    open_dos_library();
    wb_startup_begin();   /* Workbench launch: take the WBStartup msg + cwd = icon's drawer,
                           * so the startup LoadSeg("CnetEditor"/"CnetTty") and TCPHOST/config
                           * reads resolve (minstart.o, unlike the original's SAS/C c.o, does
                           * not do this — hence the guru on double-click). Harmless from CLI. */
    /* ⚠ AFTER wb_startup_begin(), which sets the cwd to the icon's drawer — that is
     * what makes the relative log path land beside the executable. Opened here so the
     * file's mere existence proves the client started and the trace works, which the
     * download-time version could not: it left nothing behind when the run stopped
     * before the transfer. */
    cnet_log_open();
    /* BUILD TAG: identifies WHICH binary wrote the trace. A stale log was read as a
     * fresh run once already — the timestamps disagreed but the content looked
     * plausible. Bump this whenever the debug build changes. */
    cnet_log("=== CompunetDebug started (#129 IFF trace) build=D9-complete ===");
    client_main();
    return 0;
}
