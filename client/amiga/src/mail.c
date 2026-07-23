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
#include <intuition/intuition.h>
#include <clib/exec_protos.h>
#include <clib/intuition_protos.h>

#include "compunet.h"

#define STATE_ONLINE 2
#define STATE_LOGIN_CHECK 5

/* Window/dialog helpers into the not-yet-reconstructed UI layer. */
extern void set_wait_pointer(void);      /* thunk FUN_001020ae */
extern void clear_wait_pointer(void);    /* thunk FUN_0010221c */
extern void frame_display_mem(APTR src, APTR page); /* thunk FUN_001080da */

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

/* Blob small-data access + the mail window (used by mail_submit's recipient-validation
 * display below as well as by the window helpers further down). */
extern UBYTE g_data[];
#define DATA_BASE_M 0x11d000
#define DATAM(off) ((APTR)(g_data + ((off) - DATA_BASE_M)))
extern APTR open_window_tracked(APTR nw);
extern void close_window_tracked(APTR win);
extern APTR g_frame_out_ptr;        /* DAT_0012309c — output write cursor */
extern APTR g_screen;               /* current custom screen */
extern APTR g_dir_page;             /* DAT_0011d07c — directory page; [0] = its Window* */
static struct Window *g_mail_win;   /* DAT_00121698 */
static WORD g_mail_gadpos;          /* DAT_0012169c — saved AddGList position */
extern APTR g_frame_page;           /* DAT_0011d078 — frame page; [0] = its Window* */
extern void mail_close_window(void);/* FUN_0010f18e — defined below */

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

/* ---- Courier action buttons: Done / More / Dnld (recon FUN_0010e058 / e0b4 / e0fc) -------
 * mail_state_enter relabels the 5 directory action gadgets to Done / ID / More / Dnld / Upld
 * in Courier. ID = mail_read and Upld = mail_submit (below); these three are the rest. Each
 * sends a single-letter COM command and reads the ack, like the directory nav commands. */
extern APTR  frame_display(APTR page, APTR out);   /* FUN_0010818a — parse+render a frame */
extern UWORD g_frame_hdr_more;                     /* DAT_001203b2 — more-frames flag      */
extern APTR  g_frame_page;                         /* DAT_0011d078 — frame render target   */
extern void  mail_state_exit(APTR dir_page);       /* FUN_001092a6 — restore dir buttons   */

/*
 * mail_done — recon FUN_0010e058. Leave Courier: send "N", refresh the directory on ack, drop
 * back to STATE_ONLINE, and restore the Dir/Back/Goto/Dnld/Upld action buttons. Returns the
 * online flag.
 */
LONG mail_done(void)
{
    serial_write("N", 1, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK) {
        g_online = 0;                          /* recon 0x10e088: ack fail -> offline */
    } else {
        directory_refresh(g_dir_page);         /* recon 0x10e08e */
        g_online = 1;                          /* recon 0x10e098 */
    }
    g_state = STATE_ONLINE;                     /* recon 0x10e09e: g_state = 2 */
    mail_state_exit(g_dir_page);                /* recon 0x10e0a4 */
    return (LONG)g_online;                      /* recon 0x10e0ae */
}

/*
 * mail_more — recon FUN_0010e0b4. Request the next page of the mail list: send "M".
 */
LONG mail_more(void)
{
    g_state = 5;                                /* recon 0x10e0b6: g_state = 5 (mail-list state) */
    serial_write("M", 1, 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK)
        return 0;
    directory_refresh(g_dir_page);
    return 1;
}

/*
 * mail_download — recon FUN_0010e0fc. Read the selected mail message: send "D%02d" for the
 * highlighted row, display the returned frame, then loop "D" (MORE) while the frame header
 * flags more frames — the multi-frame message reader (same shape as download_text).
 */
LONG mail_download(void)
{
    g_state = 5;                                /* recon 0x10e0fe: g_state = 5 */
    sprintf(g_cmd_buf, "D%02d", (int)*(short *)((UBYTE *)g_dir_page + 0xc78));  /* selected row @0xc78 */
    for (;;) {
        serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);
        if (serial_io_c(g_ack_text) != ACK_OK)
            return 0;
        g_frame_out_end = frame_display(g_frame_page, g_frame_out);   /* recon 0x10e152 */
        frame_display_done(g_frame_out, g_frame_out_end);             /* recon 0x10e164 */
        strcpy(g_cmd_buf, "D");                                       /* recon 0x10e170: re-arm MORE */
        if (g_frame_hdr_more == 0)                                    /* recon 0x10e17e: no more frames */
            break;
    }
    return 1;
}

/* ---- Courier body send: state-7 frame-window Send / Done (recon FUN_0010e398 / e402) -----
 * After Upld (mail_submit) sends the "U<subject>T<recipients>" header it enters g_state=7.
 * The frame-window Send/Done gadgets then drive these two, once per message frame: Send
 * transmits "U" (frame-ready) followed by the current edit frame; Done transmits "N" to
 * deliver the mail. Both mirror put_frame_xfer / put_frame_done, but always keyed "U"/"N"
 * and dropping to the mail-list state (5) rather than STATE_GOTO. */
extern void send_dat_packet(APTR frame);   /* FUN_00108254 (transport.c) — DAT + trailing EOS */
extern APTR g_edit_frame;                  /* DAT_0011d080 — the frame being composed */

/*
 * mail_field_send — recon FUN_0010e398. Courier "Send": transmit "U" (frame-ready), then the
 * current edit frame as a DAT (send_dat_packet appends the EOS terminator). On either ack
 * failure, close the mail window and drop to the mail-list state. On success stays in state 7
 * for the next frame.
 */
LONG mail_field_send(void)
{
    serial_write("U", 1, 1, TOKEN_COM);         /* recon 0x10e3ac: $1a90 = "U" */
    if (serial_io_c(g_ack_text) != ACK_OK) {
        mail_close_window();                    /* recon 0x10e3c8: thunk $10e6c8 = FUN_0010f18e */
        g_state = 5;
        return 0;
    }
    send_dat_packet(g_edit_frame);              /* recon 0x10e3d6: $80 = g_edit_frame */
    if (serial_io_c(g_ack_text) != ACK_OK) {
        mail_close_window();
        g_state = 5;
        return 0;
    }
    return 1;
}

/*
 * mail_field_next — recon FUN_0010e402. Courier "Done": transmit "N" (deliver the mail), close
 * the mail window, and drop to the mail-list state. (Fire-and-forget like put_frame_done — the
 * server's response is picked up by the subsequent mail-list refresh.)
 */
LONG mail_field_next(void)
{
    serial_write("N", 1, 1, TOKEN_COM);         /* recon 0x10e416: $1a94 = "N" */
    mail_close_window();                        /* recon 0x10e422: thunk $10e6c8 = FUN_0010f18e */
    g_state = 5;                                /* recon 0x10e426 */
    return 1;
}

/*
 * mail_show_recipient — recon FUN_0010f544. Draw one recipient row's validation result into
 * the mail window: poke the shared IntuiText (0x11ee2c) with the pen (3 = confirmed name,
 * 1 = rejected), the row Y (row*0xc + 0x1d) and the text, then PrintIText it. The IntuiText's
 * LeftEdge (0x74) and NULL font come pre-initialised in the blob.
 */
static void mail_show_recipient(int row, const char *text, UBYTE pen)
{
    struct IntuiText *it = (struct IntuiText *)DATAM(0x11ee2c);
    it->FrontPen = pen;                          /* $1e2c+0 */
    it->TopEdge  = (WORD)(row * 0xc + 0x1d);      /* $1e32 = +6, via FUN_00101604 mulu + 0x1d */
    it->IText    = (UBYTE *)text;                 /* $1e38 = +0xc */
    PrintIText(g_mail_win->RPort, it, 0, 0);
}

/*
 * mail_clear_status — recon FUN_0010f586. DrawImage the solid-fill box (0x11ee40: Depth 0,
 * PlaneOnOff = 6, 312x20 @ 4,89) over the recipient area to clear it before leaving the dialog.
 */
static void mail_clear_status(void)
{
    DrawImage(g_mail_win->RPort, (struct Image *)DATAM(0x11ee40), 0, 0);
}

/*
 * mail_submit — recon FUN_0010e188. "Mail Upload" flow: open the compose window, collect the
 * subject + up to 5 recipients, send the "U%-16sT<recipients>" header, then read the server's
 * per-recipient validation response and display each confirmed name (or "*** No Such User ***").
 * If any recipient is rejected the dialog re-opens for correction; once all are valid the frame
 * and mail windows come to front and we enter the courier body-send state (7).
 */
LONG mail_submit(void)
{
    ULONG len;
    int   i, j, k, count;
    int   all_valid;

    if (mail_upload_mode() == 0)                 /* recon 0x10e190: open "Mail Upload" window */
        return 0;

    for (;;) {                                   /* recon restart target 0x10e19e */
        clear_wait_pointer();
        if (mail_run_upload_dialog() == 0)       /* recon 0x10e1a2: cancelled */
            return 0;
        set_wait_pointer();

        /* "U%-16sT": subject padded to 16, trailing 'T' marker, then recipients. */
        sprintf(g_cmd_buf, "U%-16sT", g_mail_subject);
        append_recipients(g_cmd_buf + strlen(g_cmd_buf));

        len = strlen(g_cmd_buf);
        serial_write(g_cmd_buf, len, 1, TOKEN_COM);
        if (serial_io_c(g_ack_text) != ACK_OK) { /* recon 0x10e294 */
            mail_close_window();                 /* recon 0x10e29a */
            return 0;
        }

        /* recon 0x10e2a4: read the server's recipient-validation frame. For each non-empty
         * recipient it echoes the 8-char id then the validated real name terminated by 0x1e;
         * an empty name means the id was rejected. */
        g_frame_pos = 0;
        g_frame_len = 0;
        g_frame_capture = NULL;
        g_frame_eof = 0;

        all_valid = 1;                           /* -$32(a5): stays 1 until a row is rejected */
        count = 0;
        for (i = 0; i < 5; i++)                  /* -$10(a5): number of non-empty recipients */
            if (g_mail_names[i * 9] != '\0')
                count++;

        j = 0;
        for (i = 0; i < count; i++) {
            char name[48];
            while (g_mail_names[j * 9] == '\0')  /* recon 0x10e2d0: next non-empty row */
                j++;
            for (k = 0; k < 8; k++)              /* recon 0x10e2f0: discard the 8-char id echo */
                (void)read_frame_byte();
            k = 0;
            for (;;) {                           /* recon 0x10e308: read name until 0x1e */
                UBYTE c = read_frame_byte();
                name[k] = (char)c;
                if (c == 0x1e)
                    break;
                k++;
            }
            name[k] = '\0';                      /* recon 0x10e324: drop the 0x1e */
            if (k == 0) {                        /* recon 0x10e328: empty -> rejected */
                mail_show_recipient(j, "*** No Such User ***", 1);  /* string @ 0x11ea7a */
                all_valid = 0;                   /* recon 0x10e340 */
            } else {
                mail_show_recipient(j, name, 3); /* recon 0x10e346 */
            }
            j++;
        }

        if (!all_valid)                          /* recon 0x10e366: re-open the dialog */
            continue;

        mail_clear_status();                     /* recon 0x10e36e */
        WindowToFront(*(struct Window **)g_frame_page);  /* recon 0x10e372 */
        WindowToFront(g_mail_win);               /* recon 0x10e37e */
        g_state = 7;                             /* recon 0x10e388: courier body-send state */
        return 1;
    }
}

/*
 * mail_read — recon FUN_0010e468. "ID Check" flow: open the dialog in ID mode,
 * send an "I"-prefixed record, and on ack read the returned frame, appending each
 * decoded field into the display buffer.
 */
LONG mail_read(void)
{
    char  field[48];
    char *tmpl;
    int   i, k;

    if (id_check_mode() == 0)                    /* recon 0x10e46c */
        return 0;
    clear_wait_pointer();                        /* recon 0x10e47a */
    if (mail_run_id_dialog() == 0)               /* recon 0x10e47e */
        return 0;
    set_wait_pointer();                          /* recon 0x10e48c */

    g_cmd_buf[0] = 'I';                          /* recon 0x10e490: 0x49 */
    append_recipients(g_cmd_buf + 1);            /* recon 0x10e496: pack recipients after 'I' */
    serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);   /* recon 0x10e542 */
    if (serial_io_c(g_ack_text) != ACK_OK) {     /* recon 0x10e562 */
        mail_close_window();                     /* recon 0x10e568 */
        return 0;
    }

    /* recon 0x10e572: seed the display page and output buffer with the frame template
     * ($1a44). The output cursor g_frame_out_ptr is then advanced by mail_append. */
    frame_display_mem(DATAM(0x11ea44), g_frame_page);
    g_frame_out[0] = 0;                          /* recon 0x10e580 */
    g_frame_out_ptr = &g_frame_out[1];           /* recon 0x10e58a */
    tmpl = (char *)DATAM(0x11ea44);
    for (i = 1; tmpl[i] != '\0'; i++) {          /* recon 0x10e592: copy template[1..] */
        *(UBYTE *)g_frame_out_ptr = (UBYTE)tmpl[i];
        g_frame_out_ptr = (APTR)((UBYTE *)g_frame_out_ptr + 1);
    }

    /* recon 0x10e5b4: reset the frame reader, then read id records until end-of-frame.
     * Each record is an 8-char id followed by the validated real name terminated by 0x1e;
     * an empty name means the id was not found. */
    g_frame_pos = 0;
    g_frame_len = 0;
    g_frame_capture = NULL;
    g_frame_eof = 0;
    while (g_frame_eof == 0 || g_frame_pos < g_frame_len) {     /* recon 0x10e5ca */
        mail_append((char *)DATAM(0x11ea98));    /* "\x1f   " row lead-in */
        for (k = 0; k < 8; k++)                  /* recon 0x10e5ea: 8-char id */
            field[k] = (char)read_frame_byte();
        field[8] = '\0';
        mail_append(field);
        mail_append((char *)DATAM(0x11ea9e));    /* " : " */
        k = 0;                                   /* recon 0x10e624: name until 0x1e */
        for (;;) {
            char c = (char)read_frame_byte();
            field[k] = c;
            if (c == 0x1e)
                break;
            k++;
        }
        field[k] = '\0';                         /* recon 0x10e640: drop the 0x1e */
        if (k == 0)                              /* recon 0x10e648: empty -> not found */
            mail_append((char *)DATAM(0x11eaa2));/* "\x90*** NO SUCH USER ***" */
        else
            mail_append(field);
        mail_append((char *)DATAM(0x11eab8));    /* "\r" */
    }

    /* recon 0x10e674: NUL-terminate the display buffer and render it. */
    *(UBYTE *)g_frame_out_ptr = 0;
    g_frame_out_ptr = (APTR)((UBYTE *)g_frame_out_ptr + 1);
    frame_display_done(g_frame_out, g_frame_out_ptr);   /* recon 0x10e67e */
    mail_close_window();                         /* recon 0x10e68c */
    return 1;
}

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

/*
 * mail_upload_mode — recon FUN_0010f09e. Set the window title to "Mail Upload", open the
 * shared shell, draw the mode's title label, then add + draw the 8 upload gadgets (subject,
 * 5 recipients, Send, Cancel). RemoveGList captures the list position for the dialog loop.
 */
LONG mail_upload_mode(void)
{
    struct NewWindow *nw = (struct NewWindow *)DATAM(0x11eac8);
    nw->Title = (UBYTE *)DATAM(0x11ee68);            /* recon 0x10f09e: "Mail Upload" */
    if (mail_open_window() == 0)
        return 0;
    PrintIText(g_mail_win->RPort, (struct IntuiText *)DATAM(0x11ee00), 0, 0); /* title label */
    AddGList(g_mail_win, (struct Gadget *)DATAM(0x11ed4c), ~0, ~0, NULL);     /* $1d4c: 8 gads */
    RefreshGList((struct Gadget *)DATAM(0x11ed4c), g_mail_win, NULL, ~0);
    g_mail_gadpos = RemoveGList(g_mail_win, (struct Gadget *)DATAM(0x11ed4c), 8); /* ->$469c */
    return 1;
}

/*
 * id_check_mode — recon FUN_0010f116. As mail_upload_mode but titled "ID Check" with the
 * 7-gadget ID list ($1cd8: 5 recipients, OK, Cancel — no subject field).
 */
LONG id_check_mode(void)
{
    struct NewWindow *nw = (struct NewWindow *)DATAM(0x11eac8);
    nw->Title = (UBYTE *)DATAM(0x11ee74);            /* recon 0x10f116: "ID Check" */
    if (mail_open_window() == 0)
        return 0;
    PrintIText(g_mail_win->RPort, (struct IntuiText *)DATAM(0x11ee18), 0, 0); /* title label */
    AddGList(g_mail_win, (struct Gadget *)DATAM(0x11ecd8), ~0, ~0, NULL);     /* $1cd8: 7 gads */
    RefreshGList((struct Gadget *)DATAM(0x11ecd8), g_mail_win, NULL, ~0);
    g_mail_gadpos = RemoveGList(g_mail_win, (struct Gadget *)DATAM(0x11ecd8), 7); /* ->$469c */
    return 1;
}

/* ------------------------------------------------------------------ *
 *  Mail window helpers (recon FUN_0010f000 / f18e / f23a / e430)
 *  (g_data/DATAM/g_mail_win/open_window_tracked are declared up top.)
 * ------------------------------------------------------------------ */

/*
 * mail_open_window — recon FUN_0010f000. Open the shared mail window (blob NewWindow at
 * 0x11eac8), positioned relative to the directory window, clear the fields, and draw the
 * field backdrop image + border. The two callers set NewWindow.Title first.
 *
 * Reconstruction fix: the blob string gadgets' StringInfo.Buffer fields hold stale
 * a4=0x11d000 pointers (0x1216xx), so they are repointed at our C globals g_mail_subject /
 * g_mail_names — exactly the put_frame dialog fix in ui_dialogs.c. Field addresses were
 * found by scanning the blob for the 0x1216xx buffer pointers.
 */
LONG mail_open_window(void)
{
    struct NewWindow *nw  = (struct NewWindow *)DATAM(0x11eac8);
    struct Window    *dir = *(struct Window **)g_dir_page;
    int i;

    nw->Screen   = (struct Screen *)g_screen;         /* recon 0x10f004: 0x11eae6 */
    nw->LeftEdge = dir->LeftEdge + 5;                 /* recon 0x10f00a: dir+5,   0x11eac8 */
    nw->TopEdge  = dir->TopEdge + 0x4b;               /* recon 0x10f01c: dir+0x4b, 0x11eaca */

    g_mail_win = (struct Window *)open_window_tracked(nw);   /* recon 0x10f028 */
    if (g_mail_win == NULL)
        return 0;

    g_mail_subject[0] = 0;                             /* recon 0x10f03e */
    for (i = 0; i < 5; i++)                            /* recon 0x10f042 */
        g_mail_names[i * 9] = 0;

    /* repoint the 6 string-gadget StringInfo.Buffer fields (subject + 5 recipients) */
    *(APTR *)DATAM(0x11ed28) = (APTR)g_mail_subject;      /* subject */
    *(APTR *)DATAM(0x11ecb4) = (APTR)&g_mail_names[0 * 9];/* recipient 0 */
    *(APTR *)DATAM(0x11ec64) = (APTR)&g_mail_names[1 * 9];/* recipient 1 */
    *(APTR *)DATAM(0x11ec14) = (APTR)&g_mail_names[2 * 9];/* recipient 2 */
    *(APTR *)DATAM(0x11ebc4) = (APTR)&g_mail_names[3 * 9];/* recipient 3 */
    *(APTR *)DATAM(0x11eb74) = (APTR)&g_mail_names[4 * 9];/* recipient 4 */

    DrawImage(g_mail_win->RPort,  (struct Image  *)DATAM(0x11ed78), 0, 0); /* recon 0x10f064 */
    DrawBorder(g_mail_win->RPort, (struct Border *)DATAM(0x11edd0), 0, 0); /* recon 0x10f07e */
    return 1;
}

/* mail_close_window — recon FUN_0010f18e. */
void mail_close_window(void)
{
    if (g_mail_win) {
        close_window_tracked(g_mail_win);
        g_mail_win = NULL;
    }
}

/* mail_append — recon FUN_0010e430: append a string to the frame output buffer and
 * render each char into the frame page (so the ID-check result shows on screen). */
void mail_append(const char *s)
{
    UBYTE c;
    while ((c = (UBYTE)*s++) != '\0') {
        *(UBYTE *)g_frame_out_ptr = c;
        g_frame_out_ptr = (APTR)((UBYTE *)g_frame_out_ptr + 1);
        render_char(c, g_frame_page);
    }
}

/*
 * mail_trim — recon FUN_0010f1a4. In place: uppercase a field and strip its leading and
 * trailing spaces. Applied to the subject and each recipient id when the user commits.
 */
static void mail_trim(char *s)
{
    int  in = 0, out = 0;
    char c;
    while ((c = s[in]) != '\0') {                /* recon 0x10f1b6 */
        if (out == 0 && c == ' ') {              /* recon 0x10f1d0: skip leading spaces */
            in++;
            continue;
        }
        if (c >= 'a' && c <= 'z')                /* recon 0x10f1de: uppercase */
            c -= 0x20;
        s[out++] = c;
        in++;
    }
    while (out > 0 && s[out - 1] == ' ')         /* recon 0x10f208: strip trailing spaces */
        out--;
    s[out] = '\0';                               /* recon 0x10f226 */
}

/*
 * mail_dialog_loop — shared body of mail_run_upload_dialog (FUN_0010f23a) and
 * mail_run_id_dialog (FUN_0010f3c8). Re-adds the mode's gadget list at the saved position,
 * activates the first field, then runs the modal IDCMP loop: drain messages keeping the last
 * gadget, and dispatch on GadgetID — 0 = Cancel (close, return 0), 1/2 = OK, 3 = tab to the
 * next field, >=4 = ignore. On OK the fields are trimmed, redrawn, and validated (at least one
 * recipient, and — upload only — a non-empty subject); if valid the gadgets are removed, a
 * confirmation image drawn, and 1 returned; otherwise the loop continues.
 *
 * glist  — the mode's gadget list (0x11ed4c upload / 0x11ecd8 ID)
 * ngad   — total gadgets (8 / 7)          nfield — editable fields (6 / 5)
 * want_subject — validate the subject (upload = 1, ID = 0)
 */
static LONG mail_dialog_loop(APTR glist, int ngad, int nfield, int want_subject)
{
    struct IntuiMessage *msg;
    struct Gadget *last = NULL;
    struct RastPort *rp = g_mail_win->RPort;
    int i, any;

    AddGList(g_mail_win, (struct Gadget *)glist, g_mail_gadpos, ngad, NULL);  /* recon 0x10f244 */
    ActivateGadget((struct Gadget *)glist, g_mail_win, NULL);                 /* recon 0x10f25e */

    for (;;) {
        WaitPort(g_mail_win->UserPort);                       /* recon 0x10f26e */
        while ((msg = (struct IntuiMessage *)GetMsg(g_mail_win->UserPort)) != NULL) {
            last = (struct Gadget *)msg->IAddress;            /* recon 0x10f29a: keep IAddress */
            ReplyMsg((struct Message *)msg);                  /* recon 0x10f2a0 */
        }
        if (last == NULL || last->GadgetID >= 4)              /* recon 0x10f2b2: ignore >=4 */
            continue;
        if (last->GadgetID == 0) {                            /* recon 0x10f2c6: Cancel */
            mail_close_window();
            return 0;
        }
        if (last->GadgetID == 3) {                            /* recon 0x10f2d0: tab to next */
            ActivateGadget(last->NextGadget, g_mail_win, NULL);
            continue;
        }

        /* GadgetID 1/2: OK — recon 0x10f2e6. Trim fields (removed then re-added so the
         * gadgets pick up the trimmed buffers), then validate. */
        g_mail_gadpos = RemoveGList(g_mail_win, (struct Gadget *)glist, nfield);
        if (want_subject)
            mail_trim(g_mail_subject);
        for (i = 0; i < 5; i++)
            mail_trim(&g_mail_names[i * 9]);
        AddGList(g_mail_win, (struct Gadget *)glist, g_mail_gadpos, nfield, NULL);
        RefreshGList((struct Gadget *)glist, g_mail_win, NULL, nfield);

        if (want_subject && g_mail_subject[0] == '\0')        /* recon 0x10f366: subject req'd */
            continue;
        any = 0;                                              /* recon 0x10f36e: >=1 recipient */
        for (i = 0; i < 5; i++)
            if (g_mail_names[i * 9] != '\0') { any = 1; break; }
        if (!any)
            continue;

        g_mail_gadpos = RemoveGList(g_mail_win, (struct Gadget *)glist, ngad);  /* recon 0x10f38e */
        DrawImage(rp, (struct Image *)DATAM(0x11ee54), 0, 0);                   /* recon 0x10f3a8 */
        return 1;
    }
}

LONG mail_run_upload_dialog(void) { return mail_dialog_loop(DATAM(0x11ed4c), 8, 6, 1); }
LONG mail_run_id_dialog(void)     { return mail_dialog_loop(DATAM(0x11ecd8), 7, 5, 0); }
