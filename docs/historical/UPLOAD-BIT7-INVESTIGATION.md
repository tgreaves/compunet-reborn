# Upload Bit 7 Stripping — Investigation

## Symptom

Program uploads (P-type, client→server) arrive with bit 7 cleared on all
data bytes. For example, `$E8` becomes `$68`, `$A9` becomes `$29`. The uploaded
file is also ~700 bytes shorter than expected (19532 vs 20219 bytes) due to
some packets being discarded from CRC mismatches caused by the same corruption.

Program downloads (server→client) work correctly — all 8 bits are preserved.

## Data Path

```
C64 ACIA ($DE00) → VICE ip232 socket → tcpser → TCP → Python server
```

## Investigation Summary

### Client-Side (compunet.s) — No Masking

- **ACIA_INIT** (line 6726): Control register set to `$1F`.
  MOS 6551 bit layout: bit 7=stop bits, bits 6-5=word length (00=8bit),
  bit 4=clock source, bits 3-0=baud rate. So `$1F` = 8N1 at 19200 baud.
  The ACIA is correctly configured for 8-bit transmission.

- **ACIA_WAIT_READY** (line 6867): `STA ACIA_DATA` — byte written directly to
  the data register with no AND masking. All 8 bits are sent.

- **ACIA_UPLOAD_BYTE / @upload_stuffed_crc** (line 7339): Upload data bytes
  pass through byte-stuffing (only affects values $01/$02/$03) then to
  ACIA_WAIT_READY. No bit masking anywhere in the upload path.

- **NMI handler** (line 6768): `LDA ACIA_DATA` — received bytes stored
  directly to ring buffer with no masking. Confirms RX path is 8-bit clean.

### tcpser — No Masking for Our Configuration

- **ip232_read** (ip232.c:174): Reads bytes from VICE socket, passes through
  unchanged (only $FF is special — ip232 DTR escape).

- **ip232_write** (ip232.c:138): Writes bytes to VICE socket unchanged
  (only $FF doubled as escape).

- **dce_read** (dce.c:174): After ip232_read, checks `if(0 < cfg->parity)` —
  only strips bit 7 if parity was detected as ODD or EVEN. Parity is auto-
  detected from the 'A' and 'T' of the first AT command.

- **Parity detection** (dce.c:16): For our `ATDT` command, 'A'=$41 and 'T'=$54
  produce `parity = ((0x41 >> 6) & 2) | (0x54 >> 7) = 0` (SPACE parity).
  Since `cfg->parity = 0`, the `dce_read` bit-stripping is **not activated**.

- **line_write** (line.c:26): Applies `& 0x7F` mask only when `is_telnet=TRUE`
  and binary mode is not negotiated. Our server doesn't speak telnet (first
  byte is $20, not $FF), so `is_telnet=FALSE` and no masking occurs.

- **mdm_parse_data** (modem_core.c:664): In data mode, calls `line_write`
  directly. No intermediate masking.

**Conclusion: tcpser does not strip bit 7 for our connection profile.**

### VICE's ACIA/ip232 Emulation — Prime Suspect

VICE's 6551 ACIA emulation translates writes to `$DE00` (ACIA_DATA) into
bytes sent over the ip232 TCP socket. The emulation must interpret the
control register to determine word length.

A known behaviour (documented in the server's CRC validation comment at
x25_protocol.py:283) is that "VICE SwiftLink strips bit 7 from transmitted
bytes". This was observed during CRC validation — the server masks bit 7
when checking CRC bytes received from the client.

Despite the control register being set for 8-bit word length ($1F), VICE's
ACIA emulation appears to send only 7 bits over the ip232 socket. This
may be a VICE bug, a quirk of the ip232 protocol implementation, or a
consequence of how VICE models the 6551's TX path.

### Why Downloads Work

The asymmetry exists because:

1. **Downloads (server→VICE)**: Bytes arrive at the ip232 socket and VICE
   copies them to $DE00 for the NMI handler to read. VICE does NOT apply
   word-length masking on the receive path — it delivers all 8 bits to the
   emulated CPU.

2. **Uploads (VICE→server)**: Bytes written to $DE00 by the emulated CPU
   pass through VICE's ACIA TX emulation before being sent to the ip232
   socket. VICE appears to apply word-length masking (clearing bit 7) on
   this path, even though the control register specifies 8-bit mode.

### Why It Was Never Noticed Before

All command packets (login, DIR, SHOW, BUY etc.) contain only ASCII bytes
($00-$7F). Bit 7 is never set in command payloads, so the stripping is
invisible. Only binary program data (containing arbitrary byte values
$00-$FF) exposes the issue.

## Root Cause (Confirmed via tcpser trace + uploaded file analysis)

**tcpser trace log** (with `-t sSiI` flags) reveals:

```
TRACE:SR<-|0000|c1    ← 'A' arrives from VICE as $C1 ($41 + bit 7)
TRACE:SR<-|0000|d4    ← 'T' arrives from VICE as $D4 ($54 + bit 7)
TRACE:SR<-|0000|31    ← '1' arrives clean ($31, bit 7 NOT set)
TRACE:SR<-|0000|43    ← 'C' of CNET arrives clean ($43)
TRACE:SR<-|0000|01    ← X.25 packet start arrives clean ($01)
```

**Critical finding**: Only the 4 `ATDT` bytes have bit 7 set. ALL other
bytes from VICE (IP address digits, CNET identification, X.25 framed data)
arrive with bit 7 already CLEARED. No bytes above $7F appear in the
serial input trace during the upload data phase.

**This means VICE's ACIA emulation IS stripping bit 7** from transmitted
data bytes (except possibly the first few chars which get mark parity).
The tcpser parity detection is a secondary issue — the bit 7 information
is already lost by the time bytes reach tcpser.

### Uploaded file analysis

Comparing uploaded BALLSNOW vs original SNOWBALL:

```
Upload structure: [4 zero padding] [load_lo $01] [load_hi $08] [size_lo] [size_hi] [data...]
Size field: $79 $4E (received) vs $F9 $4E (expected) — bit 7 stripped on size_lo
Data at offset 8: matches bit-7-stripped original program data
```

The upload is 19532 bytes vs expected 20219+8=20225 — ~693 bytes lost from
discarded packets (CRC mismatches caused by byte-stuffing corruption from
the bit-7 issue interacting with the X.25 framing bytes $01/$02/$03).

## Why VICE Sets Bit 7

The ACIA control register is set to `$1F` (8-bit word length, 19200 baud)
and the command register is `$09` (DTR active, RX NMI enabled). Based on
VICE source code analysis (aciacore.c), `datamask` should be `$FF` for
8-bit mode. However, VICE empirically sends bytes with bit 7 set.

Possible explanations:
- VICE may be applying parity from the command register setting
- VICE's ip232 implementation may have a quirk for 8-bit data
- The ACIA command register bits 7-5 (parity control) with value `000`
  should mean "parity disabled" but VICE may interpret differently

## Possible Fixes

1. **Fix tcpser parity detection**: Modify tcpser to not auto-detect
   parity, or force `cfg->parity = 0`. Since we're using ip232 mode
   (not a real serial port), parity is meaningless.

2. **VICE ACIA command register**: Try different command register values
   that explicitly disable parity and ensure clean 8-bit transmission.
   The current $09 has bits 7-5 = 000. Try $E9 (bits 7-5 = 111 = no
   parity, but transmitted and received as 8 bits).

3. **Bypass tcpser**: Connect VICE directly to the server. Requires
   implementing AT command handling in the server or skipping the Hayes
   dial sequence in the client.

4. **Server-side bit-7 restoration**: Since VICE consistently sets bit 7
   on TX, the server could OR $80 onto received bytes to undo tcpser's
   stripping. But this would corrupt genuinely 7-bit data.

5. **Patch tcpser**: Disable parity detection for ip232 connections
   (since parity is meaningless over TCP).

## Recommended Fix

The problem is in VICE's ACIA TX emulation. Despite the control register
being configured for 8-bit word length ($1F, bits 6-5 = 00), VICE clears
bit 7 on transmitted bytes before sending them to the ip232 socket.

**Next steps:**
1. Test with a newer VICE version — this may be a known bug that's been
   fixed. The VICE source code (aciacore.c) correctly computes
   `datamask = 0xFF` for our $1F control register, so the emulation
   SHOULD send 8 bits. A version-specific bug is plausible.
2. Try Turbo232 mode (`-acia1mode 2`) or user-port RS232 emulation
   (`-rsuser`) which may use a different TX code path.
3. If VICE cannot be fixed: implement a 7-bit-safe encoding on the upload
   path (e.g. escape bytes with bit 7 set into two-byte sequences).

Note: changing the ACIA control/command register values is unlikely to
help — VICE source confirms our $1F already selects 8-bit word length
and the datamask logic is mode-independent.

**Eliminating tcpser alone will NOT fix the issue** — VICE strips bit 7
before bytes reach the ip232 socket.

## Resolution

**FIXED** — The bit-7 corruption was caused by VICE's ip232 protocol layer,
NOT the ACIA core emulation. With ip232 disabled and VICE connecting via
raw TCP socket directly to the server (no tcpser), all 8 bits are preserved
on both upload and download paths.

The server now handles Hayes AT commands directly (auto-detected from the
first byte), eliminating the need for tcpser entirely. Full round-trip
verified: upload program → store as PRG → download → save to disk → runs
correctly.
