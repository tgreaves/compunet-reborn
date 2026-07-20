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
extern void main_event_loop(void);   /* recon FUN_00102814 — Intuition IDCMP loop */
extern void open_dos_library(void);  /* recon FUN_001001c4 */

int main(void)
{
    /* The runtime has already set SysBase and the a4 small-data base. Open DOS,
     * then bring up the whole client. */
    open_dos_library();
    launch_tty();          /* opens libraries, screen, window, font; loads config */

    /* Enter the Intuition event loop. It only returns when the user quits, at
     * which point the SAS/C runtime epilogue (or our cleanup) frees everything. */
    main_event_loop();
    return 0;
}
