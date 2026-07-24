# Amiga frame format & the PETSCII question (goal 3)

## Question

C64 Compunet content is PETSCII. The Amiga has no native PETSCII. Does the Amiga
client translate PETSCII, use a custom font, or something else?

## Answer: the Amiga DOES use PETSCII — it converts it in the frame renderer

**Correction of an earlier interim note.** An initial glance at `Frames/test.frame`
(ASCII-looking "WELCOME", `s`/`#` bytes, a `0x1b`) suggested a non-PETSCII "ESC-code"
format. That was wrong. Disassembling the frame renderer shows the Amiga client
**consumes PETSCII** and converts it to its own screen/font codes on the fly. The
"ASCII" text is just the PETSCII bytes for those letters (0x20-0x5F overlaps ASCII),
and the `0x1b` was a control-table index, not an ESC prefix.

### The receive → render pipeline

1. **`read_frame_byte` (`FUN_0010800c`)** — buffered get-byte from the incoming frame
   stream (0x8f-byte buffer, refilled via `serial_read`).
2. **RLE de-compressor (`FUN_00108086`)** — same scheme as the C64/server SEQ frames:
   - `0x06 <n>` → repeat space
   - `0x07 <char> <n>` → repeat char
3. **Frame header parse** — reads a high-bit flag, then two colour nibbles indexed
   through a colour table (`DAT_0011e1c0`), a charset flag (`== 0x0e`).
4. **`render_char` (`FUN_001054f8`)** — the key routine. Switches on `byte >> 5`:

   | byte range | action |
   |------------|--------|
   | `0x00-0x1F` | control code → jump table `PTR_FUN_0011d8a8[byte]` |
   | `0x20-0x3F` | screen code = byte (as-is) |
   | `0x40-0x5F` | screen code = byte & 0x1F |
   | `0x60-0x7F` | screen code = (byte & 0x1F) \| 0x40 |
   | `0x80-0x9F` | control code → jump table `PTR_FUN_0011d928[byte & 0x7F]` |
   | `0xA0-0xBF` | screen code = (byte & 0x1F) \| 0x60 |
   | `0xC0-0xDF` | screen code = byte & 0x7F |
   | `0xE0-0xFF` | screen code = (0x5E if 0xFF else byte & 0x7F) |

   This is the **canonical PETSCII → C64 screen-code conversion** — verified to match
   the standard transform for 0x20-0xBF exactly (only 0xFF differs by one). The
   converted code is written into the screen buffer with the current colour.

### The control-code table = PETSCII controls

`PTR_FUN_0011d8a8` (codes 0x00-0x1F) dispatches exactly the C64 PETSCII controls:

| code | PETSCII meaning |
|------|-----------------|
| 0x05 | white |
| 0x0D | carriage return |
| 0x0E | switch to lower/mixed charset |
| 0x11 | cursor down |
| 0x12 | reverse on |
| 0x13 | home |
| 0x14 | delete |
| 0x1C | red |
| 0x1D | cursor right |
| 0x1E | green |
| 0x1F | blue |
| others (incl. 0x1B) | default/no-op (`0x1054f0`) |

The second table `PTR_FUN_0011d928` (codes 0x80-0x9F) is the rest of the standard
C64 PETSCII control set — **fully enumerated and all standard**:

| code | PETSCII meaning | | code | PETSCII meaning |
|------|-----------------|-|------|-----------------|
| 0x81 | orange | | 0x93 | clear screen |
| 0x8D | shift-return | | 0x94 | insert |
| 0x8E | uppercase charset | | 0x95 | brown |
| 0x90 | black | | 0x96 | light red |
| 0x91 | cursor up | | 0x97 | dark grey |
| 0x92 | reverse off | | 0x98 | grey 2 |
| 0x9C | purple | | 0x99 | light green |
| 0x9E | yellow | | 0x9A | light blue |
| 0x9F | cyan | | 0x9B | light grey |
| 0x9D | cursor left | | (0x80,82-8C,8F) | no-op |

Colour handlers store the **C64 colour index** (0=black, 1=white, 2=red, … 15) into
the per-character colour byte (`frame_state + 8`), which `blit_char_cell` uses. The
RGB palette itself is loaded separately via `GfxBase.LoadRGB4`. The index scheme is
the standard C64 0-15 palette order.

**Conclusion: the Amiga implements the complete, standard C64 PETSCII control set**
(both 0x00-0x1F and 0x80-0x9F) plus the PETSCII→screencode conversion and the RLE
compression. Frame content is fully C64-PETSCII-compatible.

## Implication for Compunet Reborn — GOOD NEWS

The Amiga renders **the same PETSCII frames** the C64 does, using the same RLE
compression and PETSCII control codes. So Reborn's existing PETSCII frame content
should render on the Amiga **without a separate frame format** — subject to
confirming the 0x80-0x9F control table and the colour palette mapping. This is a
much easier path than the "separate Amiga frame format" the earlier note implied.

Combined with the confirmed transport and command matches, a Reborn Amiga client via
a TCP `cnet.device` looks viable with the **existing** PETSCII frame content.

## Font — embedded C64 character ROM (answers "which font?")

Frame content is **not** drawn with an Amiga font. The client carries its own C64
character set and builds a bitmap font at runtime:

- `build_font` (`FUN_00106000`) allocates 8 KB CHIP RAM (`g_font_base` /
  `DAT_00120258`) = 512 glyphs of 16 bytes each.
- Source glyphs are two embedded 1 KB C64 bitmaps (128 chars × 8 rows, 8×8 px):
  - `c64_charset_upper` @ `0x11d9c0` — uppercase/graphics set
  - `c64_charset_lower` @ `0x11ddc0` — lowercase set
  (These are the bytes that showed up as the junk "string" `<fnn`b<` in early scans —
  actually C64 char-ROM bitmap data. Verified: rendering glyph 0x01 gives a perfect
  C64 'A', 0x13 gives 'S', etc.)
- Each glyph is expanded to Amiga bitplane words (`row << 8`), plus an **inverted**
  copy at +0x800 / +0x1800 for reverse-video (the PETSCII RVS control).
- `blit_char_cell` (`FUN_00107000`) indexes the font at `screencode * 0x10` and blits
  with `BltBitMapRastPort`.

`topaz.font` (string @0x11d084) is used only for Intuition window chrome
(titles/gadgets/menus), not frame content.

So the Amiga reproduces the C64 display by embedding the C64 character ROM + its own
PETSCII→screencode conversion + blitter — directly analogous to Reborn's web/terminal
renderers embedding `charrom.js`.

## Status: PETSCII frame compatibility CONFIRMED

Both control tables enumerated (all standard C64 PETSCII), PETSCII→screencode
conversion verified, RLE matches, font is the embedded C64 char-ROM. Reborn's
existing PETSCII frames render on the Amiga with no separate format.

Both jump tables (`0x11d8a8` / `0x11d928`) were later dumped verbatim and every entry
cross-checked against its handler in the flat image: all 16 colour pens, reverse on/off
(`P_ATTR` bit 7), charset lower/upper (mode toggle + `frame_redraw` = `FUN_00107156` via
the `0x1056cc` thunk), and the cursor handlers' exact **bounds/wrap** — home (row/col/wrap
= 0), down (`if row<0x17`), up (`if row>0`), right (col wrap at 0x28 → row advance), left
(col wrap to 0x27 → row back), and CR (wrap-guarded row advance, clears the reverse attr).
The reconstruction in [`../../src/frame_control.c`](../../src/frame_control.c) matches
byte-for-byte. Nothing outstanding here.

Optional follow-up (not a blocker):
- Exact RGB values in the `LoadRGB4` palette table vs VIC-II (cosmetic — index scheme
  already confirmed standard).
