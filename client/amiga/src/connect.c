/*
 * connect.c — transport bring-up (reconstructed).
 *
 * open_transport (recon: FUN_001192b6) creates three message ports and two
 * request blocks, computes their completion signal masks, sets the serial
 * parameters (Compunet 1275 split baud: 75 up / 1200 down), and opens
 * cnet.device. On any failure it unwinds the tracked resources.
 *
 * Reconstructed from recon_annotated.c. The original nests error handling; here
 * it is flattened to early-returns (behaviour-identical) for readability.
 *
 * cnet.device itself dials the modem and performs the X.25 framing/CRC — this
 * routine just establishes the IO channel. The Reborn TCP transport replaces the
 * OpenDevice here (and the serial_read/write in transport.c) with a socket.
 */
#include <exec/types.h>
#include <exec/io.h>
#include <exec/ports.h>
#include <clib/exec_protos.h>

#include "compunet.h"

/* Serial parameters, loaded from config at startup (recon globals):
 *   g_dev_name_param : string param stored in the request (+0x2e region)
 *   g_baud_up/g_baud_down : 75 / 1200 (DAT_0012012c / DAT_0012012e)
 *   g_open_flags     : OpenDevice flags (DAT_00120130); bit 1 passed to OpenDevice */
extern UWORD  g_baud_up;       /* was DAT_0012012c = 0x4b  (75)   */
extern UWORD  g_baud_down;     /* was DAT_0012012e = 0x4b0 (1200) */
extern UWORD  g_dev_param2e;   /* was DAT_0012012c-adjacent config word at req+0x2e */
extern ULONG  g_open_flags;    /* was DAT_00120130 */
extern struct Device *g_cnet_device;  /* was DAT_001230a4 (req->io_Device after open) */

char open_transport(void)
{
    resource_mark();                              /* thunk_FUN_0011a000 */

    /* Three reply ports: device, read-completion, write-completion. */
    g_device_port = create_port_tracked(0, 0);
    if (g_device_port == NULL) { cleanup_resources(); return XPORT_FAIL; }

    g_read_port = create_port_tracked(0, 0);
    if (g_read_port == NULL) { cleanup_resources(); return XPORT_FAIL; }

    g_write_port = create_port_tracked(0, 0);
    if (g_write_port == NULL) { cleanup_resources(); return XPORT_FAIL; }

    /* Completion signal masks from each port's mp_SigBit. */
    g_device_sig = 1UL << g_device_port->mp_SigBit;
    g_read_sig   = 1UL << g_read_port->mp_SigBit;
    g_write_sig  = 1UL << g_write_port->mp_SigBit;

    /* Two request blocks (CNET_REQ_SIZE = 0x36) bound to the write/read ports. */
    g_write_req = create_extio_tracked(g_write_port, CNET_REQ_SIZE);
    if (g_write_req == NULL) { cleanup_resources(); return XPORT_FAIL; }

    g_read_req = create_extio_tracked(g_read_port, CNET_REQ_SIZE);
    if (g_read_req == NULL) { cleanup_resources(); return XPORT_FAIL; }

    /* Serial parameters on the write request (copied to the read request below). */
    REQ_PARAM2E(g_write_req) = g_dev_param2e;
    REQ_BAUD_UP(g_write_req) = g_baud_up;         /* 75   */
    REQ_BAUD_DN(g_write_req) = g_baud_down;       /* 1200 */

    if (open_device_tracked("cnet.device", 0, (struct IORequest *)g_write_req,
                            g_open_flags & 2) != 0) {
        cleanup_resources();                      /* OpenDevice failed */
        return XPORT_FAIL;
    }

    /* Clone the write request's parameter/device fields (0x14..0x35) into the read
     * request so both share the opened device/unit and serial settings. */
    {
        UBYTE *w = (UBYTE *)g_write_req;
        UBYTE *r = (UBYTE *)g_read_req;
        int i;
        for (i = 0x14; i < CNET_REQ_SIZE; i++)
            r[i] = w[i];
    }

    /* Reject if the opened device reports an unusable version (io_Device->lib_Version).
     * The original checks the LIB_VERSION/LIB_REVISION words at device+0x14/+0x16. */
    g_cnet_device = g_write_req->io.io_Device;
    {
        UWORD ver = *(UWORD *)((UBYTE *)g_cnet_device + 0x14);
        UWORD rev = *(UWORD *)((UBYTE *)g_cnet_device + 0x16);
        if (ver < 2 || (ver == 2 && rev == 0)) {
            cleanup_resources();
            return XPORT_BADVER;
        }
    }

    resource_commit();                            /* thunk_FUN_0011a00a */
    return XPORT_OK;
}
