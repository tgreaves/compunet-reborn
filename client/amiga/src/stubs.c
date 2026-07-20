/*
 * stubs.c — placeholder bodies for not-yet-reconstructed helpers.
 *
 * These are the UI (Intuition window/gadget/menu), DOS file I/O, and modem-
 * script functions that the reconstructed application modules call into but
 * which have not themselves been reconstructed yet. Each is a linkable no-op so
 * the whole program links into a HUNK executable and the reconstructed logic can
 * be exercised. They are NOT faithful — replacing each with its real
 * reconstruction (from the recon_annotated.c address noted where known) is the
 * remaining work. Grouped by subsystem.
 *
 * See coverage-census.md: the 53 census functions are reconstructed in the other
 * modules; these stubs are the supporting UI/IO glue below the application layer.
 */
#include <exec/types.h>
#include "compunet.h"

/* ---- data globals referenced across modules ---- */
/* g_ctrl_lo / g_ctrl_hi are now real (frame_control.c) */
APTR  g_editor_port = 0;
APTR  g_editor_seg  = 0;
/* g_editor_status is a byte inside the startup message (globals.c: g_editor_msg[0x15]). */
APTR  g_screen = 0;
APTR  g_window = 0;
APTR  g_res_list = 0;    /* PTR_DAT_0011ff1c */
BYTE  g_res_level = 0;   /* DAT_0011ff2a */

/* ---- function stubs ---- */
