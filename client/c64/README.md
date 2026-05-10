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
- ✅ Input length correct (no off-by-one)
- ✅ ACIA TX works — `ATDT<address>\r` transmitted correctly via IP232
- ✅ tcpser dials through to server
- ✅ "Connecting..." message appears
- ✅ Login screen ("COMPUNET SYSTEM LOGON") displays
- ✅ User can type ID and password
- ✅ Login credentials transmit to server via raw ACIA (through $94C1)
- ✅ Server authenticates correctly (verified TEST/TEST works)
- ✅ Server sends 7707 bytes of linking data (cnet.prg minus PRG header)

### Blocked
- ❌ **ROM never receives the server's linking response** — stuck on "PLEASE WAIT"
  - Server sends 7707 bytes → tcpser logs show "Read N bytes from socket"
  - But bytes never reach VICE's ACIA
  - "LINKING" never appears, border never turns red
  - Same tcpser + VICE setup works fine for CCGMS, so the data path CAN work

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

Everything above the modem layer (X.25 protocol, terminal software,
duckshoot, frame rendering) remains unchanged — only the ACIA access
layer and the login/linking entry points are patched.
