/*
 * partyline.c — "login ready" device handshake + optional partyline window
 * (reconstructed, faithful).
 *
 *   logon_window_ready (FUN_0011949a) — tell cnet.device the login record is ready:
 *       if the partyline option is enabled in the config (open-flags bit 2), open the
 *       partyline window first, then issue write-request io_Command 9 (with the
 *       io_Offset scratch byte = 1) via DoIO. Called from do_connect once the carrier
 *       handshake completes, immediately before reading the login ack.
 *   partyline_open (FUN_00119000) — open the partyline window from its blob NewWindow
 *       (DAT_0011fd84), draw its border Image + banner IntuiText, share the main
 *       window's UserPort, set its IDCMP, attach the menu strip, show the busy
 *       pointer, and prime the device with io_Command 10 (open the partyline stream).
 *
 * TRANSCRIPTION: bodies from the recon (FUN_0011949a / FUN_00119000); the io_Command
 * values, the io_Offset scratch byte, and the blob addresses are from the decompile,
 * with DoIO / OpenWindow / DrawImage / PrintIText / ModifyIDCMP / SetMenuStrip the
 * KS1.3 vectors the thunks resolve to. Request scratch fields use the same byte/word
 * offsets the rest of the transport layer uses (io_Command at +0x1c, io_Data at +0x28,
 * io_Offset[0] at +0x2c).
 */
#include <exec/types.h>
#include <exec/io.h>
#include <intuition/intuition.h>
#include <clib/exec_protos.h>
#include <clib/intuition_protos.h>

#include "compunet.h"
#include "net.h"

extern APTR  g_screen;        /* DAT_001200f8 */
extern APTR  g_main_uport;    /* DAT_00120100 — main window UserPort */
extern APTR  g_menu_pair[2];  /* DAT_001201ae — menu list            */
extern APTR  g_party_win;     /* DAT_0011fd70 */
extern APTR  g_party_screen;  /* DAT_0011fda2 — screen ptr copy      */
extern UBYTE g_party_active;  /* DAT_0011fd74 */
extern struct MsgPort *g_device_port;

extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

/* Config open-flags word (config.c: g_config+0x28 == DAT_00120130). */
extern UBYTE g_config[];
#define CFG_OPENFLAGS  (*(UWORD *)(g_config + 0x28))

/* Tracked OpenWindow + shared-UserPort helper + busy pointer (other modules). */
extern APTR open_window_tracked(APTR newwindow);   /* FUN_0011a534 */
extern APTR share_user_port(APTR win, APTR port);  /* FUN_0011a636 */
extern void set_menu_strip_tracked(APTR win, APTR menu); /* FUN_0011a588 */
extern void set_wait_pointer(void);                /* FUN_001020ae */

/*
 * partyline_open — recon FUN_00119000. Open the partyline window and prime the device.
 */
void partyline_open(void)
{
    struct Window *w;

    /* Patch the partyline NewWindow.Screen (0x11fd84 + 0x1e = 0x11fda2) INTO THE BLOB
     * with g_screen (CUSTOMSCREEN). recon FUN_00119000 line 14223: DAT_0011fda2 =
     * g_screen — DAT_0011fda2 IS the NewWindow.Screen field, not a separate copy.
     * (Writing the detached g_party_screen global left it NULL -> OpenWindow NULL.) */
    *(APTR *)DATA(0x11fda2) = g_screen;
    w = (struct Window *)open_window_tracked(DATA(0x11fd84));
    g_party_win = (APTR)w;
    if (w == NULL)
        return;

    DrawImage(w->RPort, (struct Image *)DATA(0x11fdb4), 0, 0);
    PrintIText(w->RPort, (struct IntuiText *)DATA(0x11fe02), 0, 0);
    share_user_port(w, g_main_uport);
    ModifyIDCMP(w, 0x120);                       /* MENUPICK | GADGETDOWN */
    set_menu_strip_tracked(w, g_menu_pair[0]);
    set_wait_pointer();

    /* Prime the device: io_Command 10 opens the partyline stream. (No cnet.device in
     * TCP mode; partyline-over-TCP is not yet handled, so skip the device priming.) */
    if (!g_tcp_mode) {
        g_write_req->io.io_Data    = (APTR)g_device_port;   /* +0x28 (recon literal) */
        g_write_req->io.io_Command = 10;                     /* +0x1c */
        DoIO((struct IORequest *)g_write_req);
    }
    g_party_active = 1;
}

/*
 * logon_window_ready — recon FUN_0011949a. Open the partyline window if enabled, then
 * issue io_Command 9 (io_Offset scratch byte = 1) to signal "login record ready".
 */
void logon_window_ready(void)
{
    if (CFG_OPENFLAGS & 4)
        partyline_open();

    /* io_Command 9 (+0x2c=1) switched cnet.device into framed read mode ("login record
     * ready"). net_read_stream is always framed, so this is implicit in TCP mode. */
    if (g_tcp_mode)
        return;

    REQ_SERFLAGS(g_write_req)  = 1;    /* +0x2c io_Offset[0] */
    g_write_req->io.io_Command = 9;    /* +0x1c */
    DoIO((struct IORequest *)g_write_req);
}
