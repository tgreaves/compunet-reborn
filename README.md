# Compunet Reborn

A recreation of the Compunet online service protocol and experience using modern systems.

<img src="website/static/animated-walkthrough.gif" width="768">

[Compunet](https://en.wikipedia.org/wiki/Compunet) (also known as CNet) was a UK-based interactive online service that ran from 1984 to May 1993, primarily serving Commodore 64 users. It was operated by Compunet Teleservices Ltd and developed by Ariadne Software. The service featured user-generated content, electronic mail (Courier), telesoftware downloads, a page editor, and a unique horizontally-scrolling menu system known as the "duckshoot".

Users connected via a custom 1200/75 baud modem (the "brick") that plugged into the C64's cartridge port. The modem contained an 8K ROM that bootstrapped the system — the full terminal software was downloaded from the server during each session ("linking"), or cached locally via the CNSAVE command.

## Live Service

The official live instance is running at [https://compunet.live/](https://compunet.live/)

## Current Status

**BETA.** Core functionality is working and under active development.

Working features: directory browsing, content viewing, multi-page frames,
telesoftware downloads/uploads, electronic mail (Courier) with send/receive,
user-generated content, voting, GOTO navigation, sub-directories, UCAT,
advert system, partyline chat, WHO IS ONLINE, and the full duckshoot menu.

Two connection methods are available:
- **Custom client** (port 6400) — full binary protocol, requires SwiftLink emulation
- **PETSCII terminal** (port 6401) — server-rendered, works with any PETSCII terminal program

## Quick Start

### Option 1: PETSCII Terminal (Easiest)

Connect with any PETSCII terminal program (e.g. SyncTerm):
1. Start the server (see below)
2. In SyncTerm: create entry with Connection Type **Raw**, Font **Commodore 64 (UPPER)**, address `localhost:6401`
3. Login with TEST/TEST

### Option 2: Custom Client in VICE

1. Copy templates: `cp -R server/data.example server/data && cp server/cfg/users.json.example server/cfg/users.json`
2. Start server: `./server.sh`
3. In VICE: Settings → Peripheral Devices → RS232 → Enable ACIA, Device Serial 3
4. Serial 3: Host `127.0.0.1:6400`, Baud 1200, IP232 unchecked
5. Load `client/c64/compunet-reborn.d64` — `LOAD "COMPUNET",8` then `RUN`

### Option 3: C64 Ultimate

1. Configure Ultimate: Modem Interface → ACIA / SwiftLink, DE00/NMI
2. Load the auto-connect client (`COMPUNET-LIVE` from D64)
3. Connects automatically to vme.compunet.live:6400

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

Produces: PRG, SFX (self-extracting), auto-connect live variant, and D64 disk image.

Requires: [cc65](https://cc65.github.io/) (ca65/ld65), `c1541` from VICE, `exomizer`.

### Server (local, without Docker)

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
./server.sh start
```

## Repository Structure

### Client

- **[client/c64/src/](client/c64/src/)** — Client source (6502 assembly, ca65)
- **[client/c64/src/partyline/](client/c64/src/partyline/)** — Partyline chat client
- **[client/c64/compunet-reborn.d64](client/c64/compunet-reborn.d64)** — Ready-to-run disk image
- **[client/c64/vintage/](client/c64/vintage/)** — Original reverse engineering artefacts

### Server

- **[server/compunet_server.py](server/compunet_server.py)** — Main server (protocol, API, session management)
- **[server/terminal.py](server/terminal.py)** — PETSCII terminal mode (port 6401)
- **[server/partyline.py](server/partyline.py)** — Multi-user partyline chat
- **[server/cfg/](server/cfg/)** — Configuration (users, bans, templates)
- **[server/data/](server/data/)** — Runtime content (not tracked in git)

### Website

- **[website/](website/)** — Flask web app (registration, admin panel, password reset)

### Documentation

- **[docs/PROTOCOL.md](docs/PROTOCOL.md)** — X.25-derived binary protocol specification
- **[docs/TERMINAL.md](docs/TERMINAL.md)** — PETSCII terminal mode architecture
- **[docs/MODEM.md](docs/MODEM.md)** — Hardware comparison and ACIA driver approach
- **[docs/partyline.md](docs/partyline.md)** — Partyline chat system design
- **[docs/ROM-REWRITE.md](docs/ROM-REWRITE.md)** — PRG-based architecture and build system

### Historical

- **[historical/](historical/)** — Original SEQ files, D64 disk images, documentation

## Acknowledgements

Thanks to Charles Headey for providing the cnboot.prg and cnet.prg files.

Historical SEQ file sources:
- **4Rich** — Graeme Norgate (PIMAN)
- **compunet-pages-interviews** — Frank @ Games That Weren't
- **compunet-sequence-files** — Unknown
- **neil_shumsky** — Neil Shumsky (256 SEQ files extracted from D64 disk images)

Thanks to Mark Wilson for providing the Welcome screen and other historical frames.

Thanks to Richard Hawkins (RH18 FROODLE) for helping source some of these files.

## Links

- [Compunet on Wikipedia](https://en.wikipedia.org/wiki/Compunet)
- [C64 Apocalypse - Compunet pages](http://www.64apocalypse.com/compunet/compunet.htm)
