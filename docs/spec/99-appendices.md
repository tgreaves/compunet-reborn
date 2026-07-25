# §A — Appendices

> Part of the [Compunet Client Specification](README.md). These appendices consolidate the
> reference tables and carry the concrete binary assets (font, palette, template) so the
> specification is self-contained — a client can be built from this document alone.
>
> All assets are extracted verbatim from the reference clients: the font and palette from the
> **Amiga client** (its embedded C64 character ROM and its `LoadRGB4` colour table), and the
> directory template from the **C64 terminal** (`client/c64/src/compunet.s`).

## §A.1 — Command table

Single-letter commands, carried in a COM (`$43`) packet as `command byte [+ ASCII-decimal
argument]` (§4). "Typical reply" is indicative; some commands vary by context.

| Cmd | Byte | Name | Arg | Meaning | Typical reply | Tier |
|---|---|---|---|---|---|---|
| `Z` | `$5A` | LOGIN | credentials | Login packet (first command only, §3.5) | FRAME | 1 |
| `D` | `$44` | SHOW / MORE | entry index | +index = SHOW (frame(s)/download of the highlighted entry, never enters a dir); no arg = MORE (next frame) | FRAME/download | 1 |
| `P` | `$50` | DIR / FINISH | entry index | +index = DIR (enter/create the highlighted entry as a directory); no arg = FINISH (leave a frame → its directory) | DIR | 1 |
| `N` | `$4E` | MORE | — | Next frame; bare ACK `$41` past the last frame (§4.5) | FRAME/ACK | 1 |
| `B` | `$42` | BACK | — | Parent directory | DIR | 1 |
| `L` | `$4C` | GOTO | keyword/page | Jump to a page by number or keyword | DIR | 1 |
| `A` | `$41` | ACCOUNT | — | Credit balance as a fixed 10-byte ASCII string (§4.4) — not a frame | 10-byte text | 1 |
| `I` | `$49` | ID lookup | 8-byte user IDs | Look up user IDs → name pairs (`id`+name+`$1E`); no arg = no response | lookup | 2 |
| `C` | `$43` | UCAT | — | User catalogue | DIR | 2 |
| `M` | `$4D` | MAIL | — | Enter Courier (mailbox directory) | DIR | 2 |
| `V` | `$56` | VOTE | index+score | Vote on the highlighted entry (2-digit index + score 1–9) | ACK | 2 |
| `X` | `$58` | LIFE | index+amount | Extend the highlighted entry's content lifetime (§8.6) — not BUY | ACK | 2 |
| `U` | `$55` | UPLOAD | params | Content upload or mail send | ACK / stream | 3 |
| `E` | `$45` | LEAVE | — | Log off (server closes) | FRAME | 1 |

*(The source constant `CMD_EDITR = $45` is vestigial — `$45` is LEAVE; there is no editor
command, see §4.4.)*

## §A.2 — Token table

Packet `token` byte (§2.5) and, separately, the response-type taxonomy (§4.3).

**Wire tokens** (the values the Reborn server acts on):

| Token | Value | Direction | Meaning |
|---|---|---|---|
| ACK | `$20` | either | Acknowledge a received DAT (§2.9) |
| DAT | `$22` | server → client | Data (frames, directories, responses, LINKING) |
| COM | `$43` | client → server | Command carrier (login + all commands) |
| (proceed) | `$40` | client → server | Program-download proceed (§8.3.1) |
| (abort) | `$41` | client → server | Program-download abort (§8.3.1) |

*(The ROM's internal display-name enumeration lists `ACK=$20, DIR=$21, DAT=$22, OK=$23,
ERR=$24, FTL=$25, COM=$26`; of these only `$20`/`$22` match the wire, and COM on the wire is
`$43`, not `$26` — see §2.5.)*

**Response types** (§4.3 — inferred by the client from the issued command and its mode, §4.5):

| Type | Byte | Meaning |
|---|---|---|
| ACK | `$41` (`A`) | Bare acknowledgement / proceed (single packet, no EOS) |
| DIR | `$44` (`D`) | Directory listing (§7) |
| FRAME | `$46` (`F`) | Frame content (§6) |
| ERROR | `$45` (`E`) | Error (renderable message frame) |
| LINKING | `$4C` (`L`) | Terminal (re)link required (ROM path, §3.6) |

The single-byte command ack read by native clients is `@` (`$40`) = OK/proceed (§4.3).

## §A.3 — Colour palette

The 16 C64 colours, index 0–15 (§5.5), with the RGB values the **Amiga client** loads via
`LoadRGB4` (table at `0x11d0c2`, indexed through the C64-index→pen remap of §5.5). These are
4-bit-per-channel values (each channel a multiple of `$11`) — the Amiga hardware's rendition
of the C64 palette, and the authoritative extractable RGB in the repository.

| Idx | Colour | RGB | | Idx | Colour | RGB |
|---|---|---|---|---|---|---|
| 0 | black | `#000000` | | 8 | orange | `#FF9944` |
| 1 | white | `#FFFFFF` | | 9 | brown | `#BB7700` |
| 2 | red | `#DD0000` | | 10 | light red | `#FF9999` |
| 3 | cyan | `#00DDDD` | | 11 | dark grey | `#888888` |
| 4 | purple | `#DD00DD` | | 12 | medium grey | `#AAAAAA` |
| 5 | green | `#00DD00` | | 13 | light green | `#99FF99` |
| 6 | blue | `#0000DD` | | 14 | light blue | `#9999FF` |
| 7 | yellow | `#DDDD00` | | 15 | light grey | `#CCCCCC` |

## §A.4 — PETSCII control codes

The complete control set (§5.6), consolidated. Colour codes set the current text colour;
the rest move the cursor, switch mode, or toggle reverse. Unlisted codes in `$00`–`$1F` /
`$80`–`$9F` are no-ops. `$00` is the frame terminator (§6), not a control code.

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| `$05` | white | `$90` | black |
| `$1C` | red | `$81` | orange |
| `$1E` | green | `$95` | brown |
| `$1F` | blue | `$96` | light red |
| `$9C` | purple | `$97` | dark grey |
| `$9F` | cyan | `$98` | medium grey |
| `$9E` | yellow | `$99` | light green |
| `$11` | cursor down | `$9A` | light blue |
| `$91` | cursor up | `$9B` | light grey |
| `$1D` | cursor right | `$0D` | carriage return |
| `$9D` | cursor left | `$8D` | shifted return (= CR) |
| `$13` | home | `$93` | clear + home |
| `$12` | reverse on | `$14` | delete |
| `$92` | reverse off | `$94` | insert |
| `$0E` | lowercase/mixed set | `$8E` | uppercase/graphics set |

## §A.5 — Font (C64 character ROM)

The content font is the C64 character ROM **embedded in the Amiga client** and
extracted verbatim from it (`0x11d9c0` uppercase/graphics, `0x11ddc0` lowercase/mixed;
128 glyphs per set, 8 bytes each, one byte per pixel row, MSB = leftmost pixel). It is
the standard C64 character ROM. Screen codes `$00`–`$7F` are the base glyphs below;
codes `$80`–`$FF` are their reverse-video forms (invert all 8 rows, §5.7). A glyph is
looked up by screen code (§5.3) in the currently-selected set (§5.2).

### Set 1 (uppercase / graphics), screen codes $00–$7F
```
  $00: 3C 66 6E 6E 60 62 3C 00
  $01: 18 3C 66 7E 66 66 66 00
  $02: 7C 66 66 7C 66 66 7C 00
  $03: 3C 66 60 60 60 66 3C 00
  $04: 78 6C 66 66 66 6C 78 00
  $05: 7E 60 60 78 60 60 7E 00
  $06: 7E 60 60 78 60 60 60 00
  $07: 3C 66 60 6E 66 66 3C 00
  $08: 66 66 66 7E 66 66 66 00
  $09: 3C 18 18 18 18 18 3C 00
  $0A: 1E 0C 0C 0C 0C 6C 38 00
  $0B: 66 6C 78 70 78 6C 66 00
  $0C: 60 60 60 60 60 60 7E 00
  $0D: 63 77 7F 6B 63 63 63 00
  $0E: 66 76 7E 7E 6E 66 66 00
  $0F: 3C 66 66 66 66 66 3C 00
  $10: 7C 66 66 7C 60 60 60 00
  $11: 3C 66 66 66 66 3C 0E 00
  $12: 7C 66 66 7C 78 6C 66 00
  $13: 3C 66 60 3C 06 66 3C 00
  $14: 7E 18 18 18 18 18 18 00
  $15: 66 66 66 66 66 66 3C 00
  $16: 66 66 66 66 66 3C 18 00
  $17: 63 63 63 6B 7F 77 63 00
  $18: 66 66 3C 18 3C 66 66 00
  $19: 66 66 66 3C 18 18 18 00
  $1A: 7E 06 0C 18 30 60 7E 00
  $1B: 3C 30 30 30 30 30 3C 00
  $1C: 0C 12 30 7C 30 62 FC 00
  $1D: 3C 0C 0C 0C 0C 0C 3C 00
  $1E: 00 18 3C 7E 18 18 18 18
  $1F: 00 10 30 7F 7F 30 10 00
  $20: 00 00 00 00 00 00 00 00
  $21: 18 18 18 18 00 00 18 00
  $22: 66 66 66 00 00 00 00 00
  $23: 66 66 FF 66 FF 66 66 00
  $24: 18 3E 60 3C 06 7C 18 00
  $25: 62 66 0C 18 30 66 46 00
  $26: 3C 66 3C 38 67 66 3F 00
  $27: 06 0C 18 00 00 00 00 00
  $28: 0C 18 30 30 30 18 0C 00
  $29: 30 18 0C 0C 0C 18 30 00
  $2A: 00 66 3C FF 3C 66 00 00
  $2B: 00 18 18 7E 18 18 00 00
  $2C: 00 00 00 00 00 18 18 30
  $2D: 00 00 00 7E 00 00 00 00
  $2E: 00 00 00 00 00 18 18 00
  $2F: 00 03 06 0C 18 30 60 00
  $30: 3C 66 6E 76 66 66 3C 00
  $31: 18 18 38 18 18 18 7E 00
  $32: 3C 66 06 0C 30 60 7E 00
  $33: 3C 66 06 1C 06 66 3C 00
  $34: 06 0E 1E 66 7F 06 06 00
  $35: 7E 60 7C 06 06 66 3C 00
  $36: 3C 66 60 7C 66 66 3C 00
  $37: 7E 66 0C 18 18 18 18 00
  $38: 3C 66 66 3C 66 66 3C 00
  $39: 3C 66 66 3E 06 66 3C 00
  $3A: 00 00 18 00 00 18 00 00
  $3B: 00 00 18 00 00 18 18 30
  $3C: 0E 18 30 60 30 18 0E 00
  $3D: 00 00 7E 00 7E 00 00 00
  $3E: 70 18 0C 06 0C 18 70 00
  $3F: 3C 66 06 0C 18 00 18 00
  $40: 00 00 00 FF FF 00 00 00
  $41: 08 1C 3E 7F 7F 1C 3E 00
  $42: 18 18 18 18 18 18 18 18
  $43: 00 00 00 FF FF 00 00 00
  $44: 00 00 FF FF 00 00 00 00
  $45: 00 FF FF 00 00 00 00 00
  $46: 00 00 00 00 FF FF 00 00
  $47: 30 30 30 30 30 30 30 30
  $48: 0C 0C 0C 0C 0C 0C 0C 0C
  $49: 00 00 00 E0 F0 38 18 18
  $4A: 18 18 1C 0F 07 00 00 00
  $4B: 18 18 38 F0 E0 00 00 00
  $4C: C0 C0 C0 C0 C0 C0 FF FF
  $4D: C0 E0 70 38 1C 0E 07 03
  $4E: 03 07 0E 1C 38 70 E0 C0
  $4F: FF FF C0 C0 C0 C0 C0 C0
  $50: FF FF 03 03 03 03 03 03
  $51: 00 3C 7E 7E 7E 7E 3C 00
  $52: 00 00 00 00 00 FF FF 00
  $53: 36 7F 7F 7F 3E 1C 08 00
  $54: 60 60 60 60 60 60 60 60
  $55: 00 00 00 07 0F 1C 18 18
  $56: C3 E7 7E 3C 3C 7E E7 C3
  $57: 00 3C 7E 66 66 7E 3C 00
  $58: 18 18 66 66 18 18 3C 00
  $59: 06 06 06 06 06 06 06 06
  $5A: 08 1C 3E 7F 3E 1C 08 00
  $5B: 18 18 18 FF FF 18 18 18
  $5C: C0 C0 30 30 C0 C0 30 30
  $5D: 18 18 18 18 18 18 18 18
  $5E: 00 00 03 3E 76 36 36 00
  $5F: FF 7F 3F 1F 0F 07 03 01
  $60: 00 00 00 00 00 00 00 00
  $61: F0 F0 F0 F0 F0 F0 F0 F0
  $62: 00 00 00 00 FF FF FF FF
  $63: FF 00 00 00 00 00 00 00
  $64: 00 00 00 00 00 00 00 FF
  $65: C0 C0 C0 C0 C0 C0 C0 C0
  $66: CC CC 33 33 CC CC 33 33
  $67: 03 03 03 03 03 03 03 03
  $68: 00 00 00 00 CC CC 33 33
  $69: FF FE FC F8 F0 E0 C0 80
  $6A: 03 03 03 03 03 03 03 03
  $6B: 18 18 18 1F 1F 18 18 18
  $6C: 00 00 00 00 0F 0F 0F 0F
  $6D: 18 18 18 1F 1F 00 00 00
  $6E: 00 00 00 F8 F8 18 18 18
  $6F: 00 00 00 00 00 00 FF FF
  $70: 00 00 00 1F 1F 18 18 18
  $71: 18 18 18 FF FF 00 00 00
  $72: 00 00 00 FF FF 18 18 18
  $73: 18 18 18 F8 F8 18 18 18
  $74: C0 C0 C0 C0 C0 C0 C0 C0
  $75: E0 E0 E0 E0 E0 E0 E0 E0
  $76: 07 07 07 07 07 07 07 07
  $77: FF FF 00 00 00 00 00 00
  $78: FF FF FF 00 00 00 00 00
  $79: 00 00 00 00 00 FF FF FF
  $7A: 03 03 03 03 03 03 FF FF
  $7B: 00 00 00 00 F0 F0 F0 F0
  $7C: 0F 0F 0F 0F 00 00 00 00
  $7D: 18 18 18 F8 F8 00 00 00
  $7E: F0 F0 F0 F0 00 00 00 00
  $7F: F0 F0 F0 F0 0F 0F 0F 0F
```

### Set 2 (lowercase / mixed), screen codes $00–$7F
```
  $00: 3C 66 6E 6E 60 62 3C 00
  $01: 00 00 3C 06 3E 66 3E 00
  $02: 00 60 60 7C 66 66 7C 00
  $03: 00 00 3C 60 60 60 3C 00
  $04: 00 06 06 3E 66 66 3E 00
  $05: 00 00 3C 66 7E 60 3C 00
  $06: 00 0E 18 3E 18 18 18 00
  $07: 00 00 3E 66 66 3E 06 7C
  $08: 00 60 60 7C 66 66 66 00
  $09: 00 18 00 38 18 18 3C 00
  $0A: 00 06 00 06 06 06 06 3C
  $0B: 00 60 60 6C 78 6C 66 00
  $0C: 00 38 18 18 18 18 3C 00
  $0D: 00 00 66 7F 7F 6B 63 00
  $0E: 00 00 7C 66 66 66 66 00
  $0F: 00 00 3C 66 66 66 3C 00
  $10: 00 00 7C 66 66 7C 60 60
  $11: 00 00 3E 66 66 3E 06 06
  $12: 00 00 7C 66 60 60 60 00
  $13: 00 00 3E 60 3C 06 7C 00
  $14: 00 18 7E 18 18 18 0E 00
  $15: 00 00 66 66 66 66 3E 00
  $16: 00 00 66 66 66 3C 18 00
  $17: 00 00 63 6B 7F 3E 36 00
  $18: 00 00 66 3C 18 3C 66 00
  $19: 00 00 66 66 66 3E 0C 78
  $1A: 00 00 7E 0C 18 30 7E 00
  $1B: 3C 30 30 30 30 30 3C 00
  $1C: 0C 12 30 7C 30 62 FC 00
  $1D: 3C 0C 0C 0C 0C 0C 0C 00
  $1E: 00 18 3C 7E 18 18 18 18
  $1F: 00 10 30 7F 7F 30 10 00
  $20: 00 00 00 00 00 00 00 00
  $21: 18 18 18 18 00 00 18 00
  $22: 66 66 66 00 00 00 00 00
  $23: 66 66 FF 66 FF 66 66 00
  $24: 18 3E 60 3C 06 7C 18 00
  $25: 62 66 0C 18 30 66 46 00
  $26: 3C 66 3C 38 67 66 3F 00
  $27: 06 0C 18 00 00 00 00 00
  $28: 0C 18 30 30 30 18 0C 00
  $29: 30 18 0C 0C 0C 18 30 00
  $2A: 00 66 3C FF 3C 66 00 00
  $2B: 00 18 18 7E 18 18 00 00
  $2C: 00 00 00 00 00 18 18 30
  $2D: 00 00 00 7E 00 00 00 00
  $2E: 00 00 00 00 00 18 18 00
  $2F: 00 03 06 0C 18 30 60 00
  $30: 3C 66 6E 76 66 66 3C 00
  $31: 18 18 38 18 18 18 7E 00
  $32: 3C 66 06 0C 30 60 7E 00
  $33: 3C 66 06 1C 06 66 3C 00
  $34: 06 0E 1E 66 7F 06 06 00
  $35: 7E 60 7C 06 06 66 3C 00
  $36: 3C 66 60 7C 66 66 3C 00
  $37: 7E 66 0C 18 18 18 18 00
  $38: 3C 66 66 3C 66 66 3C 00
  $39: 3C 66 66 3E 06 66 3C 00
  $3A: 00 00 18 00 00 18 00 00
  $3B: 00 00 18 00 00 18 18 30
  $3C: 0E 18 30 60 30 18 0E 00
  $3D: 00 00 7E 00 7E 00 00 00
  $3E: 70 18 0C 06 0C 18 70 00
  $3F: 3C 66 06 0C 18 00 18 00
  $40: 00 00 00 FF FF 00 00 00
  $41: 18 3C 66 7E 66 66 66 00
  $42: 7C 66 66 7C 66 66 7C 00
  $43: 3C 66 60 60 60 66 3C 00
  $44: 78 6C 66 66 66 6C 78 00
  $45: 7E 60 60 78 60 60 7E 00
  $46: 7E 60 60 78 60 60 60 00
  $47: 3C 66 60 6E 66 66 3C 00
  $48: 66 66 66 7E 66 66 66 00
  $49: 3C 18 18 18 18 18 3C 00
  $4A: 1E 0C 0C 0C 0C 6C 38 00
  $4B: 66 6C 78 70 78 6C 66 00
  $4C: 60 60 60 60 60 60 7E 00
  $4D: 63 77 7F 6B 63 63 63 00
  $4E: 66 76 7E 7E 6E 66 66 00
  $4F: 3C 66 66 66 66 66 3C 00
  $50: 7C 66 66 7C 60 60 60 00
  $51: 3C 66 66 66 66 3C 0E 00
  $52: 7C 66 66 7C 78 6C 66 00
  $53: 3C 66 60 3C 06 66 3C 00
  $54: 7E 18 18 18 18 18 18 00
  $55: 66 66 66 66 66 66 3C 00
  $56: 66 66 66 66 66 3C 18 00
  $57: 63 63 63 6B 7F 77 63 00
  $58: 66 66 3C 18 3C 66 66 00
  $59: 66 66 66 3C 18 18 18 00
  $5A: 7E 06 0C 18 30 60 7E 00
  $5B: 18 18 18 FF FF 18 18 18
  $5C: C0 C0 30 30 C0 C0 30 30
  $5D: 18 18 18 18 18 18 18 18
  $5E: 33 33 CC CC 33 33 CC CC
  $5F: 33 99 CC 66 33 99 CC 66
  $60: 00 00 00 00 00 00 00 00
  $61: F0 F0 F0 F0 F0 F0 F0 F0
  $62: 00 00 00 00 FF FF FF FF
  $63: FF 00 00 00 00 00 00 00
  $64: 00 00 00 00 00 00 00 FF
  $65: C0 C0 C0 C0 C0 C0 C0 C0
  $66: CC CC 33 33 CC CC 33 33
  $67: 03 03 03 03 03 03 03 03
  $68: 00 00 00 00 CC CC 33 33
  $69: CC 99 33 66 CC 99 33 66
  $6A: 03 03 03 03 03 03 03 03
  $6B: 18 18 18 1F 1F 18 18 18
  $6C: 00 00 00 00 0F 0F 0F 0F
  $6D: 18 18 18 1F 1F 00 00 00
  $6E: 00 00 00 F8 F8 18 18 18
  $6F: 00 00 00 00 00 00 FF FF
  $70: 00 00 00 1F 1F 18 18 18
  $71: 18 18 18 FF FF 00 00 00
  $72: 00 00 00 FF FF 18 18 18
  $73: 18 18 18 F8 F8 18 18 18
  $74: C0 C0 C0 C0 C0 C0 C0 C0
  $75: E0 E0 E0 E0 E0 E0 E0 E0
  $76: 07 07 07 07 07 07 07 07
  $77: FF FF 00 00 00 00 00 00
  $78: FF FF FF 00 00 00 00 00
  $79: 00 00 00 00 00 FF FF FF
  $7A: 01 03 06 6C 78 70 60 00
  $7B: 00 00 00 00 F0 F0 F0 F0
  $7C: 0F 0F 0F 0F 00 00 00 00
  $7D: 18 18 18 F8 F8 00 00 00
  $7E: F0 F0 F0 F0 00 00 00 00
  $7F: F0 F0 F0 F0 0F 0F 0F 0F
```

### Sample glyphs (8×8 visual reference)

Pixel grids for representative glyphs, to cross-check the hex above (`#` = set pixel).

**Set 1:**

`$20` space
```
........
........
........
........
........
........
........
........
```

`$01` A
```
...##...
..####..
.##..##.
.######.
.##..##.
.##..##.
.##..##.
........
```

`$08` H
```
.##..##.
.##..##.
.##..##.
.######.
.##..##.
.##..##.
.##..##.
........
```

`$0E` N
```
.##..##.
.###.##.
.######.
.######.
.##.###.
.##..##.
.##..##.
........
```

`$1A` Z
```
.######.
.....##.
....##..
...##...
..##....
.##.....
.######.
........
```

`$30` 0
```
..####..
.##..##.
.##.###.
.###.##.
.##..##.
.##..##.
..####..
........
```

`$35` 5
```
.######.
.##.....
.#####..
.....##.
.....##.
.##..##.
..####..
........
```

`$39` 9
```
..####..
.##..##.
.##..##.
..#####.
.....##.
.##..##.
..####..
........
```

`$2C` comma
```
........
........
........
........
........
...##...
...##...
..##....
```

`$2E` period
```
........
........
........
........
........
...##...
...##...
........
```

`$2A` asterisk
```
........
.##..##.
..####..
########
..####..
.##..##.
........
........
```

**Set 2:**

`$01` a
```
........
........
..####..
.....##.
..#####.
.##..##.
..#####.
........
```

`$02` b
```
........
.##.....
.##.....
.#####..
.##..##.
.##..##.
.#####..
........
```

`$05` e
```
........
........
..####..
.##..##.
.######.
.##.....
..####..
........
```

`$0E` n
```
........
........
.#####..
.##..##.
.##..##.
.##..##.
.##..##.
........
```

`$1A` z
```
........
........
.######.
....##..
...##...
..##....
.######.
........
```

## §A.6 — Built-in directory template

The directory chrome a client draws when Part 1 of a directory response is empty
(§7.5), extracted verbatim from the C64 terminal at `$BCE1`–`$BD77` (151 bytes). It is
an ordinary frame (§6): header `[flags=$00][border=$F4][background=$FF]`, charset `$8E`
(uppercase), then an RLE/PETSCII body, terminated by `$00`. Rendered (verified), it draws the
bordered content box with its **left border at column 0**, the **vertical divider at column 30**
and the **right border at column 39**, and a
mid-height separator line carrying the **`<F7)(F8>` column-cycle indicator**. The title, path
(§7 Part 4), entry list (Part 6) and footer (Part 2) are **overlaid** onto this frame from the
directory response (§7.7) — they are not part of the template.
```
  $BCE1: 00 F4 FF 8E 07 0D 05 05 D5 07 C3 1B C0 B2 07 C0
  $BCF1: 07 C9 0D DD 06 1C DD 06 07 DD 0D DD 06 1C C2 06
  $BD01: 07 C2 0D AB 07 C3 15 07 C0 06 DB 07 C3 07 B3 0D
  $BD11: DD 06 1C C2 06 07 C2 0D DD 06 1C C2 06 07 DD 0D
  $BD21: DD 06 1C C2 06 07 C2 0D DD 06 1C DD 06 07 C2 0D
  $BD31: DD 06 1C C2 06 07 C2 0D DD 06 1C C2 06 07 C2 0D
  $BD41: DD 06 1C C2 06 07 C2 0D DD 06 1C C2 06 07 C2 0D
  $BD51: DD 06 1C C2 06 07 C2 0D DD 06 1C C2 06 07 C2 0D
  $BD61: DD 06 1C C2 06 07 C2 0D CA 07 C0 1C B1 3C 46 37
  $BD71: 29 28 46 38 3E CB 00
```

## §A.7 — End-to-end session trace

A minimal native-client session — connect, log in, view the top directory, open a frame,
and leave. `→` is client-to-server, `←` is server-to-client. Framed packets are shown as
`$01 … $02`; raw (un-framed) bytes are shown without markers. This is the worked example an
implementer follows; every step is specified in the section cited.

```
   TCP connect to server:6400

←  20 20 20 20 20 20 20 20 20 20 20 20        handshake: 12 × $20            (§3.2)

→  43 20 43 4E 45 54 0D                        "C CNET\r"                     (§3.3)
→  43 20 43 4E 45 54 0D                        "C CNET\r"  (doubled)          native ident
→  30 30 30 30 30 30 30 30 30 30 30 30 30 30 0D  "00000000000000\r"          → server: native

←  (optional MOTD lines, raw, CR-terminated)                                 (§3.4)
←  2A 43 4F 4E 0D                              "*CON\r" connection signal     (§3.4)

→  $01 <len> 43 <seq> 5A <user×8> <pass×6> <sysinfo…> <crc16> $02
                                                COM login: 'Z' + creds        (§3.5)
←  $01 <len> 22 21 <welcome-frame bytes…> <crc> $02   DAT (welcome, §6)      (§2, §3.5)
→  $01 06 20 20 21 <crc> $02                   ACK seq $21                    (§2.9)
←  … more DAT packets …                        (each ACKed)
←  $01 05 22 <seq> <crc> $02                   zero-length DAT = EOS          (§2.9)
                                                (not ACKed — welcome complete)

→  $01 <len> 43 <seq> 50 <crc> $02             COM 'P' (FINISH) — leave welcome frame → current dir (= root here)  (§4, §7)
←  $01 <len> 22 <seq> 8E 0D 0D … <crc> $02     DAT: 6-part directory (§7)
→  $01 06 20 20 <seq> <crc> $02                ACK
←  $01 05 22 <seq> <crc> $02                   EOS (directory complete)
   client draws the built-in template (§A.6) + the entries

→  $01 <len> 43 <seq> 44 30 30 <crc> $02       COM 'D' "00" — select entry 0  (§4.4, §7.3)
←  $01 <len> 22 <seq> 00 06 0F 8E … 00 <crc> $02   DAT: frame (§6)
→  … ACK …
←  $01 05 22 <seq> <crc> $02                   EOS (frame complete; render §5)

→  $01 <len> 43 <seq> 45 <crc> $02             COM 'E' — LEAVE                (§4.4, §3.8)
←  $01 <len> 22 <seq> <goodbye-frame> <crc> $02   DAT (goodbye)
←  $01 05 22 <seq> <crc> $02                   EOS
   server closes the TCP connection (§3.8)
```

Notes:

- Sequence numbers advance in `$20`–`$5F` and wrap (§2.8); the server's first DAT uses `$21`.
- Every non-empty DAT is ACKed; the zero-length EOS DAT is not (§2.9).
- A ROM/C64 client differs only in the identification (hash-gated, §3.3) and in receiving a
  LINKING stream after the welcome frame (§3.6); the command loop is identical.
- Bare `P` here reaches the root because it is **FINISH** returning the *current* directory,
  and immediately after login the current directory **is** the root. Bare `P` is **not** a
  "go home" command: issued from inside a sub-directory it returns *that* directory, not the
  root. To ascend, use `B` (BACK) — repeated `B` walks up to the root (§4.4).
