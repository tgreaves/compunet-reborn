# §8 — Subsystems

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority & triangulation: the server subsystem handlers (`_cmd_mail`, `_cmd_upload`,
> `_cmd_buy`, `_cmd_vote`, program-download path, and `server/partyline.py`), corroborated
> against `docs/PROTOCOL.md` (verified upload/mail/telesoftware traces) and the Amiga
> reconstruction. Platform-specific mechanics (C64 memory maps, the resident Amiga viewer)
> are cited as platform notes, not requirements.

The subsystems are the application features layered on the transport (§2), commands (§4),
and content formats (§§5–7). They are **optional** in the tier model: a Tier 1 client
implements none of them; a Tier 2 client implements content, mail, downloads, and
LIFE/VOTE; a Tier 3 client implements all of them including uploads, the editor, and
Partyline. Each subsystem below states which commands it uses and the wire exchange.

## 8.1 Content viewing and paging

Selecting a text entry (type `T`, §7.4) shows its frame(s). This is the core read path and
is built entirely from §§4–6:

- The client selects an entry with `D` + index (§4.4); the server replies with the first
  frame (type FRAME).
- If the frame's flags bit 7 is set (§6.5), more pages follow. The client advances with `D`
  (no argument) or `N` and the server sends the next frame.
- `P` (FINISH) leaves frame view and returns to the directory.

A Tier 1 client **MUST** implement this loop (it is just §6 paging over the §4 commands).

## 8.2 Mail (Courier)

Compunet mail is called **Courier**. It reuses the directory machinery: the mailbox *is* a
directory listing.

- **Enter mail:** the client sends `M` (§4.4). The server replies with a **six-part
  directory response** (§7) whose entries are the user's messages — sender/subject in the
  first field, metadata (date, status) in the column fields. A client **MUST** parse this
  exactly as a §7 directory.
- **Read a message:** selecting a message entry (with `D` + index) returns the message body
  as frame(s) (§6), paged like any other content.
- **Send a message:** mail send uses the upload command `U` — see §8.3, which distinguishes
  mail-send from content-upload by the parameter shape.

*(Non-normative: once read, a message is presented in the client's editor buffer and is not
re-served by the server; the login screen and the next directory carry an unread-mail
indicator — a red `MAIL` marker, §7.2 Part 4.)*

## 8.3 Downloads and uploads

### 8.3.1 Program download (telesoftware)

Selecting a program entry (type `P`/`PP`/`S`) downloads an executable/file. Instead of a
text frame, the server sends an **8-byte binary header** then waits for the client to
request the body:

| Byte | Meaning |
|---|---|
| 0 | machine type (`0` = C64, `1` = Amiga) |
| 1–3 | reserved (`0`) |
| 4 | load address low |
| 5 | load address high |
| 6 | size low |
| 7 | size high |

Exchange:

1. Server sends the 8-byte header (as a FRAME-type DAT response).
2. The client, ready to receive, sends a **proceed** packet with token **`$40`** (§2.5).
3. The server streams the program bytes as a DAT stream + EOS (§2, §4.2).
4. To decline, the client sends token **`$41`** (abort) instead of `$40`, and the server
   drops the pending download.

A client that offers downloads **MUST** implement the `$40`/`$41` control tokens; these two
values are meaningful only within this exchange. *(Non-normative: for a C64 program the
load address is honoured; for an Amiga program the body is the raw relocatable HUNK
executable and the load field is 0 — the client `LoadSeg`s it.)*

### 8.3.2 Upload (The Jungle) and mail send

Uploads use the `U` command for both content upload and mail send; the server tells them
apart by the parameter shape:

**Mail-send parameters** (`U` payload): 16-byte subject, a 1-byte type (`T`), then up to
five 8-byte destination IDs (space-padded).

**Content-upload parameters** (`U` payload): 16-byte title, 1-byte type (`T`/`P`), an
8-byte price in `NNN.NNNN` form (the `.` is what marks it as an upload rather than mail),
and a 1-byte life-in-days digit.

Wire flow (verified against live testing):

1. Client sends `U` + parameters (COM `$43`).
2. Server returns a **validation stream**: for each destination/target, the echoed ID
   followed by a confirmation, each terminated by `$1E`; `$1E` immediately after an ID means
   "no such user". *(Mail send: this stream ends with EOS. Content upload: the validation
   response has **no EOS** — the client proceeds immediately.)*
3. **Mail:** on confirm, the client sends a second `U` (no parameters) = "frame ready",
   waits for an ACK, then sends the frame; repeat per page; `N` (§4.4) finishes and delivers
   the message.
   **Content:** the client sends the frame immediately after validation (metadata
   accompanies each frame); `P` (directory refresh) finishes the upload and the server
   commits the page.

A Tier 3 client that uploads **MUST** follow the mail-vs-content distinction above; getting
the EOS/no-EOS or the finish command (`N` vs `P`) wrong desynchronises the session.

## 8.4 Editor

The frame **editor** is a client feature, not a server command — recall from §4.4 that
there is no editor command byte (the `CMD_EDITR` constant is vestigial; `E` = LEAVE). The
editor lets the user compose one or more frames (PETSCII pages, §5–6) offline or online; the
composed frames are then submitted through the **upload** path (§8.3.2) — content upload for
Jungle pages, or mail send for Courier messages.

A client **MAY** implement editing in any way its environment allows; the only wire
requirement is that what it submits is a valid frame (§6) delivered via §8.3.2. The editor
is therefore Tier 3 by virtue of depending on uploads, but imposes no protocol of its own.

## 8.5 Partyline

**Partyline** is multi-user chat, reached through a directory **link** entry (type `L`,
§7.4). It is the one subsystem that leaves the framed protocol: after activation, the
session switches to a **raw, line-based** exchange.

**Activation and transport differ by platform**, but the chat protocol is identical:

- **Raw line protocol (both platforms).** Once in Partyline, both sides exchange
  **`CR`-terminated (`$0D`) ASCII text lines** — no framing, no CRC, no sequence numbers.
  The server pushes lines as events occur (messages, joins, command replies); the client
  sends a completed input line when the user commits it (the original clients transmit on a
  double-RETURN). Only printable ASCII (`$20`–`$7E`) is exchanged.
- **C64 activation.** Selecting the link downloads a small chat program (the C64 loads it
  via the type-`L` `MODEM_INIT_DOWNLOAD` stream, §7.4) which then runs the raw session. Exit:
  the client sends `*quit<CR>`; the server broadcasts the leave and replies `*EXIT<CR>`; the
  client restores the screen and the session returns to the framed protocol.
- **Native activation.** A native (Amiga-classified) client is served the link differently
  (§3.3 gating): the server sends an **8-byte link header** `01 00 00 01 00 00 00 00` as a
  single DAT frame **with no EOS**, then switches to the raw stream. The client validates the
  first long == `0x01000001` and the second == `0`, then a raw preamble handshake runs
  (server `01 01 01`; client replies `01`×6), the ASCII chat session runs, and teardown is
  three `$02` bytes from the server (client replies `$02`×6) after which the framed protocol
  resumes.

**Chat commands** are `*`-prefixed lines the user types (handled by the server's partyline
module), e.g. `*who`, `*enter <room>`, `*alias <name>`, `*quit`. A client passes them
through as ordinary input lines; they are not a separate wire format.

A Tier 3 client **MUST** implement the raw line protocol and the activation/teardown for at
least one transport variant. *(Non-normative: the detailed C64 memory map and the resident
Amiga viewer "CnetTty" are platform mechanics — see `docs/partyline.md`.)*

## 8.6 UCAT, LIFE, and VOTE

Three lightweight commands round out the interactive tier:

- **UCAT** — `C` (§4.4): the user catalogue; the server replies with a directory response
  (§7).
- **VOTE / LIFE** — `V` + an ASCII digit choice casts a vote on the current page; the server
  replies with a bare **ACK** (§4.3, single packet, no EOS). The related **LIFE** operation
  extends a page's lifetime. A client **MUST** treat the ACK as success and not wait for a
  frame stream.
- **BUY** — `X` + page (§4.4): purchase a paid page; the server replies with an ACK and the
  page's credit is deducted. (Paid pages are also purchased implicitly on first view, §7.)

These are Tier 2. Each is a single command with a simple ACK-or-directory reply and adds no
new wire mechanics beyond §4.

## 8.7 Subsystem → command → tier summary

| Subsystem | Commands | Reply | Tier |
|---|---|---|---|
| Content viewing / paging | `D`, `N`, `P` | FRAME / DIR | 1 |
| Mail (Courier) read | `M`, `D` | DIR, then FRAME | 2 |
| Program download | `D` then `$40`/`$41` | header, then DAT stream | 2 |
| LIFE / VOTE | `V` | ACK | 2 |
| BUY | `X` | ACK | 2 |
| UCAT | `C` | DIR | 2 |
| Upload (Jungle) / mail send | `U`, `N`/`P` | validation stream, ACK | 3 |
| Editor | (client-side) → `U` | via upload | 3 |
| Partyline | link (`L`) → raw lines | raw ASCII | 3 |
