# C64 Client

Patched Compunet ROM for use with real C64 hardware (C64 Ultimate) or
VICE emulator with 6551 ACIA modem emulation.

## Architecture

```
C64 (real or VICE)
  └── Patched Compunet ROM (6551 ACIA at $DE00)
        └── Hayes AT commands for dialling
              └── TCP connection to Compunet server
```

The patched ROM replaces the original Compunet modem register routines
with 6551 ACIA equivalents and uses Hayes AT commands to establish a TCP
connection. The X.25 protocol layer and terminal software are unchanged.

## Testing with VICE + tcpser

This setup allows testing the patched ROM without real hardware.

### Prerequisites

- **VICE** (C64 emulator) — https://vice-emu.sourceforge.io/
- **tcpserial** (Java serial-to-TCP bridge with Hayes modem emulation) — https://github.com/MyDeveloperThoughts/tcpserial
- **Java Runtime** (for tcpserial)
- **Compunet server** running on localhost:6400

### Setup

#### 1. Install tcpser (go4retro C version)

```
git clone https://github.com/go4retro/tcpser.git
cd tcpser
make
```

#### 2. Start tcpser

```
tcpser -v 25232 -p 6401 -s 1200 -l 7 -I
```

Options:
- `-v 25232` — listen for VICE IP232 connection on TCP port 25232
- `-p 6401` — inbound listen port (set to 6401 to avoid clash with server on 6400)
- `-s 1200` — serial speed 1200 baud
- `-l 7` — max log level (DEBUG)
- `-I` — invert DTR (required for IP232 mode with VICE)

#### 3. Configure VICE

In VICE (x64sc), configure the RS-232 interface:

**ACIA settings:**
- Enable ACIA RS232 interface emulation: ✓
- Device: Serial 3
- Base address: $DE00
- IRQ: NMI
- Emulation mode: SwiftLink

**RS232 devices:**
- Serial 3: `127.0.0.1:25232`, Baud: 38400, IP232: ✓ (checked)

These settings are confirmed working with CCGMS terminal for 2-way
BBS communication over the Internet.

#### 4. Start the Compunet server

```
cd server
python compunet_server.py
```

This listens on TCP port 6400.

#### 5. Load the patched ROM

Load the patched Compunet cartridge ROM in VICE:
```
x64sc -cartcrt "client/c64/compunet-patched.crt"
```

Or attach it via the VICE menu:
- **File → Attach cartridge image → CRT image**

#### 6. Connect

At the BASIC prompt, type `CONNECT`. The patched ROM will:
1. Send `ATDT127.0.0.1:6400` to tcpser (via the 6551 ACIA)
2. tcpser establishes a TCP connection to the Compunet server
3. tcpser responds with `CONNECT 1200`
4. The ROM proceeds with the login sequence
5. After login, the terminal software is downloaded (linking)
6. The directory duckshoot appears

### Alternative: VICE Direct TCP (no tcpser)

VICE can also connect RS-232 directly to a TCP host without tcpser.
In this mode, VICE handles the TCP connection itself, but there is no
Hayes modem emulation — bytes pass through transparently.

This requires the patched ROM to skip the AT dial sequence and go
straight to the protocol layer after connection. This is a simpler
patch but less realistic.

Configure VICE:
```
x64sc -acia1 -acia1base 0xDE00 -rsdev1 "|nc 127.0.0.1 6400"
```

Or on Windows:
```
x64sc -acia1 -acia1base 0xDE00 -rsdev1 "127.0.0.1:6400"
```

### Real Hardware: C64 Ultimate

The C64 Ultimate has built-in 6551 ACIA emulation with Hayes modem
support over Ethernet/WiFi. Configure it:

1. Open C64U Menu → Modems
2. Set "ACIA (6551) Mapping" to "DE00/NMI"
3. Set "Hardware Mode" to "SwiftLink"
4. Save settings

Then load the patched ROM cartridge and type `CONNECT`. The C64U will
handle the TCP connection via its built-in modem emulation.

## ROM Patch Details

The patch modifies these routines in the 8K ROM at $8000-$9FFF:

| Address | Original | Patched | Purpose |
|---------|----------|---------|---------|
| $807B | "COMPUNET TERMINAL 1.22" | "COMPUNET REBORN 1.00" | Version string |
| $94E4 | MODEM_WAIT_READY | 6551 TX with delay loop | Send byte via ACIA |
| $94F0 | MODEM_REG_WRITE | Filter: TX only if X=3 or 4 | Ignore modem config writes |
| $94FA | MODEM_REG_READ | JMP to extended RX handler | Register-aware read |
| $8D30 | MODEM_CHECK | ACIA init ($DE02=$09, $DE03=$1F) | Initialise 6551 |
| $8D48 | (modem fault path) | JMP $8D52 | Skip fault detection |
| $8D79 | Input max 16 chars | 30 chars | Longer for hostnames |
| $913C/$9140 | Digit-only input filter | Allow $20-$7B | Accept dots, colons, letters |
| $8DA6 | Pulse dial sequence | ATDT + delay + drain | Hayes dial via ACIA |
| $8DF9 | (end of dial code) | Extended RX handler | Register fakes + RDRF poll |
| $8E2A | JSR $96D2 (protocol send) | Break-cancel CR + fall-through | Skip X.25 init send |
| $8E30 | (error path) | JMP to login screen setup | Skip PROTO_CONNECT |
| $8EE0 | JSR $96D2 (login send) | Send CR to cancel break delay | Keep tcpser active |
| $96C6 | Modem init entry | RTS | Disable modem init (no-op) |
| $96C9 | Per-byte send handler | Y-preserving TX wrapper | Used by $94C1 login send |
| $96CC | RECV_BYTE entry | JMP $8E07 (raw ACIA read) | Replace X.25 recv with raw |
| $96D2 | SEND_DATA entry | RTS | Replaced by $94C1 loop |
| $96DB | Modem init data | Y-preserving TX wrapper | 8-byte helper for $96C9 |
| $8EEF-$8EFD | JSR $96CC × 4 | JSR $8E07 × 4 | Direct ACIA reads |

## Progress Summary

### Working
- ✅ Boot message shows "COMPUNET REBORN 1.00"
- ✅ EDITOR command works (no modem needed)
- ✅ CONNECT reaches the "Number?" prompt
- ✅ Input accepts full stops, colons, and letters (for IP addresses/hostnames)
- ✅ ACIA TX works — `ATDT<address>\r` transmitted correctly via IP232
- ✅ tcpser dials through to server
- ✅ "Connecting..." message appears
- ✅ NMI-driven ring buffer receive working (CCGMS-style disable/re-enable RX IRQ)
- ✅ IRQ handler at $9FC8 reads bytes from buffer correctly
- ✅ tcpser break delay handled (register 3 writes filtered, no bytes during delay)
- ✅ Server byte-by-byte sending works through tcpser
- ✅ PROTO_CONNECT handshake: server sends 12 spaces, ROM's 10-byte loop exits
- ✅ ROM sends CNET identification ("C CNET\r...\rADP\rNO\rRUN\r")
- ✅ Server receives identification and responds with `*CON\r`
- ✅ `*CON` appears on C64 screen (bytes received and printed via CHROUT)

### Blocked
- ❌ **PROTO_CONNECT negotiation not completing** — `*CON` signal received and printed
  but the match check at $9F79 fails due to buffer contamination
  - The ROM's own identification bytes (sent via X.25 packets) may be interfering
    with the receive buffer at $0200
  - The `*` character resets the buffer, but other bytes arrive between `*` and `CON\r`
  - Next step: debug the exact buffer contents at the match check point ($9F79)

## The Server→ROM Receive Mystery

This is the current blocker. The return path from server → tcpser → VICE → ACIA → ROM
is not delivering bytes, yet the exact same tcpser + VICE setup works for CCGMS.

### What we know

1. **VICE ACIA TX works** (ROM → server): the server receives all bytes correctly
2. **tcpser receives data from server**: logs show "Read N bytes from socket"
3. **tcpser's `parse_ip_data` writes to VICE via `ip232_write`** (verified in tcpser source)
4. **With CCGMS, data flows both ways**: confirmed by tcpser-known-good-with-ccgms.log
5. **Our ROM's ACIA init**: writes $09 to $DE02 (command) and $1F to $DE03 (control)

### What we've tried

- Polling RDRF (bit 0 of $DE01) — RDRF never gets set
- Reading $DE00 directly — returns the handshake $AA once, then never changes
- Reading $DE01 before $DE00 (in case it acknowledges/advances the ACIA)
- Sending break-cancel bytes ($00, $0D) from the ROM before receiving
- Waiting for tcpser's break delay to expire before server sends
- Direct VICE TCP mode (no tcpser) — same problem: first byte latches, never advances

### Hypotheses to explore next

1. **ACIA init is subtly wrong** — our $DE02/$DE03 values may differ from what CCGMS uses
   - A VSF snapshot of CCGMS is saved at `client/c64/vice-snapshot-ccmgs.vsf`
   - Extract CCGMS's memory state and look at how it polls/reads the ACIA
2. **The receive polling loop is too tight** — needs small delays between polls
3. **Interrupt handling** — with IRQ=NMI, VICE may only deliver bytes via the NMI vector,
   not by updating $DE01 bit 0. Our polling approach may fundamentally not work without
   setting up an NMI handler.

## CCGMS Source Code Analysis

Source: https://github.com/mist64/ccgmsterm (SwiftLink driver in
`rs232lib/rs232_swiftlink.s`). A copy is in `3rd-party/ccgmsterm-main/`.

### Root Cause Identified: NMI-driven receive, not polling

**CCGMS never polls RDRF.** It uses an NMI-driven interrupt handler to receive
bytes. This confirms hypothesis #3 above — with VICE configured for IRQ=NMI,
the emulated 6551 delivers received data by firing an NMI. Polling the status
register does not work.

### How CCGMS receives data (SwiftLink mode)

1. **NMI handler installed** at `$0318/$0319` (KERNAL NMINV vector)
2. When a byte arrives, the 6551 fires an NMI
3. The NMI handler (`nmisw`) reads the byte from `$DE00` (data register)
4. The byte is stored in a 256-byte ring buffer at `$CE00` (`ribuf`)
5. A head/tail pointer pair tracks buffer state (`rtail`/`rhead` at `$029B`/`$029C`)
6. Application code calls `sw_getxfer` which reads from the ring buffer — never
   touches the ACIA directly for receive

### CCGMS NMI handler (annotated)

```
nmisw:
    PHA / TXA / PHA / TYA / PHA     ; save registers
    LDA $DE01                        ; read ACIA status
    AND #%00001000                   ; check bit 3 (TX interrupt flag)
    BNE sm2                          ; if set, this is a real RX interrupt
    SEC                              ; otherwise, not ours — set carry
    BCS recch1                       ; and exit

sm2:
    LDA $DE02                        ; read command register
    ORA #%00000010                   ; disable RX interrupt (bit 1 = 1)
    STA $DE02                        ; write back
    LDA $DE00                        ; read received byte
    LDX rtail                        ; get buffer write pointer
    STA ribuf,X                      ; store byte in ring buffer
    INC rtail                        ; advance write pointer (wraps at 256)
    INC rfree                        ; increment byte count
    LDA rfree
    CMP #200                         ; buffer getting full?
    BCC :+
    LDX #1                           ; yes — assert RTS to pause sender
    STX paused
    JSR flow                         ; toggle RTS via command register
:
    LDA $DE02                        ; read command register
    AND #%11111101                   ; re-enable RX interrupt (bit 1 = 0)
    STA $DE02                        ; write back

recch1:
    PLA / TAY / PLA / TAX / PLA      ; restore registers
    JMP rs232_rti                    ; return from interrupt
```

### CCGMS ACIA initialisation

```
Command register ($DE02) = %00001001 = $09
    Bit 0   = 1: DTR active (low)
    Bit 1   = 0: RX interrupt ENABLED ← critical
    Bits 2-3 = 10: TX interrupt disabled, RTS low
    Bit 4   = 0: normal (no echo)
    Bits 5-7 = 000: no parity

Control register ($DE03) = %00010000 | baud_bits
    Bit 4   = 1: internal baud rate generator
    Bits 5-6 = 00: 8-bit word length
    Bit 7   = 0: 1 stop bit
    Bits 0-3 = baud rate (e.g. $17 for 1200 via SwiftLink 2x divider)
```

### CCGMS application-level receive (`sw_getxfer`)

```
sw_getxfer:
    LDX rhead              ; buffer read pointer
    CPX rtail              ; compare with write pointer
    BEQ @empty             ; if equal, buffer empty — return with C set
    LDA ribuf,X            ; read byte from buffer
    PHA
    INC rhead              ; advance read pointer
    DEC rfree              ; decrement byte count
    LDX paused             ; were we paused (RTS high)?
    BEQ :+
    LDA rfree
    CMP #50                ; buffer drained enough?
    BCS :+
    LDX #0                 ; yes — de-assert RTS to resume sender
    STX paused
    JSR flow
:   CLC                    ; carry clear = byte available
    PLA
@empty:
    RTS                    ; carry set = no data
```

### CCGMS RAM NMI vector setup

CCGMS patches the RAM-under-ROM NMI vector at `$FFFA/$FFFB` to point to a
trampoline (`ramnmi`) that banks in RAM and jumps through `$0318/$0319`:

```
setup_ram_irq_nmi:
    LDA #<ramnmi
    STA $FFFA          ; NMI vector (RAM under KERNAL ROM)
    LDA #>ramnmi
    STA $FFFB
    ...

ramnmi:
    INC $01            ; bank in RAM (hide I/O? or KERNAL?)
    DEC ram_flag       ; mark we're in RAM mode
    JMP ($0318)        ; jump to actual NMI handler (nmisw)
```

The `rs232_rti` routine restores `$01` and does RTI.

### Comparison with our ROM patch

| Aspect | Our ROM (broken) | CCGMS (working) |
|--------|-----------------|-----------------|
| RX method | Poll RDRF (bit 0 of $DE01) | NMI interrupt handler |
| NMI vector | Not set up | Custom handler at $0318/$0319 |
| Buffer | None — direct read from $DE00 | 256-byte ring buffer at $CE00 |
| Flow control | None | RTS toggled via command register |
| $DE02 init | $09 (RX IRQ enabled) | $09 (same) |
| $DE03 init | $1F (19200 baud) | $10 + baud bits |

**The init values match** — our $09 in the command register does enable the
RX interrupt (bit 1 = 0). But we never installed an NMI handler to service
it. VICE's emulated 6551 fires the NMI, the default KERNAL NMI handler runs
(which does nothing useful with ACIA data), and the byte is lost.

### What needs to change

1. **Install an NMI handler** that reads bytes from `$DE00` into a ring buffer
2. **Set up the NMI vector** at `$0318/$0319` (or patch `$FFFA/$FFFB` in RAM)
3. **Rewrite RECV_BYTE** ($8E07) to read from the ring buffer instead of
   polling the ACIA status register
4. Optionally implement RTS flow control (may not be needed at 1200 baud)

### RAM locations available for the NMI handler

The ring buffer can go at `$CE00` (same as CCGMS — 256 bytes, not used by
the Compunet ROM or terminal software). Head/tail pointers can use the
KERNAL RS-232 locations at `$029B`/`$029C` (same as CCGMS).

The NMI handler code (~40 bytes) can be placed in the protocol workspace
area or in the gap between the BASIC stub and the ROM code.

## Known-good configuration (verified with CCGMS)

**tcpser:** `tcpser -v 25232 -p 6401 -s 1200 -l 7 -I`

**VICE ACIA:**
- Enable ACIA RS232 interface emulation: ✓
- Device: Serial 3
- Base address: $DE00
- IRQ: **NMI**
- Emulation mode: **SwiftLink**

**VICE Serial 3:**
- Address: `127.0.0.1:25232`
- Baud: 38400
- IP232: ✓ (checked)

**Server:** `python3 server/compunet_server.py` (listens on port 6400)

## The 6551 ACIA register map

| Address | Read | Write |
|---------|------|-------|
| $DE00 | RX Data | TX Data |
| $DE01 | Status (bit 0=RDRF, bit 3=TDRE, bit 5=DCD) | Reset |
| $DE02 | Command | Command ($09 = DTR active, RX IRQ on) |
| $DE03 | Control | Control ($1F = 19200 baud 8N1) |

## Files in this directory

- `patch_rom.py` — Builds `compunet-reborn.crt` from `historical/Compunet Terminal.crt`
- `compunet-reborn.crt` — Patched ROM ready for VICE cartridge slot
- `compunet-reborn.prg` — Same ROM as a PRG (load at $8000)
- `compunet-loader.prg` — BASIC loader stub
- `ccgms.prg` — Reference working terminal (for comparison)
- `vice-snapshot-ccmgs.vsf` — VICE snapshot of running CCGMS (for disassembly)
- `extract_vsf.py` — Helper to extract memory modules from VSF snapshots
- `tcp_sniffer.py` — TCP listener that logs all bytes (for debugging VICE→tcpser)
- `check_input.py` — Helper to disassemble ROM input handling routines
- `logs/tcpser-known-good-with-ccgms.log` — Reference log of working data flow
- `3rd-party/ccgmsterm-main/` — CCGMS Future source (reference for SwiftLink driver)

Everything above the modem layer (X.25 protocol, terminal software,
duckshoot, frame rendering) remains unchanged — only the ACIA access
layer and the login/linking entry points are patched.
