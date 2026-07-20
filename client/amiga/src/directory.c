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
#include <string.h>

#include "compunet.h"

#define STATE_GOTO   2
#define STATE_UPLOAD 8

/* UI prompt helpers (dialogs) into the not-yet-reconstructed UI layer. */
extern LONG  vote_choice_prompt(void);  /* FUN_0010c4ca — read a 1-digit choice   */
extern LONG  extend_by_prompt(void);    /* FUN_0010c404 — "Extend By" dialog       */
extern void  status_ok_dialog(const char *title, const char *body); /* FUN_00110472 */
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
    serial_write("ACCOUNT", strlen("ACCOUNT"), 1, TOKEN_COM);
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
    status_ok_dialog("ACCOUNT", msg);
    return 1;
}

/*
 * put_frame — recon FUN_0010c2f8. Publish the frame currently in the editor. The
 * page must have room and a valid LIFE and page type. Builds
 * "U%-16s%c%03d.%02d%03d" (name, type, page.subpage, life) then dispatches to a
 * per-page-type upload handler (put_frame_xfer). The per-type jump table and the
 * "No room / Invalid Life / Invalid page type" guards are preserved.
 */
extern LONG  put_frame_xfer(void);      /* FUN_0010c270 — send cmd + DAT payload */
extern LONG  put_frame_type_ok(char type); /* per-type validity (recon jump table) */
extern short g_put_life;   /* DAT_0012161a — parsed LIFE value        */
extern short g_put_page;   /* DAT_00121612 — parsed page number       */
extern short g_put_sub;    /* DAT_00121616 — parsed sub-page number   */
extern char  g_put_type;   /* DAT_00121605 — page type char           */
extern char  g_put_name[]; /* DAT_001215f4 — 16-char frame name        */

#define PAGE_FULL_FLAG(p) (*(short *)((UBYTE *)(p) + 0xc76))

LONG put_frame(void)
{
    if (PAGE_FULL_FLAG(g_dir_page) == 0xb) {
        show_status_message(1, "No room on this page");
        return 0;
    }
    if (g_put_life < 1) {
        show_status_message(1, "Invalid Life");
        dir_action_cleanup();
        return 0;
    }

    sprintf(g_cmd_buf, "U%-16s%c%03d.%02d%03d",
            g_put_name, g_put_type, g_put_page, g_put_sub, g_put_life);

    if (!put_frame_type_ok(g_put_type)) {
        show_status_message(1, "Invalid page type");
        dir_action_cleanup();
        return 0;
    }

    return put_frame_xfer();   /* sends g_cmd_buf, then the frame as DAT blocks */
}
