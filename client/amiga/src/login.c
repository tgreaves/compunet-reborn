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
#include "net.h"

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

    /* terminal id written directly into rec[0x15..0x1a] (recon 0x1033c0-0x1033fe):
     * "AM21" then the device version and revision digits. The original writes these
     * into the record buffer itself — an earlier reconstruction wrote them into a
     * separate local array that was never sent, leaving rec[0x15..0x1a] uninitialised
     * garbage in the transmitted login record. */
    {
        /* TCP mode has no cnet.device (g_write_req is NULL); use the cnet.device 2.1
         * version/revision so the "AM21" terminal id + digits are still well-formed.
         * (These bytes become the server's cnload hash check, which an Amiga client
         * never matches anyway, so LINKING is simply not skipped.) */
        UWORD ver = 2, rev = 1;
        if (!g_tcp_mode) {
            struct Device *dev = g_write_req->io.io_Device;
            ver = *(UWORD *)((UBYTE *)dev + 0x14);
            rev = *(UWORD *)((UBYTE *)dev + 0x16);
        }
        rec[0x15] = 'A';
        rec[0x16] = 'M';
        rec[0x17] = '2';
        rec[0x18] = '1';
        rec[0x19] = (char)(ver + 0x30);   /* version digit  (recon add.l #$30) */
        rec[0x1a] = (char)(rev + 0x30);   /* revision digit                    */
    }

    serial_write(rec, 0x1b, 1, TOKEN_COM);

    /* clear the scratch region for next time */
    for (i = 0; i < 7; i++)
        g_login_scratch[i] = '\0';
}

/*
 * wait_connect_handshake — recon FUN_00103162. After dialling, read host bytes and scan
 * for the connect banner. Faithful transcription of the original's byte loop:
 *
 *   - modem_read_status() gives the count of bytes waiting; 0 -> Delay(5) and retry;
 *     -1 -> "Carrier lost" (code 0x42) + longjmp(g_jmpbuf, 9).
 *   - read the bytes in chunks of at most 0x28 via serial_io_variant into g_hs_read.
 *   - per byte c: mask to 7 bits; 0x5f ('_') or 0x0d ('\r') -> 0x0a ('\n'); a '?' or '*'
 *     arms line-capture (line_flag). While armed: a '\n' flushes the accumulated line to
 *     the logon window (flush_logon_line) and, if the line begins "*con", returns 1
 *     (success); otherwise a printable char (0x20..0x7e) is appended to g_hs_line, which
 *     is flushed first if it reached 0x28 chars.
 *   - every byte is also pushed into an 8-byte sliding window (newest at [7], then the
 *     window shifts left) tested against "@ okayxk" (success -> 1) and "NO CARRI"
 *     (failure -> 0). Verified strings: 0x11d5ce "*con", 0x11d5d4 "@ okayxk",
 *     0x11d5de "NO CARRI", 0x11d5c0 "Carrier lost".
 */
extern void  serial_io_variant(APTR buf, UWORD len);  /* FUN_0011998a */
extern char  g_hs_line[];        /* DAT_001201c4 */
extern UWORD g_hs_line_len;      /* DAT_001201ee */
extern UBYTE g_hs_read[];        /* DAT_001201f2 */

/* flush_logon_line — recon FUN_001030ae: echo the accumulated line to the logon window
 * (modem_send of g_hs_line for g_hs_line_len chars) and reset the length. */
static void flush_logon_line(void)
{
    modem_send(g_hs_line, (LONG)g_hs_line_len);
    g_hs_line_len = 0;
}

LONG wait_connect_handshake(void)
{
    UBYTE window[9];
    ULONG status, got, chunk, j, k;
    UBYTE line_flag = 0;

    for (j = 0; j < 9; j++)
        window[j] = 0;

    for (;;) {
        while ((status = modem_read_status()) == 0)
            modem_delay(5);

        if (status == (ULONG)-1) {
            show_status_message(0x42, "Carrier lost");
            set_connection_error(9);         /* longjmp — does not return */
        }

        for (got = 0; got < status; ) {
            chunk = status - got;
            if (chunk > 0x28) chunk = 0x28;
            got += chunk;
            serial_io_variant(g_hs_read, (UWORD)chunk);

            for (j = 0; j < chunk; j++) {
                UBYTE c = g_hs_read[j] & 0x7f;
                if (c == 0x5f || c == 0x0d)
                    c = 0x0a;
                if (c == '?' || c == '*')
                    line_flag = 1;
                if (line_flag) {
                    if (c == 0x0a) {
                        flush_logon_line();
                        line_flag = 0;
                        /* Connection signal. The original matched lowercase "*con" (real
                         * Compunet sent lowercase); the Reborn server sends uppercase
                         * "*CON" (what the C64 receives). Match case-insensitively so the
                         * Amiga client recognises the Reborn signal. */
                        if (g_hs_line[0] == '*' &&
                            (g_hs_line[1] | 0x20) == 'c' &&
                            (g_hs_line[2] | 0x20) == 'o' &&
                            (g_hs_line[3] | 0x20) == 'n')
                            return 1;
                    } else if (c >= 0x20 && c <= 0x7e) {
                        if (g_hs_line_len == 0x28)
                            flush_logon_line();
                        g_hs_line[g_hs_line_len++] = c;
                    }
                }
                window[7] = c;
                if (strcmp((char *)window, "@ okayxk") == 0)
                    return 1;
                if (strcmp((char *)window, "NO CARRI") == 0)
                    return 0;
                for (k = 0; k < 8; k++)
                    window[k] = window[k + 1];
            }
        }
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

    /* Must be configured: either a TCPHOST server address (Reborn TCP), or a phone
     * number + valid baud setting (legacy modem path). */
    if (!net_host_configured() && (g_phone_number[0] == '\0' || g_baud_setting == 0)) {
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
        /* recon 0x1034ba: only close_logon_window here (no close_connection_window). */
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

    /* recon 0x103528 / 0x103544: the bracketing sends are a single SPACE (0x20 at
     * 0x11d650 / 0x11d664), not CR. The middle line is "Carrier detected." (17 bytes). */
    modem_send(" ", 1);
    modem_send("Carrier detected.", 0x11);
    modem_send(" ", 1);

    /* Two "_" line-turnaround probes (recon 0x11d666/0x11d668 = 0x5f, underscore — NOT
     * "K"), each after a 0x4b-tick delay, then wait for >=10 status bytes. */
    modem_delay(0x4b);
    modem_send_delayed("_", 1);      /* recon DAT_0011d666 = '_' */
    modem_delay(0x4b);
    modem_send_delayed("_", 1);      /* recon DAT_0011d668 = '_' */
    do {
        modem_delay(5);
    } while (modem_read_status() < 10);

    /* The Compunet identification handshake: "C CNET\r" twice, delay, then 14 '0' chars
     * followed by a CR (recon 0x11d67a = fourteen 0x30 + 0x0d, total length 0x0f). */
    modem_send_delayed("C CNET\r", 7);
    modem_send_delayed("C CNET\r", 7);
    modem_delay(0xfa);
    modem_send_delayed("00000000000000\r", 0x0f);

    if (wait_connect_handshake() == 0) {
        show_status_message(1, "Failed to connect");
        close_connection_window();
        close_logon_window();
        return 0;
    }

    logon_window_ready();

    /* Pre-login host ack: the original Compunet PAD sent an initial ack after "*con",
     * before the login record. The Reborn server instead waits for the login frame after
     * *CON, so reading here would deadlock — skip it in TCP mode and go straight to the
     * send-login loop below (which sends the record first, then reads the ack). */
    if (!g_tcp_mode) {
        ack = serial_io_c(g_ack_text);
        if (ack != ACK_OK) {
            close_connection_window();
            close_logon_window();
            return 0;
        }
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
