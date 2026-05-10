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

#### 1. Install tcpserial

```
git clone https://github.com/MyDeveloperThoughts/tcpserial.git
cd tcpserial
```

Build with Maven or use the pre-built JAR if available.

#### 2. Start tcpserial

tcpserial listens on a TCP port for VICE to connect to, and emulates a
Hayes modem. When the C64 software sends AT commands, tcpserial handles
them and establishes outbound TCP connections.

```
java -jar tcpserial.jar -p 25232 -s 1200
```

Options:
- `-p 25232` — listen for VICE connection on TCP port 25232
- `-s 1200` — serial speed 1200 baud (matches Compunet's 1200/75)

Refer to the tcpserial documentation for full command-line options.

#### 3. Configure VICE

In VICE (x64sc), configure the RS-232 interface:

1. **Settings → Cartridge/IO Settings → RS-232 Interface**
   - Enable "ACIA DE00" (SwiftLink at $DE00)
   - Set "ACIA Device" to "Device 1"

2. **Settings → RS-232 Settings**
   - Device 1: `127.0.0.1:25232` (connects to tcpser)

Alternatively, use VICE command-line options:
```
x64sc -acia1 -acia1base 0xDE00 -rsdev1 "127.0.0.1:25232"
```

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

| Original | Patched | Purpose |
|----------|---------|---------|
| $94E4 (MODEM_WAIT_READY) | 6551 TX (STA $DE00 + delay) | Send byte via ACIA |
| $94F0 (MODEM_REG_WRITE) | JMP $94E4 | Redirect to TX |
| $94FA (MODEM_REG_READ) | 6551 RX with poll | Receive byte via ACIA |
| $8D30-$8D4A (modem check) | ACIA init ($DE02/$DE03) | Initialise 6551 |
| $8DA6-$8DE5 (dial sequence) | Hayes ATDT command | Send AT command via ACIA |
| $913C/$9140 (input filter) | Widened char range | Accept dots/colons/letters |
| $8D79 (input max length) | 30 chars | Longer for hostnames |
| $807B (version string) | "COMPUNET REBORN 1.00" | Identify patched version |

## Current Progress

- ✅ Boot message shows "COMPUNET REBORN 1.00"
- ✅ EDITOR command works (no modem needed)
- ✅ CONNECT reaches the "Number?" prompt
- ✅ Input accepts full stops, colons, and letters (for IP addresses/hostnames)
- ✅ ACIA TX confirmed working — full `ATDT<address>` command transmitted via IP232
- ✅ VICE connects to tcpserial, tcpserial connects to Compunet server
- ⏳ C64 hangs waiting for "CONNECT" response from tcpserial — AT command may not be fully recognised (investigating CR/LF termination and timing)

### Known Issues

1. **VICE ACIA requires IRQ set to "None"** — NMI mode causes byte drops during TX
2. **TX requires a delay loop** ($FF iterations) between bytes — without it, VICE's ACIA emulation drops characters
3. **tcpserial not responding with CONNECT** — the AT command is being sent correctly (verified with tcp_sniffer.py) but tcpserial may not be recognising it. Possible causes: extra trailing byte, CR not received, or IP232 framing issue

The 6551 ACIA registers at $DE00-$DE03:

| Address | Read | Write |
|---------|------|-------|
| $DE00 | RX Data | TX Data |
| $DE01 | Status (bit 3=TX empty, bit 0=RX full) | Reset |
| $DE02 | Command | Command |
| $DE03 | Control | Control (baud rate) |

Everything above the modem layer (X.25 protocol, terminal software,
duckshoot, frame rendering) remains unchanged.
