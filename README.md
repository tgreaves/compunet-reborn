# Compunet Reborn

An effort to reverse engineer and recreate the Compunet protocol using modern systems.

[Compunet](https://en.wikipedia.org/wiki/Compunet) (also known as CNet) was a UK-based interactive online service that ran from 1984 to May 1993, primarily serving Commodore 64 users. It was operated by Compunet Teleservices Ltd and developed by Ariadne Software. The service featured user-generated content, electronic mail (Courier), telesoftware downloads, a page editor, and a unique horizontally-scrolling menu system known as the "duckshoot".

Users connected via a custom 1200/75 baud modem (the "brick") that plugged into the C64's cartridge port. The modem contained an 8K ROM that bootstrapped the system — the full terminal software was downloaded from the server during each session ("linking"), or cached locally via the CNSAVE command.

## Repository Contents

### Analysis

- **[PROTOCOL.md](PROTOCOL.md)** — Full reverse-engineered protocol specification including modem hardware interface, connection sequence, packet format, command tokens, flow control, and CRC details. This is the key document for reimplementation.

- **[compunet_terminal_v122.asm](compunet_terminal_v122.asm)** — Annotated 6502 disassembly of the Compunet Terminal cartridge ROM (v1.22, September 1984). The bootstrap loader: modem control, dialling, login, protocol engine.

- **[cnet_terminal_disasm.asm](cnet_terminal_disasm.asm)** — Annotated 6502 disassembly of the downloaded terminal software (cnet.prg). The application layer: directory navigation, duckshoot, SHOW, BUY, MAIL, UPLOAD, VOTE, etc. Runs at $9FF0-$BE02.

### Tools

- **[generate_final.py](generate_final.py)** — Python script that produces the ROM disassembly from the raw binary.
- **[gen_cnet_disasm.py](gen_cnet_disasm.py)** — Python script that produces the terminal software disassembly from cnet.prg.

### Historical Sources

- **[historical/Compunet Terminal.crt](historical/Compunet%20Terminal.crt)** — Original cartridge ROM image in VICE .crt format.
- **[historical/chip0_bank0_8000.bin](historical/chip0_bank0_8000.bin)** — Extracted 8K ROM binary (raw bytes at $8000-$9FFF).
- **[historical/cnet.prg](historical/cnet.prg)** — The downloaded terminal software (7.5KB). This is the code sent during "linking" that provides the full interactive experience: directory navigation, duckshoot, Courier mail, uploads, downloads, etc. Provided by Charles Headey.
- **[historical/cnboot.prg](historical/cnboot.prg)** — Multi-mode boot loader (2.1KB) offering CNET, TTY, Viewdata, and user-to-user modes. Provided by Charles Headey.
- **[historical/Terminal Disassembly.txt](historical/Terminal%20Disassembly.txt)** — Third-party disassembly found online, used for cross-referencing.
- **[historical/compunet-instructions-uk.pdf](historical/compunet-instructions-uk.pdf)** — Scanned original Compunet instruction manual.
- **[historical/compunet-instructions-extracted.txt](historical/compunet-instructions-extracted.txt)** — OCR text extraction of the instruction manual.

## What We Know

The 8K ROM is a bootstrap loader. It provides:
- BASIC commands: `CONNECT`, `EDITOR`, `CNLOAD`, `CNSAVE`, `HELP`, `OFF`
- Modem hardware control (register-select I/O at $DE00/$DE01)
- Dialling and carrier detection
- Login sequence (user ID + password)
- X.25-derived packet protocol with CRC-CCITT and windowed flow control
- The "linking" download mechanism (receives up to 8K of terminal software)

The full interactive terminal (duckshoot navigation, directory browsing, frame rendering, Courier mail, uploads, etc.) lives in **downloaded code** that was sent from the server during linking and stored in RAM at $C800+. This code is not present in the ROM image.

## What's Missing

- **Server-side protocol details** — the application-layer commands and responses beyond what can be inferred from the client code.
- **Frame format specification** — how pages (text, graphics, colour) are encoded in the data stream (partially recoverable from cnet.prg analysis).

## Acknowledgements

Thanks to Charles Headey for providing the cnboot.prg and cnet.prg files — the downloaded terminal software that was previously missing from this analysis.

## Protocol Summary

| Aspect | Detail |
|--------|--------|
| Speed | 1200 baud down, 75 baud up (asymmetric Viewdata) |
| Framing | $01 = start of packet, $02 = end of packet |
| Commands | ACK ($20), DIR ($21), DAT ($22), OK ($23), ERR ($24), FTL ($25), COM ($26) |
| Error detection | CRC-CCITT (polynomial $1021) |
| Flow control | Sliding window, size 4, sequence range $20-$5F |
| Timeout | 2 minutes idle, 10 minutes in editor |

## Goal

Recreate the Compunet protocol on modern infrastructure so that original C64 clients (or emulated ones) can connect to a new server, and the community experience can be revived.

## Links

- [Compunet on Wikipedia](https://en.wikipedia.org/wiki/Compunet)
- [C64 Apocalypse - Compunet pages](http://www.64apocalypse.com/compunet/compunet.htm)
