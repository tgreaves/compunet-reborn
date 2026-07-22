/*
 * directory.c — directory / page action commands (reconstructed).
 *
 * These four commands were MISSED by the original hand-picked module list and
 * recovered by the coverage census (see coverage-census.md). They are all
 * command/ack exchanges over TOKEN_COM:
 *
 *   vote        (FUN_0010c510) — V%02d%s : cast a vote on the current page.
 *   extend_life (FUN_0010c428) — X%02d%4.4s : extend a page's LIFE (not directories).
 *   account     (FUN_0010c582) — ACCOUNT : query and display the account balance.
 *   put_frame   (FUN_0010c2f8) — U%-16s%c%03d.%02d%03d : publish an edited frame.
 *
 * The page's directory number is at dir_page+0xc78; per-row metadata (page type,
 * name) lives in the 0x66-byte-per-row table at dir_page+0x790..+0x82e.
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/intuition_protos.h>
#include <string.h>

#include "compunet.h"

#define STATE_GOTO   2
#define STATE_UPLOAD 8

/* UI prompt helpers (dialogs) into the not-yet-reconstructed UI layer. */
extern LONG  vote_choice_prompt(void);  /* FUN_0010c4ca — read a 1-digit choice   */
extern LONG  extend_by_prompt(void);    /* FUN_0010c404 — "Extend By" dialog       */
extern void  status_ok_dialog(const char *line1, const char *line2, UBYTE p4, UBYTE p5); /* FUN_00110472 */
extern void  dir_action_cleanup(void);  /* thunk FUN_0010d0d0 */

extern char  g_vote_choice[];   /* DAT_0012164c — the vote string       */
extern char  g_extend_days[];   /* DAT_00121648 — the extend-by string  */

#define DIR_NO(p)     (*(short *)((UBYTE *)(p) + 0xc78))
#define ROW_TYPE(p,r) (*(char  *)((UBYTE *)(p) + (r) * 0x66 + 0x828))

/*
 * vote — recon FUN_0010c510. Prompt for a choice digit, then send "V%02d%s"
 * (page number + choice) and wait for the ack.
 */
LONG vote(void)
{
    char  cmd[8];
    ULONG len;

    g_state = STATE_GOTO;
    g_vote_choice[0] = 0;
    if (vote_choice_prompt() == 0)
        return 0;

    sprintf(cmd, "V%02d%s", (int)DIR_NO(g_dir_page), g_vote_choice);
    len = strlen(cmd);
    serial_write(cmd, len, 1, TOKEN_COM);
    return (serial_io_c(g_ack_text) == ACK_OK) ? 1 : 0;
}

/*
 * extend_life — recon FUN_0010c428. Extend the LIFE of the current page. Directory
 * pages (type 'D') cannot be extended. Sends "X%02d%4.4s".
 */
LONG extend_life(void)
{
    char  cmd[16];
    ULONG len;
    short page_no;

    g_state = STATE_GOTO;
    page_no = DIR_NO(g_dir_page);

    if (ROW_TYPE(g_dir_page, page_no) == 'D') {
        show_status_message(1, "Can't extend directories");
        return 0;
    }

    g_extend_days[0] = 0;
    if (extend_by_prompt() == 0)
        return 0;

    sprintf(cmd, "X%02d%4.4s", (int)page_no, g_extend_days);
    len = strlen(cmd);
    serial_write(cmd, len, 1, TOKEN_COM);
    return (serial_io_c(g_ack_text) == ACK_OK) ? 1 : 0;
}

/*
 * account — recon FUN_0010c582. Send the literal "ACCOUNT" command, read back the
 * balance string, and show "You are <amount> in credit/debit".
 */
LONG account(void)
{
    char  balance[16];
    char  msg[0x47];
    UBYTE ser_flags, status_hi;
    ULONG actual;
    int   i;
    const char *side;

    g_state = STATE_GOTO;
    /* Wire command is the single byte 'A' (recon serial_write("A",1,1,TOKEN_COM) —
     * strlen of "A" = 1). "ACCOUNT" is ONLY the requester title below, NOT the
     * command sent to the server. */
    serial_write("A", 1, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK)
        return 0;

    serial_read(balance, 0x10, &ser_flags, &status_hi, &actual);
    balance[actual] = '\0';

    /* skip leading spaces; a leading '-' means debit */
    for (i = 0; balance[i] == ' '; i++)
        ;
    side = "credit";
    if (balance[i] == '-') {
        i++;
        side = "debit";
    }

    sprintf(msg, "You are %s in %s", balance + i, side);
    status_ok_dialog("ACCOUNT", msg, 1, 6);   /* recon: p4=1, p5=6 (FrontPen 6) */
    return 1;
}

/*
 * put_frame — recon FUN_0010c2f8. Publish the frame currently being edited. Verified
 * structure (full disasm trace):
 *   1. if page-full flag (dir+0xc76) == 0xb -> "No room on this page", return 0
 *   2. run the publish dialog (FUN_0010d0e6); if it returns 0 (cancel), return 0
 *   3. sscanf the dialog's "page.sub" string (g_put_type_str) with "%d.%d" and its
 *      life string (g_put_life_str) with "%d" into the LONG globals
 *   4. if life <= 0 -> "Invalid Life", dir_action_cleanup, return 0
 *   5. sprintf(g_cmd_buf,"U%-16s%c%03d.%02d%03d", name, type, page, sub, life)
 *   6. dispatch on type via the jump table at 0x10c3c2 (verified from the raw bytes,
 *      stride 6 = [key.w][bra.w]):
 *        'T'           -> put_frame_publish (FUN_0010c250): bring the edit + courier
 *                         windows to front, g_state = 4, return 1 (in-editor text frame)
 *        'A','S','P','F' -> upload_file (FUN_0010c0ee): stream a local file as the
 *                         frame content, using the "U…" header put_frame just built
 *        any other     -> "Invalid page type", dir_action_cleanup, return 0
 * (put_frame does NOT call put_frame_xfer/FUN_0010c270 — that belongs to the editor.)
 */
extern LONG  put_frame_dialog(void);    /* FUN_0010d0e6 — the publish details requester */
extern LONG  put_frame_publish(void);   /* FUN_0010c250 — close edit windows + state=4  */
extern LONG  upload_file(void);         /* FUN_0010c0ee — stream local file as content  */
extern LONG  g_put_life;   /* DAT_0012161a — parsed LIFE (LONG)       */
extern LONG  g_put_page;   /* DAT_00121612 — parsed page (LONG)       */
extern LONG  g_put_sub;    /* DAT_00121616 — parsed sub-page (LONG)   */
extern char  g_put_type[];     /* DAT_00121605 — page type char        */
extern char  g_put_type_str[]; /* DAT_00121607 — "page.sub" string     */
extern char  g_put_life_str[]; /* DAT_0012160e — life string           */
extern char  g_put_name[];     /* DAT_001215f4 — 16-char frame name    */

#define PAGE_FULL_FLAG(p) (*(short *)((UBYTE *)(p) + 0xc76))

LONG put_frame(void)
{
    if (PAGE_FULL_FLAG(g_dir_page) == 0xb) {
        show_status_message(1, "No room on this page");
        return 0;
    }
    if (put_frame_dialog() == 0)            /* recon gate: cancel -> abort */
        return 0;

    g_put_page = 0; g_put_sub = 0;
    sscanf(g_put_type_str, "%d.%d", &g_put_page, &g_put_sub);
    g_put_life = 0;
    sscanf(g_put_life_str, "%d", &g_put_life);

    if (g_put_life <= 0) {
        show_status_message(1, "Invalid Life");
        dir_action_cleanup();
        return 0;
    }

    sprintf(g_cmd_buf, "U%-16s%c%03d.%02d%03d",
            g_put_name, g_put_type[0], (int)g_put_page, (int)g_put_sub, (int)g_put_life);

    switch (g_put_type[0]) {                      /* recon jump table @0x10c3c2 */
    case 'T':
        return put_frame_publish();              /* in-editor text frame */
    case 'A': case 'S': case 'P': case 'F':
        return upload_file();                    /* stream a local file  */
    default:
        show_status_message(1, "Invalid page type");
        dir_action_cleanup();
        return 0;
    }
}

/*
 * put_frame_publish — recon FUN_0010c250. The 'T' (text) publish path: the frame is
 * already in the editor, so nothing is uploaded. It just brings the two windows to the
 * front and switches state. Verified disasm: WindowToFront(*0x11d078); WindowToFront
 * (0x121650); g_state (0x11d070) = 4; return 1. (0x12b1ec is a WindowToFront veneer —
 * jsr -0x138(IntuitionBase) — NOT CloseWindow.) */
extern APTR g_frame_page;    /* DAT_0011d078 — page struct; [0] = its Window */
extern APTR g_courier_win;   /* DAT_00121650 — courier/publish window        */

LONG put_frame_publish(void)
{
    WindowToFront(*(struct Window **)g_frame_page);   /* recon: WindowToFront(*0x11d078) */
    WindowToFront((struct Window *)g_courier_win);    /* recon: WindowToFront(0x121650)  */
    g_state = 4;
    return 1;
}

/*
 * put_frame_xfer — recon FUN_0010c270. Send the "U" publish command in g_cmd_buf,
 * and on ack send the edited frame's data as a DAT packet, then confirm. Sets the
 * connection state back to directory on completion.
 */
extern void send_dat_packet(APTR frame);
extern APTR g_edit_frame;    /* DAT_0011d080 — the frame being published */
extern void dir_action_cleanup(void);

LONG put_frame_xfer(void)
{
    serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK) {
        dir_action_cleanup();
        g_state = STATE_GOTO;
        return 0;
    }
    send_dat_packet(g_edit_frame);
    if (serial_io_c(g_ack_text) != ACK_OK) {
        dir_action_cleanup();
        g_state = STATE_GOTO;
        return 0;
    }
    return 1;
}
