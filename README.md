# Compunet Reborn

An effort to reverse engineer and recreate the Compunet protocol using modern systems.

<img src="website/static/animated-walkthrough.gif" width="768">

[Compunet](https://en.wikipedia.org/wiki/Compunet) (also known as CNet) was a UK-based interactive online service that ran from 1984 to May 1993, primarily serving Commodore 64 users. It was operated by Compunet Teleservices Ltd and developed by Ariadne Software. The service featured user-generated content, electronic mail (Courier), telesoftware downloads, a page editor, and a unique horizontally-scrolling menu system known as the "duckshoot".

Users connected via a custom 1200/75 baud modem (the "brick") that plugged into the C64's cartridge port. The modem contained an 8K ROM that bootstrapped the system — the full terminal software was downloaded from the server during each session ("linking"), or cached locally via the CNSAVE command.

## Current Status

**This project is in BETA.** Most core functionality has been implemented and is working, but things may break. The system is under active development.

Working features include: directory browsing, content viewing, multi-page frames, telesoftware downloads and uploads, electronic mail (Courier) with send/receive, user-generated content uploads, voting, GOTO navigation, sub-directories, UCAT, advert system, and the full duckshoot menu. 

## Quick Start (C64 in VICE)

### Prerequisites
- VICE C64 emulator (x64sc)
- Python 3 for the server
- cc65 suite (ca65/ld65) and c1541 for building

### Steps
1. Copy the user database template: `cp server/cfg/users.json.example server/cfg/users.json`
2. Start server: `./server.sh`
3. In VICE: Settings → Peripheral Devices → RS232
4. Enable ACIA RS232 interface emulation, set Device to Serial 3
5. Serial 3 settings: Host `127.0.0.1:6400`, Baud 1200, IP232 unchecked
6. Attach `client/c64/compunet-reborn.d64` to drive 8
7. `LOAD "COMPUNET",8,1` then `SYS 33184`
8. Type `CONNECT`, enter `127.0.0.1:6400`
9. Login with TEST/TEST
10. Duckshoot menu appears!

### Automated Testing

```bash
./vice_test.sh <ip_address> <username> <password> [--restart-server]
```

Example: `./vice_test.sh 127.0.0.1:6400 test test --restart-server`

## Docker

The server and website can be deployed with Docker Compose:

```bash
cp .env.example .env
# Edit .env with your configuration
docker compose up -d --build
```

This starts:
- **compunet-server** — C64 protocol server (port 6400) + REST API (port 6403)
- **compunet-web** — Registration website (port 6464)

See `.env.example` for required configuration variables.

## Building from Source

### Client

```bash
cd client/c64/src
make
# Output: ../compunet-reborn.prg, ../compunet-reborn.d64
```

Requires `ca65` and `ld65` from the [cc65](https://cc65.github.io/) suite, and `c1541` from VICE.

### Server (local, without Docker)

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
./server.sh start
```

## Repository Contents

### C64 Client

- **[client/c64/src/](client/c64/src/)** — Source code and build system
- **[client/c64/compunet-reborn.d64](client/c64/compunet-reborn.d64)** — Ready-to-run disk image
- **[client/c64/vintage/](client/c64/vintage/)** — Original reverse engineering artefacts

### Server

- **[server/](server/)** — Python Compunet server
  - TCP interface (port 6400) for C64 clients
  - WebSocket interface (port 6502) for the web client
  - REST API (port 6403) for user management
  - Config in `server/cfg/`, dynamic data in `server/data/`

### Website

- **[website/](website/)** — Flask web app for registration and account management

### Documentation

- **[docs/PROTOCOL.md](docs/PROTOCOL.md)** — Full X.25-derived protocol specification
- **[docs/MODEM.md](docs/MODEM.md)** — Hardware comparison and ACIA driver approach
- **[docs/ROM-REWRITE.md](docs/ROM-REWRITE.md)** — PRG-based architecture and build system
- **[client/c64/README.md](client/c64/README.md)** — Client architecture and known issues

### Historical Sources

- **[historical/](historical/)** — SEQ files, D64 disk images, documentation

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
