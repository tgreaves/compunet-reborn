/*
 * navigate.c — page navigation commands (reconstructed).
 *
 *   goto_page      (FUN_0010a1e2) — the P command: request a page by number, or
 *                  re-request the current directory page.
 *   link_follow    (FUN_001098e8) — the L command: follow the link under a gadget
 *                  (6-char link code stored in the directory page).
 *   link_goto      (FUN_0010a310) — the L command: prompt for a link code and go.
 *   (set_connection_state, recon FUN_001023ec, now lives in ui_state.c.)
 *
 * All server commands go out through serial_write(..., TOKEN_COM) and wait for the
 * '@' ack via serial_io_c — the same command/ack pattern as the C64 client.
 */
#include <exec/types.h>
#include <clib/exec_protos.h>
#include <string.h>

#include "compunet.h"

#define STATE_GOTO   2   /* recon DAT_0011d070 = 2 while navigating */

/* Refresh the on-screen directory after a successful navigation (FUN_00109a5e). */
extern void directory_refresh(APTR dir_page);   /* thunk FUN_00109a5e */
/* Prompt helpers into the UI layer. */
extern LONG goto_page_prompt(void);             /* FUN_0010a2e2 "Goto Page" */
extern void link_lock(APTR dir, int n);         /* FUN_00109520 */

extern short g_goto_page_no; /* DAT_0012157e — the number entered in Goto Page */
extern char  g_link_code[];  /* DAT_00121580 region — 6-char link code buffer  */

/*
 * goto_page — recon FUN_0010a1e2. If not yet online (g_online==0), send the
 * bare directory request; otherwise send "P%02d" for the page whose number lives
 * at dir_page+0xc78.
 */
LONG goto_page(void)
{
    char  cmd[8];
    ULONG len;

    g_state = STATE_GOTO;

    if (g_online == 0) {
        len = strlen(g_link_code);       /* recon DAT_0011e3f8: bare "D" request */
        serial_write(g_link_code, len, 1, TOKEN_COM);
        if (serial_io_c(g_ack_text) != ACK_OK)
            return 0;
        directory_refresh(g_dir_page);
        g_online = 1;
        return 1;
    }

    sprintf(cmd, "P%02d", (int)*(short *)((UBYTE *)g_dir_page + 0xc78));
    len = strlen(cmd);
    serial_write(cmd, len, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK)
        return 0;
    directory_refresh(g_dir_page);
    return 1;
}

/*
 * link_follow — recon FUN_001098e8. Follow the 6-char link code stored for the
 * currently-selected directory row (page+0x790 + row*7). Returns 0 if the row has
 * no link.
 */
LONG link_follow(APTR gadget)
{
    UBYTE *g   = (UBYTE *)gadget;
    short  row = *(short *)(g + 0x26);
    UBYTE *dir = *(UBYTE **)(g + 0x30);
    char  *code = (char *)(dir + row * 7 + 0x790);
    char   cmd[8];
    ULONG  len;

    if (code[0] == '\0')
        return 0;

    link_lock(dir, 2);
    g_state = STATE_GOTO;
    sprintf(cmd, "L%.6s", code);
    len = strlen(cmd);
    serial_write(cmd, len, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) == ACK_OK) {
        directory_refresh(g_dir_page);
        g_online = 1;
        link_lock(dir, 2);
        return 1;
    }
    link_lock(dir, 2);
    return 0;
}

/*
 * link_goto — recon FUN_0010a310. Prompt for a link code ("Goto Page" dialog) and
 * issue "L%.6s".
 */
LONG link_goto(void)
{
    char  cmd[8];
    ULONG len;

    g_state = STATE_GOTO;
    g_goto_page_no = 0;
    if (goto_page_prompt() == 0)
        return 0;

    sprintf(cmd, "L%.6s", (char *)&g_goto_page_no);
    len = strlen(cmd);
    serial_write(cmd, len, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) == ACK_OK) {
        directory_refresh(g_dir_page);
        g_online = 1;
        return 1;
    }
    return 0;
}

/* set_connection_state (recon FUN_001023ec) is reconstructed faithfully in
 * ui_state.c — it retitles every window AND drives the per-state menu-enable and
 * directory/frame gadget-enable tables from the data blob. (The earlier title-only
 * approximation that lived here has been removed.) */
