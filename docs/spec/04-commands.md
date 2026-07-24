# §4 — Command protocol

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
| 1… | argument | Optional. **ASCII decimal digits**, zero or more |

The argument, when present, is plain ASCII text parsed as a decimal number — e.g. the
"show page 7" command is the three bytes `P 0 7` (`$50 $30 $37`), and "select directory
entry 3" is `D 0 3`. A command with no argument is just the single command byte. A client
**MUST** encode arguments as ASCII digits, not as binary integers.

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
character (`ID` and mail-send), the server prepends `@` (`$40`) to the response so the
native client's ack read succeeds; it then reads the frame that follows. This prefix is
applied **only** to native (Amiga-classified) sessions — the C64/ROM stream is unchanged,
because the ROM keys off the DAT token rather than a leading ack byte. A client that does
not use a leading-ack read **MUST NOT** be sent this prefix (it is gated on the native
classification of §3.3).

*(Non-normative — status bytes. The original ROM treats a non-`@` status byte such as `A`
(`$41`) or `B` (`$42`) arriving in place of frame data as an error/status indication and
shows a status message — e.g. `A` maps to a "Host error" message. The exact status-text
mapping is a client concern and is not required to interoperate.)*

## 4.4 Command set

The commands the server dispatches. Command bytes are ASCII letters; the "Arg" column
notes the ASCII-decimal argument where one is used. "Typical response type" is indicative
(§4.3) — some commands vary by context (e.g. `D` and `P` change behaviour depending on
whether a frame is currently being viewed).

| Cmd | Byte | Name | Arg | Meaning | Typical response |
|---|---|---|---|---|---|
| `D` | `$44` | DIR / next | entry index (2 digits) | Select a directory entry: enter a sub-directory, show an entry's first frame, or — with no arg while viewing — advance to the next frame; past the last entry, page the directory | DIR or FRAME |
| `P` | `$50` | SHOW / finish | page (digits) | Show the current page's directory; also used by FINISH to leave frame view and return to the directory | FRAME or DIR |
| `N` | `$4E` | MORE | — | Advance / continue: next frame, or the continuation step in an upload (§8) | FRAME |
| `B` | `$42` | BACK | — | Go to the parent directory | DIR |
| `L` | `$4C` | GOTO | keyword/page | Jump directly to a page by keyword or number | DIR or FRAME |
| `A` | `$41` | ACCOUNT | — | Show the account/personal-information frame | FRAME |
| `I` | `$49` | ID lookup | one or more 8-byte user IDs | Look up user IDs; returns per-ID `id` + real name (if known) + `$1E`. With no argument it returns **nothing** (see note). Not "who is online" — that is a content page, not this command | lookup stream |
| `C` | `$43` | UCAT | — | User catalogue | DIR |
| `M` | `$4D` | MAIL | — | Enter mail (Courier); see §8.2 | DIR |
| `V` | `$56` | VOTE | choice | Cast a vote (LIFE / VOTE); see §8.6 | ACK |
| `X` | `$58` | BUY | page | Purchase a paid page | ACK |
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
| `P` (show current dir), `B` (back), `M` (mail), `C` (ucat), `L` (goto) | any | directory | 6-part directory (§7) |
| `A` (account), `E` (leave) | any | frame | frame (§6) |
| `I` (ID lookup) | any | lookup stream | `id`+name+`$1E` per requested ID (§4.4) — not a 6-part directory |
| `N` (more) | viewing a frame | frame | frame (§6) |
| `V`, `X`, `U` | any | acknowledgement | bare ACK (single packet, no EOS) |
| `D` (select) with index | in a directory | depends on the **selected entry's type** (§7.4): `T`→frame; `D`/`+`→directory; `P`/`PP`/`S`→download (§8.3.1); `L`→link (§8.5) | per entry type |
| `D` (no argument) | viewing a frame | next frame, or — past the last frame — return to the directory | frame, else directory |

So the two context-sensitive commands are `D` and `P`: a client **MUST** track whether it is
viewing a directory or a frame, and for `D`-with-index **MUST** use the selected entry's type
to choose the parser. That type is not delivered separately — the client reads it from the
entry it selected, where the type occupies characters 24–26 of the entry's first field
(screen column 25; see §7.3/§7.4). A client therefore **MUST** retain each listed entry's
type when it parses a directory, so it can dispatch the subsequent `D`. Everything else is
determined by the command byte alone. The ERROR type (§4.3) is delivered as a frame and can
be rendered by the frame parser, so a client **MAY** treat an unexpected frame where it
expected a directory as an error message rather than crashing.

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
  the foot of the screen that the user scrolls through and selects (this is the reference
  user experience, reproduced by the C64 and Amiga clients; a client **MAY** emulate it but
  is not required to).

Concretely, the minimum obligations by tier are:

- **Tier 1 (Browse):** the user **MUST** be able to invoke directory navigation and frame
  viewing — at least `P` (show directory), `D` (select entry / next), `B` (back), `N`
  (more), `L` (GOTO), `A` (account), and `E` (leave). Selecting a directory entry (§7.7)
  is itself the `D` command and satisfies the entry-selection requirement.
- **Tier 2 (Interact):** additionally the commands for the subsystems it implements — e.g.
  `M` (mail), `C` (UCAT), `I` (who), `V` (vote), `X` (buy).
- **Tier 3 (Full):** additionally `U` (upload) and the editor / Partyline entry points.

A command the client's tier does not implement need not be offered. The command byte and
wire exchange for each are defined in §4.4 and §8; this section only requires that a user
can trigger them.

## 4.7 Standard command vocabulary

When a client surfaces commands to the user, it **SHOULD** use the original Compunet command
names below rather than inventing its own, so the experience is recognisable across clients.
These are the words the original "duckshoot" presented; they map onto the wire commands of
§4.4. (The *how* — buttons, menu, scrolling duckshoot — remains the client's choice, §4.6;
this table standardises the *names*, not the interface.)

**While viewing a directory:**

| Name | User action | Wire command |
|---|---|---|
| `DIR` | Enter the highlighted entry's sub-directory | `D` + index |
| `SHOW` | Read the highlighted entry's page | `D` + index |
| `BACK` | Go to the parent directory | `B` |
| `GOTO` | Jump to a page by number or keyword | `L` + arg |
| `ACCNT` | Show the account / personal-information page | `A` |
| `MAIL` | Enter Courier (mailbox) | `M` |
| `UCAT` | User catalogue | `C` |
| `VOTE` | Vote on the current content | `V` + digit |
| `BUY` | Purchase a paid page | `X` + page |
| `UPLD` | Upload content | `U` (§8.3.2) |
| `LEAVE` | Log off | `E` |
| `EDITR`, `HELP`, `PRINT`, `SAVE` | Editor / help / print / save | client-side (no wire command) |

**While reading a page (frame):**

| Name | User action | Wire command |
|---|---|---|
| `MORE` | Show the next page of a multi-frame item | `D` (no arg) / `N` |
| `FINISH` | Return to the directory | `P` |

> **DIR vs SHOW — one wire command, two names.** In the original, `DIR` (enter a
> sub-directory) and `SHOW` (read a text page) were distinct duckshoot commands, but in
> Reborn **both send `D` + index** and the server dispatches on the selected entry's type
> (§4.5, §7.4): a directory-type entry is entered, a text-type entry is shown, a
> program/link entry is downloaded/activated (§8.3.1/§8.5). A client **MAY** therefore expose
> a single "SHOW"/open action that does the right thing per entry type, or keep the separate
> `DIR`/`SHOW`/`BUY` labels — both are conformant, since the byte on the wire is identical.
> A client **SHOULD NOT** invent a non-Compunet label (e.g. "OPEN") for this action.
>
> **Opening an entry uses `D`+index, not `P`.** On the framed (TCP) transport there is no
> "move the selection" command — the client tracks the highlighted entry **locally** and acts
> on it by sending `D` + that entry's index. `FINISH` (`P`) carries **no index**: it returns
> to, or refreshes, the current directory, using only the server's last-selected entry. A
> client **MUST NOT** use `P` to enter a highlighted sub-directory (the server does not know
> the client's local highlight, so `P` will appear to "do nothing" or act on the wrong entry).
> `DIR` and `SHOW` are therefore both `D`+index; `FINISH` is `P`.
