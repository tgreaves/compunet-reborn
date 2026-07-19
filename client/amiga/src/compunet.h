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
#include <devices/serial.h>

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
extern struct IOExtSer *g_read_req;      /* read  IORequest  (CMD_READ)  */
extern struct IOExtSer *g_write_req;     /* write IORequest  (CMD_WRITE) */
extern struct MsgPort  *g_device_port;   /* shared reply port            */
extern struct MsgPort  *g_read_port;     /* read-completion reply port   */
extern struct MsgPort  *g_write_port;    /* write-completion reply port  */
extern ULONG            g_device_sig;    /* 1 << device_port mp_SigBit   */
extern ULONG            g_read_sig;      /* 1 << read_port   mp_SigBit   */
extern ULONG            g_write_sig;     /* 1 << write_port  mp_SigBit   */

/* serial_read / serial_write: submit one IORequest and wait for completion,
 * servicing the other ports' signals meanwhile. Return 1 on completion
 * (including error, which also shows a status message). */
LONG serial_write(APTR data, ULONG length, UBYTE status_hi, UBYTE ser_flags);
LONG serial_read(APTR data, ULONG length,
                 UBYTE *out_ser_flags, UBYTE *out_status_hi, ULONG *out_actual);

/* ------------------------------------------------------------------ *
 *  Status / UI helpers (defined elsewhere in the reconstruction)
 * ------------------------------------------------------------------ */
void show_status_message(UBYTE code, const char *text);

#endif /* COMPUNET_H */
