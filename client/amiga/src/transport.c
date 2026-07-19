/*
 * transport.c — cnet.device serial I/O (reconstructed).
 *
 * Reconstructed from recon_annotated.c: serial_write @0011956a, serial_read
 * @0011967c. These submit a single IORequest (CMD_WRITE / CMD_READ) with SendIO,
 * then Wait() on the combined signal set of the device port, this request's reply
 * port, and an "extra" UI/abort signal, draining messages until this request
 * completes. On completion they inspect io_Error and surface "Carrier lost" /
 * "Comms problem" as needed.
 *
 * cnet.device itself performs the modem dial and the X.25 framing/CRC; this layer
 * just hands it (data, length, command) and waits. This is the seam a future TCP
 * transport replaces.
 *
 * Struct note: the original stashes two bytes in the request's io_Offset field
 * (offsets +0x2c/+0x2d), which serial.device does not use. We preserve that exactly
 * via the io_Offset byte accessors below rather than inventing field names.
 *   +0x2c = high byte of io_Offset   (write: ser_flags param; read: out_ser_flags)
 *   +0x2d = next byte of io_Offset   (write: status param;   read: out_status)
 */
#include <exec/types.h>
#include <exec/io.h>
#include <exec/ports.h>
#include <devices/serial.h>
#include <clib/exec_protos.h>

#include "compunet.h"

extern ULONG g_extra_sig;                          /* was DAT_00120104 (UI/abort signal) */
extern void  handle_extra_signal(void);            /* was FUN_00119506 */
extern void  handle_device_message(struct Message *msg); /* was FUN_001190e8 */
extern BOOL  g_log_device_messages;                /* was DAT_0011fd74 */
extern void  set_connection_error(int code);       /* was thunk_FUN_00101638(&DAT_00120170,n) */

/* The two scratch bytes the client keeps in io_Offset. io_Offset is a ULONG at
 * +0x2c; byte +0x2c is bits 31..24, byte +0x2d is bits 23..16 (68k big-endian). */
#define REQ_B2C(req)  (((UBYTE *)&(req)->IOSer.io_Offset)[0])
#define REQ_B2D(req)  (((UBYTE *)&(req)->IOSer.io_Offset)[1])

/*
 * Wait for the in-flight request on 'my_port' (my_sig) to complete, replying to any
 * device-port messages and servicing the extra UI signal meanwhile. Mirrors the
 * shared do/while loop in both serial routines.
 */
static void wait_for_completion(struct MsgPort *my_port, ULONG my_sig)
{
    ULONG mask = g_extra_sig | my_sig | g_device_sig;
    ULONG got;
    struct Message *msg;

    do {
        got = Wait(mask);

        if (got & g_device_sig) {
            msg = GetMsg(g_device_port);
            if (g_log_device_messages)
                handle_device_message(msg);
            /* original clears (msg + 0x14): the io_Device word of the returned
             * request, used here as a scratch reset. */
            ((struct IORequest *)msg)->io_Message.mn_ReplyPort = NULL;
        }

        if (got & g_extra_sig)
            handle_extra_signal();

    } while (!(got & my_sig) || (GetMsg(my_port) == NULL));
}

/* Classify io_Error and show the appropriate message. The original returns 1 from
 * every path (success and error alike). */
static LONG report_result(BYTE io_error)
{
    if (io_error == CNET_ERR_EXPECTED)
        return 1;
    if (io_error == CNET_ERR_CARRIER) {
        show_status_message(0x42, "Carrier lost");
        set_connection_error(9);
        return 1;
    }
    if (io_error == CNET_ERR_OK)
        return 1;

    show_status_message(0x42, "Comms problem");
    set_connection_error(7);
    return 1;
}

LONG serial_write(APTR data, ULONG length, UBYTE status_hi, UBYTE ser_flags)
{
    g_write_req->IOSer.io_Data    = data;
    g_write_req->IOSer.io_Length  = length;
    REQ_B2C(g_write_req)          = ser_flags;   /* +0x2c */
    REQ_B2D(g_write_req)          = status_hi;   /* +0x2d */
    g_write_req->IOSer.io_Command = CMD_WRITE;   /* 3 */

    SendIO((struct IORequest *)g_write_req);
    wait_for_completion(g_write_port, g_write_sig);

    return report_result(g_write_req->IOSer.io_Error);
}

LONG serial_read(APTR data, ULONG length,
                 UBYTE *out_ser_flags, UBYTE *out_status_hi, ULONG *out_actual)
{
    g_read_req->IOSer.io_Data    = data;
    g_read_req->IOSer.io_Length  = length;
    g_read_req->IOSer.io_Command = CMD_READ;     /* 2 */

    SendIO((struct IORequest *)g_read_req);
    wait_for_completion(g_read_port, g_read_sig);

    *out_ser_flags = REQ_B2C(g_read_req);                /* +0x2c */
    *out_status_hi = REQ_B2D(g_read_req);                /* +0x2d */
    *out_actual    = g_read_req->IOSer.io_Actual;        /* +0x20 */

    return report_result(g_read_req->IOSer.io_Error);
}
