# Compunet Reborn

An effort to reverse engineer and recreate the Compunet protocol using modern systems.

[Compunet](https://en.wikipedia.org/wiki/Compunet) (also known as CNet) was a UK-based interactive online service that ran from 1984 to May 1993, primarily serving Commodore 64 users. It was operated by Compunet Teleservices Ltd and developed by Ariadne Software. The service featured user-generated content, electronic mail (Courier), telesoftware downloads, a page editor, and a unique horizontally-scrolling menu system known as the "duckshoot".

Users connected via a custom 1200/75 baud modem (the "brick") that plugged into the C64's cartridge port. The modem contained an 8K ROM that bootstrapped the system — the full terminal software was downloaded from the server during each session ("linking"), or cached locally via the CNSAVE command.

## Current Status

**Directory browsing is working!**

- ✅ Single PRG file loads and runs in VICE (`LOAD "COMPUNET",8,1 : NEW : SYS 33184`)
- ✅ EDITOR, HELP, CONNECT commands functional
- ✅ SwiftLink/ACIA communication via polling (no IRQ deadlocks)
- ✅ Hayes AT dial through tcpser → TCP connection to server
- ✅ X.25 handshake: CNET identification + `*CON` response
- ✅ Login screen displays correctly
- ✅ Login packet sent, server authenticates
- ✅ Welcome frame displayed after login (template-based with user info, last login, mail indicator)
- ✅ Terminal code enters, duckshoot menu runs
- ✅ DIR command sends request, server responds with directory data
- ✅ Directory entries display with titles, type suffixes, page numbers
- ✅ Correct colours (blue unselected, red selected/highlighted)
- ✅ Cursor up/down navigation of directory entries
- ✅ F7/F8 column switching (PRICE, LIFE, AUTHOR, VOTE all display correctly)
- ✅ Column data renders correctly for all entries
- ✅ SHOW command displays text frames with correct colours
- ✅ Multi-page frames supported (MORE advances, FINISH returns to DIR)
- ✅ Sub-directories: entries with "+" suffix can be entered via DIR
- ✅ BACK command navigates to parent directory
- ✅ Multi-packet responses (>100 bytes) delivered reliably with EOS marker
- ✅ Courier (MAIL): inbox listing, read messages, mark as read
- ✅ Courier SEND: compose and deliver messages to other users
- ✅ Courier SEND: destination user validation with real names
- ✅ Courier SEND: FROM/DATE/TIME fields on compose screen
- ✅ Courier envelope: server auto-generates header frame (FROM/DATE/TIME/SUBJECT/TO) on delivery
- ✅ Frame upload via ACIA_UPLOAD_BYTE (replaced PROTO_RECV_FRAME)
- ✅ LEAVE command: goodbye frame displayed, connection closed gracefully
- ✅ UPLOAD: users can upload text frames to directories, persisted to root.json
- ✅ UPLOAD permissions: admins anywhere, users in JUNGLE or own directories only
- ✅ Sub-directory creation: DIR on page without children creates empty sub-directory
- ✅ VOTE: users vote 1-9 on pages, average + count shown in VOTE column
- ✅ GOTO: navigate by page number or keyword (e.g. "GOTO JUNGLE")
- ✅ JUNGLE area (page 600): communal upload area accessible by keyword
- ✅ Advert area: two configurable text lines above duckshoot, per-directory or global
- ✅ Live content reload: directory tree re-read from disk on each request (no restart needed)
- ✅ Historical content: THE ZOO archive (14 articles by PIMAN) in the JUNGLE
- ✅ Telesoftware: program downloads (type 'P') with 2-phase header/data protocol
- ✅ Duckshoot fully functional throughout

### Architecture

The C64 client is a single combined PRG (~16KB) containing:
- **ROM code** ($8000-$9FFF) — BASIC commands, protocol engine, frame renderer
- **Terminal code** ($A000-$BE02) — duckshoot, directory navigation, frame display
- **ACIA driver** ($BE03+) — polling-based SwiftLink communication

All communication uses **NMI-driven receive** with a ring buffer at $CE00. The NMI handler stores incoming ACIA bytes; driver routines poll the ring buffer exclusively (never reading ACIA_DATA directly from mainline code, which would race with the NMI handler and cause byte duplication). X.25 packets are assembled from the ring buffer by ACIA_FLOW_CONTROL and delivered byte-by-byte via ACIA_PROCESS_CMD.

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
  - Raw PETSCII text viewer (auto-detected, paginates text files like Partyline logs)
  - Open `client/web/index.html` in a browser to use

### Server

- **[server/](server/)** — Python Compunet server
  - WebSocket interface (port 6502) for the web client
  - TCP interface (port 6400) for C64 clients via tcpser
  - X.25 protocol with CRC-CCITT, byte stuffing, flow control
  - User authentication, directory tree, frame serving
  - Run with: `./server.sh` (supports start/stop/restart/status)
  - Content stored in folder-per-page layout under `server/content/root/`
  - Per-directory JSON files with flat page lists
  - Advert system: configurable text per directory, global fallback

### Documentation

- **[docs/PROTOCOL.md](docs/PROTOCOL.md)** — Full X.25-derived protocol specification
- **[docs/MODEM.md](docs/MODEM.md)** — Original modem vs ACIA hardware comparison and polling approach
- **[docs/ROM-REWRITE.md](docs/ROM-REWRITE.md)** — PRG-based architecture and build system

### Historical Sources

- **[historical/](historical/)** — Original ROM, terminal code, SEQ files, manuals
  - `historical/seq/` — Extracted SEQ files from various sources (indexed with INDEX.txt per directory)
  - `historical/Neil Shumsky DISKS/` — Collection of 107 D64 disk images from Neil Shumsky
  - `historical/neil_shumsky_disk_listing.txt` — Directory listing of all D64 images

## Quick Start (C64 in VICE)

### Prerequisites
- VICE C64 emulator with SwiftLink enabled
- tcpser (`tcpser -v 25232 -p 6401 -s 1200 -l 7`)
- Python 3 for the server
- cc65 suite (ca65/ld65) and c1541 for building

### Steps
1. Start tcpser: `tcpser -v 25232 -p 6401 -s 1200 -l 7`
2. Start server: `./server.sh`
3. In VICE: enable SwiftLink (Settings → Cartridge/IO → SwiftLink, port 25232)
4. Attach `client/c64/compunet-reborn.d64` to drive 8
5. Load: `LOAD "COMPUNET",8,1` then `NEW` then `SYS 33184`
6. Type `CONNECT`, enter `127.0.0.1:6400`
7. Login with any username/password (e.g., TEST/TEST)
8. Duckshoot menu appears!

### Automated Testing

Use `vice_test.sh` to launch VICE with the client and automate the login sequence:

```bash
./vice_test.sh <ip_address> <username> <password> [--restart-server]
```

Example: `./vice_test.sh 127.0.0.1:6400 test test --restart-server`

This launches x64sc with the D64 disk image on drive 8, remote monitor on port 6510, and injects keystrokes via `keybuf` to automate SYS, CONNECT, and login. The remote monitor remains available for debug sessions after login completes. Downloaded programs are saved to the same D64 disk image.

### Why `NEW` is needed
The `LOAD "...",8,1` command loads the PRG at $8000-$CFXX, which overwrites BASIC's top-of-memory pointer. `NEW` resets BASIC's internal state so that `SYS 33184` doesn't trigger an "OUT OF MEMORY" error. A future improvement will handle this automatically in the ROM's MAIN_INIT.

## Building from Source

```bash
cd client/c64/src
make
# Output: ../compunet-reborn.prg, ../compunet-reborn.d64
```

Requires `ca65` and `ld65` from the [cc65](https://cc65.github.io/) suite, and `c1541` from VICE.

The build produces a PRG file with a $8000 load address and a D64 disk image containing it. The D64 is used by VICE for both loading the client and saving downloaded programs.

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

Our approach: NMI stores incoming bytes in a ring buffer ($CE00). All mainline code reads exclusively from the ring buffer — never directly from ACIA_DATA — to avoid race conditions where the NMI handler and mainline code both read the same byte, causing duplication. ACIA_STATUS reads are used solely to trigger VICE's socket polling.

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

- Handle the `NEW` requirement automatically (BASIC memory pointers)
- Fix CRC calculation in ACIA_SEND_PACKET
- Replace L96C9 (PROTO_RECV_FRAME) with ACIA-based upload routine for MAIL SEND frame upload
- Advert area (bottom two screen rows)
- Disconnect detection: client does not detect server disconnection (restart/timeout). The ROM checks modem register 0 bit 5 for carrier loss, but VICE's ACIA emulation doesn't map TCP socket state to DCD. A software-level solution is needed — possibly a server-sent keepalive packet or a protocol-aware idle timeout that distinguishes "end of stream" from "connection dead".

## Acknowledgements

Thanks to Charles Headey for providing the cnboot.prg and cnet.prg files.

Historical SEQ file sources:
- **4Rich** — Graeme Norgate (PIMAN)
- **compunet-pages-interviews** — Frank @ Games That Weren't
- **compunet-sequence-files** — Unknown
- **neil_shumsky** — Neil Shumsky (256 SEQ files extracted from D64 disk images)

Thanks to Richard Hawkins (RH18 FROODLE) for helping source some of these files.

## Links

- [Compunet on Wikipedia](https://en.wikipedia.org/wiki/Compunet)
- [C64 Apocalypse - Compunet pages](http://www.64apocalypse.com/compunet/compunet.htm)
