# §4 — Command protocol

**Layer — application model** (shared across bindings, §1.8). The command *semantics* (what each command does, response types, ack conventions) are reused by every binding; the single-letter byte encoding is Binding-A-specific.

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority: `CompunetSession.handle_command` and the `_cmd_*` handlers in
> `server/compunet_server.py`. The command table below is taken from the server's dispatch
> — the definitive list of what the server acts on.

Once online (§3.6), a client drives the service by issuing **commands**. This section
defines how a command is encoded, how the response is delivered, and the full command set.

## 4.1 Command encoding

A command is sent as a **COM (`$43`) packet** (§2) whose payload is:

| Payload offset | Field | Description |
|---|---|---|
| 0 | command byte | A single ASCII letter (see §4.4) |
| 1… | argument | Optional. Plain ASCII text, zero or more bytes |

The argument, when present, is plain ASCII text. For the **numeric** commands it is a
**decimal number written as ASCII digits** (not a binary integer) — e.g. "show page 7" is the
three bytes `P 0 7` (`$50 $30 $37`), and "select directory entry 3" is `D 0 3`. One command
takes **text, not digits**: `GOTO` (`L`, §4.4) accepts either a page number *or* a keyword
(e.g. `L JUNGLE`), matched **case-insensitively**; a client **MUST** send the keyword as raw
ASCII, un-padded. A command with no argument is just the single command byte.

The login packet (§3.5) is the special first command `Z`; all subsequent commands use the
table in §4.4.

## 4.2 Response delivery

The server replies to a command with a **DAT (`$22`) stream** (§2): zero or more DAT
packets carrying the response bytes, each ACK-paced per §2.9, followed by a zero-length
**EOS** packet that marks the end of the response — **except** for a bare acknowledgement
response (§4.3), which is a **single DAT packet with no EOS**.

A client **MUST**:

- ACK each non-empty DAT packet (§2.9);
- treat the zero-length EOS packet as "response complete" and **not** ACK it;
- for a bare-acknowledgement response, accept the single packet as complete without
  waiting for an EOS.

Responses are chunked by the server at 100 payload bytes per packet; a client **MUST NOT**
assume any particular chunk boundary and **MUST** reassemble the stream by concatenating
payloads until EOS.

## 4.3 Response types and the ack convention

Every response has a **type**, which tells the client how to interpret the bytes:

| Type | Byte | Meaning | Delivery |
|---|---|---|---|
| **ACK** | `A` (`$41`) | Bare acknowledgement / proceed — the command succeeded, no content follows | single DAT packet, no EOS |
| **DIR** | `D` (`$44`) | Directory listing (§7) | DAT stream + EOS |
| **FRAME** | `F` (`$46`) | Frame / page content (§6) | DAT stream + EOS |
| **ERROR** | `E` (`$45`) | Error; the payload is a renderable message frame | DAT stream + EOS |
| **LINKING** | `L` (`$4C`) | Terminal (re)link required | (ROM path; see §3.6) |

On the wire there is **no in-band type marker** — nothing in the DAT stream tells the client
whether the bytes are a frame or a directory. The client determines the type from the
command it issued and its current mode; this is specified in §4.5. The EOS convention
distinguishes an ACK (single packet, no EOS) from a streamed DIR/FRAME/ERROR (stream + EOS).

**The single-byte `@` ack (native clients).** A native client that reads a leading
one-byte acknowledgement before a response expects `@` (`$40`) to mean "OK / proceed". For
the two commands whose response could begin with a byte that collides with an ack
character (`I` (ID lookup, §8.6-adjacent) and mail-send, §8.3.2), the server prepends `@`
(`$40`) to the response. This prefix is applied to **every native (Amiga-classified) session**
(§3.3) — the C64/ROM stream is unchanged, because the ROM keys off the DAT token rather than a
leading ack byte.

Because a native-identified client (the recommended path, §3.3) **always** receives this
prefix on `I` and mail-send replies, it **MUST** account for it — either by consuming a leading
one-byte ack before reading the body, **or** by **stripping a single leading `@` (`$40`) byte**
from the response before parsing. Forgetting to strip it shifts every field by one byte (e.g.
an `ID` lookup returns `@ADMIN…` and the records parse wrong), and the first record still looks
plausible, so the bug is easy to miss.

*(Non-normative — status bytes. The original ROM treats a non-`@` status byte such as `A`
(`$41`) or `B` (`$42`) arriving in place of frame data as an error/status indication and
shows a status message — e.g. `A` maps to a "Host error" message. The exact status-text
mapping is a client concern and is not required to interoperate.)*

## 4.4 Command set

The commands the server dispatches. Command bytes are ASCII letters; the "Arg" column
notes the ASCII-decimal argument where one is used. "Typical response type" is indicative
(§4.3) — `D` and `P` each carry two commands, distinguished by whether an index argument is
present: `D`+index = SHOW / `D` alone = MORE; `P`+index = DIR / `P` alone = FINISH (§4.7).

| Cmd | Byte | Name | Arg | Meaning | Typical response |
|---|---|---|---|---|---|
| `D` | `$44` | SHOW / MORE | entry index (2 digits) | With an index = **SHOW**: display the highlighted entry's text **frame(s)** (or, for a program/link entry, download/activate it — "BUY"). **Never enters a directory** — use DIR for that. With no argument = **MORE**: advance to the next frame; past the last frame, page the directory | FRAME / download |
| `P` | `$50` | DIR / FINISH | entry index (2 digits) | With an index = **DIR**: enter the highlighted entry **as a directory**. If the entry has no sub-directory yet, this opens an **empty** one (permission permitting), which becomes real once something is uploaded into it — this is how directories are created (§8.3.2). With no argument = **FINISH**: leave the frame currently being viewed and return to its directory (only meaningful while viewing a frame) | DIR |
| `N` | `$4E` | MORE | — | Advance to the next frame of the item being read (or the continuation step in an upload, §8). At the last frame it returns a bare **ACK** (`$41`), **not** the directory — see §4.5 | FRAME / ACK |
| `B` | `$42` | BACK | — | Go to the parent directory | DIR |
| `L` | `$4C` | GOTO | keyword/page | Jump to a page by keyword or number. The reply is **always a directory** (never the target's own frame, §4.5): for a **leaf** target (a text/program page) the server returns the directory *containing* it, with the target as an entry within it; for a **directory-typed** target it returns that directory **opened as a listing** (its own children). Either way the client parses the reply as a §7 directory and takes the breadcrumb/selection from the response — it must **not** compute "the parent" locally | DIR |
| `A` | `$41` | ACCOUNT | — | Returns the account **credit balance** as a fixed **10-byte ASCII** string (e.g. `999.00␣␣␣␣`), left-justified and space-padded; a leading `-` marks a debit. **Not** a §6 frame — the client formats it (e.g. "YOU ARE {value} IN CREDIT/DEBIT") | 10-byte text |
| `I` | `$49` | ID lookup | one or more 8-byte user IDs | Look up user IDs; returns per-ID `id` + real name (if known) + `$1E`. With no argument it returns **nothing** (see note). Not "who is online" — that is a content page, not this command | lookup stream |
| `C` | `$43` | UCAT | — | User catalogue | DIR |
| `M` | `$4D` | MAIL | — | Enter mail (Courier); see §8.2 | DIR |
| `V` | `$56` | VOTE | index + score | Vote on the highlighted directory entry — 2-digit index + 1-digit score 1–9 (§8.6) | ACK |
| `X` | `$58` | LIFE | index + amount | **Extend the life** of the highlighted entry's content — 2-digit index + extension amount (§8.6). **Not** BUY | ACK |
| `U` | `$55` | UPLOAD | params | Begin an upload (content or mail); see §8.3 | ACK |
| `E` | `$45` | LEAVE | — | Log off; the server sends a final frame then closes (§3.8) | FRAME |
| `Z` | `$5A` | LOGIN | credentials | The login packet (§3.5) — only valid as the first command | FRAME |

> **Resolved discrepancy.** The server source defines a constant `CMD_EDITR = $45` ('E'),
> but the dispatch actually maps `'E'` to **LEAVE**, not an editor command. The dispatch is
> authoritative: in Reborn, `'E'` = LEAVE. There is **no** server-side editor command — the
> off-line/on-line editor is a client feature that submits its result through the upload
> commands (`U`/`N`), specified in [§8.4](08-subsystems.md). A client **MUST NOT** expect an
> editor command byte; the `CMD_EDITR` constant is vestigial.

An unknown command byte yields an `UNKNOWN COMMAND` error response; an empty command
payload yields `NO COMMAND`. A client **SHOULD** only send bytes from the table above.

Note that some commands can legitimately produce **no response at all** — e.g. `I` (ID
lookup) with no arguments, or a lookup that matches nothing, returns zero bytes and the
server sends nothing. A client **MUST** therefore read responses with a timeout and treat a
timed-out read as "no response" rather than blocking forever.

The single-letter set is identical across the C64 and Amiga reference clients (both send
these bytes in COM `$43` frames and both use the `@` ack convention), which is what makes
one server drive both — see the appendix (§A) for the consolidated table alongside the
token table.

## 4.5 Determining the response type

Because the DAT stream carries no type marker (§4.3), a client **MUST** decide how to parse
a response from **the command it just issued and its current mode** — not by inspecting the
response bytes. Choosing the wrong parser corrupts state: e.g. the reference clients' GOTO
handler *always* parses its response as a directory, and feeding it frame data will crash
the client. The rule:

| Command issued | Current mode | Expect | Parse as |
|---|---|---|---|
| `P` + index (DIR), `P` no-arg (FINISH), `B` (back), `M` (mail), `C` (ucat), `L` (goto) | any | directory | 6-part directory (§7) |
| `E` (leave) | any | frame | frame (§6) |
| `A` (account) | any | 10-byte text | fixed 10-byte credit string (§4.4) — not a §6 frame, but delivered as a **normal DAT stream + EOS** (not a bare ACK); read it with the ordinary stream reader |
| `I` (ID lookup) | any | lookup stream | `id`+name+`$1E` per requested ID (§4.4) — not a 6-part directory |
| `N` (more) | viewing a frame | frame **or** bare ACK | next frame (§6); at the last frame, a bare ACK `$41` (single packet, no EOS) — **not** the directory |
| `D` no-arg (MORE) | viewing a frame | frame **or** directory | next frame (§6); past the last frame, the 6-part directory (§7) |
| `V`, `X`, `U` | any | acknowledgement | bare ACK (single packet, no EOS) |
| `D` + index (SHOW / BUY) | in a directory | the selected entry's **base type** (§7.4): `T`→frame; `P`/`PP`/`S`→download (§8.3.1); `L`→link (§8.5). To **enter** a directory-type entry, use DIR (`P`+index), not this | frame / download / link |

**Paging a multi-frame item: prefer `D` (no argument) over `N`.** Both advance to the next
frame, but they differ at the end: `D` (no arg) returns to the directory after the last
frame, whereas `N` returns a bare `$41` ACK and leaves the client sitting on the last page.
A browse client **SHOULD** page with `D` (no arg). And crucially, a client **MUST NOT** infer
"more frames are coming" from a frame's bit-7 flag alone (§6.5): a `+`-modified entry's splash
frame sets bit 7 yet has no further frames (its extra content is a sub-directory, reached by
navigation, not paging), so `N`/`D` on it return an ACK / the directory immediately. Drive
paging from the **actual response** (a frame vs. an ACK/directory), not from the flag.

`D` and `P` each mean two things depending on whether an index is present (§4.7): `D`+index =
**SHOW** (parse per the selected entry's base type below), `D` no-arg = **MORE**; `P`+index =
**DIR** → a directory, `P` no-arg = **FINISH** → a directory. So a client that tracks whether
it is viewing a directory or a frame, and whether it is sending an index, knows the parser
before the bytes arrive. For `D`+index (SHOW/BUY) it **MUST** use the selected entry's base
type to pick between frame / download / link — that type is not delivered separately; the
client reads it from characters 24–26 of the entry's first field (screen column 25, §7.3/§7.4),
so it **MUST** retain each listed entry's type when it parses a directory. Everything else is
determined by the command byte alone. The ERROR type (§4.3) is delivered as a frame and can be
rendered by the frame parser, so a client **MAY** treat an unexpected frame where it expected a
directory as an error message rather than crashing.

**Exception — `D` (no arg) and `N` require inspecting the response.** For these two, the
command + mode genuinely does *not* determine the outcome (the same `D`-no-arg reply is a
frame while pages remain, or a directory at the end; `N` gives a frame or a bare ACK). Here a
client **MUST** distinguish by the response's **structure**, which is unambiguous:

- a **bare ACK** is a single DAT packet carrying one payload byte, with **no EOS** following;
- a **frame** is a DAT stream + EOS whose reassembled body is a §6 frame (it may end in `$00`,
  or simply at EOS, §6.1);
- a **directory** is a DAT stream + EOS whose body is the six-part structure of §7.

This is the one place inspecting the bytes is required; everywhere else the command + mode
rule above suffices.

## 4.6 Command invocation (conformance)

Rendering content is not enough — a conforming client **MUST** provide the user a means to
**invoke** every command applicable to its conformance tier (§1.4). A client that displays
frames and directories but offers no way to issue commands does not conform: the user could
never navigate, read mail, or leave.

This specification does **not** mandate *how* commands are surfaced — that is a client-UX
choice and is explicitly non-normative. Any of the following (or others) is acceptable, as
long as the user can reach the applicable commands:

- keyboard shortcuts (e.g. a key per command);
- an on-screen menu, button bar, or command palette;
- the original Compunet **"duckshoot"** — a horizontally-scrolling row of command words at
  the foot of the screen (this is the reference user experience, reproduced by the C64 and
  Amiga clients; a client **MAY** emulate it but is not required to). A client that *does*
  reproduce it **SHOULD** follow the original's look and behaviour: the command words are
  **white text on a black background**; the user scrolls the row **left and right**; the
  **currently-selected command stays in the centre** of the row; and that centred selection is
  drawn **inverse** (black text on a white background). The user commits the centred command
  to invoke it.

Concretely, the minimum obligations by tier are:

- **Tier 1 (Browse):** the user **MUST** be able to invoke directory navigation and frame
  viewing — at least SHOW (`D`+index), DIR (`P`+index), BACK (`B`), MORE (`D` no-arg / `N`),
  FINISH (`P` no-arg), GOTO (`L`), ACCOUNT (`A`), and LEAVE (`E`). Highlighting a directory
  entry (§7.7) and issuing SHOW or DIR on it satisfies the entry-selection requirement.
- **Tier 2 (Interact):** additionally the commands for the subsystems it implements — e.g.
  `M` (mail), `C` (UCAT), `I` (who), `V` (vote), `X` (LIFE / extend).
- **Tier 3 (Full):** additionally `U` (upload) and the editor / Partyline entry points.

A command the client's tier does not implement need not be offered. The command byte and
wire exchange for each are defined in §4.4 and §8; this section only requires that a user
can trigger them.

**Prefer one command surface, and make it context-appropriate.** Surfacing *how* is the
client's choice, but a client **SHOULD** present a **single** primary command surface rather
than two competing full command bars (e.g. a duckshoot *and* a separate button row that both
list the same commands) — two parallel menus of commands are confusing and make it unclear which
is authoritative. Pick one primary surface (a duckshoot, or a button/menu bar) and, if a second
affordance is offered, keep it clearly secondary (e.g. keyboard shortcuts, or click-to-select on
entry rows) rather than a duplicate command menu. Whichever surface is used **MUST** show the
commands **appropriate to the current context** — never a fixed list that offers inapplicable
commands or omits reachable ones. **§4.8 is the authoritative table of which commands belong to
which context.**

## 4.7 Standard command vocabulary

When a client surfaces commands to the user, it **SHOULD** use the original Compunet command
names below rather than inventing its own, so the experience is recognisable across clients.
These are the words the original "duckshoot" presented; they map onto the wire commands of
§4.4. (The *how* — buttons, menu, scrolling duckshoot — remains the client's choice, §4.6;
this table standardises the *names*, not the interface.)

**While viewing a directory** (these act on the client's locally-highlighted entry, §4.5):

| Name | User action | Wire command |
|---|---|---|
| `SHOW` | Show the highlighted entry's **text frame(s)** — never enters a directory | `D` + index |
| `DIR` | **Enter** the highlighted entry *as a directory* (opens an empty one if it has none — directory creation, §8.3.2/§7.4) | `P` + index |
| `BACK` | Go to the parent directory | `B` |
| `GOTO` | Jump to a page by number or keyword | `L` + arg |
| `ACCNT` | Show the account / personal-information page | `A` |
| `MAIL` | Enter Courier (mailbox) | `M` |
| `UCAT` | User catalogue | `C` |
| `VOTE` | Vote on the highlighted entry | `V` + index + score |
| `LIFE` | Extend the highlighted entry's life | `X` + index + amount |
| `BUY` | Download / activate / **pay for** the highlighted entry — same bytes as `SHOW`, but `BUY` confirms the price and `SHOW` refuses paid pages (**§8.6.4**) | `D` + index (no separate byte) |
| `UPLD` | Upload into the current directory | `U` (§8.3.2) |
| `LEAVE` | Log off | `E` |
| `EDITR`, `HELP`, `PRINT`, `SAVE` | Editor / help / print / save | client-side (no wire command) |

**While reading a page (frame)** (these apply *only* while a frame is on screen):

| Name | User action | Wire command |
|---|---|---|
| `MORE` | Show the next page of a multi-frame item | `D` (no arg) / `N` |
| `FINISH` | Return to the directory | `P` (no arg) |

> **`D` and `P`, with or without an index — four distinct actions.** The presence of the
> entry index distinguishes each pair:
>
> | Byte | + index | no index |
> |---|---|---|
> | `D` | **SHOW** — show the highlighted entry's text frames | **MORE** — next frame |
> | `P` | **DIR** — enter the highlighted entry as a directory | **FINISH** — return to the directory |
>
> **DIR and SHOW are different commands, not one.** `SHOW` (`D`+index) *only* shows the entry's
> text frames and never enters a directory; `DIR` (`P`+index) enters the entry as a directory.
> On a `T+` entry, SHOW reads its pages while DIR goes into its sub-directory — two actions on
> the same entry. A client **MUST NOT** collapse them onto one byte, and **SHOULD NOT** invent a
> non-Compunet label like "OPEN".
>
> **Context.** SHOW / DIR and the other directory commands apply while a **directory** is
> displayed; MORE / FINISH apply *only* while a **frame** is displayed (there is no "finish" in
> a directory). Selection is client-local (§4.5): the client sends the highlighted entry's index
> with `D`/`P`; `FINISH` and `MORE` carry no index because there is no selection while reading.
>
> **FINISH returns the *current* directory, not "home".** `P` no-arg drops out of the frame
> back to the directory you were in when you opened it — which, right after login, is the root
> (so a bare `P` on the welcome frame reaches the top directory). It is **not** a jump-to-root:
> issued from within a sub-directory it returns *that* directory. To move **up** the hierarchy,
> use `B` (BACK), which returns the parent; repeated `B` ascends to the root. (`GOTO`/`L` jumps
> to a page by keyword/number, but does not "go home" either.)

**The welcome frame is an entry point — surface `DIR` there.** After login the client is showing
the **welcome frame** (§3.5), but this is *not* an ordinary "reading a page" context: it is the
gateway into the system, and the original client shows the **directory** command set here — most
importantly **`DIR`**, which enters the **top directory**. A client **MUST** surface `DIR` on the
welcome screen (alongside `GOTO`, `ACCNT`, `MAIL`, `LEAVE`); offering only `MORE`/`FINISH` there
is wrong — the user is left with no visible way into Compunet. Because no entry is highlighted
yet, `DIR` on the welcome frame carries **no index** and goes on the wire as a **bare `P`**,
which the server answers with the current directory — the root (this is the "terminal entry"
`P` that also serves FINISH; the two coincide here). Once inside a directory, `DIR` reverts to
its normal `P`+index meaning (enter the highlighted entry).

## 4.8 Command availability by context (normative)

The command set a client offers **MUST** change with what is on screen. The original client did
not present one fixed list: it swapped the duckshoot per context, so the user only ever saw
commands that made sense. A client that shows every command everywhere will offer `MORE` on a
directory and `VOTE` in a chat window, both meaningless.

This table consolidates the contexts and is the authority for *when* each command is offered;
§4.7 remains the authority for their names and wire mapping.

| Context | Commands to offer | Notes |
|---|---|---|
| **Welcome frame** (just logged in, §3.5) | `DIR`, `GOTO`, `ACCNT`, `MAIL`, `UCAT`, `LEAVE` | The entry point. `DIR` is **required** here (§4.7) — without it the user cannot reach the system. Not a "reading" context: do **not** offer `MORE`/`FINISH` |
| **Directory listing** | `HELP`, `DIR`, `SHOW`, `BACK`, `GOTO`, `UCAT`, `MAIL`, `ACCNT`, `SAVE`, `EDITR`, `LEAVE`, `PRINT`, `LIFE`, `BUY`, `LOAD`, `UPLD`, `VOTE` — **`BUY` is required alongside `SHOW`**, not redundant with it (§8.6.4) | The full working set, **in the original's display order** (see note below). Commands acting on a highlighted entry (`SHOW`, `DIR`, `VOTE`, `LIFE`, `BUY`) require a selection — see below |
| **Reading a frame** | `MORE`, `FINISH` (+ `ALL` if implemented) | **Only** these. There is no `FINISH` in a directory and no `MORE` in one (§4.7) |
| **Mail (Courier, §8.2)** — listing and message | `DIR`, `SEND`, `SHOW`, `MORE`, `ID`, `EDITR`, `DONE` | A **distinct**, verified set (the mail menu has its own table). Content commands — `VOTE`, `UPLD`, `BUY`, `BACK`, `GOTO` — do **not** apply. `DIR`/`DONE` leave mail — **on the wire that is `B` (BACK)**, which is what clears mail mode (`N`/MORE also does when it runs past the last message); `SHOW` reads the highlighted message and `MORE` pages it |
| **Upload / send** (§8.3.2) | `SEND`, `LOAD`, `GET`, `FINISH` | The original entered an upload sub-context with its own set |
| **Editor** (§8.4) | `HELP`, `EDIT`, `LAST`, `NEXT`, `NEW`, `COPY`, `ERASE`, `GET`, `PUT`, `STORE`, `PRINT`, `FREE`, `DOS`, `RETURN` | Entirely client-side (no wire commands); `RETURN` leaves the editor |
| **Partyline** (§8.5) | None of the above — the `*`-commands (`*help`, `*who`, `*enter`, `*dice`, `*call`, `*quit`…) and free text | While in Partyline the client is in a **chat** context. Normal commands resume only after leaving |

*(Provenance: decoded from the C64 client source — the 6-byte command-name table at `L_A176`,
the directory duckshoot configuration at `L_A21E` (a count byte followed by string offsets in
display order), and the mail menu's own offset table at `L_AE15`. Recorded in
`docs/PROTOCOL.md`, whose earlier mail and directory lists were wrong and have been corrected
from these bytes.)*

**The original shortened the list by lowering a count.** `L_A21E` begins with a count byte that
the client rewrites at runtime, dropping commands from the **end** of the directory order above.
So that order is a **priority order**: a client with less room (or a narrower context) should
drop from the end — `VOTE`, `UPLD`, `LOAD` first — rather than pick arbitrarily.

**Selection-dependent commands.** `SHOW`, `DIR`, `VOTE`, `LIFE` and `BUY` act on the
**highlighted entry** (§4.5). When no entry is highlighted — an empty directory, or a listing
whose only row is the `(EMPTY)` placeholder (§7.3) — a client **SHOULD** disable them rather than
send a command with no valid index. `DIR` on the welcome frame is the documented exception: it
carries no index by design.

**Disable rather than hide (recommended).** Where the interface allows it, a client **SHOULD**
show inapplicable commands as *unavailable* rather than removing them, so the command set does
not appear to change shape as the user moves around — the original's duckshoot kept a stable row
of words and simply offered a different set per context. Either is conforming; what is **not**
conforming is offering a command that cannot work in the current context.

This is **shared model**, not Binding-A detail: a Binding-B client faces exactly the same
contexts (its `partyline.*` and editor flows included) and **MUST** apply the same rules.
