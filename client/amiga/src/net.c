/*
 * net.c — native TCP transport (bsdsocket.library) + X.25 framing.
 *
 * The bottom half of the Reborn transport: it replaces cnet.device's serial+modem
 * layer AND the X.25 framing cnet.device performed (the client above the seam is
 * unchanged). Wire format verified against server/x25_protocol.py. See TCP-TRANSPORT.md.
 *
 * Kickstart 2.04+ and a TCP/IP stack (Roadshow/AmiTCP/Miami) required at runtime;
 * net_open() returns FALSE without one so the client keeps its offline UI on 1.3.
 *
 * The KS1.3 NDK we build against has the bsdsocket call stubs (proto/socket.h) but
 * not the BSD struct headers (sys/socket.h, netinet/in.h), so the few structs and
 * constants we need are defined locally below (they are API-stable across stacks).
 */
#include <exec/types.h>
#include <exec/libraries.h>
#include <clib/exec_protos.h>

/* The inline bsdsocket prototypes reference BSD types from the (absent) netinclude
 * tree. We only ever pass them as pointers, so incomplete forward declarations
 * satisfy the prototypes without the full headers. */
struct sockaddr;
struct timeval;
struct msghdr;
struct netent;
struct protoent;
struct servent;
struct hostent;                 /* fully defined below */
typedef struct fd_set fd_set;   /* incomplete — WaitSelect (unused) only */

/* The vbcc m68k-amigaos target ships only inline/socket_protos.h, not the ANSI
 * clib/socket_protos.h that proto/socket.h tries to pull in. Predefining its guard
 * makes proto/socket.h skip that include and use the inline stubs (which both declare
 * and implement the calls). Keeps the build toolchain-patch-free on every host. */
#define CLIB_SOCKET_PROTOS_H
#include <proto/socket.h>
#include <proto/dos.h>       /* for net_load_host: reads the TCPHOST config file */
#include <string.h>

#include "net.h"

/* ---- Minimal BSD definitions (absent from the KS1.3 NDK) -------------------- */
#define AF_INET      2
#define SOCK_STREAM  1
#define INADDR_NONE  0xFFFFFFFFUL
#define SOL_SOCKET   0xFFFF
#define SO_RCVTIMEO  0x1006
struct timeval { LONG tv_sec; LONG tv_usec; };  /* full def (forward-declared above) */
/* FIONREAD = _IOR('f',127,int): dir OUT | len 4 | group 'f' | num 127. */
#define FIONREAD     0x4004667FUL
/* 68k is big-endian, so host/network byte order match: htons/htonl are identity. */
#define htons_(x)    ((UWORD)(x))

struct in_addr { ULONG s_addr; };
struct sockaddr_in {
    UBYTE          sin_len;      /* AmiTCP/Roadshow 4.4-style: len + family bytes */
    UBYTE          sin_family;
    UWORD          sin_port;
    struct in_addr sin_addr;
    UBYTE          sin_zero[8];
};
struct hostent {
    char  *h_name;
    char **h_aliases;
    LONG   h_addrtype;
    LONG   h_length;
    char **h_addr_list;          /* h_addr_list[0] = first address */
};

/* ---- State ------------------------------------------------------------------ */
struct Library *SocketBase = NULL;    /* bsdsocket.library base (used by proto/socket.h) */
BOOL  g_tcp_mode = FALSE;
static LONG  g_sock = -1;
static UBYTE g_tx_seq = 0x20;         /* X.25 TX sequence, range $20-$5F (wraps) */

static UBYTE next_tx_seq(void)
{
    UBYTE s = g_tx_seq;
    g_tx_seq = (g_tx_seq >= 0x5F) ? 0x20 : (UBYTE)(g_tx_seq + 1);
    return s;
}

/* ---- CRC-CCITT (poly $1021, init $0000) — matches x25_protocol.crc_ccitt ----- */
static UWORD crc_ccitt(const UBYTE *data, int len)
{
    ULONG crc = 0;
    int i, b;
    for (i = 0; i < len; i++) {
        crc ^= (ULONG)data[i] << 8;
        for (b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (((crc << 1) ^ 0x1021) & 0xFFFF)
                                 : ((crc << 1) & 0xFFFF);
    }
    return (UWORD)crc;
}

/* ---- Byte stuffing: bytes $01..$03 -> $03,(b+$20) --------------------------- */
static int byte_stuff(const UBYTE *in, int n, UBYTE *out)
{
    int i, m = 0;
    for (i = 0; i < n; i++) {
        if (in[i] >= 0x01 && in[i] <= 0x03) {
            out[m++] = 0x03;
            out[m++] = (UBYTE)(in[i] + 0x20);
        } else {
            out[m++] = in[i];
        }
    }
    return m;
}

/* ---- Lifecycle -------------------------------------------------------------- */
BOOL net_open(void)
{
    if (SocketBase == NULL)
        SocketBase = OpenLibrary("bsdsocket.library", 4);
    if (SocketBase == NULL)
        return FALSE;                 /* no stack / KS1.3 — caller degrades to offline */

    if (g_sock < 0)
        g_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (g_sock < 0) {
        net_close();
        return FALSE;
    }
    g_tcp_mode = TRUE;      /* commit to TCP; the actual connect() is in net_connect */
    return TRUE;
}

BOOL net_connect(const char *host, UWORD port)
{
    struct sockaddr_in sa;
    ULONG addr;

    if (SocketBase == NULL || g_sock < 0)
        return FALSE;

    memset(&sa, 0, sizeof sa);
    sa.sin_len    = sizeof sa;
    sa.sin_family = AF_INET;
    sa.sin_port   = htons_(port);

    addr = inet_addr((char *)host);   /* numeric dotted-quad? */
    if (addr == INADDR_NONE) {
        struct hostent *he = gethostbyname((char *)host);
        if (he == NULL || he->h_addr_list == NULL || he->h_addr_list[0] == NULL)
            return FALSE;
        memcpy(&sa.sin_addr, he->h_addr_list[0], 4);
    } else {
        sa.sin_addr.s_addr = addr;
    }

    if (connect(g_sock, (struct sockaddr *)&sa, sizeof sa) < 0)
        return FALSE;

    net_set_rcvtimeo(10);   /* default: blocking reads can't hang forever */

    g_tx_seq   = 0x20;
    g_tcp_mode = TRUE;
    return TRUE;
}

void net_set_rcvtimeo(LONG secs)
{
    struct timeval tv;
    if (g_sock < 0)
        return;
    tv.tv_sec  = secs;
    tv.tv_usec = 0;
    setsockopt(g_sock, SOL_SOCKET, SO_RCVTIMEO, (char *)&tv, sizeof tv);
}

static void rd_discard(void);            /* framing read-ahead buffer, defined below */

void net_close(void)
{
    /* Drop any read-ahead before the socket goes: on reconnect the next framed read
     * would otherwise be served the previous session's bytes. */
    rd_discard();

    if (g_sock >= 0) {
        CloseSocket(g_sock);
        g_sock = -1;
    }
    if (SocketBase != NULL) {
        CloseLibrary(SocketBase);
        SocketBase = NULL;
    }
    g_tcp_mode = FALSE;
}

/* ---- Raw byte I/O (unframed connect handshake) ----------------------------- */
LONG net_send_raw(const void *buf, ULONG len)
{
    const UBYTE *p = (const UBYTE *)buf;
    ULONG sent = 0;
    while (sent < len) {
        LONG n = send(g_sock, (UBYTE *)p + sent, len - sent, 0);
        if (n <= 0)
            return -1;
        sent += (ULONG)n;
    }
    return (LONG)sent;
}

LONG net_recv_raw(void *buf, ULONG len)
{
    return recv(g_sock, buf, len, 0);   /* count, 0 = EOF, -1 = error */
}

/* ---- Buffered byte reader for the framing layer ----------------------------
 * net_recv_frame scans the wire a byte at a time (sync to $01, collect to $02), and
 * doing that with one recv() per byte costs 203x: a 169,966-byte download took 36.4 s
 * against 0.179 s for the same file uploaded, because the receive side made ~187,000
 * syscalls where the send side made ~43. At ~0.195 ms per trap through the emulated
 * bsdsocket.library that IS the transfer time — the inter-packet gap was flat at
 * 21 ms with no stalls, which is per-byte overhead, not waiting on anything.
 *
 * Note this is NOT fixed by larger packets: the syscall count tracks wire BYTES, not
 * frames, so a 40x bigger payload would still make ~187,000 calls.
 *
 * Over the original cnet.device at 1200 baud the per-byte read cost nothing — the line
 * was ~400x slower than the syscall. Re-pointing to TCP inverted that.
 *
 * ⚠ net_recv_raw stays genuinely raw, and net_avail keeps reporting the SOCKET only.
 * serial_io_variant (modem.c) and the link viewer read the socket directly, and
 * modem_read_status hands net_avail's count straight to serial_io_variant as "read
 * exactly this many raw bytes" — so making net_avail count buffered bytes would have it
 * block forever waiting for bytes that are in g_rd, not in the socket. The buffer is
 * instead kept empty whenever those paths can run: every command transaction begins
 * with net_reset_stream (which discards it), and net_close discards it too.
 */
static UBYTE g_rd[4096];
static int   g_rd_have = 0;             /* bytes valid in g_rd */
static int   g_rd_pos  = 0;             /* read cursor */

static LONG rd_byte(UBYTE *out)
{
    if (g_rd_pos >= g_rd_have) {
        LONG n = net_recv_raw(g_rd, (ULONG)sizeof g_rd);
        if (n <= 0)
            return n;                   /* 0 = EOF, -1 = error; same as before */
        g_rd_have = (int)n;
        g_rd_pos  = 0;
    }
    *out = g_rd[g_rd_pos++];
    return 1;
}

static void rd_discard(void)
{
    g_rd_have = 0;
    g_rd_pos  = 0;
}

LONG net_avail(void)
{
    LONG n = 0;
    if (g_sock < 0)
        return -1;
    if (IoctlSocket(g_sock, FIONREAD, (char *)&n) < 0)
        return -1;                      /* socket error/closed */
    return n;                           /* socket only — see the note above g_rd */
}

/* ---- X.25 framing over the socket ------------------------------------------ */
/* Frame buffers sized for the client's largest transfers (4000-byte g_xfer_buf +
 * overhead + worst-case stuffing). */
#define NET_FRAME_MAX  8300

LONG net_send_frame(UBYTE token, const void *payload, ULONG len)
{
    static UBYTE content[NET_FRAME_MAX];
    static UBYTE wire[NET_FRAME_MAX + 2];
    UWORD crc;
    int   c = 0, w = 0;

    content[c++] = (UBYTE)(len + 5);    /* length = payload + len+token+seq+crc(2) */
    content[c++] = token;
    content[c++] = next_tx_seq();
    memcpy(content + c, payload, len);
    c += (int)len;
    crc = crc_ccitt(content, c);
    content[c++] = (UBYTE)(crc >> 8);
    content[c++] = (UBYTE)(crc & 0xFF);

    wire[w++] = 0x01;
    w += byte_stuff(content, c, wire + w);
    wire[w++] = 0x02;

    return net_send_raw(wire, (ULONG)w);
}

LONG net_send_ack(UBYTE seq)
{
    UBYTE content[4], crc_c[6], wire[16];
    UWORD crc;
    int   w = 0, m;

    content[0] = 0x06;                  /* ACK packet length (matches make_ack) */
    content[1] = 0x20;                  /* token ACK                            */
    content[2] = 0x20;                  /* fixed byte                           */
    content[3] = seq;
    crc = crc_ccitt(content, 4);
    memcpy(crc_c, content, 4);
    crc_c[4] = (UBYTE)(crc >> 8);
    crc_c[5] = (UBYTE)(crc & 0xFF);

    wire[w++] = 0x01;
    m = byte_stuff(crc_c, 6, wire + w);
    w += m;
    wire[w++] = 0x02;
    return net_send_raw(wire, (ULONG)w);
}

LONG net_recv_frame(UBYTE *out_token, UBYTE *out_seq, void *payload, ULONG maxlen)
{
    static UBYTE raw[NET_FRAME_MAX + 2];
    static UBYTE un[NET_FRAME_MAX + 2];
    UBYTE b;
    int   n = 0, m = 0, i = 0, plen;
    UWORD crc;

    /* Sync to start marker. */
    do {
        if (rd_byte(&b) != 1)            /* buffered: one recv() per ~4K, not per byte */
            return -1;
    } while (b != 0x01);

    /* Collect to end marker. */
    for (;;) {
        if (rd_byte(&b) != 1)
            return -1;
        if (b == 0x02)
            break;
        if (n < (int)sizeof raw)
            raw[n++] = b;
    }

    /* De-stuff: $03,($2X) -> $0X. */
    while (i < n) {
        if (raw[i] == 0x03 && i + 1 < n && raw[i + 1] >= 0x20 && raw[i + 1] <= 0x2F) {
            un[m++] = (UBYTE)(raw[i + 1] - 0x20);
            i += 2;
        } else {
            un[m++] = raw[i++];
        }
    }
    if (m < 5)                          /* len+token+seq+crc_hi+crc_lo minimum */
        return -1;

    if (out_token) *out_token = un[1];
    if (out_seq)   *out_seq   = un[2];

    crc = crc_ccitt(un, m - 2);         /* CRC over all but the 2 CRC bytes */
    if (((crc >> 8) & 0xFF) != un[m - 2] || (crc & 0xFF) != un[m - 1])
        return -1;                      /* CRC mismatch — corrupt frame */

    plen = m - 5;
    if (plen > (int)maxlen)
        plen = (int)maxlen;
    if (plen > 0)
        memcpy(payload, un + 3, plen);
    return plen;
}

/* ---- Reborn read model (streaming DAT frames, empty-DAT = EOS) ------------- */
/* Retained frame remainder between calls, plus a 1-byte pushback for the ack peek. */
static UBYTE g_rx_frame[NET_FRAME_MAX];   /* current frame's payload */
static int   g_rx_have = 0;               /* bytes remaining in g_rx_frame */
static int   g_rx_pos  = 0;               /* read cursor within g_rx_frame */
static UBYTE g_rx_token = 0;              /* current/last frame token */
static int   g_pb_valid = 0;              /* pushback byte present? */
static UBYTE g_pb_byte  = 0;

void net_unread_byte(UBYTE b)
{
    g_pb_byte  = b;
    g_pb_valid = 1;
}

/*
 * net_reset_stream — discard any buffered/partly-read receive state so the next read
 * starts clean at a frame boundary. Called at the start of each command transaction
 * (serial_write of a TOKEN_COM). This is a strict request/response protocol, so when a
 * new command goes out there is never legitimately-unread response data — anything left
 * is stale residue from the previous command (e.g. serial_io_c peeks one ack byte and
 * pushes back a non-ack byte, or leaves the tail of a multi-byte ack frame). Without
 * this, that residue becomes the first byte(s) of the next command's response and
 * desyncs the stream (observed as a download stalling a few packets in after a LIFE or
 * UPLOAD). Note: the pushback/frame state is only ever populated after login, so calling
 * this during the login COM send is a harmless no-op (the connect handshake reads via a
 * separate g_hs_read buffer, not net_read_stream).
 *
 * ⚠ RESETTING THE PARSE STATE IS NOT ENOUGH — IT MUST DRAIN THE SOCKET TOO.
 * Clearing g_rx_have/g_rx_pos/g_pb_valid only discards the bytes this module is already
 * holding. A whole unread *response* still sits in the TCP receive buffer, survives the
 * reset untouched, and is then parsed as the next command's reply. Observed 2026-07-30
 * on a download issued after an upload: the client read the previous listing's first 8
 * bytes as the download descriptor and wrote the remaining 893 bytes of that listing to
 * disk as the "program", reporting success. The real 169966 bytes stayed queued behind
 * it. This is the failure the comment above already described — the guard was in the
 * right place, at the wrong layer.
 *
 * Draining a single time is sufficient here rather than racy: this runs when the user
 * issues a new command, which is at minimum hundreds of milliseconds after the previous
 * response finished arriving, so nothing is still in flight. It is NOT a general-purpose
 * barrier — it cannot discard bytes the server has not yet sent.
 */
void net_reset_stream(void)
{
    LONG avail, want;
    int  guard = 0;

    g_rx_have  = 0;
    g_rx_pos   = 0;
    g_pb_valid = 0;
    rd_discard();                        /* the framing read-ahead is stale residue too */

    /* g_rx_frame is scratch here: its contents were just discarded above. */
    while ((avail = net_avail()) > 0) {
        want = (LONG)sizeof g_rx_frame;
        if (avail < want)
            want = avail;
        if (net_recv_raw(g_rx_frame, (ULONG)want) <= 0)
            break;                       /* closed or error — let the next read report it */
        if (++guard >= 1024)
            break;                       /* ~8 MB ceiling; never spin on a live stream */
    }

    g_rx_have = 0;
    g_rx_pos  = 0;
}

LONG net_read_stream(void *buf, ULONG maxlen, UBYTE *eof, UBYTE *token)
{
    UBYTE *out = (UBYTE *)buf;
    ULONG  filled = 0;
    UBYTE  seq;
    LONG   plen;

    if (eof) *eof = 0;

    if (g_pb_valid && filled < maxlen) {   /* replay a pushed-back byte first */
        out[filled++] = g_pb_byte;
        g_pb_valid = 0;
    }

    while (filled < maxlen) {
        if (g_rx_pos >= g_rx_have) {       /* need another frame */
            plen = net_recv_frame(&g_rx_token, &seq, g_rx_frame, sizeof g_rx_frame);
            if (plen < 0)
                return (filled > 0) ? (LONG)filled : -1;
            net_send_ack(seq);             /* flow control: server waits for this */
            if (plen == 0) {               /* empty DAT frame = end-of-data */
                if (eof) *eof = 1;
                break;
            }
            g_rx_have = (int)plen;
            g_rx_pos  = 0;
        }
        while (g_rx_pos < g_rx_have && filled < maxlen)
            out[filled++] = g_rx_frame[g_rx_pos++];
    }

    if (token) *token = g_rx_token;
    return (LONG)filled;
}

/* ---- Config host:port parse ------------------------------------------------ */
UWORD net_parse_hostport(const char *cfg, char *host_out, int host_sz)
{
    int i = 0;
    UWORD port = REBORN_DEFAULT_PORT;

    while (cfg[i] != '\0' && cfg[i] != ':' && i < host_sz - 1) {
        host_out[i] = cfg[i];
        i++;
    }
    host_out[i] = '\0';

    if (cfg[i] == ':') {
        UWORD p = 0;
        const char *q = cfg + i + 1;
        while (*q >= '0' && *q <= '9') {
            p = (UWORD)(p * 10 + (*q - '0'));
            q++;
        }
        if (p != 0)
            port = p;
    }
    return port;
}

/*
 * net_load_host — read the server address from the TCPHOST config file (the phone-number
 * config field is only ~15 bytes, too small for a hostname). Looks in the current dir,
 * then ENV:, then S:. Writes host into host_out (host_sz) and the port into *port.
 * Returns TRUE if a non-empty host was read. Uses the client's DOSBase (globals.c).
 */
LONG net_load_host(char *host_out, int host_sz, UWORD *port)
{
    char  cfg[128];
    BPTR  fh;
    LONG  n;
    int   i;

    fh = Open("TCPHOST", MODE_OLDFILE);
    if (fh == 0) fh = Open("ENV:CompunetHost", MODE_OLDFILE);
    if (fh == 0) fh = Open("S:TCPHOST", MODE_OLDFILE);
    if (fh == 0) return FALSE;

    n = Read(fh, cfg, sizeof cfg - 1);
    Close(fh);
    if (n <= 0) return FALSE;
    cfg[n] = '\0';
    for (i = (int)n - 1; i >= 0 && (cfg[i] == '\n' || cfg[i] == '\r' ||
                                    cfg[i] == ' '  || cfg[i] == '\t'); i--)
        cfg[i] = '\0';
    if (cfg[0] == '\0') return FALSE;

    *port = net_parse_hostport(cfg, host_out, host_sz);
    return host_out[0] != '\0';
}

/* net_host_configured — TRUE if a TCPHOST server address is available (used to gate the
 * "Not set up" check so a TCP client works without a dial-string in the config). */
LONG net_host_configured(void)
{
    char  host[128];
    UWORD port;
    return net_load_host(host, sizeof host, &port);
}
