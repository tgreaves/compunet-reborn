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

## Command protocol (NOT yet confirmed — open)

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
