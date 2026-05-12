# Compunet Reborn

An effort to reverse engineer and recreate the Compunet protocol using modern systems.

[Compunet](https://en.wikipedia.org/wiki/Compunet) (also known as CNet) was a UK-based interactive online service that ran from 1984 to May 1993, primarily serving Commodore 64 users. It was operated by Compunet Teleservices Ltd and developed by Ariadne Software. The service featured user-generated content, electronic mail (Courier), telesoftware downloads, a page editor, and a unique horizontally-scrolling menu system known as the "duckshoot".

Users connected via a custom 1200/75 baud modem (the "brick") that plugged into the C64's cartridge port. The modem contained an 8K ROM that bootstrapped the system — the full terminal software was downloaded from the server during each session ("linking"), or cached locally via the CNSAVE command.

## Current Status

**The full login → duckshoot flow is working!** (Tag: `login-duckshoot-working`)

- ✅ Single PRG file loads and runs in VICE (`LOAD "COMPUNET",8,1 : NEW : SYS 33184`)
- ✅ EDITOR, HELP, CONNECT commands functional
- ✅ SwiftLink/ACIA communication via polling (no IRQ deadlocks)
- ✅ Hayes AT dial through tcpser → TCP connection to server
- ✅ X.25 handshake: CNET identification + `*CON` response
- ✅ Login screen displays correctly
- ✅ Login packet sent, server authenticates
- ✅ Terminal code enters, duckshoot menu runs
- ✅ EDITOR and HELP work from within the duckshoot (jump table validated)

### Architecture

The C64 client is a single combined PRG (~16KB) containing:
- **ROM code** ($8000-$9FFF) — BASIC commands, protocol engine, frame renderer
- **Terminal code** ($A000-$BE02) — duckshoot, directory navigation, frame display
- **ACIA driver** ($BE03+) — polling-based SwiftLink communication

All communication uses **polling** (like CCGMS), not the original IRQ-driven approach which deadlocks with ACIA hardware. The NMI handler stores incoming bytes in a ring buffer at $CE00; the ACIA driver routines poll this buffer to assemble and deliver X.25 packets.

### Connection Flow

```
SYS 33184 → CONNECT → phone input → ACIA_DIAL (Hayes ATDT via tcpser)
→ ACIA_PROTO_CONNECT (send CNET ID, receive *CON)
→ Login screen → ACIA_SEND_PACKET (login credentials)
→ Skip linking (terminal already embedded) → JMP $A005
→ Terminal init → Duckshoot menu
```

## Repository Contents

### C64 Client

- **[client/c64/src/](client/c64/src/)** — Source code and build system
  - `compunet.s` — Combined source (ROM + terminal + ACIA driver)
  - `compunet.cfg` — ca65/ld65 linker configuration
  - `Makefile` — Build with `make` (requires ca65/ld65 from cc65 suite)
  - `gen_source.py` — ROM disassembler (generates compunet_rom.s from binary)
  - `gen_terminal.py` — Terminal disassembler (generates terminal.s from cnet.prg)
- **[client/c64/compunet-reborn.prg](client/c64/compunet-reborn.prg)** — Ready-to-run PRG

### Web Client

- **[client/web/](client/web/)** — Browser-based Compunet terminal emulator
  - Authentic C64 PETSCII rendering using the real chargen ROM
  - Duckshoot menu, frame editor, SEQ file renderer
  - Open `client/web/index.html` in a browser to use

### Server

- **[server/](server/)** — Python Compunet server
  - WebSocket interface (port 6502) for the web client
  - TCP interface (port 6400) for C64 clients via tcpser
  - X.25 protocol with CRC-CCITT, byte stuffing, flow control
  - User authentication, directory tree, frame serving
  - Run with: `./start-server.sh`

### Documentation

- **[PROTOCOL.md](PROTOCOL.md)** — Full X.25-derived protocol specification
- **[MODEM.md](MODEM.md)** — Original modem vs ACIA hardware comparison and polling approach
- **[ROM-REWRITE.md](ROM-REWRITE.md)** — PRG-based architecture and build system

### Historical Sources

- **[historical/](historical/)** — Original ROM, terminal code, SEQ files, manuals

## Quick Start (C64 in VICE)

### Prerequisites
- VICE C64 emulator with SwiftLink enabled
- tcpser (`tcpser -v 25232 -p 6401 -s 1200 -l 7`)
- Python 3 for the server

### Steps
1. Start tcpser: `tcpser -v 25232 -p 6401 -s 1200 -l 7`
2. Start server: `./start-server.sh`
3. In VICE: enable SwiftLink (Settings → Cartridge/IO → SwiftLink, port 25232)
4. Load: `LOAD "COMPUNET",8,1` then `NEW` then `SYS 33184`
5. Type `CONNECT`, enter `127.0.0.1:6400`
6. Login with any username/password (e.g., TEST/TEST)
7. Duckshoot menu appears!

### Why `NEW` is needed
The `LOAD "...",8,1` command loads the PRG at $8000-$CFXX, which overwrites BASIC's top-of-memory pointer. `NEW` resets BASIC's internal state so that `SYS 33184` doesn't trigger an "OUT OF MEMORY" error. A future improvement will handle this automatically in the ROM's MAIN_INIT.

## Building from Source

```bash
cd client/c64/src
make
# Output: ../compunet-reborn.prg
```

Requires `ca65` and `ld65` from the [cc65](https://cc65.github.io/) suite.

The build produces a single PRG file with a $8000 load address. The Makefile prepends the 2-byte load address header and concatenates the assembled binary.

## How It Works

### Build System

The source (`compunet.s`) is a single combined assembly file containing:
1. The original ROM code (generated from disassembly, with labels for all address references)
2. The terminal code (generated from cnet.prg disassembly)
3. The ACIA driver (hand-written polling-based communication layer)

The `gen_source.py` script performs recursive-descent disassembly of the original ROM binary, identifying code vs data regions and generating proper ca65 source with labels. Address tables use `.lobyte()/.hibyte()` for correct relocation when code shifts.

### Communication Model

The original ROM used IRQ-driven packet assembly — a CIA timer fired at ~60Hz, each tick reading one byte from the brick modem and feeding it into an X.25 state machine. This is incompatible with ACIA/SwiftLink because:
- The ACIA delivers bytes via NMI (not polled one-at-a-time)
- TCP delivers data in bursts (not one byte per 833μs)
- The IRQ handler would consume all buffered bytes in one tick, racing with the main code

Our approach (like CCGMS): NMI stores bytes in a ring buffer. The main code polls the buffer directly, assembling packets inline. No IRQ involvement in receive.

### ROM Modifications

The original ROM code is preserved with targeted patches:
- `MODEM_CHECK` → `JSR ACIA_INIT; JMP L8D52` (skip brick modem detection)
- `MODEM_WAIT_READY` → `JMP ACIA_WAIT_READY`
- `MODEM_REG_WRITE` → `JMP ACIA_REG_WRITE`
- `MODEM_REG_READ` → `JMP ACIA_REG_READ`
- Dial sequence → `JSR ACIA_DIAL; BCS fail; JSR ACIA_PROTO_CONNECT`
- Post-login → skip PROTO_FLOW_CONTROL and MODEM_INIT_DOWNLOAD, jump to $A005
- `$96CC` → `JMP ACIA_PROCESS_CMD` (byte delivery)
- `$96D2` → `JMP ACIA_FLOW_CONTROL` (packet receive)

## Next Steps

- Fix CRC calculation in ACIA_SEND_PACKET (stack offset bug)
- Server sends welcome frame after login
- Implement frame serving (DIR, SHOW commands)
- Handle the `NEW` requirement automatically (BASIC memory pointers)
- Implement Courier (MAIL) and uploads
- Proper TX sequence number initialisation

## Acknowledgements

Thanks to Charles Headey for providing the cnboot.prg and cnet.prg files.

## Links

- [Compunet on Wikipedia](https://en.wikipedia.org/wiki/Compunet)
- [C64 Apocalypse - Compunet pages](http://www.64apocalypse.com/compunet/compunet.htm)
