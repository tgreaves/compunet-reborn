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
        /* Offline: request page 0 with the literal "P00" (recon serial_write("P00",3,
         * 1,TOKEN_COM) — the string at DAT_0011e3f4). An earlier version sent
         * g_link_code, a different global with variable content — wrong command. */
        serial_write("P00", 3, 1, TOKEN_COM);
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
 * back_dir — recon FUN_0010a29a. The "Back" action gadget: send the single-char "B"
 * (back / up one directory level) as a TOKEN_COM frame and, on ack '@', reload the
 * directory. Same command/ack pattern as goto_page's offline branch, but sends "B"
 * and does not set g_online (we are already online when Back is available).
 */
LONG back_dir(void)
{
    g_state = STATE_GOTO;                       /* recon 0x10a29c: g_state = 2 */
    serial_write("B", 1, 1, TOKEN_COM);         /* recon 0x10a2b8: send "B"    */
    if (serial_io_c(g_ack_text) != ACK_OK)      /* recon 0x10a2ca: ack != '@'  */
        return 0;
    directory_refresh(g_dir_page);              /* recon 0x10a2d8 */
    return 1;
}

/* Frame display state, for frame_more (declared elsewhere; DAT addresses noted). */
extern APTR  frame_display(APTR page, APTR out);      /* thunk FUN_0010818a */
extern void  frame_display_done(APTR out, APTR len);  /* thunk FUN_0011754e */
extern APTR  g_frame_page;                            /* DAT_0011d078 */
extern char  g_frame_out[];                           /* DAT_001220fc */
extern APTR  g_frame_out_end;                         /* DAT_0012309c */
extern UWORD g_frame_hdr_more;                        /* DAT_001203b2 — more-frames flag */

/*
 * frame_more — recon FUN_00113062. The "More" frame button: send the bare "D" (the
 * server's MORE command), display the next frame it returns, and drop back to state 2
 * (which disables More) only when the more-frames flag clears (last frame). On a
 * non-'@' ack, go to state 2 and fail. This is how multi-frame text pages page forward.
 */
LONG frame_more(void)
{
    serial_write("D", 1, 1, TOKEN_COM);            /* recon 0x113076: send "D" (MORE) */
    if (serial_io_c(g_ack_text) != ACK_OK) {       /* recon 0x11308c: ack != '@'      */
        g_state = STATE_GOTO;                       /* recon 0x113094: g_state = 2     */
        return 0;
    }
    g_frame_out_end = frame_display(g_frame_page, g_frame_out);  /* recon 0x1130a4 */
    frame_display_done(g_frame_out, g_frame_out_end);           /* recon 0x1130b4 */
    if (g_frame_hdr_more == 0)                      /* recon 0x1130ba: no more -> state 2 */
        g_state = STATE_GOTO;
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

/*
 * leave_page — recon FUN_00103704, the "Leave" menu item. Sets state=2, sends the
 * single-char "E" command (leave/back) as a TOKEN_COM frame, and reads the ack. On
 * ack '@' it reads the returned goodbye frame and displays it (frame_display /
 * frame_display_done at 0x10373a-0x103760), pauses, then always disconnects. The
 * goodbye-frame display is implemented and working. (The earlier binding wrongly called
 * do_connect here, which redialled instead of leaving.)
 */
extern void  disconnect(void);                        /* FUN_00102968 */
extern APTR  frame_display(APTR page, APTR out);      /* thunk FUN_0010818a */
extern void  frame_display_done(APTR out, APTR len);  /* thunk FUN_0011754e */
extern void  modem_delay(LONG ticks);                 /* FUN_001280f8 = Delay() */
extern char  g_frame_out[];                           /* DAT_001220fc */
extern APTR  g_frame_out_end;                          /* DAT_0012309c */

LONG leave_page(void)
{
    static const char cmd_E[2] = "E";    /* recon DAT_0011d6cc = "E" */
    g_state = STATE_GOTO;                 /* recon 0x103704: g_state = 2 */
    serial_write((APTR)cmd_E, 1, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) == ACK_OK) {
        /* '@': read + display the returned goodbye frame, then pause (recon
         * 0x10373a-0x103760: frame_display / frame_display_done / Delay(0xfa)). */
        g_frame_out_end = frame_display(g_frame_page, g_frame_out);
        frame_display_done(g_frame_out, g_frame_out_end);
        modem_delay(0xfa);
    }
    /* ALWAYS tear down and go offline (recon 0x103762 -> FUN_00102968 disconnect). The
     * earlier reconstruction only disconnected on a non-'@' ack, so a normal LEAVE left
     * the client stuck "online" after the server had already closed the connection. */
    disconnect();
    return 1;
}
