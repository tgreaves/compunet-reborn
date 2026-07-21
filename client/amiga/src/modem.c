/*
 * modem.c — dial / modem-status transport calls (reconstructed).
 *
 * These sit alongside transport.c: they drive cnet.device with the modem-control
 * io_Commands rather than plain read/write, and they're what do_connect (login.c)
 * uses to dial and run the Compunet handshake.
 *
 *   dial_modem        (FUN_00119950) — io_Command 0xc (dial): DoIO, succeeds if
 *                     io_Error == 0.
 *   modem_read_status (FUN_00119a60) — io_Command 0xe (status/carrier poll): SendIO
 *                     + wait, returns io_Actual (the status word).
 *   modem_send_delayed(FUN_001198e0) — CMD_WRITE with a wait on the write signal;
 *                     used for the "C CNET" handshake bytes.
 *   modem_delay       (FUN_001280f8) — AmigaDOS Delay() (ticks).
 *   modem_send        (FUN_00103024) — echo a string into the logon window's
 *                     scrolling text area (dial progress / "Carrier detected.").
 *
 * A Reborn TCP transport replaces dial_modem/modem_read_status with a socket
 * connect + carrier check; the handshake bytes still flow through modem_send_delayed
 * unchanged.
 */
#include <exec/types.h>
#include <clib/exec_protos.h>
#include <clib/dos_protos.h>

#include "compunet.h"

#define CNET_CMD_WRITE_M  3
#define CNET_CMD_DIAL     0xc
#define CNET_CMD_STATUS   0xe

extern ULONG g_extra_sig;                    /* DAT_00120104 */
extern void  handle_extra_signal(void);      /* FUN_00119506 */

/* The logon window's scrolling-text sink (recon FUN_00103024 machinery). These are
 * UI-layer; modem_send delegates the actual text rendering to the window helper. */
extern void  logon_text_append(const char *s, int len);  /* the FUN_00103024 body */

/* Wait for a write-request completion on the write port (recon inline loop). */
static void wait_write(void)
{
    ULONG mask = g_extra_sig | g_write_sig;
    ULONG got;
    do {
        do {
            got = Wait(mask);
            if (got & g_extra_sig)
                handle_extra_signal();
        } while (!(got & g_write_sig));
    } while (GetMsg(g_write_port) == NULL);
}

/* Wait for a read-request completion on the read port. */
static void wait_read(void)
{
    ULONG mask = g_extra_sig | g_read_sig;
    ULONG got;
    do {
        do {
            got = Wait(mask);
            if (got & g_extra_sig)
                handle_extra_signal();
        } while (!(got & g_read_sig));
    } while (GetMsg(g_read_port) == NULL);
}

/*
 * dial_modem — recon FUN_00119950. Point the write request at the dial string and
 * issue io_Command 0xc synchronously (DoIO). Returns TRUE (dialled) if io_Error==0.
 */
LONG dial_modem(char *number)
{
    g_write_req->io.io_Data    = (APTR)number;
    g_write_req->io.io_Command = CNET_CMD_DIAL;
    DoIO((struct IORequest *)g_write_req);
    return g_write_req->io.io_Error == 0;
}

/*
 * modem_read_status — recon FUN_00119a60. Issue io_Command 0xe on the read request
 * and wait; the status word comes back in io_Actual.
 */
ULONG modem_read_status(void)
{
    g_read_req->io.io_Command = CNET_CMD_STATUS;
    SendIO((struct IORequest *)g_read_req);
    wait_read();
    return g_read_req->io.io_Actual;
}

/*
 * modem_send_delayed — recon FUN_001198e0. Write raw bytes (CMD_WRITE) and wait for
 * completion. Used for the "C CNET\r" identification bytes during connect.
 */
void modem_send_delayed(const char *data, ULONG len)
{
    g_write_req->io.io_Data    = (APTR)data;
    g_write_req->io.io_Length  = len;
    g_write_req->io.io_Command = CNET_CMD_WRITE_M;
    SendIO((struct IORequest *)g_write_req);
    wait_write();
}

/*
 * serial_io_variant — recon FUN_0011998a. A read variant used by the link (download)
 * path: point the read request at buf/len, issue io_Command 2 (read), and wait exactly
 * like wait_read (Wait on read_sig|extra_sig, servicing extra, until the reply arrives).
 * If the completed request reports io_Error 9 (carrier lost, at io+0x1f) it pops the
 * fatal "Carrier lost" requester (code 0x42) and longjmps back to the top level. */
extern void set_connection_error(int code);   /* longjmp FUN_00101638 */
extern void show_status_message(UBYTE code, const char *text);

void serial_io_variant(APTR buf, LONG len)
{
    g_read_req->io.io_Data    = (APTR)buf;
    g_read_req->io.io_Length  = len;
    g_read_req->io.io_Command = CNET_CMD_READ;   /* 2 */
    SendIO((struct IORequest *)g_read_req);
    wait_read();
    if (((UBYTE *)g_read_req)[0x1f] == 9) {       /* io_Error == carrier lost */
        show_status_message(0x42, "Carrier lost");
        set_connection_error(1);
    }
}

/*
 * link_viewer_exit — recon FUN_001194c8. End a link session: set the write request's
 * scratch byte (+0x2c) to 1 and issue io_Command 9 (the device's "session end" /
 * login-ready control), synchronously.
 */
void link_viewer_exit(void)
{
    ((UBYTE *)g_write_req)[0x2c] = 1;
    g_write_req->io.io_Command = 9;
    DoIO((struct IORequest *)g_write_req);
}

/* modem_delay — recon FUN_001280f8 = AmigaDOS Delay(). */
void modem_delay(LONG ticks)
{
    Delay(ticks);
}

/* modem_send — recon FUN_00103024: echo dial progress into the logon window. */
void modem_send(const char *s, LONG len)
{
    logon_text_append(s, (int)len);
}
