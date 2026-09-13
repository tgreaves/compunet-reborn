# Federation

> **Protocol content is normative in [docs/spec/§8.5.1](spec/08-subsystems.md).** This page is
> the operator's view: how to point Compunet at a federation server, what it sends, and what it
> does when the far end is not there.

Federation is a **link out of Compunet**. A user activates a link page as they would for
Partyline; the server opens a TCP connection to a federation server, says who has arrived, and
then proxies complete lines in both directions until one side leaves.

The federation server itself is **not in this repository**. Nothing here knows what it offers —
rooms, games, another BBS entirely — and deliberately so: everything after the login line is
its own protocol.

```
   C64 / Amiga / terminal / web        server/federation.py       federation server
   ---------------------------------------------------------------------------
   PETSCII, CR-terminated        <->   translate + proxy    <->   ASCII, LF
```

## Configuring it

Two environment variables, in `server/.env`:

```
FEDERATION_ADDR=fed.example.com:30003
FEDERATION_TOKEN=0123456789abcdef0123456789abcdef
```

**Unset means the feature is off**, and off is a defined state, not a fault: the link page
still appears, and activating it says `Federation is not available.` and returns the user to
the directory. A malformed value (no port, a non-numeric port) is logged as an error and
treated as unset — the server never guesses a port.

`FEDERATION_TOKEN` must be a value the Federation server expects.

Changing either needs a server restart (`./server.sh restart`), like any other server change.

## The link page

Federation is reached through a directory entry of type `L`, exactly as Partyline is. What
tells the two apart is a `link` field on the entry, which the server reads and the wire never
carries:

```json
{
  "page_num": 501,
  "title": "PLAY FEDERATION",
  "type": "L",
  "link": "federation",
  "frames": ["pegterm.prg"]
}
```

Absent, the field means `partyline` — every link page that predates Federation keeps working
untouched. The C64 program the entry downloads (`client/c64/src/federation/pegterm.s`) is a
copy of the Partyline client with its own title bar, minus the `*PING` handling it has no use
for; the two speak the same raw line protocol, which is why no client needed changing to gain
Federation.

## What crosses the bridge

**On connect**, one line names the user, the surface they came from and their IP:

```
JOIN 01234567...abcdef ZARD c64 203.0.113.9
```

**Then, lines.** Anything the user commits goes upstream verbatim, converted from PETSCII to
ASCII and terminated with `\n`. Anything the federation server sends comes back converted to
PETSCII, terminated with `$0D`, and **wrapped to 40 columns** — the width of pegterm's output
area.

⚠ **No command is ours — `*quit` included — and Federation has none.** The bridge interprets
nothing. Leaving is the federation server's business: it ends the session on an in-game
command or event, or by crashing, and the client is sent the `*EXIT` that returns it to
Compunet.

**No client has a local way out** — not RUN/STOP, not ESC, and the gateway refuses
`partyline.leave` — as in the original: a stray keypress must not drop a player from the game.
The Amiga CnetTty viewer's Done gadget is the one exception, and it is the original viewer's.

The one line this server originates is `*EXIT`, and only to end the session — the C64 program
waits for it before handing control back to the protocol engine. **There is no keepalive**:
Federation has never had one on either side, and adding one would put a line on the wire that
every client would have to be taught to ignore. A session that sits idle simply sits idle.

⚠ **Remote text starting with `*` is text.** It is converted like any other line rather than
passed through as a protocol sentinel — otherwise a federation server saying `*EXIT` would end
the session on the client's side while this server carried on proxying into a program that had
already gone.

## When the far end goes away

If the federation server closes the connection, the user is told on one line
(`Federation link closed.`) and then sent `*EXIT`, so it looks like any other exit and the
session returns to Compunet. If it cannot be reached at all, the user sees
`Cannot reach the Federation server.` and comes straight back to the directory.

## What is recorded

`federation_entered`, with the user, the surface, their address, and the `server` the link was
opened to — written by `federation.Link.open`, the one function all four surfaces go through
(see [docs/audit-log.md](audit-log.md)).

**The conversation itself is not logged.** It happens on a server that is not ours, and
Partyline's `partyline.jsonl` chat history has no equivalent here by choice.

## Surfaces

| Surface | Entry |
|---|---|
| C64 | Activating the link page downloads and runs `pegterm.prg` (§8.5) |
| Amiga | The resident CnetTty viewer, with Partyline's `01`/`02` handshake (§8.5) |
| Terminal | Activating the link page draws the chat window server-side |
| Web / Electron | The gateway's existing `partyline.*` messages, with `service: "federation"` |
