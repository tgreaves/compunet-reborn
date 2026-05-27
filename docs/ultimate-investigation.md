# C64 Ultimate SwiftLink Investigation

## Goal

Get the Compunet Reborn client working on the C64 Ultimate's built-in SwiftLink-to-TCP bridge (ACIA at DE00/NMI mode).

## Ultimate Configuration

- Modem Interface: ACIA / SwiftLink
- ACIA (6551) Mapping: DE00/NMI
- Hardware Mode: SwiftLink
- Listening Port: 3000
- Do RING sequence (incoming): Enabled
- Drop connection on DTR low: Enabled
- RTS Handshake (Rx): Enabled
- CTS Behavior: Active (Low)
- DCD Behavior: Active (Low)
- DSR Behavior: Active when connected
- Automatic Rx Pushback: Disabled
- Modem Connect Text: /flash/welcome.txt
- Modem Offline Text: /flash/offline.txt
- Modem Busy Text: /flash/busy.txt

Note: The connect/offline/busy text files may not resolve to anything.

## What Works

- **CCGMS** connects to BBSes via the same bridge with DE00/NMI.
- **UltimateTerm** connects to our server (seen in prod server logs, logged in as DAZZ).
- Our client's `ACIA_INIT` completes without issue.
- Our client's `ACIA_DIAL` returns "success" (receives a CR from bridge echo).
- A tight polling loop (`LDA $029C / CMP $029B`) runs for 16+ seconds without crashing.
- The NMI handler (at $CF00) correctly buffers bytes when data arrives.

## What Fails

- After `ACIA_DIAL`, the bridge never sends a "CONNECT" response or server handshake data.
- The NMI buffer remains empty during `ACIA_PROTO_CONNECT` wait.
- Server logs never show a connection from the Ultimate (TCP never established).
- If the wait loop exits via `RTS`, it crashes to BASIC (stack corruption).

## Findings

### 1. Stack Corruption

The Ultimate's firmware uses the stack page ($0100-$01FF) for its own trampoline code. A code fragment at ~$0150 writes to $DFFF/$DFFE (Ultimate control registers). This is present even at boot before our program loads. Any `RTS`/`RTI` that tries to use a return address in the affected region will crash.

The stack corruption is NOT caused by our NMI handler — it's the Ultimate's firmware performing background operations (DNS resolution, TCP state management, etc.) using the stack page as working memory.

**Workaround**: Avoid `RTS` during the connection phase. Use infinite loops with border color for state indication, or reset SP to $FF before the connect sequence to keep return addresses high.

### 2. NMI Handler

Our NMI handler works correctly on the Ultimate. Testing confirmed:
- Handler installed at $CF00, vector at $0318 = $00CF.
- RDRF check prevents spurious reads when NMI isn't from ACIA.
- Data IS buffered correctly when bytes arrive.

The IRQ disable/re-enable toggling (`ORA #$02 / STA ACIA_CMD` ... `AND #$FD / STA ACIA_CMD`) present in CCGMS's handler has been removed from ours to prevent potential nested NMI issues on the Ultimate, though CCGMS uses it successfully.

### 3. ACIA_WAIT_READY (TX)

Original code wrote to ACIA_DATA immediately without checking transmit readiness. Fixed to poll ACIA_STATUS bit 4 (TDRE) before writing, matching CCGMS's approach.

### 4. DTR Drop

`ACIA_INIT` originally wrote $00 to ACIA_CMD which drops DTR. Since the Ultimate has "Drop connection on DTR low: Enabled", this would disconnect the bridge. Fixed to write $01 (DTR active, interrupts off) instead.

### 5. Bridge Not Processing ATDT

The core unsolved problem. The bridge echoes back the ATDT command (confirmed by NMI buffer contents showing `ATDTvme.compunet...` in earlier tests), but never establishes TCP or sends a CONNECT response.

CCGMS sends `ATV1\r` (enable word result codes) before `ATDT`. We added this but it didn't help — still no CONNECT response.

## CCGMS Reference (rs232_swiftlink.s)

CCGMS's dial sequence:
1. `rs232_clear` — clear buffers
2. `rs232_init` — initialize ACIA (CMD=$09, CTRL=$1F, install NMI handler at $0318)
3. Send `ATV1\r` with inter-character delay — configure word result codes
4. Send `ATDT` + number (CR-terminated)
5. Parse response for "CONNECT" / "NO CARRIER" / "BUSY"

Key CCGMS register values:
- ACIA_CMD: $09 (`%00001001` — DTR active, RX NMI enabled, TX IRQ off, RTS low)
- ACIA_CTRL: $1F (`%00011111` — 1 stop bit, 8-bit word, internal clock, 19200 baud)

These match our values exactly.

## Open Questions

1. Why does the bridge echo ATDT but not act on it? Is there a required initialization sequence beyond ATV1?
2. Does the bridge need `ATE0` (disable echo) or `ATZ` (reset) first?
3. Is there a timing requirement between ATV1 and ATDT that our delay doesn't satisfy?
4. Does the bridge require a specific "OK" response to ATV1 before accepting ATDT?
5. Could the bridge need the ACIA to be in a specific state (e.g., reading the "OK" response) before it processes the next command?
6. Is there something about how CCGMS uses `strmod_delay` (inter-character delay when sending AT commands) that matters?

## UltimateTerm Analysis

UltimateTerm does NOT use the modem emulation at all. It communicates directly via
the Ultimate Command Interface (UCI) at $DF1C-$DF1F, using the Network Target ($03)
to open TCP sockets directly:

- Command: `$03 $07 <PORT_LSB> <PORT_MSB> <HOST_STRING>` (NET_CMD_OPEN_TCP)
- Response: socket handle
- Read: `$03 $10 <HANDLE> <LEN_LSB> <LEN_MSB>`
- Write: `$03 $11 <HANDLE> <DATA...>`
- Close: `$03 $09 <HANDLE>`

UCI docs: https://1541u-documentation.readthedocs.io/en/master/uci/index.html

The Ultimate has two separate networking paths:
1. **UCI** ($DF1C-$DF1F) — direct socket API (UltimateTerm uses this)
2. **Modem emulation** ($DE00 ACIA) — Hayes AT bridge (CCGMS uses this)

Our client uses the modem emulation path. CCGMS proves this works on the Ultimate.

## Deep Dive: CCGMS vs Our Code

Comprehensive comparison of how CCGMS communicates with the SwiftLink bridge vs our
implementation. CCGMS successfully connects; our ATDT is ignored.

### Root Cause #1: ATV1→ATDT Delay Too Short

CCGMS waits **533ms** (32 jiffies) between sending `ATV1\r` and `ATDT`. Our code waits
~20ms (4096 CPU cycles). The bridge needs time to process ATV1, generate an "OK"
response, and be ready for the next command. With only 20ms, the ATDT likely arrives
while the bridge is still echoing/processing ATV1, causing it to be silently dropped.

### Root Cause #2: Buffer Pointers Initialized to $01

In `ACIA_INIT`, after `LDA #$01 / STA ACIA_CMD`, the A register holds $01. The
subsequent `STA NMI_BUF_TAIL / STA NMI_BUF_HEAD / STA UPLOAD_POS` stores $01 (not
$00) into the buffer pointers. This means head and tail start misaligned.

### Root Cause #3: RTS De-asserted During Init

Our initial CMD write of `$01` sets bits 2-3 to `00`, which means RTS HIGH
(de-asserted). The Ultimate's "RTS Handshake (Rx): Enabled" setting means the bridge
may interpret this as "not ready" and stop accepting input. CCGMS writes `$09` from
the start (bits 2-3 = `10` = RTS low/asserted) and never de-asserts RTS.

### Root Cause #4: TX Routine Missing Enable Step

CCGMS's `swwait` explicitly enables the transmitter (`ORA #%00001000` on CMD) before
polling TDRE. It also checks both bit 4 (TDRE) and bit 5 (DCD). Our `ACIA_WAIT_READY`
only polls bit 4 without explicitly enabling TX. Additionally, CCGMS waits AFTER
writing the byte (double-wait pattern) to ensure it's fully shifted out before
returning.

### Root Cause #5: No RAM Bank Protection

CCGMS installs NMI wrappers that ensure $01 has I/O visible ($DE00 accessible)
regardless of current bank config. Our handler at $CF00 assumes I/O is always mapped
in. If $01 is changed (e.g. during KERNAL calls), our NMI handler reads RAM instead
of ACIA registers.

### Additional Differences

| Feature | CCGMS | Ours |
|---------|-------|------|
| rs232_clear before init | YES (zeros tail/head/free) | BUG: stores $01 |
| Full re-init before dial | YES (sw_setup + rs232_clear) | Single ACIA_INIT |
| ATV1→ATDT delay | 533ms | ~20ms |
| TX method | Enable TX, poll TDRE+DCD, write, poll again, restore CMD | Poll TDRE, write |
| RTS flow control | Active (de-asserts at 200 bytes, re-asserts at 50) | None |
| Response parsing | Matches CONNECT/BUSY/NO CARRIER words | Waits for any CR |
| Timeout on response | YES (144-iteration counter) | NO (infinite loop) |
| NMI handler RX disable | YES (prevents re-entrancy) | NO |

## UltimateTerm Analysis

UltimateTerm does NOT use the modem emulation at all. It communicates directly via
the Ultimate Command Interface (UCI) at $DF1C-$DF1F, using the Network Target ($03)
to open TCP sockets directly:

- Command: `$03 $07 <PORT_LSB> <PORT_MSB> <HOST_STRING>` (NET_CMD_OPEN_TCP)
- Response: socket handle
- Read: `$03 $10 <HANDLE> <LEN_LSB> <LEN_MSB>`
- Write: `$03 $11 <HANDLE> <DATA...>`
- Close: `$03 $09 <HANDLE>`

UCI docs: https://1541u-documentation.readthedocs.io/en/master/uci/index.html

The Ultimate has two separate networking paths:
1. **UCI** ($DF1C-$DF1F) — direct socket API (UltimateTerm uses this)
2. **Modem emulation** ($DE00 ACIA) — Hayes AT bridge (CCGMS uses this)

Our client uses the modem emulation path. CCGMS proves this works on the Ultimate.

## Resolution

### The Actual Root Cause: PETSCII vs ASCII

The AT commands were being sent in **PETSCII** ($C1 $D4 $D6 $31 for "ATV1") instead
of **ASCII** ($41 $54 $56 $31). In ca65 with a C64 target, `LDA #'A'` produces $C1
(PETSCII uppercase A), not $41 (ASCII A).

The bridge echoed the bytes back but never parsed them as AT commands because it
expects ASCII. The hostname portion worked coincidentally because our PETSCII→lowercase
conversion (`ORA #$20` on $41-$5A) happens to produce valid ASCII lowercase.

**Fix**: Use explicit hex values for AT command bytes:
```
LDA #$41    ; 'A' ASCII
LDA #$54    ; 'T' ASCII
LDA #$44    ; 'D' ASCII
```

This was confirmed by dumping the NMI buffer ($CE00) which showed:
```
C1 D4 D6 31 0D C1 D4 C4 D4 76 6D 65 2E 63 6F 6D ...
```
— PETSCII "ATV1\r" followed by PETSCII "ATDT" then ASCII hostname.

### VICE Compatibility

Not an issue. In VICE, the SwiftLink emulation connects the ACIA directly to a TCP
socket (no modem bridge). The AT command bytes pass through to the server, which has
its own Hayes emulation that detects the "AT" prefix. The server was already expecting
ASCII, so this fix makes both platforms consistent.

### Additional Fixes Applied

While investigating, several other issues were also fixed:
1. Buffer pointer initialization ($01 → $00)
2. RTS never de-asserted during init (CMD goes straight to $09)
3. ATV1→ATDT delay increased to 533ms (matching CCGMS)
4. TX routine now enables transmitter and checks TDRE+DCD (matching CCGMS)
5. Status register read after init to clear pending interrupts

### Current Status

TCP connection established successfully. Server receives connection and sends X.25
handshake (12x $20). Client receives handshake data in NMI buffer (yellow border
debug indicator). Full login sequence not yet tested (debug hangs still in place).

## Known Limitation: Reconnect on Ultimate

After LEAVE, the Ultimate's bridge captures the server's goodbye frame data
("GOODBYE!") into its AT command buffer. On the next CONNECT, the bridge sends
a corrupted hostname to DNS (e.g. "vme.atdtvme.atdtvme." or "oodbye!" prefix).

Root cause: the bridge returns to AT command mode after TCP disconnects, and any
bytes still in transit from the server's goodbye frame are interpreted as AT command
data. The bridge accumulates this until it sees a valid ATDT, prepending the stale
data to the hostname.

This ONLY affects the auto-connect client (no delay between ACIA_INIT and ATDT).
The manual client works because typing the hostname introduces enough delay for
the bridge's buffer to clear.

Attempted fixes that didn't work:
- DTR drop in ACIA_INIT (bridge ignores or locks up the Ultimate menu)
- ATH (hang up) before ATDT (bridge ignores)
- Bare CR before ATDT (breaks VICE — server sees CR as first byte)

Possible future solutions:
- Server stops sending goodbye frame on LEAVE (avoids polluting bridge buffer)
- UCI path (bypasses modem bridge entirely)
- User reloads the PRG between sessions (workaround)

## Next Steps

- Consider implementing UCI path as an alternative to modem emulation (would bypass
  all ACIA/NMI issues entirely, but requires Ultimate-specific code).
