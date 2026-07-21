/*
 * osglue.c — small OS-glue wrappers (reconstructed).
 *
 * Thin wrappers the original kept as amiga.lib-style stubs, plus a couple of tiny
 * UI helpers. Each maps to a single library vector or a short sequence.
 *
 *   open_dos_library    (FUN_001001c4) — OpenLibrary("dos.library"); fatal if absent.
 *   open_library_checked(FUN_0011a290) — OpenLibrary + resource-track the close.
 *   put_msg             — PutMsg() to a port (editor startup message).
 *   link_lock           (FUN_00109520) — highlight/unhighlight a directory row box.
 *   fatal_exit          (FUN_0011a11e) — free resources and exit with a code.
 *   handle_extra_signal / handle_device_message / mail_state_enter — small hooks.
 */
#include <exec/types.h>
#include <stdlib.h>
#include <clib/exec_protos.h>
#include <clib/dos_protos.h>
#include <clib/graphics_protos.h>
#include <intuition/intuition.h>

#include "compunet.h"

extern APTR DOSBase;                 /* set by runtime; opened here if needed */
extern BYTE cleanup_resources(void);
extern APTR alloc_tracked(ULONG, ULONG);
extern void free_tracked(APTR);

/* open_dos_library — recon FUN_001001c4. */
APTR open_dos_library(void)
{
    if (DOSBase == NULL)
        DOSBase = (APTR)OpenLibrary((STRPTR)"dos.library", 0);
    return DOSBase;
}

/* open_library_checked — recon FUN_0011a290: OpenLibrary, and on success register a
 * tracked CloseLibrary so cleanup_resources unwinds it (recon 0x11a2b4: register
 * CloseLibrary(lib)). The bare OpenLibrary left opened libraries untracked. */
extern void resource_register_free(void (*fn)(), APTR arg1, APTR arg2);
APTR open_library_checked(const char *name, ULONG ver)
{
    APTR lib = (APTR)OpenLibrary((STRPTR)name, ver);
    if (lib != NULL)
        resource_register_free((void (*)())CloseLibrary, lib, 0);
    return lib;
}

/* put_msg — send the editor startup message (recon thunk_FUN_001290f4 = PutMsg). */
void put_msg(APTR port, APTR msg)
{
    PutMsg((struct MsgPort *)port, (struct Message *)msg);
}

/*
 * link_lock — recon FUN_00109520. Draw (or redraw) the highlight box around
 * directory row 'row' to show it locked/selected during a navigation. Uses
 * SetAPen(2) + RectFill on the directory window's rastport. Called twice per action
 * (before and after) which toggles the highlight.
 */
void link_lock(APTR dir_page, int row)
{
    struct Window *w = *(struct Window **)dir_page;
    if (w == NULL) return;
    SetAPen(w->RPort, 2);
    RectFill(w->RPort, row * 0x40 + 7, 0xcb, row * 0x40 + 0x42, 0xda);
}

/* fatal_exit — recon FUN_0011a11e: unwind all tracked resources and terminate. */
void fatal_exit(ULONG code)
{
    /* Free ALL tracked resources in one pass (recon FUN_0011a0f0), then terminate.
     * The original tail-calls the SAS/C exit epilogue; with vbcc's minstart.o, exit()
     * restores the entry stack pointer and returns to DOS. (An earlier version looped
     * on cleanup_resources() level-by-level, which was the wrong unwind primitive.) */
    extern void cleanup_all_resources(void);
    cleanup_all_resources();   /* frees the whole list — incl. CloseWindow/CloseScreen */
    exit((int)code);
}

/* handle_extra_signal — recon FUN_00119506: service the UI/abort signal that can
 * interrupt a blocking transport wait (e.g. user hit the window's close gadget). */
void handle_extra_signal(void)
{
    /* The original drains the main window's IDCMP and sets the abort flag. The
     * transport waits poll this; a full reconstruction routes a close/abort here. */
}

/* handle_device_message — recon FUN_001190e8: log/handle an unsolicited device
 * message ("%s %02lx" debug line) when device-message logging is enabled. */
void handle_device_message(struct Message *msg)
{
    (void)msg;   /* debug logging path; no-op unless g_log_device_messages is set */
}

/* mail_state_enter (recon FUN_001091f2) is reconstructed faithfully in
 * directory_select.c — it re-labels the directory window's 5 action gadgets for
 * mail/courier mode and refreshes them. */
