# §8 — Subsystems

**Layer — application model** (shared across bindings, §1.8). The subsystem *semantics* (mail, downloads, uploads, editor, Partyline, LIFE/VOTE) are reused by every binding; the byte-level exchanges described here are Binding-A's encoding of them.

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
- **The mailbox carries a Part-1 header** like any other directory (§7.2) — the Courier banner
  (`courier-header.seq`), body-only PETSCII served after a `$8E` charset byte. A client renders it
  exactly as it renders a content directory's header; a mailbox with no header is a serialisation
  bug, not a property of Courier.
- **⚠ The mailbox breadcrumb identifies the MAILBOX OWNER**, not a position in the content tree:
  line 1 is `USER ID : <id>` and line 2 the user's **real name**. Courier is not a place in the
  hierarchy, so the usual `*** COMPUNET *** / …` trail says nothing the title does not — and the
  owner's identity is what the sender needs, since it is the `FROM` shown on every message they
  send (§A.11).
- **Read a message — `SHOW` downloads ALL of it (normative).** Courier does **not** page a
  message frame by frame. `SHOW` sends `D`+index for the first frame and then **repeats bare
  `D`** until the reply stops being a frame — the same loop §4.7 defines for `ALL` — pulling the
  entire message as fast as the line allows, and ending on a **`PRESS ANY KEY`** screen with
  **no duckshoot** (§4.8). The server clears the open message after the last frame and answers
  with the **mailbox listing**, which is what terminates the loop; a client **MUST** hold that
  listing back until the keypress, or the message it just fetched is wiped off the screen before
  it can be read.

  **⚠ The point is the editor, not the screen.** Every frame is captured into the editor buffer
  on the way past (§8.4.2), so the user can hang up and read their mail **offline**. That is what
  the download-it-all gesture was *for* on a metered phone line, and it is why `SHOW` behaves
  unlike `SHOW` anywhere else in the system. A client that fetches one frame and waits has
  implemented content paging, not Courier.

  **⚠ Pace the download (normative — §4.7's frame-pacing rule).** "As fast as the line allows"
  was seconds per frame at 1200 baud; over TCP it is one flash, and the user sees only the last
  frame and concludes that only the last frame arrived. Hold each for **~500 ms**. The
  correctness of the download is not the issue — the frames *are* all in the editor — but a
  client that leaves the user believing otherwise has lost the feature all the same.
- **⚠ `MORE` in Courier pages the MAILBOX, and sends `M` — not `D` (normative).** It is a
  command of the **listing** row only (§4.8); there is no `MORE` while reading, because there is
  no duckshoot while reading. `M` issued while already in mail mode advances the mailbox one
  page. A client that sends bare `D` from the listing gets the index defaulted to 0 and **opens
  the first message** — `MORE` silently becomes `SHOW`, marking mail read on the way. (Verified
  in the original C64 client: the mail menu's bare-`M` handler at `$B039` is `LDA #$4D /
  LDY #$01 / JMP $A35F`. See `docs/PROTOCOL.md`, which had the mail menu's handler column
  misaligned.) Bare `D` in Courier is not a user command at all — it is the frame-advance step
  of `SHOW`'s download loop, above.
- **⚠ This is why the mail row has a `MORE` and the directory row does not** (§4.8). Authored
  directories do not paginate at all; generated listings page by *selection* (§7.6). But
  **Binding A's mailbox response carries no synthetic pagination row** — it emits up to eleven
  real entries and nothing else — so on the wire `MORE` is the **only** way to reach page 2 of a
  mailbox. That is what the command is for, and why the mail menu is a *distinct* table rather
  than the directory's with substitutions.

  A binding that *does* add the pagination row (Binding B appends one to generated listings)
  therefore offers **two** routes to the same place: the `MORE` command and selecting the row.
  Both are conforming and both **MUST** work — the row is how the general §7.6 gesture applies
  here, and `MORE` is the mail row's own command, which a client displays whether or not its
  binding also draws the row.
- **Send a message:** mail send uses the upload command `U` — see §8.3, which distinguishes
  mail-send from content-upload by the parameter shape. The user-facing flow is §8.2.1.

### 8.2.1 Sending mail, and checking IDs

Both `SEND` and `ID` (§4.8's mail row) **open on the COURIER frame** — the client asset at
§A.10, displayed *before* anything is asked, so the user is in Courier before they start typing.
Its five slots are the five recipients.

**`SEND`** follows this sequence, verified from the C64 client (the prompt strings live at
`$AFDC`–`$B003`, the recipient loop at `$AEBA`):

1. **`SUBJECT?`** — up to **16** characters.
2. **`DESTINATION ID?`** — up to **five** IDs of **8** characters each. The original asks
   repeatedly, ending the list on an empty entry, and stops at five (`CMP #$05`).
3. **⚠ Each ID is validated before anything is sent, and the resolved NAME is shown.** The
   server accepts unknown recipients **silently**, so an unchecked typo becomes a message that is
   never delivered and never reported — the §8.3.2 silent-failure pattern again. A client
   **MUST** resolve every ID (`I`, §4.4) and **MUST NOT** proceed while any is unknown. The name
   is written beside the ID on the envelope, in the same colours as the `ID` screen (blue when
   found, black `*** NO SUCH USER ***` when not) — an ID alone does not tell the sender they have
   the right person, which is the whole reason to look it up.
4. **`OKAY?`** — confirm, with the completed envelope (sender, date, time, subject, recipients
   **and their names**) on screen to be checked.
5. **`SENDING`** — the composed frames go via the upload path (§8.3.2).

**The message body comes from the editor** (§8.4), not from a text box in the send dialogue:
`SEND` submits the editor buffer, and a client **SHOULD** bring the editor in front of the user
while sending (§4.10.2).

**⚠ An empty buffer MUST NOT block the flow.** Addressing a message before writing it is a
normal order of work, and the editor is where the writing happens — so a client **MUST NOT**
refuse `SEND` because nothing has been composed yet. Collect the subject and recipients, validate
them, then hand the user the editor and **keep the addressing** so a second `SEND` transmits
without asking again. The same applies to `UPLD` and its metadata (§8.3.2): fill the form first,
compose second, upload third. Refusing at step one forces the user to guess the client's
preferred order, which the original never imposed.

**⚠ `DONE` on the COURIER screen returns to the MAILBOX, not out of Courier.** The `SEND` and
`ID` screens are **client-side** sub-states — the frame is a client asset (§A.10) and an ID
lookup changes nothing on the server — so leaving them is a **local redraw**, not a wire command.
A client that issues `B` here unwinds one level too many and drops the user out of mail
altogether. This is the same stepwise model as §4.8's `DONE` note: COURIER screen → mailbox
listing → out of Courier, one step per command.

**⚠ `SEND` and `ID` use DIFFERENT frames.** `ID` uses §A.10 (title and five bare slots); `SEND`
uses **§A.11**, a larger frame carrying `FROM` / `DATE` / `TIME` / `SUBJECT` / `TO` above the same
five slots. They open identically — `COURIER` in red with an underline — so reusing the `ID`
frame for `SEND` looks right and silently drops the entire message header. A client **MUST**
render the `SEND` frame's fields: sender ID and **real name** (two lines), date, time, subject,
and the recipients.

**`ID`** is the lookup screen: prompt **`ID TO CHECK?`** (`$B0D9`), up to five IDs, then show each
one's real name against its slot. It is **not** a "who is online" command — there is no such
command (§4.7).

**⚠ `ID` results are a `PRESS ANY KEY` screen, not a command row.** There is nothing to choose,
only something to read, so the duckshoot is replaced by the prompt exactly as for a single-frame
page (§4.8). Any key returns to the **mailbox**.

**⚠ Result colours are normative:** the **ID** and a **found name** are **blue**; the not-found
marker **`*** NO SUCH USER ***`** is **black**. The colour is the signal — a failed lookup must
be distinguishable at a glance from a successful one, not merely by reading the text.

*(Layout: each ID is written from **column 3**, with the frame's `:` at **column 12** and the
name after it — §A.10.)*

### 8.2.2 Composing the message

Once the subject and recipients are accepted, the Compunet surface becomes a **message
composition** context with its own command row (§4.8):

```
  SEND  FINISH  LAST  NEXT  EDITR
```

- **`SEND`** adds the current editor frame to the message. The original transmits the message
  frame by frame, so this is issued **once per frame** — it is not "send the message".
- **`FINISH`** ends the message: the server delivers it and the user returns to the **mailbox**.
- **`LAST` / `NEXT`** page through the **editor's** frames, so the user can pick which to send.
- **`EDITR`** opens the editor to compose or correct a frame.

**⚠ The Compunet surface now shows the FRAME BEING SENT, not the envelope.** The screen becomes
essentially the editor's: `LAST`/`NEXT` page through the frames and `SEND` adds *the one on
screen*, so the user **MUST** be able to see which that is. Leaving the addressed envelope up
makes `SEND` a blind command — the user is choosing frames they cannot see.

**⚠ `SEND` and `FINISH` are two commands doing two jobs** — adding a frame, and completing the
message. Collapsing them into one "send" button loses the ability to build a multi-frame message,
which is the normal case for anything longer than a screen.

*(This is a **user-facing** requirement, not a wire one. Binding A transmits frame by frame, so
the two map onto the wire directly. Binding B's `mail.send` carries all the frames in one message,
so `SEND` appends to a pending list and `FINISH` emits the single call — the behaviour above is
preserved and only the transport differs, which is what a binding is for. VALIDATION.md, F32.)*

**There is always a frame to show.** The editor buffer holds **at least one page** — a blank one
when nothing has been composed or captured (§8.4) — so this context is reachable with an empty
editor and the user simply writes into the blank frame. A client **MUST NOT** require that
something be composed first (§8.2.1).

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

**The client MUST gather these fields from the user before sending `U` (normative).** A content
upload's `U` payload is not derivable from the frame alone — the client **MUST** prompt the user
for, and send, all of:

- the **title** (the 16-byte subject/title field);
- the **type** — **`T` for text frames** or **`P` for a program** — this is the type byte, and
  it also decides the step-2 transfer (a `T` streams §6 frames; a `P` sends the 8-byte header +
  raw file, §8.3.1). A client that always uploads as `T` cannot upload software;
- the **price** (the 6-byte `NNN.NN` field — `000.00` for free); and
- the **lifetime** in days.

An upload UI that omits the **type** or **price** prompt is incomplete: the type is mandatory to
the wire format and to what gets stored, and the price is the field the server keys the
mail-vs-content detection on (`.` in `rest[:8]`, above). Collect all four, then build the
payload.

**⚠ Collecting the four fields does not start the upload — it opens the upload sub-context
(normative).** Accepting them sends **nothing**; it puts the client in the **upload sub-context**
(§4.8), whose row is `SEND`, `LOAD`, `GET`, `FINISH`. `U` goes on the wire when the user issues
`SEND`, and **it carries the metadata every time** — steps 1 and 2 below run once *per frame*, not
once per upload. (Verified by live testing, 2026-05-14; recorded in `docs/PROTOCOL.md`, "Content
UPLOAD Flow". This is a difference from mail send, where the recipients are validated once.)

The four commands are §4.7's, with §4.7's meanings; what this section fixes is their *function
here*, so that a client meeting the row does not have to guess (the §4.7 closed-vocabulary rule
again):

| Command | Function in the upload sub-context |
|---|---|
| `SEND` | Send **one** frame: `U` + metadata, the validation reply, then the frame (steps 1–2), repeated per frame |
| `LOAD` | Read a page back from local storage into view (§4.7), for uploading material saved earlier |
| `GET` | Load editor frames from local storage (§8.4.1) — the same local facility the editor offers |
| `FINISH` | Complete the upload — step 3's `P`, which commits the page and returns the directory |

**⚠ `SEND` and `FINISH` are two commands doing two jobs**, exactly as in mail composition
(§8.2.2): one adds a frame, the other ends the exchange. A client that collapses them into a
single "upload" button has implemented a form, not this context — and has no way to send a
second frame. There is no command in the row to *abandon* the exchange: `ABORT` (§4.7) exists
for that, but the row is these four, so a client **SHOULD** offer abandonment through its host
environment (the reference client binds `Esc`) rather than adding a fifth word.

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

**A full directory silently discards the upload — so the client MUST check for room first
(normative).** This 11-entry limit is a **capacity rule for uploads**, not the 11-per-page
*display* limit of §7.6 — the two are independent and only coincidentally the same number. The
server gives **no error** when a directory is full (11 entries): the finish
`P` just returns the directory unchanged, with the new page missing. The client therefore
**MUST NOT** offer or begin an upload into a directory that already holds **11 entries** — it
**MUST** check the target's entry count (which it already has from the listing it is showing)
and, if full, refuse with a clear message ("this directory is full — 11 entries max") rather
than run an upload the server will throw away. Because a full directory swallows the page
without a signal, "the exchange completed" is **not** proof of success; the only positive
confirmation is the new entry appearing in the refreshed listing. (To add content anyway, the
user opens a **new sub-directory** with DIR and uploads into that — see below.)

**Creating a directory (the hierarchy).** A client cannot create a directory *directly* — the
**server** does, in response to the client's actions. There is no "make directory" command; a
new directory falls out of DIR + upload, both of which the server acts on:

1. **Open a latent directory with DIR.** While viewing a listing, the user highlights an entry
   and issues **DIR** (`P`+index, §4.7). DIR descends into the entry *as a directory*. If the
   entry has no sub-directory yet — its type is not `D` and carries no `+` (§7.4) — the server
   opens a **fresh, empty** sub-directory under it (permission permitting) and returns it as a
   normal directory response. At this point the directory is **latent**: it exists in the
   session but has not been persisted.
2. **Upload into it to make it real.** Running a content upload (steps 1–3 above) while
   navigated into that latent directory **materialises** it: the server persists the new
   sub-directory together with the uploaded page. A latent directory that never receives an
   upload is not retained.

So the directory tree grows organically: DIR into an entry and the server spawns an empty child;
upload into it and the server commits it. The client never writes the tree itself — it only
issues the DIR and upload commands that cause the server to do so. Creation therefore needs the
**same permission and space checks** as
any upload (you own/administer the parent, or it is open for uploads; the parent still has room
within its 11 entries). A client that offers upload **SHOULD** also expose DIR-on-any-entry so
the user can build the hierarchy; §7.4 covers the entry-type rule that makes this unambiguous.

**ACK the accept DAT before finishing (normative).** The per-frame `@`-accept is an ordinary
non-empty DAT (`40 00 …`), so the standard rule applies (§2.9): the client **MUST ACK it**
(echoing its seq) **before** sending the next packet. If the client sends the finishing `P`/`N`
*without* first ACKing the `@`-accept, the server is still waiting for that ACK and the finish
read times out — the upload silently fails. The same holds for the validation reply when it is
a DAT stream. Rule of thumb: on the upload path, ACK every server DAT (the validation reply and
each `@`-accept) before your next send.

A Tier 3 client that uploads **MUST** honour all of: the mail-vs-content detection (`.` in
`rest[:8]`), the EOS/no-EOS difference in the validation reply, the `@`-ack (not `A`) per
frame, **ACKing each `@`-accept DAT before the finish command**, the 8-byte big-endian header
for programs, and the correct finish command (`N` for mail, `P` for content). Any of these
wrong desynchronises the session.

## 8.4 Editor

The frame **editor** is a client feature, not a server command — recall from §4.4 that
there is no editor command byte (the `CMD_EDITR` constant is vestigial; `E` = LEAVE). The
editor lets the user compose one or more frames (PETSCII pages, §5–6) offline or online; the
composed frames are then submitted through the **upload** path (§8.3.2) — content upload for
Jungle pages, or mail send for Courier messages.

A client **MAY** implement editing in any way its environment allows; the only wire
requirement is that what it submits is a valid frame (§6) delivered via §8.3.2. The editor
is therefore Tier 3 by virtue of depending on uploads, but imposes no protocol of its own.

**The buffer is never empty.** It holds **at least one page** at all times — a blank one before
anything is composed or captured. `LAST` and `NEXT` clamp at the ends rather than running off
them (verified in the C64 client: both compare the current pointer against the buffer bounds and
return without moving), so there is always a current page to display and edit. A client
**SHOULD** therefore start the editor on a blank page rather than presenting an empty state.

*(Unverified detail: whether the original materialises that first blank page at editor
initialisation or on first use is not established from a static read of the client — the buffer
start pointer is a fixed address that the code never writes. Both readings give the same
user-visible behaviour, so this specifies the behaviour, not the mechanism.)*

**⚠ The editor works OFFLINE, and this is not optional.** It is a **local** application that
happens to be bundled with the terminal: on the original, `EDITOR` is one of the BASIC commands
the ROM installs (alongside `CONNECT`, `CNLOAD`, `CNSAVE` — see the parser table at `$8249`), so
a user could compose pages with the modem hung up and connect later only to upload them. That
was the point: composing online burned call charges.

A client therefore **MUST** make the editor reachable **without a session** — before login,
after logout, and while disconnected — and **MUST NOT** require connectivity for any of
`EDIT`, `LAST`, `NEXT`, `NEW`, `COPY`, `ERASE`, `GET`, `PUT`, `STORE`, `PRINT`, `FREE` or
`HELP` (§8.4.1). None of them touch the wire. Only the **submission** of the finished buffer —
`UPLD` (§8.3.2) or `SEND` (§8.2) — needs a session, and those are commands of the *directory*
and *mail* contexts, not of the editor.

### 8.4.2 Pages viewed on Compunet are stored in the editor

**Pages the user views are automatically added to the editor buffer as new pages** — this is
original behaviour, not a convenience. It is what makes the editor a *reading* tool as well as a
writing one: having read something online, the user can hang up and still have it, edit it, `PUT`
it to disk, or use it as the basis of their own page. Combined with offline working (above), it
is how the original kept call charges down.

A client implementing the editor **SHOULD** capture viewed frames into the buffer, subject to:

- **Capture must not disturb the user.** It happens while they may be editing something else, so
  it **MUST NOT** move the current page position, steal focus, or interrupt an edit in progress.
- **A full buffer must be reported.** The original's limit was **memory** — it held "10–15 pages
  simultaneously", a range because pages compress differently (§6.4). When a page cannot be
  stored the client **MUST** say so; silently dropping it is the §8.3.2 failure pattern again,
  where the user believes something was kept and it was not.
- **Directory listings are not frames** and are not captured; nor are client-side assets such as
  the help pages (§A.8, §A.9), which the user did not fetch.

**⚠ Capture is VERBATIM (normative).** A captured page **MUST** preserve everything that was on
screen: **per-cell colour**, **reverse video**, **graphics characters**, **both character sets**,
and the frame's border and background. The user is storing the page they read — not an
impression of it. A client **MUST NOT** capture into a reduced form and **MUST NOT** present a
degraded page as the captured one.

This is what dictates the **page model**: an editor page is a **40×24 cell grid**, exactly what a
frame is (§5, §6). The two are the same object, which is why capture is a copy rather than a
conversion, and why an edited page can be uploaded as a frame at all.

Two consequences worth stating, because both are easy to get wrong:

- **A page is the FULL 40×24.** A client **MUST NOT** reserve a row of the page for its own
  furniture — a status line, a page counter, a mode indicator. Doing so makes the editor unable
  to represent a frame it can display, so some captured pages cannot be held without loss.
  Buffer position ("page 2 of 5") belongs in the surrounding interface.
- **An unedited captured page SHOULD be re-uploaded as the bytes it arrived as**, not re-encoded
  from its grid. Re-encoding is *visually* faithful but need not be byte-identical (RLE choices,
  redundant control codes differ), and a page that is republished unchanged should be unchanged.
  Keep the original bytes with the page and drop them the moment it is edited — after an edit
  they no longer describe it.

> **⚠ Do not model a page as lines of text.** It is the obvious shortcut and it silently
> discards colour, reverse video and graphics. It also introduces a trap that survives casual
> inspection: converting a rendered frame back to text means inverting §5.3, where the two
> character sets map letters **differently**. In the **lowercase/mixed** set (`$0E`) screen codes
> `$01`–`$1A` are `a`–`z` and **capitals live at `$41`–`$5A`**; in the **uppercase/graphics** set
> (`$8E`), `$01`–`$1A` are `A`–`Z` and `$41`+ is graphics. Handle only `$01`–`$1A` and every
> capital on a mixed-case page becomes a **space** — `DIRECTORY` reads back as `IRECTORY`,
> `USER GUIDE` as `SER UIDE`. The result still looks like text, which is why it passes review.
> Storing cells avoids the conversion, and therefore the trap, entirely.

**⚠ Offline entry is a host-environment affordance, not a command row.** With no session there
is no Compunet screen, and therefore **no duckshoot** — the original sits at the **BASIC prompt**,
where `EDITOR` is one of the BASIC commands the ROM installs (`$8249`), typed like `CONNECT`. A
client **MUST NOT** manufacture a command row for the disconnected state to hold a lone `EDITR`:
that invents a context the original does not have, and (if the row is a duckshoot) produces a
one-word row, which §4.9 does not describe because it never occurs. Use whatever the host
environment offers — a menu item, a button, a command line. Once **inside** the editor, the
duckshoot returns with the editor's own row (§8.4.1).

`EDITR` in the **directory** and **mail** rows (§4.8) is the *in-session* route to the same
editor. Both routes are correct; they differ only in where the user is when they take them.

This has two consequences a client is likely to get wrong:

- **The buffer outlives the connection.** Composing, disconnecting, reconnecting and then
  uploading is a normal sequence, not an edge case; the buffer **MUST NOT** be cleared on
  disconnect. `RETURN` from an offline editor returns to the host environment (the original's
  BASIC prompt), not to a connection attempt.
- **`GET`/`PUT`/`STORE` are what make offline work useful.** They are local storage, so they
  **MUST** function with no session. A client that implements them as server-side storage has
  misread §8.4.1 and has broken offline use.

### 8.4.1 The editor command set (normative where the editor is offered)

Freedom over the *editing surface* is not freedom over the *command set*. A client that
presents an editor **MUST** offer the commands below, under these names, in this order —
they are §4.8's editor context, and §4.7's closed-vocabulary rule applies to them exactly as
it does everywhere else. What a client may choose is **how** they are invoked and what
"a page" looks like while being edited.

**⚠ Load-bearing: the order ends `FREE`, `RETURN`, `DOS`.** Verified from the C64 client's
string table at `$83AA` and its **offset table** at `$83FE` — the offsets are
`$00 $06 $0C $12 $18 $1E $24 $2A $30 $36 $3C $42 $4E $48`, and the last two are
**non-monotonic**: `$4E` (`RETURN`) precedes `$48` (`DOS`). That inversion is the proof this
table is a *display order* and not merely the order the strings happen to be stored in. Reading
the strings in storage order yields `… FREE DOS RETURN`, which is **wrong** — and is the error
this specification and `docs/PROTOCOL.md` both previously carried.

| # | Command | Function |
|---|---|---|
| 1 | `HELP` | Display the editor's help frame — a **client asset**, §A.9 (*not* the §A.8 frame) |
| 2 | `EDIT` | Enter edit mode on the current page |
| 3 | `LAST` | Go to the previous page in the editor buffer |
| 4 | `NEXT` | Go to the next page in the editor buffer |
| 5 | `NEW` | Create a fresh blank page |
| 6 | `COPY` | Duplicate the current page |
| 7 | `ERASE` | Delete the current page |
| 8 | `GET` | Load editor frames from local storage |
| 9 | `PUT` | Save the **current page** to local storage |
| 10 | `STORE` | Save the **entire buffer** to local storage |
| 11 | `PRINT` | Print the current frame |
| 12 | `FREE` | Report remaining editor space |
| 13 | `RETURN` | Leave the editor (to Compunet if online, to the host environment if not) |
| 14 | `DOS` | Local storage / filesystem commands |

**⚠ `PUT` and `STORE` are not synonyms** — one page versus the whole buffer. They are the
editor's instance of the §4.7 shared-encoding rule, and collapsing them ("both save") loses
behaviour the user can see. Likewise `NEW` (blank page) is not `COPY` (duplicate), and `ERASE`
removes a page rather than clearing one.

**The editor holds a multi-page buffer, not one page.** `LAST`/`NEXT`/`NEW`/`COPY`/`ERASE` only
mean anything against a buffer of pages with a current position, and `STORE` versus `PUT` only
differ because that buffer exists. A client offering a single text box has not implemented
this context — it has implemented an upload form (see §4.8, and the conformance item in
[CONFORMANCE.md](CONFORMANCE.md) §A).

### 8.4.3 Editing controls

The editor's **help frame** (§A.9) is not decoration — it is the specification of the editing
keys, and a client implementing the editor **SHOULD** provide all seven functions:

| Original key | Function |
|---|---|
| **STOP** | stop editing, **store the frame** |
| **RUN** (shifted STOP) | **restore** the frame to its stored state |
| **SHIFT-C=** | change case — switch which character set typed text enters |
| **f3 / f4** | delete / insert a line above the cursor |
| **f5** | auto-repeat on / off |
| **f6** | colour on / off — when off, typing changes the character but not the colour under it |
| **f7 / f8** | screen and border colour |

**⚠ The cursor BLINKS, and it blinks in colour as well as in reverse video (normative).**
A client offering the editor **MUST** show a blinking cursor, and it **MUST NOT** be possible for
that cursor to become invisible. The original guarantees this with **two** mechanisms, and both
are needed — implementing either alone leaves a cursor that vanishes:

1. **Per-tick, it alternates with the cell's own colour.** Each blink toggles reverse video on
   the character *and* chooses a colour: the client's current colour normally, but the **cell's
   existing colour** if the two are identical. Because the choice is written back, the test flips
   on the next tick, so the cursor oscillates between the two — a cursor that changes colour as
   it blinks is correct, not a bug.
2. **The drawing colour itself is derived from the background.** The client keeps its current
   colour contrasting with the screen background by table lookup, so the cursor can never take
   the background's colour. Where a client lets the user choose a drawing colour freely (as the
   editor does), it **MUST** apply this as a final guard: a cursor the same colour as the cell it
   sits on is invisible in **both** blink phases.

The reference contrast table, indexed by background colour 0–15 — each entry is black or white,
by luminance:

```
1 0 1 0 1 1 1 0 0 1 0 1 1 0 1 0
```

*(Provenance: the blink routine at `$87A0` in the C64 cartridge ROM — `EOR #$80` on the screen
code, then `LDX $0286 / EOR ($F3),Y / AND #$0F / BNE +` and, on equality, `LDX $C158`. The table
is at `$93A4`, read as `LDA $D021 / AND #$0F / TAX / LDA $93A4,X / STA $0286` at `$90A0`; the
same table colours the duckshoot row at `$938B`, which is why that row stays readable over any
frame. The blink period is a software delay loop around `GETIN`, so no exact interval is
specified — the reference client uses 300 ms a phase. Unverified: which polarity of the f6
colour flag at `$C15B` selects which alternate; both readings blink correctly.)*

**⚠ `STOP` stores and `RUN` restores — they are a pair.** Editing without a restore is editing
without an undo, on a page the user may have spent a long time on. `STOP` is what *makes* the
restore point, so a client that stops editing without storing leaves `RUN` with nothing to
return to.

**Mapping to a modern keyboard.** The C64 keys have no direct equivalents, so a client **MUST**
choose bindings; these are the reference client's, and are **RECOMMENDED** for consistency:

| C64 | Modern | Note |
|---|---|---|
| `C=` (Commodore) | **`Tab`** | the VICE convention — so `SHIFT`+`Tab` is *change case* |
| `RUN/STOP` | **`Esc`** | `Esc` = STOP; **`SHIFT`+`Esc`** = RUN, matching the shifted-key pairing on the original |
| `f3`–`f8` | the same function keys | |

**⚠ Both of those collide with common client bindings, and the collision resolves the same way
each time: the C64 mapping wins.** `Tab` is conventionally focus-switching and `Esc` conventionally
"cancel", but the editor's key assignments are **fixed by the original** while a client's own
gestures are free to move. In the reference client pane focus moved to `Ctrl`+`Tab`. Note that
`Esc` = STOP is not a deviation from "cancel" so much as a refinement: on the original it does
stop the edit — it also *stores*, which a plain cancel would not.

**Adaptation is expected, substitution is not.** `DOS`, `PRINT`, `GET`, `PUT` and `STORE` name
*local* facilities that differ per platform; a client **SHOULD** map them onto its own
equivalents (a file picker, the system print dialogue, browser download/upload) and **MAY**
disable any it genuinely cannot provide — a sandboxed web client has no `DOS`. What it
**MUST NOT** do is rename them, merge them, or invent replacements: a disabled `DOS` is
conforming, a `SAVE AS…` that replaces `PUT` and `STORE` is not.

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
  **⚠ Draw the chat surface in the lowercase/mixed set (`$0E`).** That range includes lower case,
  and the server uses it — `Users in partyline:-`, `Alias set to TESTER`. The uppercase/graphics
  set has no lower case at all, so rendering chat in it flattens everything to capitals and the
  who-listing reads as shouting. (VALIDATION.md, F33.)
- **C64 activation.** Selecting the link downloads a small chat program (the C64 loads it
  via the type-`L` `MODEM_INIT_DOWNLOAD` stream, §7.4) which then runs the raw session. Exit:
  the client sends `*quit<CR>`; the server broadcasts the leave and replies `*EXIT<CR>`; the
  client restores the screen and the session returns to the framed protocol.
- **Native activation.** A native (Amiga-classified) client is served the link differently
  (§3.3 gating): the server sends an **8-byte link header** `01 00 00 01 00 00 00 00` as a
  single DAT frame **with no EOS**. The client validates the first long == `0x01000001` and the
  second == `0`, then **MUST ACK that DAT** (§2.9, echoing its seq) — the server sends nothing
  further until it does. Only *after* the ACK does the server switch to the raw stream and send
  the preamble. Then a raw preamble handshake runs (server `01 01 01`; client replies `01`×6),
  the ASCII chat session runs, and teardown is three `$02` bytes from the server (client replies
  `$02`×6) after which the framed protocol resumes.

  > **Why the header seems to "hang".** Because the 8-byte header arrives with no EOS, it is a
  > single DAT that still expects its ACK like any other. A client that reads the 8 bytes and
  > waits for `01 01 01` **without ACKing first** will wait forever — the missing ACK, not a
  > protocol error, is why the preamble never comes.

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
  partyline` **and then, unprompted, pushes an initial who-style listing** of who is present
  (e.g. `Users in partyline:-` followed by one line per user, `{ID} ({alias}) {room}`). A
  client **MUST** simply render whatever lines the server pushes after activation as the opening
  scrollback — do **not** assume only the single join broadcast arrives, and do not send `*who`
  yourself to get it.
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

### 8.6.4 BUY vs SHOW — the price gate (client-side, normative)

`BUY` and `SHOW` send the **same wire bytes** (`D`+index) but are **not interchangeable to the
user**: the difference is a **client-side price check**, and a client that implements only one of
them gets the behaviour wrong. Both act on the highlighted entry's **PRICE** column (§7.3), which
the server leaves **empty** when the page is free *or* already purchased.

| Command | Price empty (free / already bought) | Price non-empty (paid, not yet bought) |
|---|---|---|
| `SHOW` | sends `D`+index, renders the page | **sends nothing** — the client refuses with `PLEASE USE BUY` |
| `BUY` | sends `D`+index, renders the page (nothing to confirm) | prompts **`BUY FOR {price} - SURE?`**; on **Y** sends `D`+index, on **N** sends nothing |

So a paid page can only be opened through **BUY**, and the confirmation is the user's one chance
to decline before being charged. On confirmation the **server** deducts the credit, marks the
page purchased, and returns the frame; the client does **not** check the balance locally and the
server **allows overdraft** (a negative balance, which `ACCOUNT` then reports as *in debit*).

The PRICE shown is cached in the current listing: it is not refreshed until the directory is
re-requested, so an entry just bought may still display its price until the next listing.

A client **MUST** implement both commands with this gate. Offering only `SHOW` makes paid content
unreachable; offering only `BUY`, or letting `SHOW` open paid pages, charges the user without the
confirmation the original always gave them.

> **⚠ The server will charge without asking — the gate is the client's job and nothing else's.**
> Measured: opening a £1.50 page took the credit from 97.50 to 96.00 with no prompt and no error,
> and re-reading it was then free. There is **no server-side confirmation step to fall back on**,
> and nothing in a directory response marks an entry as paid except an ordinary string in the
> PRICE column — which a client must locate **by name** in `columns`, not by a fixed index, since
> the column set differs per listing (§7.2). This is the most consequential client-side rule in
> the specification, and the one a binding cannot help you with. (VALIDATION.md, F12.)

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
