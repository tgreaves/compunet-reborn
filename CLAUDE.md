# Compunet Reborn — Project Rules

## Protocol Rules

The original X.25-derived packet protocol is preserved on the wire. The ROM's protocol engine ($96C0-$9BFF) handles framing, CRC, sequencing, and flow control unchanged. The server implements the same protocol over TCP — TCP provides the reliable transport that the phone line couldn't, while the X.25 framing provides packet boundaries and sequencing that the ROM expects.

Only the hardware layer ($94E4/$94F0/$94FA) is replaced: the original Compunet modem registers are swapped for 6551 ACIA (SwiftLink) equivalents with NMI-driven receive.

The application-layer protocol (command bytes, response types, directory format, frame format, linking sequence) must be preserved exactly as documented in [docs/PROTOCOL.md](docs/PROTOCOL.md). Do not invent new application-layer commands or alter existing response formats.

## Behaviour Rules

The client and server must always behave like the original Compunet system. All functionality must be verified against the disassembly before implementation. Do not guess or assume behaviour — check the code first.

## Client Rules

1. The client must ALWAYS be rebuilt after any change to `client/c64/src/compunet.s`. Build with `make` in `client/c64/src/`. The output is `client/c64/compunet-reborn.prg`.

## Server Rules

1. The server must ALWAYS be restarted after any change to server Python code. It does not hot-reload. Use `./server.sh restart`. Content files (SEQ frames, root.json) are re-read on each request and do not require a restart.

## Git Rules

1. Only ever commit when instructed to do so by a human.
2. On any commit, ensure [README.md](README.md) and [docs/PROTOCOL.md](docs/PROTOCOL.md) are fully up to date and reflect any changes made.
