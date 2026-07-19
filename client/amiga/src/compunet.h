/*
 * compunet.h — shared declarations for the reconstructed Amiga Compunet client.
 *
 * This is a from-scratch, idiomatic reconstruction of the original 1989 SAS/Lattice C
 * client (see client/amiga/vintage/), verified per-function against the decompiled
 * reference in client/amiga/vintage/tools/re/recon_annotated.c.
 *
 * Goal: readable and compilable with SAS/C (and vbcc m68k-amigaos as a proxy on
 * modern hosts). Uses standard Amiga system includes and real struct types instead
 * of the decompiler's raw offset arithmetic.
 *
 * Kickstart 1.3 target (the era of the original binary).
 */
#ifndef COMPUNET_H
#define COMPUNET_H

#include <exec/types.h>
#include <exec/ports.h>
#include <exec/io.h>
#include <exec/nodes.h>

/*
 * CnetRequest — the request block the client uses with cnet.device.
 *
 * The original allocates 0x36 (54) bytes via CreateExtIO: a standard IOStdReq
 * (48 bytes) plus a 6-byte custom tail. It is NOT a stock IOExtSer (which is
 * larger). cnet.device defines its own compact request. We model it exactly so
 * the field offsets match the decompiled reference byte-for-byte.
 *
 * The client reuses the (serial-unused) io_Offset bytes as scratch:
 *   io_Offset byte 0 (+0x2c): serial flags / read: out_ser_flags
 *   io_Offset byte 1 (+0x2d): status hi     / read: out_status
 *   io_Offset byte 2 (+0x2e): set to a config value at open (UWORD @ +0x2e)
 * Custom tail:
 *   +0x32 baud_up   (UWORD)  — 75   for Compunet's 1275 split-baud
 *   +0x34 baud_down (UWORD)  — 1200
 */
struct CnetRequest {
    struct IOStdReq io;         /* 0x00..0x2f — standard IO request (io_Offset @0x2c) */
    UWORD           baud_up;    /* 0x30/0x32 region — see accessor note below */
    UWORD           baud_down;  /* Compunet 1275 split baud: 75 up / 1200 down */
};
/*
 * The original touches three sub-fields the stock structs don't name:
 *   +0x2c/+0x2d : two scratch bytes in io_Offset (serial flags + status hi)
 *   +0x2e       : a UWORD in the high half of io_Offset (a config param at open)
 *   +0x32,+0x34 : the baud_up / baud_down UWORDs in the custom tail
 * Because these straddle io_Offset and the tail, transport.c/connect.c use the
 * byte/word accessor macros below (indexed from the request base) rather than
 * relying on struct padding. Total CreateExtIO size:
 */
#define CNET_REQ_SIZE   0x36    /* size passed to CreateExtIO by the original */
#define REQ_SERFLAGS(r) (((UBYTE *)(r))[0x2c])
#define REQ_STATUS(r)   (((UBYTE *)(r))[0x2d])
#define REQ_PARAM2E(r)  (*(UWORD *)((UBYTE *)(r) + 0x2e))
#define REQ_BAUD_UP(r)  (*(UWORD *)((UBYTE *)(r) + 0x32))
#define REQ_BAUD_DN(r)  (*(UWORD *)((UBYTE *)(r) + 0x34))

/* ------------------------------------------------------------------ *
 *  Transport layer — cnet.device serial I/O
 * ------------------------------------------------------------------ *
 * The original opens cnet.device (a serial.device wrapper that dials the
 * modem and does the X.25 framing/CRC) with two IORequests sharing reply
 * ports, and Wait()s on signal masks for completion. In the decompiled
 * reference these are the globals g_device_port / g_read_req / g_write_req.
 *
 * io_Error values observed (IOExtSer.IOSer.io_Error):
 *   7  = expected/normal completion       (recon: '\a')
 *   9  = carrier lost                      (recon: '\t')
 *   0  = ok / no error
 * anything else is treated as "Comms problem".
 *
 * The client also stashes two scratch bytes in the request's io_Offset field
 * (+0x2c/+0x2d) — serial.device does not use io_Offset. transport.c preserves that
 * exactly rather than inventing serial field names.
 */
#define CNET_ERR_OK        0
#define CNET_ERR_EXPECTED  7   /* normal completion */
#define CNET_ERR_CARRIER   9   /* carrier lost */

/* Transport request/port state (was g_read_req/g_write_req/g_device_port etc). */
extern struct CnetRequest *g_read_req;   /* read  request (CMD_READ)  */
extern struct CnetRequest *g_write_req;  /* write request (CMD_WRITE) */
extern struct MsgPort     *g_device_port;/* shared reply port            */
extern struct MsgPort     *g_read_port;  /* read-completion reply port   */
extern struct MsgPort     *g_write_port; /* write-completion reply port  */
extern ULONG               g_device_sig; /* 1 << device_port mp_SigBit   */
extern ULONG               g_read_sig;   /* 1 << read_port   mp_SigBit   */
extern ULONG               g_write_sig;  /* 1 << write_port  mp_SigBit   */

/* serial_read / serial_write: submit one request and wait for completion,
 * servicing the other ports' signals meanwhile. Return 1 on completion
 * (including error, which also shows a status message). */
LONG serial_write(APTR data, ULONG length, UBYTE status_hi, UBYTE ser_flags);
LONG serial_read(APTR data, ULONG length,
                 UBYTE *out_ser_flags, UBYTE *out_status_hi, ULONG *out_actual);

/* Result codes from open_transport() (was do_connect's status switch):
 *   0 = success
 *   1 = resource allocation / OpenDevice failure ("Can't open cnet.device")
 *   3 = device opened but reported a bad version/unit (io_Device check) */
#define XPORT_OK        0
#define XPORT_FAIL      1
#define XPORT_BADVER    3

char open_transport(void);   /* was FUN_001192b6 */

/* ------------------------------------------------------------------ *
 *  Resource-tracked allocation wrappers (SAS/C-style auto-cleanup).
 *  The original registers each created resource with an unwind list so a
 *  single cleanup_resources() frees everything on error/exit.
 * ------------------------------------------------------------------ */
struct MsgPort  *create_port_tracked(char *name, LONG pri);      /* was thunk_FUN_0011a75c */
struct IOExtSer *create_extio_tracked(struct MsgPort *port, ULONG size); /* was thunk_FUN_0011a80e */
BOOL             open_device_tracked(const char *name, ULONG unit,
                                     struct IORequest *req, ULONG flags); /* was thunk_FUN_0011a2e8 */
void             cleanup_resources(void);                        /* was thunk_FUN_0011a0b0 */
void             resource_mark(void);                            /* was thunk_FUN_0011a000 */
void             resource_commit(void);                          /* was thunk_FUN_0011a00a */

/* ------------------------------------------------------------------ *
 *  Status / UI helpers (defined elsewhere in the reconstruction)
 * ------------------------------------------------------------------ */
void show_status_message(UBYTE code, const char *text);

#endif /* COMPUNET_H */
