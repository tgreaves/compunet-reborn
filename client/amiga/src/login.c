/*
 * login.c — dial + login sequence (reconstructed).
 *
 *   do_connect             (recon FUN_0010343c) — the full bring-up: open the
 *                          transport, open the logon window, dial the modem, run
 *                          the Compunet handshake, send the login record, and open
 *                          the frame + directory windows once online.
 *   send_login_record      (recon FUN_0011032fa) — build and send the "Z" login
 *                          identity record (userid + password + terminal id).
 *   wait_connect_handshake (recon FUN_00103162)  — read modem/host responses,
 *                          succeed on "@ okay", fail on "NO CARRI".
 *   validate_login         (recon FUN_0010e0fc)  — issue the post-login D command.
 *
 * This is the transport's front door. cnet.device does the actual modem dial and
 * the X.25 framing/CRC; a Reborn TCP transport replaces the dial+carrier steps with
 * a socket connect while keeping the same command/ack handshake below.
 *
 * The original is one deeply-nested function; here the error paths are flattened to
 * a small helper + early returns (behaviour-identical) for readability.
 */
#include <exec/types.h>
#include <clib/exec_protos.h>
#include <string.h>

#include "compunet.h"

/* Connection-state enum values used by set_connection_state (recon DAT_0011d070). */
#define STATE_OFFLINE     0
#define STATE_LOGGING_ON  1
#define STATE_ONLINE      2
#define STATE_LOGIN_CHECK 5

/* Externs into the not-yet-reconstructed UI / directory layer (kept as the recon
 * names' roles). These are the seams do_connect calls out to. */
extern LONG open_logon_window(void);     /* FUN_001030c6 */
extern void close_logon_window(void);    /* FUN_00119450 */
extern void logon_window_ready(void);    /* FUN_0011949a */
extern void close_connection_window(void);/* FUN_0010314c */
extern LONG dial_modem(char *number);    /* FUN_00119950 thunk: dial, io_Command 0xc */
extern void modem_send(const char *s, LONG len);         /* FUN_00103024 */
extern void modem_send_delayed(const char *s, LONG len); /* thunk FUN_001198e0 */
extern void modem_delay(LONG ticks);     /* thunk FUN_001280f8 */
extern ULONG modem_read_status(void);    /* thunk FUN_00119a60 */
extern LONG  logon_poll(void);           /* thunk FUN_00115168 */
extern LONG  open_frame_window(void);    /* thunk FUN_001174d4 */
extern LONG  init_directory(void);       /* thunk FUN_001099c0 */
extern void  set_wait_pointer(void);     /* thunk FUN_001020ae */
extern APTR  frame_display(APTR page, APTR out);  /* thunk FUN_0010818a */
extern void  frame_display_done(APTR out, APTR len); /* thunk FUN_0011754e */
extern LONG  frame_has_more_pages(void); /* tests DAT_001203b2 (top bit of frame hdr) */

extern char g_login_userid[];  /* DAT_00120244 — userid for login record */
extern char g_login_scratch[]; /* DAT_0012024d — scratch/password region  */
extern UBYTE g_frame_indent;   /* DAT_0011d078 == 0 check region          */

/* Frame-parse output buffer + trailing state the frame code shares. */
extern char  g_frame_out[];    /* DAT_001220fc */
extern APTR  g_frame_out_end;  /* DAT_0012309c */

/*
 * send_login_record — build the "Z<userid><password>" identity record plus the
 * terminal id ("AM21" + device version/revision) and write it as a command
 * (recon: FUN_0011032fa). Field widths: userid padded to 8, password to 6.
 */
void send_login_record(void)
{
    char rec[0x1b];      /* 27-byte record, sent whole (len 0x1b) */
    char termid[11];
    int  i, o;

    rec[0] = 'Z';
    o = 1;

    /* userid, space-padded to 8 */
    for (i = 0; g_login_userid[i] != '\0' && i < 8; i++)
        rec[o++] = g_login_userid[i];
    for (; i < 8; i++)
        rec[o++] = ' ';

    /* password/scratch, space-padded to 6 */
    for (i = 0; g_login_scratch[i] != '\0' && i < 6; i++)
        rec[o++] = g_login_scratch[i];
    for (; i < 6; i++)
        rec[o++] = ' ';

    /* remaining bytes (0x0f..0x14) cleared */
    for (o = 0x0f; o < 0x15; o++)
        rec[o] = '\0';

    /* terminal id: "AM21" + device version + revision digits */
    {
        struct Device *dev = g_write_req->io.io_Device;
        UWORD ver = *(UWORD *)((UBYTE *)dev + 0x14);
        UWORD rev = *(UWORD *)((UBYTE *)dev + 0x16);
        memcpy(termid + 6, "AM21", 4);
        termid[10] = (char)ver + '0';
        termid[0]  = (char)rev + '0';   /* (recon stores rev digit in local_11) */
    }

    serial_write(rec, 0x1b, 1, TOKEN_COM);

    /* clear the scratch region for next time */
    for (i = 0; i < 7; i++)
        g_login_scratch[i] = '\0';
}

/*
 * wait_connect_handshake — after dialling, read host status bytes until we see the
 * "@ okay" banner (success) or "NO CARRI[ER]" (failure) in an 8-byte sliding window
 * (recon: FUN_00103162). Returns 1 on success, 0 on failure.
 */
LONG wait_connect_handshake(void)
{
    UBYTE window[9];
    int   i;
    ULONG status;

    for (i = 0; i < 9; i++)
        window[i] = 0;

    for (;;) {
        while ((status = modem_read_status()) == 0)
            modem_delay(5);

        if (status == (ULONG)-1) {
            show_status_message(0x42, "Carrier lost");
            set_connection_error(9);
            /* fall through to keep scanning as the original does */
        }

        /* shift the new byte into the window and test the two banners */
        window[7] = (UBYTE)status;
        if (strcmp((char *)window, "@ okay") == 0)   /* recon "@ okayxk" prefix */
            return 1;
        if (strcmp((char *)window, "NO CARRI") == 0)
            return 0;
        for (i = 0; i < 8; i++)
            window[i] = window[i + 1];
    }
}

/*
 * do_connect — the top-level connect state machine (recon: FUN_0010343c).
 */
LONG do_connect(void)
{
    char  ack;
    UBYTE ser_flags, status_hi;
    ULONG actual;
    char  dial_msg[64];

    /* Must be configured: phone number and a valid baud setting. */
    if (g_phone_number[0] == '\0' || g_baud_setting == 0) {
        show_status_message(1, "Not set up");
        return 0;
    }

    /* Open the transport (ports + cnet.device). */
    switch (open_transport()) {
    case XPORT_OK:
        break;
    case 10:  /* recon: cVar5 == '\n' */
        show_status_message(1, "Modem error");
        return 0;
    case XPORT_FAIL:  /* recon: cVar5 == '\x01' */
        show_status_message(1, "No memory");
        return 0;
    default:
        show_status_message(1, "Can't open cnet.device");
        return 0;
    }

    if (open_logon_window() == 0) {
        close_connection_window();
        close_logon_window();
        show_status_message(1, "Can't open logon window");
        return 0;
    }

    /* Dial. */
    sprintf(dial_msg, "Dialling %s", g_phone_number);
    modem_send(dial_msg, strlen(dial_msg));
    if (dial_modem(g_phone_number) == 0) {
        close_connection_window();
        close_logon_window();
        show_status_message(1, "No answer");
        return 0;
    }

    modem_send("\r", 1);
    modem_send("Carrier detected.", 0x11);
    modem_send("\r", 1);

    /* Two short "K" line-turnaround probes, then wait for >=10 status bytes. */
    modem_delay(0x4b);
    modem_send_delayed("K", 1);      /* recon DAT_0011d666 */
    modem_delay(0x4b);
    modem_send_delayed("K", 1);      /* recon DAT_0011d668 */
    do {
        modem_delay(5);
    } while (modem_read_status() < 10);

    /* The Compunet identification handshake: "C CNET\r" twice + 14 zero bytes. */
    modem_send_delayed("C CNET\r", 7);
    modem_send_delayed("C CNET\r", 7);
    modem_delay(0xfa);
    modem_send_delayed("00000000000000", 0x0f);

    if (wait_connect_handshake() == 0) {
        show_status_message(1, "Failed to connect");
        close_connection_window();
        close_logon_window();
        return 0;
    }

    logon_window_ready();

    /* Send the login record and wait for it to be accepted. */
    ack = serial_io_c(g_ack_text);
    if (ack != ACK_OK) {
        close_connection_window();
        close_logon_window();
        return 0;
    }

    /* Poll the logon window; resend the login record until the host acks it. */
    do {
        if (logon_poll() == 0) {
            close_connection_window();
            close_logon_window();
            return 0;
        }
        send_login_record();
        ack = serial_io_c(g_ack_text);
    } while (ack != ACK_OK);

    close_connection_window();

    /* Bring up the frame window. */
    if (g_frame_page == NULL && open_frame_window() == 0) {
        show_status_message(1, "Can't open frame window");
        close_logon_window();
        return 0;
    }

    set_wait_pointer();
    g_frame_out_end = frame_display(g_frame_page, g_frame_out);
    frame_display_done(g_frame_out, g_frame_out_end);

    /* Drain the first frame until a non-empty status byte arrives. */
    do {
        serial_read(g_ack_text, 0x2a, &ser_flags, &status_hi, &actual);
    } while (ser_flags == '\0');

    /* Bring up the directory. */
    if (g_dir_page == NULL && init_directory() == 0) {
        show_status_message(1, "Can't init directory");
        close_logon_window();
        return 0;
    }

    return 1;
}

/*
 * validate_login — after connecting, request the user's home directory with a
 * "D%02d" command and load the returned frame(s), looping while more remain
 * (recon: FUN_0010e0fc). The page's directory number lives at page+0xc78.
 */
LONG validate_login(void)
{
    ULONG len;
    char  ack;

    g_state = STATE_LOGIN_CHECK;
    sprintf(g_cmd_buf, "D%02d", (int)*(short *)((UBYTE *)g_dir_page + 0xc78));

    do {
        len = strlen(g_cmd_buf);
        serial_write(g_cmd_buf, len, 1, TOKEN_COM);
        ack = serial_io_c(g_ack_text);
        if (ack != ACK_OK)
            return 0;

        g_frame_out_end = frame_display(g_frame_page, g_frame_out);
        frame_display_done(g_frame_out, g_frame_out_end);
        /* recon copies the "next" directory command back into g_cmd_buf and loops
         * while the frame's more-pages flag (DAT_001203b2) is set. */
        strcpy(g_cmd_buf, "D");   /* recon DAT_0011ea70 seed for the next request */
    } while (frame_has_more_pages());

    return 1;
}
