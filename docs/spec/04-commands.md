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

On the TCP protocol path a client distinguishes ACK from the streamed types by the
**EOS convention** above (ACK has no EOS) together with the response content; the type is
implicit. *(Non-normative: the server also offers a WebSocket transport that prepends the
type byte above explicitly to each response. A pure-TCP client does not receive that prefix
and infers the type from context and the EOS convention.)*

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
| `I` | `$49` | ID / WHO | — | Identify / "who is online" listing | DIR |
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

The single-letter set is identical across the C64 and Amiga reference clients (both send
these bytes in COM `$43` frames and both use the `@` ack convention), which is what makes
one server drive both — see the appendix (§A) for the consolidated table alongside the
token table.
