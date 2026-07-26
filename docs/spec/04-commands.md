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
- the original Compunet **"duckshoot"** — a horizontally-scrolling row of command words at the
  foot of the screen. This is the reference user experience, reproduced by the C64 and Amiga
  clients. A client **MAY** emulate it but is not required to; one that **does** **MUST** follow
  **§4.9**, which defines it.

**⚠ Commands that need input must still work.** `GOTO`, `VOTE`, `LIFE`, `ID`, `BUY`'s
confirmation and the upload/mail prompts all take a value from the user. Whatever a client uses
to collect it **MUST** actually function on every platform it ships to — a command that silently
does nothing is indistinguishable, to the user, from one that is missing. *(Known trap: Electron
does **not** implement `window.prompt()` / `window.confirm()` — they throw. A web client that
uses them works in a browser and quietly loses five commands when packaged as a desktop app.)*

Concretely, the minimum obligations by tier are:

- **Tier 1 (Browse):** the user **MUST** be able to invoke directory navigation and frame
  viewing — at least SHOW (`D`+index), DIR (`P`+index), BACK (`B`), MORE (`D` no-arg / `N`),
  FINISH (`P` no-arg), GOTO (`L`), ACCOUNT (`A`), and LEAVE (`E`). Highlighting a directory
  entry (§7.7) and issuing SHOW or DIR on it satisfies the entry-selection requirement.
- **Tier 2 (Interact):** additionally the commands for the subsystems it implements — e.g.
  `M` (mail), `C` (UCAT), `I` (**ID** lookup — the command is named `ID`, and only in mail;
  there is no "WHO" command), `V` (vote), `X` (LIFE / extend).
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
which context.** (A client showing several contexts at once gives **each** its own surface —
that is one surface *per context*, not two competing surfaces for one; see **§4.10**.)

## 4.7 Standard command vocabulary

When a client surfaces commands to the user, it **MUST** use the original Compunet command names
below. These are the words the original "duckshoot" presented; they map onto the wire commands of
§4.4. (The *how* — buttons, menu, scrolling duckshoot — remains the client's choice, §4.6; this
table standardises the *names*, not the interface.)

> ### ⚠ The command vocabulary is CLOSED (normative)
>
> This set is **exhaustive and authored**. A client **MUST NOT**:
> - **add** a command of its own (however convenient — no "JOIN", "HOME", "REFRESH");
> - **remove** one because it looks redundant (see the warning below);
> - **merge** two that share a wire encoding, or **rename** one to something clearer.
>
> **Why this rule exists.** Two commands can send *identical bytes* and still be different
> commands, because the difference is client-side behaviour (`BUY` vs `SHOW`, §8.6.4). And an
> invented command has no counterpart in Binding A, which breaks the §1.8 invariant that every
> binding projects the *same* model. Both mistakes produce a client that **works**, so nothing
> catches them: no error, no crash, no failing test. They are only ever caught by someone who
> knows the original.
>
> If a command looks redundant or missing, the spec is more likely to be under-explained than
> wrong — check §8 for its behaviour before concluding it is either.
>
> **⚠ "Closed" obliges this section to define every command it closes over.** A vocabulary that
> forbids invention while leaving names undefined forces exactly the invention it prohibits: the
> implementer meets the name in §4.8 or §4.9.3, finds nothing here, and has to guess. `ALL`,
> `LOAD` and `ABORT` were in that state — they had duckshoot cells and context rows but no
> definition — and a clean-room build duly invented all three (VALIDATION.md, F29). If you add a
> command anywhere in this document, it belongs in the tables **here** first.
>
> **This includes the editor's vocabulary.** The editor (§8.4) has no wire commands at all, which
> makes it tempting to treat its command set as a free choice of UI. It is not: its fourteen
> names are listed in §4.8 and defined in **§8.4.1**, and every rule above applies to them —
> `PUT` and `STORE` are the editor's `SHOW`/`BUY` (§8.4.1). A client **MAY** map them onto its
> platform's facilities or disable ones it cannot provide; it **MUST NOT** rename or merge them.

> ### ⚠ Where two commands share a wire encoding (normative)
>
> Whenever the same bytes serve more than one user-facing command, this specification **MUST**
> state what distinguishes them at the client, and a client **MUST** implement that distinction.
> The cases:
>
> | Same bytes | Commands | What separates them |
> |---|---|---|
> | `D` + index | `SHOW`, `BUY` | the **price gate** — `SHOW` refuses a paid page, `BUY` confirms the charge (§8.6.4) |
> | `D` no-arg | `MORE` | (also reached by `N`; see §4.5) |
> | `P` + index / no-arg | `DIR` / `FINISH` | the presence of the entry index (§4.7 table above) |
>
> A client that collapses any of these pairs loses behaviour the user can see.

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
| `EDITR` | Enter the frame editor (§8.4) | client-side (no wire command) |
| `PRINT` | Print the page on screen | client-side (no wire command) |
| `SAVE` | Write the **page on screen** to local storage | client-side (no wire command) — distinct from the editor's `PUT` (one *editor* page) and `STORE` (the whole buffer), §8.4.1 |
| `LOAD` | Read a page **back** from local storage into view — `SAVE`'s inverse | client-side (no wire command) |
| `HELP` | Show the help page | client-side (no wire command) — but **not a no-op**: it displays an embedded help **frame** the client must carry (§A.8) |

**While reading a page (frame)** (these apply *only* while a frame is on screen):

| Name | User action | Wire command |
|---|---|---|
| `MORE` | Show the next page of a multi-frame item | `D` (no arg) / `N` |
| `ALL` | Read the **rest** of a multi-frame item without pressing `MORE` for each — repeat the paging command until the reply stops being a frame | repeated `D` (no arg) |
| `ABORT` | Abandon an exchange in progress (an upload, §8.3.2) and return without sending | context-dependent; see §8.3.2 |
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
| **Welcome frame** (just logged in, §3.5) | the **same row as a directory** (below) | The welcome screen is not a "reading" context: it carries the directory row, with **`HELP` — the first command — centred by default**. `DIR` must therefore be reachable here (§4.7); `MORE`/`FINISH` are **not** offered |
| **Directory listing** | `HELP`, `DIR`, `SHOW`, `BACK`, `GOTO`, `UCAT`, `MAIL`, `ACCNT`, `SAVE`, `EDITR`, `LEAVE` | The row the original presents, **in its display order**, with `HELP` centred by default. The remaining commands of §4.7 (`PRINT`, `LIFE`, `BUY`, `LOAD`, `UPLD`, `VOTE`) exist and are reachable, but sit **beyond the displayed count** — see §4.9.4. Commands acting on a highlighted entry (`SHOW`, `DIR`, `VOTE`, `LIFE`, `BUY`) require a selection |
| **Reading a single-frame page** | **none — no duckshoot at all** | The row is replaced by the prompt **`PRESS ANY KEY`**. There is nothing to page and nothing to choose, so no commands are offered. Any key returns to whatever was on screen before — which is how `HELP` (§A.8) gets back, since `FINISH` is not offered here |
| **Reading a multi-frame page** | `MORE`, `ALL`, `FINISH` — in that order | **Only** these. There is no `FINISH` in a directory and no `MORE` in one (§4.7) |
| **Mail (Courier, §8.2)** — listing and message | `SEND`, `SHOW`, `MORE`, `ID`, `EDITR`, `DONE` | A **distinct**, verified set (the mail menu has its own table). Content commands — `VOTE`, `UPLD`, `BUY`, `BACK`, `GOTO` — do **not** apply. `SHOW` reads the highlighted message. **`MORE` is context-sensitive**: reading a message it pages the message (`D`), and in the listing it pages the **mailbox** (`M`) — see §8.2. **`DONE` returns the user to where they were before entering Courier** — see the note below |
| **Mail composition** (§8.2.2) | `SEND`, `FINISH`, `LAST`, `NEXT`, `EDITR` | Reached once `SEND`'s subject and recipients are accepted. `SEND` adds **one** editor frame to the message, `FINISH` completes and delivers it — two commands, two jobs. `LAST`/`NEXT` page the editor's frames |
| **Mail `ID` results** (§8.2.1) | **none — no duckshoot at all** | Replaced by the prompt **`PRESS ANY KEY`**; any key returns to the mailbox |
| **Upload / send** (§8.3.2) | `SEND`, `LOAD`, `GET`, `FINISH` | The original entered an upload sub-context with its own set. Entered once the title/type/price/lifetime are accepted; **each command's function here is defined in §8.3.2**, and `SEND`/`FINISH` are two jobs as in composition |
| **Editor** (§8.4) | `HELP`, `EDIT`, `LAST`, `NEXT`, `NEW`, `COPY`, `ERASE`, `GET`, `PUT`, `STORE`, `PRINT`, `FREE`, `RETURN`, `DOS` | Entirely client-side (no wire commands); `RETURN` leaves the editor. **Each command's function is defined in §8.4.1** — and note the order ends `FREE`, `RETURN`, `DOS` (⚠ §8.4.1). `HELP` here shows the *editor's* help frame (§A.9), not §A.8's. **⚠ This is the one context that is also available OFFLINE** (§8.4) — it is reachable with no session at all, so it is the only row that can appear before login |
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

**⚠ `DONE` returns you where you were, and `B` gets there in steps (normative).** Entering
Courier does **not** move the user's place in the content tree, so leaving it returns them to the
directory they were in — *not* to that directory's parent, and not to the root. On the wire that
is `B` (BACK), but `B` inside mail is **stepwise**, unwinding one level per command:

0. on the **COURIER screen** (`SEND` / `ID`, §8.2.1) → back to the mailbox listing. This step is
   **client-side only** — no wire command — because that screen is a client asset and the lookup
   changed nothing;
1. reading a message → back to the mailbox listing;
2. on a later mailbox page → back one page;
3. on the first page of the listing → **leave Courier**, returning the directory the user came
   from.

So a single `B` is *not* always "leave mail". A client **MUST** make `DONE` actually exit —
repeating `B` until the session is out of mail mode — rather than issuing one and assuming it
worked. (`N`/MORE also clears mail mode when it runs past the last message.)

**⚠ Paging a listing is not a command, in either binding.** There is deliberately no `MORE` in
the directory row. Binding A pages when the user selects the **synthetic pagination row** §7.6
puts at the bottom of a truncated page; a binding without that row (Binding B) reaches the same
place when the **selection moves past the last entry**. Either way it is a *selection* gesture,
so nothing is added to the closed vocabulary of §4.7 and this table stays authoritative.
(VALIDATION.md, F35 — the API document briefly instructed clients to add a `MORE` command here,
which contradicted this row.)

**⚠ Choosing between the two reading rows uses the more-pages flag — and that is allowed.**
§4.5/§6.5 forbid trusting bit 7 to *drive paging*: a client **MUST** decide whether another frame
exists from the actual response. Choosing which **command row** to display is a different
question, asked at the moment the frame appears, when the flag is the only signal available. Use
it for the row; use the response for the paging. If the flag was optimistic the user presses
`MORE` and lands back in the directory — which is exactly what the original does (§6.5).
(VALIDATION.md, F28.)

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

## 4.9 The duckshoot (optional — but defined if used)

A client is **not** required to present commands as a duckshoot (§4.6 — buttons, a menu or a
palette are equally conforming). But the duckshoot is the original's interface, and a client that
offers "a duckshoot" should give users the thing they recognise rather than something merely
duckshoot-shaped. **If a client implements one, it MUST follow this section.**

### 4.9.1 What it is

A **single row of command words** at the foot of the screen. The user **scrolls the row left and
right**; the command in the **centre** is the current one; committing it (RETURN on the
originals) invokes it. The row scrolls — the *selection* does not move.

That inversion is the defining behaviour, and the easiest thing to get wrong: a row where a
highlight moves along a fixed list is **not** a duckshoot, however similar it looks.

### 4.9.2 Placement

- The duckshoot occupies a row **outside the 40×24 content grid** (§5.1). It is client chrome:
  the C64 reserves the screen's bottom line for it, which is precisely why the content area is
  40×24 rather than 40×25.
- It **MUST NOT** overlay or shrink the content grid. Frames and directories are authored for the
  full 40×24 and will be clipped or misaligned if the duckshoot eats into them.
- **⚠ The row shows seven cells, and seven 6-character cells do not fit 40 columns.** 7 × 6 = 42,
  so the row is **two characters wider than the grid** and the outermost cells **clip** — start it
  one column left of the content grid (at column −1) and let the first and last cells run off each
  edge. That is what the original does, and it is why the centre cell lands dead centre: with an
  odd number of cells there is a true middle, which a 6-cell row would not have. Do not "fix" the
  arithmetic by dropping to six cells; §4.9.4's worked example is seven wide and is correct.
  (VALIDATION.md, F4/F5 — a clean-room build hit this contradiction and had to guess.)

### 4.9.3 Appearance

- Command words are **white on black**.
- The **centred (selected)** word is drawn **inverse** — black on white.
- **⚠ Load-bearing: each word is a 6-character cell, with its own padding.** The command-name
  table is 6-byte strings that already carry their spacing, and a client **MUST** use these forms
  rather than padding the bare names itself:

  ```
  ' HELP '  ' DIR  '  ' SHOW '  ' BACK '  ' GOTO '  ' UCAT '  ' MAIL '  'ACCNT '
  ' SAVE '  'EDITR '  'LEAVE '  'PRINT '  ' LIFE '  ' BUY  '  ' UPLD '  ' VOTE '
  ' MORE '  ' ALL  '  ' SEND '  'FINISH'  'ABORT '  ' LOAD '  ' LAST '  ' NEXT '
  ' GET  '  ' DOS  '  '  ID  '  ' DONE '
  ```

  and the editor's own cells (§8.4.1), from the C64 table at `$83AA`:

  ```
  ' HELP '  ' EDIT '  ' LAST '  ' NEXT '  ' NEW  '  ' COPY '  'ERASE '  ' GET  '
  ' PUT  '  'STORE '  'PRINT '  ' FREE '  'RETURN'  ' DOS  '
  ```

  This is what makes the row scroll in even steps **and** what separates the words. Note
  `'FINISH'` fills its cell with no padding of its own — the gap after it comes from the *next*
  word's leading space. A client that left-pads the bare names instead will run `FINISH` straight
  into whatever follows it. `'RETURN'` and `'ERASE '`, `'STORE '`, `'PRINT '` behave the same way
  in the editor row.

### 4.9.4 Contents — which commands, in what order

- The row contains the **current context's command set** from **§4.8**, and nothing else. The
  original *swaps the row per context*; it does not show one fixed list.
- Order **MUST** follow the original's display order, which is a **priority order**, not
  alphabetical. The directory row as the original presents it:

  ```
  HELP  DIR  SHOW  BACK  GOTO  UCAT  MAIL  ACCNT  SAVE  EDITR  LEAVE
  ```

  and mail (§8.2):

  ```
  SEND  SHOW  MORE  ID  EDITR  DONE
  ```

  and the editor (§8.4.1) — note the tail, which is **not** in storage order:

  ```
  HELP  EDIT  LAST  NEXT  NEW  COPY  ERASE  GET  PUT  STORE  PRINT  FREE  RETURN  DOS
  ```

- **The first command is centred by default** when a context is entered — `HELP` for the
  directory row, and it is what the user sees on the welcome screen.
- **⚠ A context remembers where its row was left (normative).** The default above applies the
  **first** time a context is entered, not every time. When the user returns to a context, its
  row **MUST** be back where they left it: `SHOW` a page from a directory, then `FINISH`, and the
  directory row is still centred on **`SHOW`** — not reset to `HELP`. Resetting punishes the
  common case, which is doing the same thing to several entries in turn.
  - The memory is **per context**, not one shared position: the directory, mail and editor rows
    each keep their own. A single remembered position would be overwritten by whichever context
    the user passed through last.
  - Remember the **command**, not its index. Selection-dependent commands appear and disappear
    (§4.9.5), so the row's length changes and a stored index drifts onto a different command.
  - If the remembered command is no longer in the row, fall back to the first.
  - **⚠ Leaving Courier forgets the mail row.** Re-entering mail **MUST** start on **`SEND`**,
    the first command, not wherever the user was last time. Mail is entered to *do* something,
    so the row resets; the exception exists because the mailbox is a destination rather than a
    place being browsed. (Within a session in mail, the row still remembers normally.)
- **⚠ The row is a circular buffer — every visible cell is filled (normative).** Where a context
  has fewer commands than the row displays, the set **repeats**: the wrap applies *within a
  single view*, not only to scrolling. The C64's mail row is the worked example — six commands
  in seven cells, centred on `SEND`:

  ```
  ID  EDITR  DONE  [SEND]  SHOW  MORE  ID
  ```

  `ID` appears **twice**, and that is correct. Suppressing the repeat — on the reasoning that a
  command should not appear twice at once — leaves the row **blank on the left**, which is the
  visible symptom of getting this wrong. Implement it as a plain modulo over the command count.
- The full §4.7 vocabulary continues past the displayed directory row (`PRINT`, `LIFE`, `BUY`,
  `LOAD`, `UPLD`, `VOTE`). These are real commands and a client **MUST** keep them reachable; the
  original simply shows a shorter row by lowering its count.
- **⚠ The loop is the whole set, not the displayed count.** The directory context's row is
  **seventeen** commands long — the eleven above followed by those six — and scrolling walks all
  seventeen. The count byte the original rewrites limits how many cells are *painted*, not how far
  the user can scroll; if the loop were eleven long, `VOTE` would be unreachable by scrolling,
  which the rule above forbids. (VALIDATION.md, F27.)

- **⚠ Load-bearing: truncate from the end.** The original shortens the row by lowering a count,
  which drops commands from the **end** of that order (§4.8). A client with less room **MUST**
  do the same — dropping `VOTE`, `UPLD`, `LOAD` first — rather than choosing its own subset. Drop
  from the front and you remove `DIR`, and with it the user's way into the system.

### 4.9.5 Availability

- **In a duckshoot, inapplicable commands are absent, not disabled.** §4.8 recommends
  *disable-rather-than-hide* for interfaces where that reads naturally (a button bar); the
  duckshoot is the documented exception, because the original changes the row's contents per
  context and a scrolling row of dead words would be worse than a shorter live one.
- Commands that act on a highlighted entry (§4.8) still require a selection. With none, a client
  **SHOULD** either omit them from the row or make committing them a no-op with a brief message —
  it **MUST NOT** send a command with no valid index.

### 4.9.6 Interaction

- **Left / right** scroll the row by one command, and **the row wraps** (normative): scrolling
  past the last command continues to the first, and vice versa. The row is a **loop**, not a
  strip with ends — so every command is reachable by scrolling in either direction, and the user
  never hits a dead stop. A client **MUST NOT** clamp at the ends.
- **Commit** is a distinct action from scrolling (RETURN on the originals); merely scrolling past
  a command **MUST NOT** invoke it.
- The duckshoot is one invocation path among several (§4.6). If a client also offers keys or
  clicks, those **MUST** obey the same §4.8 availability rules — a shortcut is not a way around
  the context.

## 4.10 Showing more than one context at once (optional)

The original clients could show only **one** context at a time, and that limit came from the
hardware, not from Compunet. The C64 has a single screen, so entering the editor *replaces* the
Compunet display and `RETURN` puts it back. The Amiga opened separate Intuition windows — a
directory window, a frame window, an editor window — which is the same idea with the constraint
relaxed. Neither arrangement is required by the protocol: **nothing on the wire knows how many
things are on screen.**

A modern client **MAY** therefore display several contexts **simultaneously** — most usefully the
Compunet display and the editor (§8.4) side by side, so a page can be composed while the
directory it is destined for stays visible. This is presentation only. A client that does so
**MUST** observe the following, all of which exist to keep §4.8 unambiguous when more than one
context is visible:

1. **Each visible context carries its own command row.** Not one shared row that changes meaning
   with focus — the Compunet row is always the Compunet context's row, the editor row always the
   editor's (§8.4.1). A shared row re-labels itself as the user's attention moves, which is
   exactly the ambiguity §4.8 exists to prevent.
2. **Exactly one context holds focus, and focus decides what the keyboard drives.** With two
   contexts on screen, "which commands apply?" has no answer without it.
3. **Focus MUST be visible** — a highlighted border, title, or equivalent. A user who cannot see
   which pane is live cannot predict what a keystroke will do.
4. **Unfocused contexts are inert.** No keystroke may reach a context that does not have focus,
   even though its commands are on screen. They are *shown*, not *available*.
5. **No context may obscure another.** If one covers the other, this section buys nothing and the
   client should show one at a time instead (below).
6. **§4.8 applies per context, unchanged.** Each row is built from its own context's set, with
   the same availability rules. Simultaneous visibility grants nothing extra.

**⚠ This is layout, not behaviour.** Showing two contexts **MUST NOT** add, remove, merge or
rename any command (§4.7), and **MUST NOT** create an action that Binding A cannot express
(§1.8). A user of a one-screen C64 client and a user of a two-pane desktop client must be able
to do exactly the same things, in the same contexts, by the same commands.

### 4.10.1 Which contexts tile, and which replace

Not every context should sit beside the others. Two questions decide it, and the second is the
one that is easy to get wrong:

**Does the original *take over* the screen?** If so, **replace**. **Partyline** (§8.5) is the
clear case: selecting the link downloads a chat program that occupies the C64's screen, and on
exit "the client restores the screen and the session returns to the framed protocol". It is
also the one context that offers **none** of the normal commands (§4.8) — so tiling it beside a
live Compunet display would show a command row with nothing in it, and imply the two are usable
together when they are not. Partyline **SHOULD** therefore take over the Compunet surface and
restore it on exit, rather than opening as an additional pane.

**Is it genuinely used *alongside* another context?** If so, **tile**. The **editor** (§8.4) is
the case that earns a pane of its own: composing a page while the directory it is destined for
stays visible is real, and it is the thing the C64's single screen prevented.

**Replacement is still a context switch, so §4.10's rules still bind:** a replaced context is no
longer visible, so it is no longer focusable and its commands are no longer offered.

### 4.10.2 Focus follows the content being committed

When the user acts on content that lives in another context, focus **SHOULD** move to the
context that *owns that content*, for as long as the action is in flight.

The case that matters is **upload and mail send** (§8.3.2, §8.2). Both submit the **editor's
buffer** — the metadata (title, type, price, recipients) is collected wherever the client likes,
but the pages come from the editor. A client **SHOULD** therefore bring the editor in front of
the user when `UPLD` or `SEND` is invoked, and keep it there until the server has taken the
pages. Asking someone to name and price pages they cannot see is how the **wrong buffer gets
published** — and unlike a mistyped title, that is visible to every other user.

Once the result arrives — the refreshed directory for an upload, an acknowledgement for mail —
focus returns to the Compunet context. **If the submission is refused, focus stays with the
editor**: the buffer is intact (§8.4), and the user is already looking at what needs fixing.

**This does not conflict with §4.6's "single primary surface".** That rule forbids *two competing
surfaces for the same context* — a duckshoot and a button bar both listing the directory
commands, where neither is clearly authoritative. One surface **per context** is the rule being
followed here, not broken.

**The grids do not reflow.** Every Compunet surface is a fixed 40×24 character grid (§5), and the
editor edits a page of the same size — which is what makes tiling them practical: two panes sit
side by side at a legible scale on any modern display, with no reflow and no resizing. Where the
viewport cannot fit them (a narrow window, a phone), a client **SHOULD** fall back to showing
**one context at a time** — the C64 arrangement — rather than shrinking a grid below legibility.
Scaling a 40×24 grid down is never the right answer; showing fewer of them is.

*(Non-normative — the reference client's arrangement: one application window; the Compunet pane
always present; the editor pane opened on demand beside it and closed by `RETURN`; **Partyline
takes over the Compunet pane** and restores it on exit (§4.10.1); mail stays inside the Compunet
pane, since it is a Compunet screen with its own row (§4.8). Focus follows click, `Tab` toggles,
and the unfocused pane is dimmed. `UPLD`/`SEND` open and focus the editor until the server
responds (§4.10.2).)*
