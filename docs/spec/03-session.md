# §3 — Session lifecycle

**Layer — application model** (shared across bindings, §1.8). The lifecycle *semantics* here are reused by every binding; only the packet bytes that carry them are Binding-A-specific (§2).

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority: `tcp_handler` in `server/compunet_server.py` (the connect/identify/login/
> command flow). Byte sequences below were verified against that handler.

This section defines the lifecycle of a session, from an open TCP connection to
disconnect. It uses the transport from [§2](02-transport.md): the handshake and
identification are exchanged as **raw bytes**, and everything from login onward is carried
in **framed packets** (COM `$43` client → server, DAT `$22` server → client).

## 3.1 Phases

A session proceeds through these phases in order:

1. **Handshake** (§3.2) — raw byte exchange that opens the protocol.
2. **Identification** (§3.3) — the client announces itself; the server detects the
   client type.
3. **Server greeting** (§3.4) — optional MOTD, then the `*CON` connection signal.
4. **Login** (§3.5) — the client sends credentials in a COM packet; the server
   authenticates and returns a welcome frame (or an error and disconnect).
5. **Online** (§3.6) — the command loop (see [§4](04-commands.md)).
6. **Disconnect** (§3.7).

A client **MUST** perform phases 1–4 in order before issuing any command.

## 3.2 Handshake

After the TCP connection opens, the server sends a burst of **twelve `$20` (space)
bytes** to open the protocol, then treats the connection as connected. A client **MUST**
tolerate this leading run of `$20` bytes and **MUST NOT** treat them as packet data (they
precede any `$01` framing).

**Do not count the `$20`s or expect them in one read (normative).** The server writes the
twelve bytes **one at a time, spaced ~100 ms apart**, so a single socket read typically returns
only a handful (e.g. 5) with the rest dribbling in over the next second — and the count is a
transport detail that has varied. A client **MUST NOT** gate on receiving exactly twelve, nor
block waiting for a fixed number. Treat the leading `$20` run as **opaque**: drain whatever
spaces are immediately available (a short read timeout), then proceed to identification (§3.3).
The client does not depend on this run at all — it may begin identification without fully
draining it, since the server tolerates leading spaces.

A client **MAY** send a single `$20` immediately after connecting, before the identification
(§3.3). The server peeks the first received byte only to tell a Hayes `AT` dialer from a raw
client (see below); a leading `$20` reads as "raw" and lets the server proceed at once,
whereas sending nothing simply makes the server wait briefly before its burst. Either is
acceptable; the client does not depend on the server's reply to this byte.

*(Non-normative — Hayes auto-detection.* Before sending the `$20` burst, the server peeks
at the first received byte. If that byte is an ASCII `'A'` (`$41`, bit 7 ignored) it enters
a brief Hayes-modem emulation: it consumes an `AT…` command up to a `CR` and replies
`CONNECT 1200\r`, then proceeds to the `$20` burst. This exists so emulated dial-up C64
setups work; a native TCP client neither needs nor should send an `AT` command, and will
simply receive the `$20` burst.)*

## 3.3 Identification and machine-type detection

Immediately after the handshake, the client sends an **identification** as **raw,
un-framed bytes**: a sequence of `CR`-separated (`$0D`) ASCII fields, the first of which is
`C CNET`. The server buffers these bytes until it can classify the client, then keys its
behaviour off the identification's **shape**. Two shapes exist:

**ROM / C64 (hash-gated) identification** — field[1] carries a client-version hash:

```
C CNET<CR>{hash}/100<CR>ADP<CR>NO<CR>RUN<CR>
```

The distinguishing feature is a `'/'` in field[1]. The server extracts `{hash}` (the text
before `/`) and compares it, case-insensitively, against `server/cfg/client_version.txt`.
On mismatch it sends `*PLEASE DOWNLOAD LATEST CLIENT<CR>` and closes the connection after
~3 seconds. A client taking this path therefore **MUST** present a `{hash}` that matches
the server's current expected value.

**Native (non-gated) identification** — as used by the native Amiga client:

```
C CNET<CR>C CNET<CR>00000000000000<CR>
```

The distinguishing features are the **doubled** `C CNET` line and/or a **14-zero** field,
and the **absence** of a `'/'`. The server classifies this as a native client, marks the
session accordingly, and **skips both the version-hash gate and the LINKING terminal
download** (§3.6).

Detection rule the server applies (a client **MUST** produce an identification that
satisfies exactly one branch):

| Condition on the buffered identification | Classified as |
|---|---|
| contains `/` | ROM / C64 (hash-gated) |
| contains `CNET` twice, **or** contains `00000000000000` | Native |

The server waits until one of these is decidable before proceeding, so a client **MAY**
send the identification split across multiple TCP segments.

> **Guidance for a new (third-party) client.** A new native client that renders its own
> frames **SHOULD** use the **native identification** form. It bypasses the C64 terminal-
> version gate (which is meaningful only to the 6502 ROM client) and suppresses LINKING,
> which a native client cannot use. Only a client that is downloading and running the 6502
> terminal binary should take the hash-gated path.

## 3.4 Server greeting

Once the client is classified, the server:

1. **Optionally sends an MOTD** as raw bytes — zero or more `CR`-terminated lines from
   `server/cfg/motd.txt`. Letters are transmitted in **PETSCII lowercase mode** (ASCII
   `A`–`Z`, `$41`–`$5A`, are sent as `$C1`–`$DA`; see [§5](05-display.md)). A client
   **SHOULD** display these lines; a client that does not implement the display contract
   **MAY** ignore them.
2. **Sends the connection signal** `*CON<CR>` (`$2A $43 $4F $4E $0D`) as raw bytes.
   This marks the end of the greeting and the transition to login.

A client **MUST** treat the greeting bytes as raw (un-framed) and **MUST NOT** attempt to
parse them as packets.

## 3.5 Login

The first **framed** packet the client sends is the **login packet**: a COM (`$43`) packet
(§2) whose payload begins with the login command byte `Z` (`$5A`):

| Payload offset | Field | Size | Description |
|---|---|---|---|
| 0 | `'Z'` (`$5A`) | 1 | Login command |
| 1 | User ID | 8 | Space-padded (`$20`) to 8 bytes |
| 9 | Password | 6 | Space-padded to 6 bytes |
| 15–24 | System info | 10 | ROM/terminal state; **not interpreted by the server** |
| 25–26 | Terminal hash | 2 | (ROM clients) current cached-terminal hash, for the LINKING skip check |

The server reads **only** the User ID (offsets 1–8), the password (9–14), and — for ROM
clients — the terminal hash at 25–26; it trims trailing spaces from the ID and password and
authenticates. The system-info region (15–24) is not interpreted, so a native client **MAY**
zero- or space-fill it. A native client (which never links) **MAY** also leave the terminal
hash zero, since it is classified to skip the hash gate and LINKING (§3.3, §3.6).

**On failure**, the server sends a single-page error frame with the text
`  INVALID ID OR PASSWORD` (as a DAT stream terminated by a zero-length-payload EOS packet,
per §2.9 and [§6](06-frame-format.md)), waits ~2 seconds, and closes the connection. A
client **MUST** be prepared to render this frame and handle the close.

**On success**, the server sends the **welcome frame** as a DAT stream + EOS. The client
**MUST** consume and (at Tier 1) render it. The user is now logged in and the session
enters the online phase.

## 3.6 LINKING (ROM clients only)

For a ROM / C64 client, the server follows the welcome frame with the **LINKING** stream —
the 6502 terminal binary, delivered as a DAT stream introduced by an 8-byte header
(`hash_hi, hash_lo, $05, $A0, $00, $A0, $00, $00`) and terminated by an EOS packet. If the
client already holds the current terminal (its login-packet hash matches), only the header
(plus a pad byte) is sent.

LINKING is a **C64-platform mechanism** for downloading executable terminal code; its
detailed stream format is a platform concern and is documented in `docs/PROTOCOL.md`
(ROM rewrite / linking). **A native client is classified so that LINKING is skipped
entirely** (§3.3) — it receives the welcome frame and nothing more before the command
loop. A native client therefore **MUST NOT** expect a LINKING stream and **MUST** treat the
post-welcome EOS as the cue to begin issuing commands.

## 3.7 Online (command loop)

After login (and LINKING, for ROM clients), the session is online. The client issues
single-letter commands in COM (`$43`) packets and the server replies with DAT (`$22`)
streams terminated by EOS, subject to the ACK pacing of §2.9. The command set and
request/response shapes are specified in [§4](04-commands.md). Application subsystems
(mail, downloads, uploads, editor, Partyline, LIFE/VOTE) layer on this loop and are
specified in [§8](08-subsystems.md).

*(Non-normative: while online the server auto-detects native (Amiga) sessions that need a
leading `@` (`$40`) ack byte prepended to certain command responses; this is a native-
client compatibility measure described in §4, not a change to the wire format itself.)*

## 3.8 Disconnect

A session ends in one of these ways:

- **Client LEAVE.** The `LEAVE` command (`E`, §4.4) causes the server to send a **goodbye
  frame** (an ordinary §6 FRAME response, DAT stream + EOS) and then close the connection
  after ~2 seconds. A client **MUST read and render that goodbye frame before handling the
  close** — it is not merely "quit and disconnect"; the server sends a farewell screen first.
  A client **SHOULD** offer LEAVE as the clean way to log off.
- **Idle timeout.** The server closes a session that sends no command for **20 minutes**
  (1200 s). A client **MAY** send activity to keep the session alive.
- **Transport close.** Either side closing the TCP connection ends the session. A client
  **MUST** handle an unexpected close at any point without corrupting user data.
