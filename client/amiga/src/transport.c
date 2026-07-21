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
 * Struct note: the request is a compact 54-byte cnet.device block (struct
 * CnetRequest), not stock IOExtSer. The client reuses two serial-unused bytes in
 * io_Offset as scratch — REQ_SERFLAGS/REQ_STATUS accessors (see compunet.h) — which
 * we preserve exactly rather than inventing serial field names.
 */
#include <exec/types.h>
#include <exec/io.h>
#include <exec/ports.h>
#include <clib/exec_protos.h>

#include <stddef.h>   /* offsetof */

#include "compunet.h"

/*
 * Compile-time proof that our struct models the same bytes the original touched.
 * CTASSERT is a negative-array-size trick (C89-safe; no C11 _Static_assert needed).
 * These offsets are exactly what recon_annotated.c reads/writes on the request.
 */
#define CT_CAT_(a,b) a##b
#define CT_CAT(a,b)  CT_CAT_(a,b)
#define CTASSERT(cond) typedef char CT_CAT(ct_assert_,__LINE__)[(cond) ? 1 : -1]
CTASSERT(offsetof(struct IOStdReq, io_Command) == 0x1c);
CTASSERT(offsetof(struct IOStdReq, io_Error)   == 0x1f);
CTASSERT(offsetof(struct IOStdReq, io_Actual)  == 0x20);
CTASSERT(offsetof(struct IOStdReq, io_Length)  == 0x24);
CTASSERT(offsetof(struct IOStdReq, io_Data)    == 0x28);
CTASSERT(offsetof(struct IOStdReq, io_Offset)  == 0x2c);
CTASSERT(offsetof(struct IOStdReq, io_Device)  == 0x14);
CTASSERT(sizeof(struct IOStdReq) <= CNET_REQ_SIZE);

extern ULONG g_extra_sig;                          /* was DAT_00120104 (UI/abort signal) */
extern void  handle_extra_signal(void);            /* was FUN_00119506 */
extern void  handle_device_message(struct Message *msg); /* was FUN_001190e8 */
extern BOOL  g_log_device_messages;                /* was DAT_0011fd74 */
/* set_connection_error() is declared in compunet.h */

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

/* Classify io_Error (read from the request at +0x1f) and act. VERIFIED against the
 * relocated disasm of serial_read (0x119744) and serial_io_c (0x119834): io_Error 0
 * is SUCCESS; io_Error 9 is carrier lost; io_Error 7 OR any other non-zero value is a
 * comms error. (An earlier reconstruction wrongly treated 7 as "expected/normal" and
 * silently returned success on it — so a genuine comms failure was ignored instead of
 * aborting.) The error paths set_connection_error(...) which longjmps back to the
 * top-level; the function only "returns 1" on the success path. */
static LONG report_result(BYTE io_error)
{
    if (io_error == 0)                      /* success */
        return 1;
    if (io_error == 9) {                    /* carrier lost */
        show_status_message(0x42, "Carrier lost");
        set_connection_error(9);            /* longjmp — no return */
    }
    show_status_message(0x42, "Comms problem");   /* 7 or any other non-zero */
    set_connection_error(7);                /* longjmp — no return */
    return 1;
}

LONG serial_write(APTR data, ULONG length, UBYTE status_hi, UBYTE ser_flags)
{
    g_write_req->io.io_Data    = data;
    g_write_req->io.io_Length  = length;
    REQ_SERFLAGS(g_write_req)  = ser_flags;   /* +0x2c */
    REQ_STATUS(g_write_req)    = status_hi;   /* +0x2d */
    g_write_req->io.io_Command = CNET_CMD_WRITE;   /* 3 */

    SendIO((struct IORequest *)g_write_req);
    wait_for_completion(g_write_port, g_write_sig);

    return report_result(g_write_req->io.io_Error);
}

LONG serial_read(APTR data, ULONG length,
                 UBYTE *out_ser_flags, UBYTE *out_status_hi, ULONG *out_actual)
{
    g_read_req->io.io_Data    = data;
    g_read_req->io.io_Length  = length;
    g_read_req->io.io_Command = CNET_CMD_READ;     /* 2 */

    SendIO((struct IORequest *)g_read_req);
    wait_for_completion(g_read_port, g_read_sig);

    *out_ser_flags = REQ_SERFLAGS(g_read_req);           /* +0x2c */
    *out_status_hi = REQ_STATUS(g_read_req);             /* +0x2d */
    *out_actual    = g_read_req->io.io_Actual;           /* +0x20 */

    return report_result(g_read_req->io.io_Error);
}

/*
 * serial_io_c — issue a command and read back the server's single-byte ACK.
 * (recon: FUN_0011979e / serial_io_c). Submits io_Command 0xb on the read
 * request and waits, then classifies the result:
 *   io_Error 7 (expected)      -> return the ack byte in io_Offset[0] (+0x2c)
 *   io_Error 9 (carrier lost)  -> "Carrier lost",  return ACK_OK-as-fail
 *   io_Error 0 (ok)            -> inspect the ack byte:
 *        'B' -> error   : show status_text as an error, return ACK_OK (fail)
 *        'A' -> message : show status_text as a message,  return ACK_MSG
 *        '@' -> accepted                                  return ACK_OK
 *   else                       -> "Comms problem", return ACK_OK (fail)
 *
 * Callers compare the return against ACK_OK ('@'). ACK_MSG ('A') also counts as
 * success at some call sites; the original returns the raw ack so callers decide.
 */
#define CNET_CMD_IO_ACK  0xb

UBYTE serial_io_c(const char *status_text)
{
    UBYTE ack;

    g_read_req->io.io_Data    = (APTR)status_text;
    g_read_req->io.io_Command = CNET_CMD_IO_ACK;
    SendIO((struct IORequest *)g_read_req);
    wait_for_completion(g_read_port, g_read_sig);

    /* io_Error (at +0x1f): VERIFIED (recon 0x119834) — 0 = success (classify the ack
     * byte at +0x2c); 9 = carrier lost; 7 or any other non-zero = comms error. (Was
     * inverted: treated 7 as the success/ack path.) */
    switch (g_read_req->io.io_Error) {
    case 0:                                 /* success — classify the ack byte */
        ack = REQ_SERFLAGS(g_read_req);     /* +0x2c */
        if (ack == ACK_ERR) {               /* 'B' — error with message */
            show_status_message(0x42, status_text);
            set_connection_error(0x42);
            return ACK_OK;
        }
        if (ack == ACK_MSG) {               /* 'A' — accepted with message */
            show_status_message(0x41, status_text);
            return ACK_MSG;
        }
        return ACK_OK;                      /* '@' (0x40) or other -> accepted */

    case 9:                                 /* carrier lost */
        show_status_message(0x42, "Carrier lost");
        set_connection_error(9);
        return ACK_OK;

    default:                                /* 7 or any other non-zero -> comms error */
        show_status_message(0x42, "Comms problem");
        set_connection_error(7);
        return ACK_OK;
    }
}

/*
 * send_dat_packet — write a frame's payload as a DAT block (recon: FUN_00108254).
 * The frame block stores its length at +0x12 and its data at +0x16. The original
 * calls serial_write(frame+0x16, frame->len, 1, TOKEN_DAT).
 */
void send_dat_packet(APTR frame)
{
    UBYTE *f = (UBYTE *)frame;
    ULONG  len = *(ULONG *)(f + 0x12);
    serial_write(f + 0x16, len, 1, TOKEN_DAT);
}
