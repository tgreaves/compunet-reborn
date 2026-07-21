/*
 * net.h — native TCP transport (bsdsocket.library) for Compunet Reborn.
 *
 * This is the replacement for cnet.device's serial+modem bottom half. It provides
 * a socket connection to the Reborn server and the X.25 framing that cnet.device
 * used to do (the client above the seam is unchanged). See TCP-TRANSPORT.md.
 *
 * Requires Kickstart 2.04+ and a TCP/IP stack (Roadshow/AmiTCP/Miami — any
 * bsdsocket.library). net_open() returns FALSE if bsdsocket is unavailable (e.g.
 * on KS1.3 or with no stack), so the client can degrade to its offline UI.
 *
 * The wire format is verified against server/x25_protocol.py:
 *   frame  = $01 <byte-stuffed [len][token][seq][payload][crc_hi][crc_lo]> $02
 *   stuff  = bytes $01..$03 -> $03,(b+$20)
 *   crc    = CRC-CCITT poly $1021, init $0000, over [len][token][seq][payload]
 *   ack    = a COM/DAT frame is acknowledged by sending a $20 (ACK) frame with seq
 */
#ifndef NET_H
#define NET_H

#include <exec/types.h>

#define REBORN_DEFAULT_PORT  6400

/* TRUE once net_open() has bsdsocket.library and a socket; the transport seams
 * (transport.c / modem.c / connect.c) branch on this to use TCP instead of
 * cnet.device. FALSE => legacy cnet.device path (or offline). */
extern BOOL g_tcp_mode;

/* Lifecycle. */
BOOL net_open(void);                 /* OpenLibrary bsdsocket + socket(); FALSE if none */
BOOL net_connect(const char *host, UWORD port); /* resolve + connect(); FALSE on failure */
void net_close(void);                /* CloseSocket + CloseLibrary; clears g_tcp_mode */

/* Raw byte I/O — used for the unframed connect handshake (the "C CNET" identification
 * and the server's 12x$20 / MOTD / "*CON" text, which cross the wire unframed). */
LONG net_send_raw(const void *buf, ULONG len);   /* send all; bytes sent, -1 on error */
LONG net_recv_raw(void *buf, ULONG len);         /* recv up to len; count, 0 eof, -1 err */
LONG net_avail(void);                            /* bytes waiting (FIONREAD); -1 if closed */
void net_set_rcvtimeo(LONG secs);                /* set the socket receive timeout (seconds) */

/* X.25 framing over the socket (matches server/x25_protocol.py). */
LONG net_send_frame(UBYTE token, const void *payload, ULONG len); /* frame+send; -1 err */
LONG net_recv_frame(UBYTE *out_token, UBYTE *out_seq,
                    void *payload, ULONG maxlen);  /* read one frame; payload len, -1 err */
LONG net_send_ack(UBYTE seq);                      /* send a $20 ACK frame for seq */

/*
 * Reborn read model (see cnet-device-re.md). The Amiga device ended a read on a
 * token&$40 terminal frame; the Reborn server instead streams DAT frames (token $22)
 * and marks end-of-data with an empty DAT frame. net_read_stream reproduces what
 * cnet.device's $1017fa handed the client, sourced from the Reborn wire model:
 *   - accumulate DAT-frame payloads into buf (up to maxlen), ACKing each frame ($20);
 *   - on an empty DAT frame (payload 0) set *eof = 1 (end-of-data) and stop;
 *   - if buf fills first, *eof = 0 (more pending) and the frame remainder is retained
 *     for the next call.
 * *token receives the last frame's token. Returns bytes delivered, or -1 on error.
 */
LONG net_read_stream(void *buf, ULONG maxlen, UBYTE *eof, UBYTE *token);
void net_unread_byte(UBYTE b);   /* push one byte back so the next read returns it first */

/* Config: parse the repurposed phone-number field "host" or "host:port". Writes the
 * host into host_out (host_sz) and returns the port (REBORN_DEFAULT_PORT if none). */
UWORD net_parse_hostport(const char *cfg, char *host_out, int host_sz);

/* Read the server address from the TCPHOST file (current dir / ENV: / S:). The config
 * phone field is too small (~15 bytes) for a hostname, so the host lives in a file. */
LONG  net_load_host(char *host_out, int host_sz, UWORD *port);
LONG  net_host_configured(void);   /* TRUE if a TCPHOST address is available */

#endif /* NET_H */
