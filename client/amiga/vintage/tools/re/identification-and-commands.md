# Amiga client — identification handshake & command protocol

## Identification handshake (CONFIRMED — differs from C64)

Right after "Carrier detected.", `do_connect` (0x10343c) sends a CNET identification
via raw sends (`thunk_FUN_001198e0(str, len)`):

```
send("C CNET\r", 7)              # 0x11d66a
send("C CNET\r", 7)              # 0x11d672   (sent TWICE)
delay(0xfa)
send("00000000000000\r", 0xf)    # 0x11d67a   14 zeros + CR (literal; not runtime-filled)
```

Compare the C64/Reborn identification:

```
C CNET\r {hash}/100\r ADP\r NO\r RUN\r      (Reborn puts the client version hash in field 1)
```

CR-split fields:

| | C64 (Reborn) | Amiga |
|---|---|---|
| field[0] | `C CNET` | `C CNET` |
| field[1] | `{hash}/100` (has `/`) | `C CNET` (no `/`) |
| field[2] | `ADP` | `00000000000000` |
| field[3+] | `NO`, `RUN` | — |

**The two are distinguishable** by shape: the Amiga repeats `C CNET\r` and has a
14-zero field; the C64 has `{hash}/100` in field 1. So the server *can* detect an
Amiga client at connect time from the identification alone.

### Server implication (future work)

The current Reborn server (`server/compunet_server.py`, ~line 2566+) parses field[1]
as `{hash}/100` and, on mismatch, rejects with `*PLEASE DOWNLOAD LATEST CLIENT`.
An Amiga client would be rejected. Supporting Amiga needs a detection branch **before**
the hash check: recognise the Amiga identification signature (e.g. field[1] == `C CNET`
or the doubled `C CNET\r`) and mark the session as Amiga, then serve Amiga-format
frames (see petscii-frame-format.md) for that session — mirroring the existing
C64-vs-terminal split.

The 14-zero field is literally zeros in this demo build (possibly a terminal-ID / NUI
slot the original PAD expected, left blank for the NEW-USER demo). Not needed for
client *detection*; the doubled `C CNET` is a sufficient discriminator.

## Command protocol — DECODED: matches the C64/Reborn command set

The Amiga sends application commands as **single ASCII letters** (some with a numeric
argument) inside a COM frame (token `0x43`), then waits for a one-byte ack `'@'`
(0x40) via `serial_io_c(&DAT_0012021a)`. Decoded from the client's command senders
(callers of `serial_write(..., 0x43)` and the format strings they build):

| Amiga payload | Byte(s) | Reborn server | Meaning | Evidence |
|---------------|---------|---------------|---------|----------|
| `P%02d` (e.g. `P07`) | `0x50`+num | `CMD_SHOW` (0x50) | **show text frame / page** | goto_page @0x10a1e2; server `_cmd_show` |
| `D%02d` | `0x44`+num | `CMD_DIR` (0x44) | enter directory | string `D%02d` @0x11ea6a |
| `A` | `0x41` | `CMD_ACCNT` | account | @0x11e6d2 |
| `B` | `0x42` | `CMD_BACK` | back / parent dir | @0x11e402 (str "Goto Page" nearby) |
| `E` | `0x45` | `CMD_EDITR` | editor | @0x11e4b8/@0x11e4ec |
| `M` | `0x4D` | `CMD_MAIL` | mail | @0x11ea66 |
| `N` | `0x4E` | handled `ord('N')` | FINISH / MORE | PROTOCOL.md §upload; server line 555; C64 `CMP #$4E` |
| `O` | `0x4F`* | C64 `CMP #$4F` @0x6022 | (upload/next — confirm) | @0x11e4f0, sent with token 0x40 |

*`O` is sent with frame token `0x40` in one path (upload data), not `0x43` — needs a
closer look, but the letter itself is in the C64's dispatch too.

**Conclusion:** the Amiga's application-command bytes are the **same set** the C64
client sends and the Reborn server already handles (`P`,`D`,`A`,`B`,`E`,`M`,`N`,`O`,
…). Selecting a text frame = `P<nn>` = `CMD_SHOW`, identical to the C64. The ack
convention (`'@'` = 0x40) is also consistent.

So across all three layers:
- **Transport** (framing/CRC/seq/tokens): matches ✓
- **Application commands** (P/D/A/B/E/M/N/O + ack `@`): matches ✓
- **Identification handshake**: differs but detectable (see above) ✓
- **Frame content encoding**: MATCHES — the Amiga renders the same PETSCII frames
  (same RLE + PETSCII control codes; converted to screen codes in the renderer). See
  petscii-frame-format.md. ✓ (pending: confirm 0x80-0x9F control table + palette)

**Net:** an unmodified Amiga `Compunet` client, given a TCP `cnet.device` and a server
that accepts its identification, should drive the Reborn server using the existing
command handlers **and the existing PETSCII frame content**. No separate Amiga frame
format is needed. Remaining verification: the 0x80-0x9F PETSCII control table and the
colour palette mapping.

## (superseded) Command protocol — was: NOT yet confirmed

**Important gap:** we have confirmed the *transport* (framing/CRC/sequence/tokens in
cnet.device) and the *identification* handshake. We have **not** confirmed the
*application-layer commands* — the actual byte sequences the Amiga sends to the server
for user actions:

- selecting/showing a text frame
- DIR / directory navigation
- GOTO page
- upload / download initiation
- login (user ID / password) exchange after PAD connect

These ride inside DAT/COM frames, but their *contents* (command bytes, page-number
encoding, field formats) may or may not match what the C64 sends and the Reborn
server expects. PROTOCOL.md documents the C64 command bytes; the Amiga's must be read
out of the client (the senders that call `serial_write(..., token)` and
`send_dat_packet`) and compared field-by-field.

Until that is done, we can say:
- **Transport: matches.** ✓
- **Identification: differs but is detectable.** ✓
- **Application commands: UNKNOWN — must be verified before claiming a Reborn Amiga
  client can drive the existing server.**

### Next

- Enumerate the Amiga client's command senders (callers of `serial_write` with a
  token, and `send_dat_packet`) and decode the payload each builds for: show-frame,
  DIR, GOTO, login. Compare against PROTOCOL.md command bytes.
- Capture a real session (client in an emulator against a logging server/PAD) if
  static reading is ambiguous.
