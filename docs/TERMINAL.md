# PETSCII Terminal Mode

## Overview

Port 6401 provides a server-rendered PETSCII terminal interface to Compunet
Reborn. Any terminal program that supports the C64 PETSCII character set can
connect — no custom client binary required.

Tested with: SyncTerm (Raw mode, Commodore 64 UPPER font, 40 columns).

## Connection

- **Port**: 6401 (TCP)
- **Protocol**: Raw TCP or Telnet (auto-detected)
- **Character set**: PETSCII (C64 shifted charset for text, unshifted for artwork)
- **Screen size**: 40 columns × 25 rows

The server auto-detects whether the client sends Telnet IAC negotiation on
connect. Telnet clients get WILL ECHO/WILL SGA negotiation and $FF byte
escaping. Raw clients get clean PETSCII with no protocol overhead.

## SyncTerm Setup

- Connection Type: **Raw**
- Font: **Commodore 64 (UPPER)**
- Screen Mode: **C64** (or 40 columns)
- Address: `<host>:6401`

## Architecture

`server/terminal.py` contains the full terminal session handler. It uses
composition with the existing server infrastructure:

- **Auth**: Same `users.json` and password hashing as the protocol client.
- **Content**: Same `CompunetDirectory` tree, same .seq frame files.
- **Online users**: Shared `_online_users` set (terminal users appear in WHO).
- **Audit**: Same `audit_log()` calls for connect, vote, etc.
- **Partyline**: Can hand off to `partyline.handle_session()` (planned).

The terminal module does NOT use the X.25 binary protocol — it renders
everything server-side and sends raw PETSCII bytes to the terminal.

## Frame Rendering

Compunet .seq frame files use a 4-byte header followed by content:

| Byte | Purpose              | Terminal handling       |
|------|----------------------|------------------------|
| 0    | Flags                | Skipped                |
| 1    | Duckshoot colour     | Skipped (VIC-specific) |
| 2    | Border colour        | Skipped (VIC-specific) |
| 3    | Background colour    | Skipped (VIC-specific) |
| 4+   | Frame content        | Expanded and sent      |

### RLE Codes

The frame content uses Compunet-specific RLE compression:

- `$06 <N>`: Emit space character **(N + 1) times**
- `$07 <char> <N>`: Emit `<char>` **(N + 1) times**
- `$00`: End of frame

The count byte represents *additional* repetitions after the first emission.
This matches the C64 ROM behaviour at $8A4B–$8A7D where the character is
returned once immediately, then the count is stored for subsequent calls.

### CR Handling

After a line fills all 40 columns, the terminal auto-wraps the cursor to the
next row. If a CR ($0D) follows, it would create a blank line. The C64 ROM
compensates by sending cursor-up ($91) before CR when the cursor is at
column 40 (see $8C26). The terminal module suppresses CR entirely when the
column counter reaches 40+, achieving the same result.

### Charset Modes

- `$8E` (uppercase/graphics): Sent before PETSCII artwork (.seq frames,
  directory headers). Characters $A0–$BF and $60–$7F are graphics.
- `$0E` (lowercase/uppercase): Sent before text rendering. $C1–$DA display
  as uppercase A–Z, $41–$5A as lowercase a–z.

## Duckshoot

The command bar on row 24 matches the C64 client's revolving display:

- 39 visible characters (avoids triggering line wrap)
- Selected command in the centre (character positions 18–23), normal text
- Surrounding commands in reverse video, wrapping circularly
- Cursor left/right revolves the bar; RETURN executes the centre command
- Full C64 command set: HELP, DIR, SHOW, BACK, GOTO, UCAT, MAIL, ACCNT,
  SAVE, EDITR, LEAVE, PRINT, LIFE, BUY, LOAD, UPLD, VOTE

## Welcome Screen Template

The welcome frame (`content/templates/welcome.seq`) contains placeholders
that are filled at runtime:

| Placeholder      | Value                     |
|------------------|---------------------------|
| `{USER_NAME}`    | User's display name       |
| `{LAST_DATE}`    | Previous login date       |
| `{LAST_TIME}`    | Previous login time       |
| `{PAGES_STATS}`  | Pages owned / near death  |
| `{FREE_STORAGE}` | Free storage remaining    |
| `{NEXT_QUARTER}` | Next quarter start date   |
| `{PB1}`–`{PB6}` | Pillarbox mail indicator  |

The `replace_padded()` function preserves line width by emitting
`(orig_len + orig_pad + 1) - value_len` literal spaces after each value.
The +1 accounts for the C64 ROM's count+1 RLE semantics that the protocol
server's `$06` code would produce.

## Limitations

- No background colour control (VIC hardware register, no PETSCII equivalent)
- No border colour (same reason)
- SAVE, LOAD, PRINT commands are N/A (C64 disk/printer operations)
- UCAT not yet implemented
- Multi-page directory scrolling (>11 entries) not yet implemented

## Quirks

- **Editor charset**: The frame editor operates in uppercase/graphics mode
  only. There is no way to toggle to the lowercase/uppercase charset while
  editing, as SyncTerm and most PC-based PETSCII terminals have no key
  mapping for the C64's Commodore+Shift charset toggle. Frames requiring
  the shifted charset should be created using the C64 client.
