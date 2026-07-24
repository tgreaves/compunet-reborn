# Compunet Reborn

A recreation of the Compunet online service for the Commodore 64, faithfully preserving the original protocol and user experience over modern TCP/IP.

<img src="website/static/animated-walkthrough.gif" width="768">

[Compunet](https://en.wikipedia.org/wiki/Compunet) (also known as CNet) was a UK-based interactive online service that ran from 1984 to May 1993, primarily serving Commodore 64 users. It was operated by Compunet Teleservices Ltd and developed by Ariadne Software. The service featured user-generated content, electronic mail (Courier), telesoftware downloads, a page editor, and a unique horizontally-scrolling menu system known as the "duckshoot".

Users connected via a custom 1200/75 baud modem (the "brick") that plugged into the C64's cartridge port. The modem contained an 8K ROM that bootstrapped the system — the full terminal software was downloaded from the server during each session ("LINKING"), or cached locally via the CNSAVE command.

Compunet also shipped a native **Amiga** client in 1989. That original binary has been recovered and reverse-engineered, reconstructed as recompilable C (vbcc), and re-pointed from its modem/`cnet.device` transport to native TCP/IP — so a real or emulated Amiga running Workbench/Kickstart 2.1+ can connect to Compunet Reborn today. See [Connection Methods](#connection-methods) and [docs/amiga-client.md](docs/amiga-client.md).

## Live Service

The official live instance is running at [https://compunet.live/](https://compunet.live/)

## Features

- Directory browsing with full duckshoot menu
- Content viewing (multi-page text frames, PETSCII graphics)
- Telesoftware downloads and uploads
- Electronic mail (Courier) with send/receive and email notifications
- User-generated content (The Jungle) with voting
- Partyline multi-user chat with rooms
- WHO IS ONLINE (live user list)
- WHAT'S NEW (most recent uploads)
- GOTO keyword navigation
- Frame editor (on-line and off-line)
- PETSCII terminal mode (server-rendered, any terminal program)
- 8K cartridge ROM — boots directly like the original hardware
- Native Amiga client — the recovered 1989 Amiga client, reconstructed over TCP/IP

## Connection Methods

| Method | Port | Description |
|--------|------|-------------|
| **C64 Client (CRT)** | 6400 | 8K cartridge — attach and boot. Recommended for VICE / C64 Ultimate. |
| **C64 Client (PRG)** | 6400 | LOAD + RUN. For real hardware with SwiftLink. |
| **Amiga Client** | 6400 | Native Amiga client (LHA download). Needs Workbench/Kickstart 2.1+ and a bsdsocket TCP/IP stack. |
| **PETSCII Terminal** | 6401 | Server-rendered. Works with SyncTerm, CCGMS, StrikeTerm, UltimateTerm. |

## Quick Start

### Option 1: CRT Cartridge (Recommended)

1. Download `compunet-reborn-live.crt` from [compunet.live/connect](https://compunet.live/connect)
2. VICE: File → Attach cartridge image → Reset
3. C64 Ultimate: Select as cartridge → Reset
4. Type `CONNECT` — LINKING downloads terminal software (~3 sec first time)
5. Login with your registered account

### Option 2: PETSCII Terminal

Connect with SyncTerm or any PETSCII terminal:
- Address: `vme.compunet.live:6401`
- Connection Type: Raw
- Screen Mode: C64
- Font: Commodore 64 (LOWER)

### Option 3: PRG (Real Hardware)

1. `LOAD "COMPUNET-REBORN-LIVE",8` then `RUN`
2. Type `CONNECT`
3. LINKING downloads terminal software
4. Login

### Option 4: Amiga

1. Download `compunet-reborn-amiga.lha` from [compunet.live/connect](https://compunet.live/connect)
2. Un-archive it (`lha x compunet-reborn-amiga.lha`) — you get a **Compunet** drawer
3. Make sure a bsdsocket TCP/IP stack (Roadshow, AmiTCP, Miami…) is installed and online
4. Double-click the **Compunet** icon (or run it from a Shell)
5. Login with your registered account

Requires Workbench / Kickstart 2.1 or higher. The bundled `TCPHOST` file is preset to `vme.compunet.live:6400` — edit it only to point at a different server.

## Docker Deployment

```bash
cp .env.example .env
# Edit .env with your configuration
docker compose up -d --build
```

This starts:
- **compunet-server** — Protocol server (6400) + PETSCII terminal (6401) + REST API (6403)
- **compunet-web** — Registration website (6464)

See `.env.example` for required configuration variables.

## Building from Source

### Client

```bash
cd client/c64/src
make
```

Produces:
- `compunet-reborn.prg` — Manual connect (LOAD + RUN)
- `compunet-reborn-live.prg` — Auto-connect (LOAD + RUN)
- `compunet-reborn.crt` — 8K cartridge (manual)
- `compunet-reborn-live.crt` — 8K cartridge (auto-connect)
- `compunet-reborn.d64` — D64 with both PRGs
- `terminal.bin` — Terminal binary for server LINKING

Requires: [cc65](https://cc65.github.io/) (ca65/ld65), `c1541` from VICE.

### Amiga Client

```bash
cd client/amiga/emulation
VBCC=/path/to/vbcc ./make_hdd.sh
```

Compiles the reconstructed client (`client/amiga/src/`) with vbcc, stages a mountable Directory-HD under `hdd/` for emulator testing, and builds the distribution LHA archives into `client/amiga/dist/` (public + `-dev`) plus the Aminet `.readme` — via `make_lha.py`.

Requires: [vbcc](http://sun.hasenbraten.de/vbcc/) (m68k-amigaos) + vasm, and `xdftool` from [amitools](https://github.com/cnvogelg/amitools) for the ADF/icon steps. See [docs/amiga-client.md](docs/amiga-client.md) for the reverse-engineering and reconstruction details.

### Server (local, without Docker)

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
./server.sh start
```

## Architecture

The client is split into two parts, matching the original Compunet design:

- **ROM** (8K, $8000-$9FFF) — Boot code, BASIC extensions (CONNECT, CNLOAD, CNSAVE, EDITOR), ACIA SwiftLink driver, protocol dispatch
- **Terminal** (~7.7K, downloaded to $A000+) — Directory rendering, frame display, duckshoot, mail, uploads, partyline link

On first connect, the server sends the terminal via LINKING (~3 seconds). Users can cache it to disk with `CNSAVE` for instant reconnects. The server tracks a version hash — LINKING is skipped if the cached terminal is current.

## Repository Structure

### Client

- **[client/c64/src/](client/c64/src/)** — C64 client source (6502 assembly, ca65)
- **[client/c64/src/partyline/](client/c64/src/partyline/)** — Partyline chat client
- **[client/c64/src/gen_sfx.py](client/c64/src/gen_sfx.py)** — PRG builder (BASIC stub + relocator)
- **[client/c64/vintage/](client/c64/vintage/)** — Original C64 reverse engineering artefacts
- **[client/amiga/src/](client/amiga/src/)** — Reconstructed native Amiga client (C, vbcc)
- **[client/amiga/emulation/](client/amiga/emulation/)** — Amiga build + packaging (`make_hdd.sh`, `make_lha.py`, Directory-HD, LHA)
- **[client/amiga/vintage/](client/amiga/vintage/)** — Recovered original Amiga binaries + RE tooling

### Server

- **[server/compunet_server.py](server/compunet_server.py)** — Main server (protocol, LINKING, API, session management)
- **[server/terminal.py](server/terminal.py)** — PETSCII terminal mode (port 6401)
- **[server/partyline.py](server/partyline.py)** — Multi-user partyline chat
- **[server/cfg/](server/cfg/)** — Configuration (users, terminal.bin, templates)
- **[server/data/](server/data/)** — Runtime content (not tracked in git)

### Website

- **[website/](website/)** — Flask web app (registration, admin panel, password reset, guide)

### Documentation

- **[docs/PROTOCOL.md](docs/PROTOCOL.md)** — X.25-derived binary protocol specification (incl. terminal linking / CNLOAD)
- **[docs/TERMINAL.md](docs/TERMINAL.md)** — PETSCII terminal mode architecture
- **[docs/MODEM.md](docs/MODEM.md)** — Hardware comparison and ACIA driver approach
- **[docs/ROM-REWRITE.md](docs/ROM-REWRITE.md)** — C64 ROM rewrite rationale and structure
- **[docs/partyline.md](docs/partyline.md)** — Partyline chat system design
- **[docs/amiga-client.md](docs/amiga-client.md)** — Analysis of the recovered vintage Amiga Compunet client
- **[docs/amiga-modern-ux.md](docs/amiga-modern-ux.md)** — Modern-UX proposal for the Amiga client
- **[docs/historical/](docs/historical/)** — Retired investigation notes and completed implementation plans

### Historical

- **[historical/](historical/)** — Original SEQ files, D64 disk images, documentation

## Acknowledgements

Thanks to Charles Headey for providing the cnboot.prg and cnet.prg files.

Historical SEQ file sources:
- **4Rich** — Graeme Norgate (PIMAN)
- **compunet-pages-interviews** — Frank @ Games That Weren't
- **compunet-sequence-files** — Unknown
- **neil_shumsky** — Neil Shumsky (256 SEQ files extracted from D64 disk images)

Thanks to Mark Wilson for providing the Welcome screen, music, and other historical frames.

Thanks to Richard Hawkins (RH18 FROODLE) for helping source some of these files.

## Links

- [Compunet on Wikipedia](https://en.wikipedia.org/wiki/Compunet)
- [C64 Apocalypse - Compunet pages](http://www.64apocalypse.com/compunet/compunet.htm)
