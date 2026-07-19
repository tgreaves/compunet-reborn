# Amiga frame format & the PETSCII question (goal 3)

## Question

C64 Compunet content is PETSCII. The Amiga has no native PETSCII. So: does the
Amiga client translate PETSCII, use a custom C64 font, or something else?

## Answer: the Amiga does NOT use PETSCII at all

Amiga Compunet frames use their own **ESC-sequence markup format**, not PETSCII.
Evidence from the sample `Frames/test.frame` (557 bytes):

```
0d 0d 0d 14 0a 1b 51 73 73 ... 73 1b 43 1b 4d 20 "WELCOME" 1b 4c 1b 51 20 73 ...
\r \r \r \x14 \n ESC Q  s  s  ...  s  ESC C ESC M   WELCOME  ESC L ESC Q     s ...
```

- **Text is plain ASCII** ("WELCOME"), not PETSCII.
- **Control via `0x1b` (ESC) + a letter**: codes seen are `ESC A B C D E F G L M Q`
  (colour / attribute / cursor / mode commands — exact meanings TBD).
- **Block graphics** use printable bytes (e.g. `0x73` 's' as a solid/graphic cell in
  the terminal's custom font), plus CR (`0x0d`), and a few low control bytes
  (`0x14`, `0x0a`).

So Amiga Compunet authored a **separate frame stream** for Amiga terminals — ASCII +
ESC codes rendered with the terminal's own font/colours — rather than shipping C64
PETSCII to be translated. Confirmed by absence of any translation table:

- No 256-byte PETSCII↔ASCII/screen translation table exists in the `Compunet`
  client **or** in `cnet.device` (scanned both; zero candidates).
- The only byte-indexed tables are the CRC-CCITT table (in `cnet.device`).

## Implication for Compunet Reborn

Reborn frames are authored as **PETSCII** (for the C64). The Amiga expects its own
**ESC-code frame format**. These are different content encodings. So a Reborn Amiga
client cannot simply be fed the C64 PETSCII frames — either:

1. The Reborn server must emit Amiga-format (ESC-code) frames when talking to an
   Amiga client (a per-client content format, like the existing C64-vs-terminal
   split), or
2. A translation layer converts PETSCII frames → Amiga ESC-code frames.

This is separate from the transport/protocol (which matches — see
protocol-analysis.md). The wire protocol is identical; the *frame content encoding*
differs by client type. The original Compunet clearly served format-appropriate
frames per client platform.

## Still to pin

- The frame interpreter function (renders ESC codes to the frame window). Not yet
  isolated in recon.c — likely a dispatch on `0x1b` then per-letter handling, or a
  table. Worth locating to document the full ESC command set (needed if Reborn
  emits Amiga-format frames).
- Exact meaning of each ESC letter (colour/mode/cursor) and the graphic byte set.
