/*
 * nettest.c — standalone TCP/IP connectivity smoke test for Compunet Reborn.
 *
 * Proves the *environment* works end to end — bsdsocket.library present, emulator
 * guest networking bridged, the Reborn server reachable on its port, and net.c's
 * socket + raw-I/O code correct — WITHOUT needing the still-unpinned read/ack demux.
 *
 * What it does:
 *   1. Open bsdsocket.library (fails cleanly if no TCP/IP stack / KS<2.04).
 *   2. Read the server address from a "TCPHOST" file (one line: host  or  host:port).
 *   3. connect() to it.
 *   4. Read the server's unprompted greeting (the Reborn server sends 12x $20).
 *   5. Send the raw "C CNET" identification (exactly what do_connect sends).
 *   6. Read + dump whatever the server sends back.
 *
 * The server currently has no Amiga branch, so step 6 will most likely show
 * "*PLEASE DOWNLOAD LATEST CLIENT" — that is a SUCCESS for this test: it means TCP,
 * the stack, and the server round-trip all work. Any bytes received prove connectivity.
 *
 * Build (needs the vbcc KS1.3 toolchain, see ../vintage/tools/re/toolchain.md):
 *   vc +kick13 -c -I. net.c     -o net.o
 *   vc +kick13 -c -I. nettest.c -o nettest.o
 *   vc +kick13 -o nettest net.o nettest.o -lamiga
 * Run from a Shell on a KS2.04+ Amiga with a TCP/IP stack, with a TCPHOST file in the
 * current dir:  nettest
 */
#include <exec/types.h>
#include <exec/libraries.h>
#include <proto/exec.h>
#include <proto/dos.h>
#include <string.h>
#include <stdio.h>          /* sprintf (vc.lib) */

#include "net.h"

struct DosLibrary *DOSBase; /* opened in main (minstart doesn't open dos.library) */

static void say(const char *s)
{
    Write(Output(), (APTR)s, (LONG)strlen(s));
}

/* Dump up to n bytes as hex + printable ASCII, in rows of 16. */
static void dump(const UBYTE *buf, int n)
{
    char line[100];
    int  i, j, o;
    for (i = 0; i < n; i += 16) {
        o = 0;
        o += sprintf(line + o, "    ");
        for (j = 0; j < 16 && i + j < n; j++)
            o += sprintf(line + o, "%02x ", buf[i + j]);
        for (; j < 16; j++)
            o += sprintf(line + o, "   ");
        o += sprintf(line + o, " |");
        for (j = 0; j < 16 && i + j < n; j++) {
            UBYTE c = buf[i + j] & 0x7f;
            line[o++] = (c >= 0x20 && c < 0x7f) ? (char)c : '.';
        }
        line[o++] = '|';
        line[o++] = '\n';
        line[o]   = '\0';
        say(line);
    }
}

/* Drain available bytes into buf (max) by POLLING net_avail (FIONREAD) — never a
 * blocking recv, since some stacks don't honour SO_RCVTIMEO. Ends after ~2s with no
 * new data. This mirrors how the real client polls (modem_read_status). Returns total. */
static int recv_drain(UBYTE *buf, int max)
{
    int  total = 0, idle = 0;
    while (total < max && idle < 20) {          /* 20 x 100ms = ~2s idle => done */
        LONG a = net_avail();
        if (a < 0)
            break;                              /* socket closed/error */
        if (a > 0) {
            LONG want = (a > max - total) ? (max - total) : a;
            LONG n = net_recv_raw(buf + total, (ULONG)want);
            if (n <= 0)
                break;
            total += (int)n;
            idle = 0;
        } else {
            Delay(5);                           /* 5 ticks = 100ms */
            idle++;
        }
    }
    return total;
}

/* Read the "TCPHOST" file into host (max sz), trimming trailing whitespace/newline. */
static BOOL read_host_file(char *host, int sz)
{
    BPTR fh;
    LONG n;
    int  i;

    fh = Open("TCPHOST", MODE_OLDFILE);
    if (fh == 0)
        fh = Open("S:TCPHOST", MODE_OLDFILE);
    if (fh == 0)
        return FALSE;

    n = Read(fh, host, sz - 1);
    Close(fh);
    if (n <= 0)
        return FALSE;
    host[n] = '\0';
    for (i = (int)n - 1; i >= 0 && (host[i] == '\n' || host[i] == '\r' ||
                                    host[i] == ' '  || host[i] == '\t'); i--)
        host[i] = '\0';
    return host[0] != '\0';
}

int main(void)
{
    char  cfg[128], host[128], msg[200];
    UBYTE rx[512];
    UWORD port;
    LONG  n;

    DOSBase = (struct DosLibrary *)OpenLibrary("dos.library", 0);
    if (DOSBase == NULL)
        return 20;

    say("\nCompunet Reborn - TCP/IP connectivity test\n");
    say("-------------------------------------------\n");

    say("[1] Opening bsdsocket.library ... ");
    if (!net_open()) {
        say("FAILED\n");
        say("    No TCP/IP stack (need KS2.04+ and Roadshow/AmiTCP/Miami running).\n");
        CloseLibrary(DOSBase);
        return 10;
    }
    say("OK (socket created)\n");

    say("[2] Reading server address from TCPHOST ... ");
    if (!read_host_file(cfg, sizeof cfg)) {
        say("FAILED\n");
        say("    Create a file TCPHOST containing one line: host  or  host:port\n");
        net_close();
        CloseLibrary(DOSBase);
        return 10;
    }
    port = net_parse_hostport(cfg, host, sizeof host);
    sprintf(msg, "OK -> host='%s' port=%u\n", host, (unsigned)port);
    say(msg);

    say("[3] connect() ... ");
    if (!net_connect(host, port)) {
        say("FAILED\n");
        say("    Could not connect. Check the address, that the server is running,\n");
        say("    and that emulator networking can reach it.\n");
        net_close();
        CloseLibrary(DOSBase);
        return 10;
    }
    say("OK - TCP connection established!\n");

    /* Short receive timeout so the drain loops end promptly after each burst. */
    net_set_rcvtimeo(3);

    /* Nudge: the server peeks the first byte with a 5s Hayes/X.25 auto-detect. Send a
     * '_' (what do_connect's line-turnaround probe sends) so it proceeds immediately. */
    say("[4] Sending line-turnaround nudge ('_') ...\n");
    net_send_raw("_", 1);

    say("[5] Reading server greeting (Reborn sends 12x $20) ...\n");
    n = recv_drain(rx, sizeof rx);
    if (n > 0) {
        sprintf(msg, "    RX %ld bytes:\n", n);
        say(msg);
        dump(rx, n);
    } else {
        say("    (no greeting bytes / timeout)\n");
    }

    say("[6] Sending 'C CNET' identification ...\n");
    net_send_raw("C CNET\r", 7);
    net_send_raw("C CNET\r", 7);
    net_send_raw("00000000000000\r", 15);
    say("    sent.\n");

    say("[7] Reading server response ...\n");
    n = recv_drain(rx, sizeof rx);
    if (n > 0) {
        sprintf(msg, "    RX %ld bytes:\n", n);
        say(msg);
        dump(rx, n);
        say("    ^ Any bytes here = full TCP round-trip works. A 'PLEASE DOWNLOAD'\n");
        say("      message is EXPECTED (server has no Amiga branch yet) and still\n");
        say("      proves connectivity end to end.\n");
    } else {
        say("    (no response / timeout)\n");
    }

    say("[8] Closing.\n\n");
    net_close();
    CloseLibrary(DOSBase);
    return 0;
}
