# C64 Client

Single PRG file containing the Compunet ROM, terminal code, and ACIA driver.
Runs in VICE emulator with SwiftLink enabled, connecting to the Compunet
server via tcpser.

## Quick Start

```
# 1. Start tcpser
tcpser -v 25232 -p 6401 -s 1200 -l 7

# 2. Start server
cd server && python3 compunet_server.py

# 3. In VICE (with SwiftLink at port 25232):
LOAD "COMPUNET",8,1
NEW
SYS 33184

# 4. Type CONNECT, enter 127.0.0.1:6400, login with TEST/TEST
```

## Architecture

```
$8000-$9FFF  ROM code (BASIC commands, protocol engine, frame renderer)
$A000-$BE02  Terminal code (duckshoot, directory, frame display)
$C900-$CC6A  ACIA driver (polling-based SwiftLink communication)
$CE00-$CEFF  NMI ring buffer (256 bytes)
$CF00-$CF2F  NMI handler (copied to RAM at init)
```

All communication uses polling (like CCGMS) — NMI stores bytes in a ring
buffer, main code polls the buffer to assemble X.25 packets.

## VICE Configuration

**SwiftLink settings:**
- Enable ACIA RS232 interface emulation: ✓
- Device: Serial 3
- Base address: $DE00
- IRQ: NMI
- Emulation mode: SwiftLink

**RS232 Serial 3:**
- Address: `127.0.0.1:25232`
- Baud: 38400
- IP232: ✓

## Building from Source

```bash
cd src
make
# Output: ../compunet-reborn.prg
```

Requires `ca65` and `ld65` from the [cc65](https://cc65.github.io/) suite.

## Current Status

- ✅ Boot, EDITOR, HELP, CONNECT commands
- ✅ Hayes AT dial through tcpser → TCP connection
- ✅ X.25 handshake (CNET identification + *CON)
- ✅ Login screen, authentication
- ✅ Terminal entry, duckshoot menu
- ✅ DIR command: directory listing with entries, types, column headers
- ✅ Cursor up/down navigation of directory entries
- ✅ F7/F8 column switching (PRICE header works)
- ✅ Duckshoot fully functional after DIR

## Files

- `compunet-reborn.prg` — Ready-to-run PRG
- `src/compunet.s` — Combined assembly source
- `src/compunet.cfg` — Linker configuration
- `src/Makefile` — Build system
- `src/tools/` — Python utilities (disassemblers, verifiers)
- `logs/` — Server log output
- `3rd-party/` — CCGMS source (reference for SwiftLink driver)

## Known Issues

- `NEW` required before `SYS 33184` (BASIC memory pointers)
- Frame header (Part 1) displays at wrong screen position
- Entry alignment off by 1 char between first and subsequent entries
- Phantom third entry from stream termination
- F7/F8 columns 2-4 (LIFE/AUTHOR/VOTE) show blank
- CRC mismatch on transmitted packets (server tolerates)
