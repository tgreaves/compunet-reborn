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

void net_close(void)
{
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

LONG net_avail(void)
{
    LONG n = 0;
    if (g_sock < 0)
        return -1;
    if (IoctlSocket(g_sock, FIONREAD, (char *)&n) < 0)
        return -1;                      /* socket error/closed */
    return n;
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
        if (net_recv_raw(&b, 1) != 1)
            return -1;
    } while (b != 0x01);

    /* Collect to end marker. */
    for (;;) {
        if (net_recv_raw(&b, 1) != 1)
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
