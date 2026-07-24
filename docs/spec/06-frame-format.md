# §6 — Frame (SEQ) format

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority & triangulation: the server frame builders (`_make_info_frame`,
> `_send_current_frame` in `server/compunet_server.py`), the server-side renderer
> (`server/terminal.py`), and the Amiga frame parser (`client/amiga/src/frame.c`, verified
> against the original disassembly). The three agree on the header, RLE, and terminator.

A **frame** is one page of displayable content. Frames are the payload of most `FRAME`-type
responses (§4) and the login welcome/error screens (§3). This section defines the byte
encoding of a frame; how it is rendered on screen is [§5](05-display.md). ("SEQ" is the
historical file extension for stored frames; the wire encoding is identical.)

## 6.1 Delivery

A frame is delivered as a **DAT (`$22`) stream** (§2): its bytes are split across one or
more DAT packets (the server chunks at 100 payload bytes), each ACK-paced, followed by a
zero-length **EOS** packet. A client reassembles the frame by concatenating DAT payloads
until either the in-band terminator `$00` (§6.3) or the EOS packet — in a well-formed
frame these coincide, the `$00` being the last content byte before EOS. A client **MUST**
reassemble across packet boundaries and **MUST NOT** assume any field lies within a single
packet.

## 6.2 Header

A frame begins with a **4-byte header**:

| Offset | Field | Description |
|---|---|---|
| 0 | flags | Bit 7 (`$80`) set = **more pages follow** (§6.5). Other bits reserved (0). |
| 1 | border colour | C64 palette index (§5.5) in the **low nibble** (`& $0F`) |
| 2 | background colour | C64 palette index in the low nibble |
| 3 | initial charset | A charset control code: `$0E` = lowercase/mixed, `$8E` = uppercase/graphics |

Byte 3 **MUST** be a charset control (`$0E` or `$8E`). This is required because a client may
consume byte 3 as a dedicated charset selector rather than as body: the reference Amiga
renderer reads exactly one byte here and sets its character set from it, and the server
always emits `$0E`/`$8E` at this position. Placing anything else at byte 3 would be consumed
and lost by such a client. Additional charset switches within the body are permitted (§5.2).

*(Non-normative: the server-side terminal renderer skips these 4 header bytes wholesale
because a text terminal supplies its own colour; a graphical client uses border/background
and the charset. A comment in that renderer mislabels the header bytes — the authoritative
layout is the table above, as emitted by the server's frame builders and consumed by the
Amiga.)*

## 6.3 Body

After the header comes the **body**: a stream of PETSCII bytes (§5) — characters, colour
codes, cursor/mode controls, and RLE runs (§6.4) — rendered a cell at a time into the
40×24 grid. The body is terminated by a `$00` byte.

A client **MUST**:

- render the body per the display contract of §5;
- stop rendering at the `$00` terminator;
- treat the terminator `$00` as the end of the frame's content regardless of any remaining
  bytes in the current packet.

## 6.4 RLE compression

Two run-length escapes may appear anywhere in the body. In both, the **count byte is the
number of *additional* emissions after the first**, so a count of `N` yields `1 + N`
characters:

| Escape | Bytes | Expansion |
|---|---|---|
| space run | `$06 N` | space (`$20`) repeated `1 + N` times |
| character run | `$07 c N` | character `c` repeated `1 + N` times |

Example: `$06 $03` → four spaces; `$07 $2A $04` → `*****` (five asterisks). A client
**MUST** decode both escapes with the `1 + N` semantics; an off-by-one corrupts every
compressed run. `$06` and `$07` never appear as literal content — they are always RLE
escapes.

## 6.5 Multi-page frames

A logical page may span several frames. If a frame's **flags bit 7 is set**, more pages
follow: the client indicates "more" to the user (the original clients show a MORE / FINISH
choice) and requests the next frame with the `D` (no argument) or `N` command (§4). When a
frame arrives with **flags bit 7 clear**, it is the last page.

A client at Tier 1 **MUST** support paging through a multi-frame page and **MUST** request
subsequent frames rather than assuming a page is a single frame.

## 6.6 Non-text pages (forward reference)

Some directory entries are not text frames. When the selected entry is a **program /
download page**, the server sends — in place of the frame above — a small binary header
(load address and size) and then, on the client's request, the program bytes. Link pages
behave differently again. These are specified in [§8 — Subsystems](08-subsystems.md)
(downloads, uploads, Partyline). A client determines which case applies from the directory
entry type (§7); a text frame is the default and is what this section describes.

## 6.7 Worked example

The server's info-frame builder produces (header bytes shown, then body):

```
00 02 00 8E   05   0D 0D   "  <message>"   0D   00
│  │  │  │    │    │       │               │    └ terminator
│  │  │  │    │    │       │               └ CR
│  │  │  │    │    │       └ message text (PETSCII)
│  │  │  │    │    └ two carriage returns (two blank lines)
│  │  │  │    └ colour code: white text ($05)
│  │  │  └ charset: uppercase ($8E)
│  │  └ background: black (0)
│  └ border: red (2)
└ flags: $00 (last page)
```

Rendered: a red border, black background, uppercase set, white text reading `<message>`
two rows down. This is a complete, minimal frame.
