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
values are meaningful only within this exchange. Each is an ordinary framed packet (§2.2–2.4)
with that token, the client's current sequence number, and an **empty payload** — i.e. content
`[length=$05][token=$40 or $41][seq][crc_hi][crc_lo]`, byte-stuffed and framed like any packet.
*(Non-normative: for a C64 program the load address is honoured; for an Amiga program the body
is the raw relocatable HUNK executable and the load field is 0 — the client `LoadSeg`s it. Note
some development-server content is stored as placeholder text frames rather than real
programs, in which case a selected `P`/`PP`/`S` entry returns a normal frame instead of the
8-byte header; a client should fall back to rendering it as a frame if the response is not
exactly 8 bytes.)*

### 8.3.2 Upload (The Jungle) and mail send

Uploads use the `U` command for both content upload and mail send. The `U` payload is:

```
subject/title (16 bytes) │ type (1 byte) │ rest…
```

The server distinguishes the two by the **`rest` field**: if a `.` appears in the first 8
bytes of `rest` it is a **content upload** (the `.` is the decimal point of the price);
otherwise it is a **mail send**.

- **Mail send** — `rest` is up to five **8-byte destination IDs** (space-padded); the type
  byte is `T`.
- **Content upload** — `rest` is a **6-byte price** (e.g. `005.00`) followed by a **lifetime
  in days** (up to 3 ASCII digits); the type byte is `T` (text) or `P` (program).

**Validation stream (step 1 → server reply).** The server replies with a validation stream
and remembers a pending-send state:

- **Mail send:** for each destination ID, the 8-byte ID (space-padded) followed by the
  recipient's real name **if the user exists** (nothing if not), then `$1E`. So `$1E`
  immediately after an ID means "no such user". Delivered as a **DIR stream + EOS**. For a
  native (Amiga) session the server prepends a `@` (`$40`) ack byte (§4.3).
- **Content upload:** the 6-byte price echoed back, then `$1E`. Delivered as a **single ACK
  packet with no EOS** — the client proceeds immediately.

**Frame transfer (step 2).** After validation the client transmits its frame(s). Frame bytes
are sent as **DAT packets** (not COM) while the pending-send is active; the server treats any
non-COM packet during an upload as frame data:

- **Text frame** (`type T`): the client streams the frame (§6) as DAT chunks; a chunk
  **shorter than 100 bytes** ends that frame. The server stores it and replies with **one**
  DAT packet whose payload is `@` (`$40`) + padding — a "clean accept" ack. (It is `@`, not
  `A`/`$41`, because a native client reads this byte and treats `A` as a host error.) One ack
  per frame; repeat for further frames.
- **Program** (`type P`): the client first sends an **8-byte header** DAT — byte 0 = machine
  type (`1` = Amiga, `0` = C64), bytes 4–7 = body size, **big-endian** — then the raw file as
  DAT chunks. The server reads the size, accumulates exactly that many bytes, and sends a
  single final `@`-ack. There is **no per-chunk ack** for a program body.

**Completion (step 3).** The client finishes the session with a different command per mode:

- **Mail:** `N` (§4.4) — the server delivers the message to the recipients.
- **Content:** `P` (directory refresh) — the server commits the new page and returns the
  directory.

**A content upload commits to the client's *current directory*** — the directory the client
is navigated to when the upload runs, **not** a fixed "Jungle root". A Tier 3 client **MUST
first navigate to the target directory** (e.g. `L JUNGLE`, or `D` into the intended
sub-directory) *before* sending `U`; the finishing `P` returns that same directory with the new
page in it. Uploading also requires **permission** to write there (you own the directory/page,
you are an editor/admin, or the directory is open for uploads) and space (a directory holds at
most 11 entries) — otherwise the server silently discards the page. "The Jungle" is simply the
conventional directory tree for user uploads, not a special upload target.

**A client cannot create directories.** Upload creates **pages** (`T`/`P`) only; there is **no
protocol command to create a directory** and no directory (`D`) upload type. The directory
**hierarchy is defined server-side** (in the service's content configuration), where a
directory can be marked open for uploads; a client only uploads pages **into** the existing,
upload-enabled directories. Building or editing the directory tree itself is a server-side
content-management task, outside this specification and not something a client implements.

A Tier 3 client that uploads **MUST** honour all of: the mail-vs-content detection (`.` in
`rest[:8]`), the EOS/no-EOS difference in the validation reply, the `@`-ack (not `A`) per
frame, the 8-byte big-endian header for programs, and the correct finish command (`N` for
mail, `P` for content). Any of these wrong desynchronises the session.

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

**Partyline** is multi-user chat, reached through a directory **link** entry (base type `L`,
§7.4). It is the one subsystem that leaves the framed protocol: after activation, the
session switches to a **raw, line-based** exchange.

The link entry may be **nested**: a menu item titled "PARTYLINE" is often a *directory*
(`D+`) that the user enters first, and the actual `L`-type link (e.g. "JOIN PARTYLINE") is an
entry **inside** it. A client **MUST** dispatch on the entry's **type letter** (`L`), not its
title — activate whichever entry is base type `L`, wherever it sits in the tree, by selecting
it with `D`+index (§7.4).

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

**The chat session.** Once in the raw session:

- The user sees a scrolling **message area** and types into an **input area** (on the C64 the
  message area has a blue border and the input area a green border with a green cursor; the
  exact chrome is a client choice). A message or command is **transmitted when the user
  presses RETURN twice** (a blank line commits it). The client sends the completed line as raw
  `CR`-terminated ASCII (§2 does not apply here — this is the un-framed stream).
- Incoming messages arrive as server-pushed lines and are shown as the sender's name on one
  line followed by the message text:
  ```
  {name}:
  Hello, this is my message.
  ```
  where `{name}` is the sender's alias, or their Compunet user ID if no alias is set; a
  message may span multiple lines. On entry the server broadcasts `{USER} has entered
  partyline`.
- **Scrollback** is by the cursor up/down keys.

**Rooms.** Every user is always *in a room*, and **messages are seen only by others in the
same room**. On entry a user starts in the default room (**`lobby`** — the server may display
its name capitalised, e.g. `Lobby`, in `*who`; the casing is cosmetic). `*enter <room>` moves
to (and creates, if new) a named room; others in the old room see `{USER} has left the room.`
and others in the new room see `{USER} has entered the room.`

**Commands** are `*`-prefixed, **lowercase**, and — like messages — committed with a double
RETURN. The client passes them through **verbatim as ordinary input lines**; the server
interprets them (they are not a separate wire format):

| Command | Effect |
|---|---|
| `*help` | Show Partyline help text |
| `*alias <name>` | Set a display alias that replaces the user ID in messages |
| `*who` | List users currently in Partyline (alias, Compunet ID, room) |
| `*enter <room>` | Join a room, creating it if it does not exist |
| `*call <user>` | Send a "{sender} calls you from {room}" notification to another user |
| `*dice <n>` | Roll an *n*-sided die; result shown to the user and broadcast to the room |
| `*quit` | Leave Partyline and return to Compunet (triggers the teardown above) |

A Tier 3 client **MUST** implement the raw line protocol and the activation/teardown for at
least one transport variant. *(Non-normative: the detailed C64 memory map and the resident
Amiga viewer "CnetTty" are platform mechanics — see `docs/partyline.md`.)*

## 8.6 UCAT, VOTE, and LIFE

Three commands round out the interactive tier: `C` (UCAT), `V` (VOTE), and `X` (LIFE). They
are three **distinct** commands. **BUY** is also a duckshoot command the user can pick, but it
is a *separate action* that maps to `D`+index, **not** to `X` — see the box at the end of this
section.

### UCAT — `C`

The **user catalogue**: a directory listing of the pages **owned by the logged-in user** (the
content *they* have uploaded to the Jungle), so they can find and manage their own material.
The server replies with an ordinary six-part directory response (§7), paged with MORE (§7.6)
like any directory, resetting to the first page each time `C` is issued. It is *the current
user's* content, not a global catalogue.

### VOTE — `V`

Casts a vote on a **directory entry** — the currently-highlighted one, identified by its
index the same way `D` selects an entry (§4.5/§7.7). The argument is therefore **two parts**,
as ASCII digits with no separator:

```
V <entry index, 2 digits> <score, 1 digit 1–9>
```

e.g. `V 00 5` votes score 5 on the first visible entry. A client **MUST** send the
highlighted entry's index (its client-local selection), not just the score — voting is
targeted at a specific listed entry, not "the current page". The score is 1–9. The server
replies with a bare **ACK** (§4.3, single packet, no EOS); a client **MUST** treat the ACK as
success and **MUST NOT** wait for a frame stream. *(A vote's effect may not be immediately
visible in the directory's `VOTE/NUM` column on the next listing.)*

### LIFE — `X`

`X` **extends the lifetime** of a directory entry's content (the LIFE duckshoot command). Like
VOTE, it targets an entry by index:

```
X <entry index, 2 digits> <extension amount, up to 4 digits>
```

e.g. `X 03 10` extends the fourth visible entry's life by 10. A client **MUST** send the
highlighted entry's index (its client-local selection). The extension is charged against the
user's free storage, overflowing to credit; a negative amount reduces life (owner/admin/editor
only). The server replies with a bare **ACK** (§4.3). On a **link** entry `X` is a no-op ACK
(links are activated by *selecting* them, not by `X`).

> **BUY is a duckshoot command, but not `X`.** `BUY` *is* a command the user picks from the
> duckshoot (§4.7) — but it has **no wire byte of its own**. Selecting BUY on the highlighted
> entry sends **`D` + index** (§4.4), which routes to the download (§8.3.1) or link-activate
> (§8.5) flow; a paid page's credit is deducted **implicitly on first view** (§7). So BUY and
> LIFE are different actions with different wire commands: **BUY → `D`+index**, **LIFE → `X`**.
> `X` never buys anything.

These are Tier 2. Each is a single command with a simple ACK reply and adds no new wire
mechanics beyond §4.

## 8.7 Subsystem → command → tier summary

| Subsystem | Commands | Reply | Tier |
|---|---|---|---|
| Content viewing / paging | `D`, `N`, `P` | FRAME / DIR | 1 |
| Mail (Courier) read | `M`, `D` | DIR, then FRAME | 2 |
| **Mail send** (Courier) | `U`, `N` | validation stream, ACK | **2** |
| Program download | `D` then `$40`/`$41` | header, then DAT stream | 2 |
| VOTE | `V` + index + score | ACK | 2 |
| LIFE (extend life) | `X` + index + amount | ACK | 2 |
| BUY (download / activate / pay) | `D` + index (no separate command) | per entry type | 2 |
| UCAT | `C` | DIR | 2 |
| Content upload (Jungle) | `U`, `P` | validation stream, ACK | 3 |
| Editor | (client-side) → `U` | via upload | 3 |
| Partyline | link (`L`) → raw lines | raw ASCII | 3 |
