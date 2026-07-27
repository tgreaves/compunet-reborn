# §5 — Display contract (PETSCII)

**Layer — mixed** (§1.8). The abstract 40×24 screen model and the 16-colour palette are shared model; the PETSCII byte encoding (screen-code→glyph mapping, control codes, RLE) is Binding-A wire format.

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority & triangulation: the C64 display model (`docs/PROTOCOL.md`) and the Amiga frame
> renderer (`client/amiga/src/frame.c`, `frame_control.c` — verified against the original
> disassembly). The window dimensions and the colour/control tables below are agreed between
> the two reference clients, and the font and palette are extracted from the Amiga client
> (Appendix §A).

Compunet content is **PETSCII** — the Commodore 64's character and colour scheme. A client
renders it into a fixed character grid using the C64 character glyphs and the C64 colour
palette. This section defines that display contract: the grid, the character sets, the
PETSCII→glyph mapping, the colour palette, and the control codes. The byte-stream encoding
that carries this content (headers, RLE, terminator) is defined in [§6](06-frame-format.md).

At **Tier 1** a client **MUST** implement this display contract: without it, frames and
directories cannot be shown.

> **What this means per binding (§1.8).** The *screen model* — the 40×24 grid, the glyphs
> (§5.4), the 16-colour palette (§5.5), and reverse video (§5.7) — is **shared**: every client
> renders the same thing, and Binding B is no exception (its clients draw from the same appendix
> font and palette). What differs is who does the **decoding**: a **Binding A** client parses the
> PETSCII byte stream itself — the screen-code conversion (§5.3), control codes (§5.6) and RLE
> (§6.4); a **Binding B** client does **not**, because the server has already expanded all of
> that into a per-cell grid. So a Binding-B implementer needs §5.1/§5.4/§5.5/§5.7 and can treat
> §5.3/§5.6 as background.

## 5.1 The screen model

The Compunet content window is a character grid of **40 columns × 24 rows**.

- Columns are numbered 0–39 (`$00`–`$27`); rows 0–23 (`$00`–`$17`).
- The Amiga frame renderer wraps the cursor column at `$28` (40) and caps the row at `$17`
  (row 23), and its `clear_screen` clears exactly `(0,0)–($17,$27)`. This is one row shorter
  than the C64's full 40×25 hardware screen — the C64 reserves the bottom line for the
  duckshoot / status row, which is client chrome and **not** part of the content grid, so the
  two clients agree on a 40×24 content area.
- Each cell holds one glyph (§5.3–5.4) plus two attributes: a **colour** (§5.5) and a
  **reverse-video** flag (§5.6).

A client **MUST** provide a 40×24 content area and **MUST** render exactly the glyph,
colour, and reverse attribute the byte stream specifies for each cell. Anything the client
draws outside that grid (menus, status, window chrome) is non-normative.

## 5.2 Character sets

C64 PETSCII has two character sets; exactly one is active at a time:

| Set | Contents | Selected by |
|---|---|---|
| **Uppercase / graphics** | capital letters, digits, punctuation, and the PETSCII graphics glyphs | control code `$8E` |
| **Lowercase / mixed** | lower- and upper-case letters, digits, punctuation | control code `$0E` |

The active set determines which glyph a screen code maps to. A frame declares its initial
set in its header (§6) and MAY switch mid-frame with `$0E`/`$8E`. A client **MUST**
implement both sets and honour switches.

## 5.3 PETSCII codes and screen codes

Content bytes in the range that is not a control code (§5.6) are **PETSCII character
codes**. To find the glyph, a client converts the PETSCII code to a **C64 screen code**
(the index into the character set) using the standard C64 transform. The reference
conversion (verified canonical against the Amiga renderer, which switches on `byte >> 5`):

| PETSCII byte | Screen code |
|---|---|
| `$20`–`$3F` | `byte` (unchanged) |
| `$40`–`$5F` | `byte & $1F` |
| `$60`–`$7F` | `(byte & $1F) \| $40` |
| `$A0`–`$BF` | `(byte & $1F) \| $60` |
| `$C0`–`$DF` | `byte & $7F` |
| `$E0`–`$FE` | `byte & $7F` |
| `$FF` | `$5E` |

Bytes `$00`–`$1F` and `$80`–`$9F` are **control codes** (§5.6), not characters, and are not
converted. A client **MUST** apply this conversion (or an equivalent that produces the same
screen code) before glyph lookup.

## 5.4 The font

PETSCII codes are meaningless without the C64 glyphs, so the glyph bitmaps are part of this
specification. The reference clients do not use a host font for content: they carry the
**C64 character ROM** and render from it.

- The font is two 1 KB bitmaps — the **uppercase/graphics** set and the **lowercase/mixed**
  set — each 128 glyphs of 8×8 pixels (8 bytes per glyph, one byte per row, MSB = leftmost
  pixel). These are the standard C64 character-ROM bitmaps.
- A cell's screen code (§5.3) indexes the active set's bitmap to obtain its glyph.
- **Reverse video** (§5.6) is the glyph with all 8×8 pixels inverted.

A client **MUST** render content using these C64 glyphs (or a pixel-exact reproduction).
The complete font bitmap is provided in [Appendix §A](99-appendices.md) so the spec is
self-contained. *(Non-normative: this is the same approach the web and terminal renderers
take — they embed the C64 character ROM.)*

## 5.5 Colour palette

Colour uses the **standard C64 16-colour palette**, indexed 0–15:

| Idx | Colour | | Idx | Colour |
|---|---|---|---|---|
| 0 | black | | 8 | orange |
| 1 | white | | 9 | brown |
| 2 | red | | 10 | light red |
| 3 | cyan | | 11 | dark grey (grey 1) |
| 4 | purple | | 12 | medium grey (grey 2) |
| 5 | green | | 13 | light green |
| 6 | blue | | 14 | light blue |
| 7 | yellow | | 15 | light grey (grey 3) |

- The **border** and **background** colours come from the frame header (§6) as a colour
  index in the low nibble of each header byte.
- The **text colour** of subsequent cells is set by the colour control codes (§5.6) and
  applies until the next colour code.
- The exact RGB values for each index are given in [Appendix §A](99-appendices.md).

*(Non-normative: the Amiga client stores an internal index→hardware-pen remap because its
screen pens are not ordered in C64 index order; that remap is a platform detail and does
not change the palette a client must present — indices and colours are exactly the standard
C64 set above.)*

## 5.5.1 Line speed (optional)

A client **MAY** offer to paint a frame **as if it were arriving down the original line**,
rather than instantly. Compunet ran at **1200/75** (V.23 — 1200 bits per second inbound, 75
out), and a page *arriving* was part of what the service felt like: you watched it paint, and a
large picture cost real seconds of a metered call. Rendering instantly is correct and loses that.

If offered:

- **Fastest MUST be the default.** The pacing is an affordance for people who want the period
  experience, not a tax on everyone else.
- **Time it from the frame's OWN bytes**, not from a guess: at 8N1 a byte is 10 bits, so 1200
  baud is **120 bytes per second** and a 1 KB frame takes about eight and a half seconds. Timing
  it from the cell count instead would misreport every RLE-compressed frame (§6.4), which is most
  of them.
- **Only the DRAWING is paced.** The frame has already arrived: capture (§8.4.2), paging and the
  command row all behave exactly as they would otherwise. This is presentation, not transport,
  and it changes nothing on the wire.
- **⚠ Pace what the SERVER sent; draw client assets instantly.** A page fetched from Compunet
  paints; the embedded help, editor-help and COURIER frames (§A.8–§A.11) do not, because they
  never crossed the line — the same reasoning §8.4.2 gives for not capturing them into the
  editor. A local asset pretending to arrive over a modem is theatre rather than reconstruction.
- **⚠ The WELCOME frame paces.** It is the first page anyone sees, which makes it the one where
  watching it arrive matters most — and it is easy to miss, because it is delivered with the
  session rather than as an ordinary frame (§3.5), so it takes a different path through a client
  and quietly skips the pacing.
- **⚠ No command row while the page is arriving (normative).** The original draws the duckshoot
  and immediately blocks for a key (`$93D0`: `JSR $9436` to draw, then `JSR $9002`, which is
  `GETIN` in a loop), so the row is on screen exactly when the client will accept input — never
  during reception, when the C64 is inside its receive loop and the frame's own clear-screen has
  wiped row 24 anyway. A client that paces the drawing **MUST** keep the row off screen until the
  page lands, or it offers commands that do nothing: the row is inert until the frame completes,
  so showing it invites a keypress the client cannot honour.
- A client **SHOULD** let a keypress complete the frame immediately. The original had no such
  escape, but a page that cannot be hurried reads as a hung client to anyone who did not realise
  what they had switched on.
- Where a client also paces multi-frame runs (§4.7), the two **MUST NOT** compound — at 1200 baud
  the painting already provides the pause that the run pacing exists to give.

## 5.6 Control codes

Bytes `$00`–`$1F` and `$80`–`$9F` in the content stream are PETSCII **control codes**, not
characters. A client **MUST** act on the codes below and **MUST** treat unlisted codes in
these ranges as no-ops. (`$00` is not in this table — it is the frame terminator, §6.)
This table is enumerated from the reference clients' control dispatch, verified
byte-for-byte against the original.

**Colour codes** (set the current text colour to the palette index in §5.5):

| Code | Colour | | Code | Colour |
|---|---|---|---|---|
| `$05` | white (1) | | `$95` | brown (9) |
| `$1C` | red (2) | | `$96` | light red (10) |
| `$1E` | green (5) | | `$97` | dark grey (11) |
| `$1F` | blue (6) | | `$98` | medium grey (12) |
| `$81` | orange (8) | | `$99` | light green (13) |
| `$90` | black (0) | | `$9A` | light blue (14) |
| `$9C` | purple (4) | | `$9B` | light grey (15) |
| `$9E` | yellow (7) | | | |
| `$9F` | cyan (3) | | | |

**Cursor, mode, and editing codes:**

| Code | Meaning |
|---|---|
| `$0D` | carriage return — to column 0, next row (guarded against double-advance after an auto-wrap) |
| `$8D` | shifted return — as `$0D` |
| `$11` | cursor down (stops at the last row) |
| `$91` | cursor up (stops at row 0) |
| `$1D` | cursor right (wraps at column 40 to the next row) |
| `$9D` | cursor left (wraps at column 0 back to column 39 of the previous row) |
| `$13` | home — cursor to row 0, column 0 |
| `$93` | clear — clear the 40×24 grid and home the cursor |
| `$14` | delete — see below |
| `$94` | insert — see below |
| `$12` | reverse video on |
| `$92` | reverse video off |
| `$0E` | select lowercase/mixed character set |
| `$8E` | select uppercase/graphics character set |

Cursor motion is bounded by the 40×24 grid: column wraps at 40, rows clamp at 0 and 23. A
client **MUST** reproduce these bounds so that content laid out by cursor positioning
lands in the same cells as on the reference clients.

**`$14` delete and `$94` insert** are line-editing codes from the C64's screen editor: `$14`
deletes the character to the *left* of the cursor and shifts the rest of the line left; `$94`
inserts a space at the cursor and shifts the rest of the line right, discarding whatever falls
off column 39. They exist because frames are authored on a C64, but **no frame in this system
uses them** — a client **MAY** treat both as no-ops, and the reference renderers do. They are
listed for completeness, not as an obligation. (VALIDATION.md, F34: previously listed by name
with no behaviour at all, which reads as an unimplemented requirement.)

### 5.6.1 The auto-wrap guard (important)

Printing a character in the last column (39) advances the cursor to column 0 of the **next
row** — an *auto-wrap*. Frames are authored assuming this, so a line that is exactly 40
characters wide is **immediately followed by a `CR`** in the byte stream. Without a guard a
client would advance the row twice (once for the wrap, once for the `CR`), inserting a blank
line between every full-width row.

A client **MUST** implement the guard, exactly as the reference clients do:

- Maintain a **"just-wrapped"** flag. Printing a character that carries the column past 39
  (wrapping to the next row) **sets** the flag; printing any character that does **not** wrap
  clears it; any explicit cursor move (`$11`/`$91`/`$1D`/`$9D`/`$13`) clears it.
- A `CR` (`$0D` or `$8D`) sets the column to 0 and clears the reverse attribute (§5.7); it
  advances the row **only if the just-wrapped flag is not set**. Either way it clears the
  flag.

In other words, a `CR` immediately after an auto-wrap resets the column but does **not**
advance the row a second time. (This mirrors the Amiga's `P_WRAP` guard in `carriage_return`
and the C64's screen-editor behaviour.)

## 5.7 Reverse video

`$12` turns reverse video on and `$92` turns it off. While on, each rendered cell uses the
**inverted** glyph (§5.4). `$0D`/carriage return clears the reverse attribute (as on the
C64). A client **MUST** track this attribute per the control codes and apply it per cell.
