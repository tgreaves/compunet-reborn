# §6 — Frame (SEQ) format

**Layer — Binding-A wire format** (§1.8). The on-the-wire encoding of a page; a modern binding delivers the same frame content as structured JSON instead (see [`api/README.md`](api/README.md)).

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority & triangulation: the server frame builders (`_make_info_frame`,
> `_send_current_frame` in `server/compunet_server.py`), the Amiga frame parser
> (`client/amiga/src/frame.c`, verified against the original disassembly), and the C64 model
> (`docs/PROTOCOL.md`). They agree on the header, RLE, and terminator.

A **frame** is one page of displayable content. Frames are the payload of most `FRAME`-type
responses (§4) and the login welcome/error screens (§3). This section defines the byte
encoding of a frame; how it is rendered on screen is [§5](05-display.md). ("SEQ" is the
historical file extension for stored frames; the wire encoding is identical.)

## 6.1 Delivery

A frame is delivered as a **DAT (`$22`) stream** (§2): its bytes are split across one or
more DAT packets (the server chunks at 100 payload bytes), each ACK-paced, followed by a
zero-length **EOS** packet. A client reassembles the frame by concatenating DAT payloads
until either the in-band terminator `$00` (§6.3) **or** the EOS packet — **whichever comes
first**. These do **not** always coincide: some frames (the login welcome frame, for one) have
**no `$00` in the body at all** and simply end at the EOS packet. A client **MUST** treat the
EOS as an equally valid end of frame — render whatever was decoded up to that point — and
**MUST NOT** require a `$00`. It **MUST** reassemble across packet boundaries and **MUST NOT**
assume any field lies within a single packet.

## 6.2 Header

A frame begins with a **4-byte header**:

| Offset | Field | Description |
|---|---|---|
| 0 | flags | Bit 7 (`$80`) set = **more pages follow** (§6.5). Other bits reserved (0). |
| 1 | border colour | C64 palette index (§5.5) in the **low nibble** (`& $0F`) |
| 2 | background colour | C64 palette index in the low nibble |
| 3 | initial charset | A charset control code: `$0E` = lowercase/mixed, `$8E` = uppercase/graphics |

Byte 3 is the **initial charset selector**, and a client **MUST** consume it as such: `$0E`
selects lowercase/mixed, and **any other value** selects uppercase/graphics (the reference
Amiga renderer reads exactly one byte here and tests only for `$0E`). Frames **SHOULD** place
a charset control (`$0E`/`$8E`) at byte 3; a client **MUST** tolerate any other value —
notably, the server's own `INVALID ID OR PASSWORD` error frame carries `$0D` here, which
correctly resolves to uppercase. Because byte 3 is *consumed* as the charset selector, a
printable byte placed there would be lost, so frames begin their visible content at byte 4.
Additional charset switches within the body are permitted (§5.2).

The authoritative layout is the table above, as emitted by the server's frame builders and
consumed by the Amiga renderer (`frame.c` reads flags, border, background, then the charset
byte). The C64 model in `docs/PROTOCOL.md` describes the same bytes with byte 3 as the first
CHROUT'd body byte — equivalent, because `$0E`/`$8E` at that position is a charset control
either way.

## 6.3 Body

After the header comes the **body**: a stream of PETSCII bytes (§5) — characters, colour
codes, cursor/mode controls, and RLE runs (§6.4) — rendered a cell at a time into the
40×24 grid. The body is terminated by a `$00` byte.

**Processing algorithm.** A client processes the body one byte at a time, maintaining a
cursor (row, column), a current text colour, a reverse-video flag, and the active character
set (§5). For each byte `b` read from the body:

1. `b == $00` → **stop**: the frame is complete.
2. `b == $06` → **space run**: read the next byte `N`; emit a space (`$20`) into `1 + N`
   successive cells (§6.4).
3. `b == $07` → **run**: read the next two bytes `c`, `N`; process `c` `1 + N` times exactly
   as steps 4/5 would process it — i.e. if `c` is a control code repeat its action, otherwise
   draw its glyph (§6.4).
4. `b` in `$00`–`$1F` or `$80`–`$9F` → **control code**: act on it (§5.6) — set colour,
   move/home the cursor, clear, toggle reverse, or switch character set — and emit nothing.
5. otherwise → **character**: convert `b` to a screen code (§5.3), draw the active set's
   glyph (§5.4) at the cursor in the current colour and reverse state, then advance the
   cursor, applying the **auto-wrap guard** of §5.6.1 (a full-width line followed by a `CR`
   must not leave a blank row).

"Emitting into a cell" writes the glyph with the current colour/reverse attributes and
advances the cursor with the same wrapping as a normal character.

A client **MUST** implement this loop (or an equivalent producing the same cell contents),
**MUST** stop at the `$00` terminator regardless of any remaining bytes in the current
packet, and **MUST** decode the RLE runs with the `1 + N` semantics of §6.4.

**Initial text colour.** A frame's body **SHOULD** set the text colour with a colour control
(§5.6) before printing text, and Compunet frames do so at the start of the body (typically
right after the charset byte). The text colour that applies *before* any colour control is
**not defined** by this specification — a frame **MUST NOT** rely on a particular default, and
a client **MAY** initialise it to any colour (the reference clients do not reset it per
frame). Border and background always come from the header (§6.2).

## 6.4 RLE compression

Two run-length escapes may appear anywhere in the body. In both, the **count byte is the
number of *additional* emissions after the first**, so a count of `N` yields `1 + N`
characters:

| Escape | Bytes | Expansion |
|---|---|---|
| space run | `$06 N` | space (`$20`) repeated `1 + N` times |
| character run | `$07 c N` | the byte `c`, processed `1 + N` times |

**⚠ Load-bearing: the `1 +` in the counts.** Example: `$06 $03` → four spaces; `$07 $2A $04` → `*****` (five asterisks). A client
**MUST** decode both escapes with the `1 + N` semantics; an off-by-one corrupts every
compressed run. `$06` and `$07` never appear as literal content — they are always RLE
escapes.

**The run byte `c` is processed exactly as it would be outside a run** (§6.3): if `c` is a
printable character it is drawn `1 + N` times; **if `c` is a control code** (§5.6, ranges
`$00`–`$1F` / `$80`–`$9F`) the **control action is performed `1 + N` times**, not drawn as a
glyph. For example the built-in directory template opens with `$07 $0D $05` — a run of the
`CR` control — which advances the cursor down **six rows** (a six-row top margin), *not* six
copies of the `$0D` glyph. A client **MUST** repeat the control action, not the glyph, when a
run's byte is a control code.

## 6.5 Multi-page frames

A logical page may span several frames. If a frame's **flags bit 7 is set**, more content is
associated with the item: the client indicates "more" to the user (the original clients show
a MORE / FINISH choice) and requests the next frame with the `D` (no argument) or `N` command
(§4). When a frame arrives with **flags bit 7 clear**, it is the last page.

**Bit 7 is a hint, not a guarantee (important).** A set bit 7 does **not** promise that a
`MORE` request will return another frame. In particular, a `+`-modified directory entry
(§7.4) — e.g. a `T+` splash page — arrives with bit 7 set even though it has no further
*frames*: its extra content is a **sub-directory**, reached by navigating into the entry
(§7.4) or via `GOTO` (§4.4), not by paging. So a `MORE` on it returns an end marker
immediately: `N` → a bare `$41` ACK, `D` (no arg) → the directory (§4.5). A client therefore
**MUST** drive paging from the **actual response** (another frame vs. an ACK / a directory),
not from bit 7 alone, and **SHOULD** page with `D` (no argument) so it lands back in the
directory cleanly at the end.

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
