/*
 * mail.c — mail upload / ID check (reconstructed).
 *
 * MISSED by the original hand-picked module list; recovered by the coverage census
 * (see coverage-census.md). Mail is a gadget-driven dialog that reuses one window
 * shell in two modes:
 *
 *   mail_upload_mode (FUN_0010f09e) — open the window titled "Mail Upload".
 *   id_check_mode    (FUN_0010f116) — open the same window titled "ID Check".
 *   mail_open_window (FUN_0010f000) — the shared window/gadget setup.
 *   mail_submit      (FUN_0010e188) — collect up to 5 recipient name fields, build
 *                    a "U%-16sT" record, send it (TOKEN_COM), wait for '@'.
 *   mail_read        (FUN_0010e468) — the ID-check path: send an "I" record, then
 *                    read the returned frame and format it into the display buffer.
 *
 * Both submit paths use the same command/ack seam (serial_write TOKEN_COM +
 * serial_io_c) as every other command; the recipient record is the C64 "U" mail
 * record with a trailing 'T'.
 */
#include <exec/types.h>
#include <string.h>

#include "compunet.h"

#define STATE_ONLINE 2
#define STATE_LOGIN_CHECK 5

/* Window/dialog helpers into the not-yet-reconstructed UI layer. */
extern LONG mail_open_window(void);      /* FUN_0010f000 */
extern void mail_close_window(void);     /* FUN_0010f18e */
extern LONG mail_run_upload_dialog(void);/* thunk FUN_0010f23a — event loop, mode 1 */
extern LONG mail_run_id_dialog(void);    /* thunk FUN_0010f3c8 — event loop, mode 2 */
extern void set_wait_pointer(void);      /* thunk FUN_001020ae */
extern void clear_wait_pointer(void);    /* thunk FUN_0010221c */
extern void frame_display_mem(APTR src, APTR page); /* thunk FUN_001080da */
extern void mail_append(const char *s);  /* FUN_0010e430 — append to display buf */

/* Mail record fields (recon DAT_00121658..DAT_00121669 region). */
extern char  g_mail_subject[];   /* DAT_00121658 — 16-char subject/name    */
extern char  g_mail_names[];     /* DAT_00121669 — 5 x 9-byte recipient rows */
extern char  g_frame_out[];      /* DAT_001220fc — frame display output      */
extern APTR  g_frame_out_end;    /* DAT_0012309c */
extern void  frame_display_done(APTR out, APTR len); /* thunk FUN_0011754e */

/* Reset the transport-fed frame reader state before reading a mail frame. */
extern UWORD g_frame_pos;    /* DAT_001203a0 */
extern UWORD g_frame_len;    /* DAT_001203a4 */
extern UBYTE *g_frame_capture; /* DAT_001203ae */
extern UBYTE g_frame_eof;    /* DAT_001203ac */

/*
 * append_recipients — shared by mail_submit and mail_read. Appends each non-empty
 * recipient name (up to 5) padded to 8 chars, starting at 'buf', and NUL-terminates.
 * Returns the number of chars written. (recon: the inner 5x8 packing loop in both
 * FUN_0010e188 and FUN_0010e468.)
 */
static int append_recipients(char *buf)
{
    int o = 0;
    int f, i;

    for (f = 0; f < 5; f++) {
        if (g_mail_names[f * 9] != '\0') {
            int pad = 0;
            for (i = 0; i < 8; i++) {
                char c = ' ';
                if (!pad) {
                    c = g_mail_names[f * 9 + i];
                    if (c == '\0') { pad = 1; c = ' '; }
                }
                buf[o++] = c;
            }
        }
    }
    buf[o] = '\0';
    return o;
}

/*
 * mail_submit — recon FUN_0010e188. "Mail Upload" flow: open the dialog, collect
 * recipients, build a "U%-16sT" record and send it.
 */
LONG mail_submit(void)
{
    ULONG len;

    if (mail_open_window() == 0)   /* opens in upload mode via caller */
        return 0;

    clear_wait_pointer();
    if (mail_run_upload_dialog() == 0)
        return 0;
    set_wait_pointer();

    /* "U%-16sT": subject padded to 16, trailing 'T' marker, then recipients. */
    sprintf(g_cmd_buf, "U%-16sT", g_mail_subject);
    append_recipients(g_cmd_buf + strlen(g_cmd_buf));

    len = strlen(g_cmd_buf);
    serial_write(g_cmd_buf, len, 1, TOKEN_COM);
    return (serial_io_c(g_ack_text) == ACK_OK) ? 1 : 0;
}

/*
 * mail_read — recon FUN_0010e468. "ID Check" flow: open the dialog in ID mode,
 * send an "I"-prefixed record, and on ack read the returned frame, appending each
 * decoded field into the display buffer.
 */
LONG mail_read(void)
{
    ULONG len;
    char  field[26];
    int   i, n;

    if (id_check_mode() == 0)
        return 0;

    clear_wait_pointer();
    if (mail_run_id_dialog() == 0)
        return 0;
    set_wait_pointer();

    g_cmd_buf[0] = 'I'; /* recon: DAT_00121588 = 0x49 */
    append_recipients(g_cmd_buf + 1);
    len = strlen(g_cmd_buf);
    serial_write(g_cmd_buf, len, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK) {
        mail_close_window();
        return 0;
    }

    /* Read the response frame into the display area. */
    frame_display_mem("", NULL);        /* recon seeds with a small literal frame */

    /* Reset the frame reader and pull field records until end-of-frame. */
    g_frame_pos = 0;
    g_frame_len = 0;
    g_frame_capture = NULL;
    g_frame_eof = '\0';
    while (g_frame_eof == '\0' || g_frame_pos < g_frame_len) {
        mail_append("\n");
        for (i = 0; i < 8; i++)
            field[i] = read_frame_byte();
        field[8] = '\0';
        mail_append(field);
        mail_append(" ");
        n = 0;
        for (;;) {
            char c = read_frame_byte();
            field[n] = c;
            if (c == 0x1e) break;       /* record separator */
            n++;
        }
        field[n] = '\0';
        mail_append(n == 0 ? "(none)" : field);
        mail_append("\n");
    }

    frame_display_done(g_frame_out, g_frame_out_end);
    mail_close_window();
    return 1;
}

/*
 * mail_upload_mode — recon FUN_0010f09e. Open the window titled "Mail Upload".
 * id_check_mode — recon FUN_0010f116. Same window titled "ID Check". These set the
 * title string the shared window shell displays, then build the mode's gadget list.
 */
extern const char **g_mail_title;   /* PTR_s_Mail_Upload_0011eae2 */

/*
 * mail_prepare — recon FUN_0010e000. Enter mail/courier mode: send the short mail
 * command, and on ack refresh the directory and switch to the login-check state.
 * (Referenced by a menu hook in the data blob.)
 */
extern char g_mail_cmd[];            /* DAT_0011ea5e — the mail-enter command */
extern void directory_refresh(APTR dir_page);
extern void mail_state_enter(APTR dir_page);   /* thunk FUN_001091f2 */

LONG mail_prepare(void)
{
    g_state = STATE_ONLINE;
    serial_write(g_mail_cmd, strlen(g_mail_cmd), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) == ACK_OK) {
        directory_refresh(g_dir_page);
        mail_state_enter(g_dir_page);
        g_state = STATE_LOGIN_CHECK;
        return 1;
    }
    return 0;
}

LONG mail_upload_mode(void)
{
    *g_mail_title = "Mail Upload";
    return mail_open_window();
}

LONG id_check_mode(void)
{
    *g_mail_title = "ID Check";
    return mail_open_window();
}
