# Binding B — Client API

> **Status: normative.** This is the modern **JSON API binding** (Binding B) introduced by the
> [Compunet Client Specification](../README.md) §1.8. It carries the **same application model**
> (§3 session, §4 commands, §8 subsystems, and §5's screen model) as the legacy X.25 binding
> (Binding A), in structured JSON instead of the ROM wire format. Design rationale — why it is
> shaped this way, and what was rejected — is in [RATIONALE.md](RATIONALE.md).
>
> Clean-room validated: an isolated builder produced a full Tier-3 Electron client from this
> document plus the model sections alone, against a live server, logging 41 findings — all folded
> in. See [VALIDATION.md](../VALIDATION.md).

**Conformance tiers.** §1.4's tier table lists the Binding-A sections a tier requires; the
equivalents here are:

| Tier | Binding B means |
|---|---|
| **1 — Browse** | `POST /v1/session` → gateway → `dir`/`enter`/`open`/`back`/`more`/`finish`/`goto`, blitting `frame` cell grids and composing directories per §7.5–§7.7 |
| **2 — Interact** | + `account`, `mail.list`/`mail.read`, `idlookup`, `vote`, `life`, `download.fetch`, `ucat` |
| **3 — Full** | + `upload`, `mail.send`, the editor (§8.4), `partyline.*` |

A Binding-B client needs **§5.3, §5.6, §6.3 and §6.4** at every tier, for its own embedded
assets — see §7.

## Locked decisions

- **Transport:** a **hybrid** — a WebSocket **gateway** for the interactive session and server
  push, plus **REST reads** for cacheable fetches. The Discord/Slack model. Both are built.
- **Encoding:** structured JSON. **Directories** are entry lists (the client composes the 40×24
  layout locally, so selection and column-cycling need no round-trip). **Frames** are a
  server-rendered **40×24 cell grid** (the client blits it with the appendix font/palette).
- **Port:** dedicated — **6404** — separate from admin (6403) and X.25 (6400).
- **Auth:** **token-first** — `POST /v1/session` returns a bearer token; the WebSocket then
  authenticates with that token. Production rides `wss://` / `https://`.
- **Reference client:** TypeScript rendering to `<canvas>` — the same codebase serves a browser
  tab and, in an Electron shell, a Windows/Mac desktop app.

Everything below reuses the server's existing content/session core
(`CompunetDirectory`, `CompunetSession`) — this binding is a serializer, not new behaviour.

## 1. Endpoints

Dedicated listener on **6404**, with two surfaces — the gateway for the interactive session,
REST for cacheable reads:

**⚠ The listener MAY also serve the client itself, and there are good reasons to.** Publishing
one hostname at 6404 that answers both `/` (the client) and `/v1/*` (this API) makes them
**same-origin**, and that removes three problems at once rather than solving them:

- **Nothing to configure.** The client defaults to the origin that served it, so the URL you
  give someone is the entire instruction.
- **No CORS.** Not even a permissive policy to get wrong.
- **No mixed content.** One hostname, one certificate — a page served over `https` cannot open a
  `ws://` socket, which is the failure a split deployment hits first.

It also suits how such a service is usually published: a tunnel or reverse proxy needs a single
route, and a CDN will typically only proxy a fixed set of ports — 6404 rarely among them, so the
port has to be translated somewhere regardless.

Two rules if the client is served this way:

- **Register the API routes BEFORE the static ones.** A static handler mounted at `/` will
  otherwise shadow `/v1/*` and answer API calls with 404s.
- **Do not let a cache pin the client.** Version the bundle's URL (a content hash or its mtime)
  and serve the page carrying that reference as `no-cache`. Otherwise a deployed fix can appear
  not to work for as long as the cache lives — a CDN default of several hours is common, and the
  only symptom is that a hard reload cures it.

| Method | Path | Purpose | Phase |
|---|---|---|---|
| `POST` | `/v1/session` | log in with credentials → bearer token | 1 |
| `GET`  | `/v1/gateway` (WebSocket upgrade) | the interactive session | 1 |
| `GET`  | `/v1/dir/{page}` | a directory as JSON (cacheable, bearer auth). `404 not_found` for a target that names no page — it does **not** fall back to the root | done |
| `GET`  | `/v1/frame/{page}[?index=N]` | a frame as a cell grid (bearer auth) | done |
| `GET`  | `/v1/health` | `{"ok": true}` — liveness, **no auth** | done |

`/v1/` is the version prefix so the binding can evolve without a ROM-style hash gate.

`/v1/health` is the one endpoint that takes no credentials: it exists so a client can check the
server is reachable *before* asking the user to log in, and so deployments have something to
probe. It reveals nothing about the service beyond that it is running.

**CORS is required (normative).** This binding exists to be called by clients served from a
**different origin** — a web client on its own host, and a desktop shell, which serves its page
from somewhere that is not this server (the reference shell uses a custom `compunet://` scheme;
an ephemeral `http://127.0.0.1` port also works, but see §8.4's warning about storage keyed to
an origin that changes each launch). The server therefore **MUST** send
`Access-Control-Allow-Origin` (plus `Allow-Methods: GET, POST, OPTIONS` and
`Allow-Headers: Content-Type, Authorization`) on `/v1/*` responses, and **MUST** answer the
`OPTIONS` preflight that `POST /v1/session` triggers. Without it a browser blocks the very
first call and the client cannot log in at all — note the failure is *silent* apart from a
generic "failed to fetch", so it is easily mistaken for a dead server.

`*` is an acceptable default because authentication is a **bearer token in a header, not a
cookie**: nothing is sent automatically by the browser, so there is no CSRF surface. Deployments
that want to pin the API to one origin set `CLIENT_API_CORS_ORIGIN`. (WebSocket connections are
not subject to CORS preflight, so only the HTTP endpoints need this — but a client that cannot
reach `/v1/session` never gets a token to open the socket with.)

## 2. Authentication (token-first)

1. `POST /v1/session` with `{"user": "...", "pass": "..."}`.
   - `200 {"token": "<opaque>", "expiresInSec": 86400, "account": {…}}` on success
     (reuses `CompunetSession.handle_login`). The token is an **opaque server-side session
     token** (simple to expire/revoke; JWT is not needed at this scale).
   - `401 {"error": {"code": "unauthorized"}}` on failure.
2. Open the WebSocket to `/v1/gateway`, then send the **first message** `{"type":"auth",
   "token":"<opaque>"}`. (First-message auth, not a `?token=` query, so tokens never land in
   access logs; browsers can't set WS headers.)
   - Server → `{"type":"ready", "account": {…}, "welcome": <frame>}` (the welcome frame, §6/§5,
     as a cell grid), or `{"type":"error","code":"unauthorized"}` then close.
3. The client **renders the welcome frame** and waits (spec §3.5). The server does **not**
   auto-send a directory — that would clobber the welcome page. The user reaches the root by
   issuing **DIR** (`{"type":"dir"}`), exactly as on the welcome screen in Binding A (§4.7).

`account` is `{"user": "TEST", "credit": 97.5, "name": "MR TEST PERSON"}` — the same object on
both the `POST` reply and `ready`. `name` is the user's real name, which §8.2.1 needs for the
`SEND` envelope (§A.11); without it a client has to look itself up through `idlookup`.

That three-step exchange is the **whole** of login in this binding. §3's handshake,
identification and LINKING are Binding-A transport concerns with no counterpart here — a
Binding-B client can ignore every reference to them.

## 3. Message envelope

Every WebSocket message is a JSON object with a `type`. Client requests **MAY** carry an `id`
(any string/number); the matching reply echoes it, so async replies pair with requests. Server
**push** messages (Partyline, notices) carry no `id`.

```jsonc
// client → server
{ "type": "enter", "id": 7, "page": 600 }
// server → client (reply)
{ "type": "directory", "id": 7, … }
// server → client (unsolicited push)
{ "type": "partyline", "line": "ADMIN has entered partyline" }
```

**Errors** are uniform: `{ "type":"error", "id"?:…, "code":"…", "message":"…" }`, with codes
`unauthorized`, `not_found`, `no_content`, `directory_full`, `permission_denied`, `invalid`.
`directory_full` and `no_content` make explicit what Binding A only signalled by silence
(spec §8.3.2, §4.5).

## 4. Commands (client → server)

Named by **intent**, not by ROM byte. Selection is client-local, so a command names the page it
acts on rather than a highlighted index (spec §4.5).

> **⚠ `page` is scoped to the CURRENT LISTING, not a global address (normative).** It names an
> entry *of the listing the session is on*, and is resolved against that listing's entries — it
> is the ROM's entry index under a friendlier name, not a page number you may jump to. `open`,
> `enter`, `vote` and `life` all work this way.
>
> Consequences a client **MUST** respect:
> - Never send `open`/`enter` for a page you are not currently displaying. From the mailbox,
>   `open` on a root page returns `not_found`, and after `goto 612` — which *opens* 612 as a
>   listing — `enter {page: 612}` is also `not_found`, because 612 is no longer an entry *within*
>   the listing, it **is** the listing.
> - Keep your idea of the current listing in lock-step with the server's. Every reply that changes
>   the listing changes what `page` means.
>
> To move to an arbitrary page, use **`goto`** — that is what takes a global target.
>
> *(A clean-room build called this "the single most consequential thing the API spec does not
> say", noting it fails as a plausible-looking `not_found` rather than obviously — VALIDATION.md,
> F7.)*

| `type` | Fields | Model | Meaning |
|---|---|---|---|
| `auth` | `token` | §3.5 | first message; authenticate the socket |
| `dir` | — | §4.7 DIR (bare `P`) | show the **current** directory — this is how the welcome screen reaches the root (§2 step 3). Also the "refresh" after an action |
| `enter` | `page` | §4.7 DIR (`P`+idx) | enter the entry as a directory (opens a latent one if none) |
| `open` | `page` | §4.7 SHOW (`D`+idx) | read the entry's frame(s); or download/activate a program/link |
| `more` | — | §4.7 MORE | next frame of a multi-frame item. **Only while a frame is displayed** — in a directory it starts reading the selected entry's frames |
| `finish` | — | §4.7 FINISH | leave the frame → its directory |
| `back` | — | §4.4 BACK | parent directory |
| `goto` | `target` (page # or keyword) | §4.4 GOTO | jump; reply is always a directory (§4.4) |
| `account` | — | §4.4 ACCOUNT | credit balance |
| `ucat` | — | §8.6 | the user's own uploads (a directory listing) |
| `vote` | `page`, `score` (1–9) | §8.6 | vote on the entry |
| `life` | `page`, `days` | §8.6 | extend the entry's life |
| `idlookup` | `ids` (array of 8-char) | §4.4 | user-ID → real-name lookup |
| `mail.list` | — | §8.2 | mailbox as a directory |
| `mail.read` | `index` (row in the current listing) | §8.2 | read a message |
| `mail.done` | — | §4.8 | **leave Courier** — the `DONE` command; replies with the directory the user came from. Valid only inside mail; an `error` (`invalid`) elsewhere |
| `mail.send` | `to` (array), `subject`, `frames` (editor pages, §5.4) | §8.3.2 | send mail |
| `upload` | `title`, `kind` (`"T"`\|`"P"`), `price`, `life`, `frames` | §8.3.2 | content upload; **`kind` and `price` are required** (§8.3.2) |
| `download.fetch` | — | §8.3.1 | after a `download` descriptor, pull the payload (the ROM's `$40` proceed) |
| `partyline.send` | `text` | §8.5 | send a chat line |
| `partyline.command` | `text` (e.g. `*who`) | §8.5 | a Partyline `*`-command |
| `partyline.leave` | — | §8.5 | leave Partyline (`*quit`) → normal commands resume |
| `leave` | — | §4.4 LEAVE | log off. Replies with the goodbye **frame** carrying `"goodbye": true`; the server closes the socket after it |

Note there is **no** column-cycle command: directory JSON carries every Part-5 column value per
entry (§5 below), so the client cycles the visible column locally (the `F7`/`F8` behaviour of
spec §7.7) with no round-trip.

**Which commands to offer when.** Command *availability* is shared model, not binding detail:
see **spec §4.8**. A Binding-B client faces the same contexts (welcome frame, directory, frame,
mailbox, mail message, upload, editor, Partyline) and **MUST** offer only the commands that
apply to the current one — e.g. `more`/`finish` only while a frame is displayed, `vote`/`life`
only with an entry highlighted, and while in Partyline only the `partyline.*` commands.

## 5. Responses (server → client)

### 5.1 `directory`

The client composes the 40×24 screen from this using the built-in template and the display rules
(spec §7.5–§7.7): first entry **red**, others **blue**, client-drawn selection bar, page number
on the selected row only. None of that colouring is in the JSON — it is the shared display
contract the client applies.

```jsonc
{
  "type": "directory", "id"?: …,
  "page": 100, "title": "WELCOME",
  "breadcrumb": ["     1 *** COMPUNET ***", "   100 WELCOME"],  // Part 4 lines, verbatim text
  "columns": [" PRICE"," AUTHOR","VOTE/NUM","UPLDDATE"," LIFE"], // Part 5, verbatim (leading spaces are positioning, §7.3)
  "advert": ["V1.00: OUR FIRST OFFICIAL RELEASE!", "THANKS FOR MAKING THIS POSSIBLE"], // Part 2 — ALWAYS exactly 2 strings, empty when there is no advert (§7.2)
  "mailWaiting": true,          // the red MAIL marker (§7.2). ALWAYS present; true when the mailbox holds unread mail, whether or not the client has opened mail
  "context": "mail"|"ucat",     // present only for those listings; absent for content directories
  "selected": 2,                // GOTO only: which entry was the target (§4.4) — the client MUST NOT compute this itself
  "header": <frame|null>,       // Part 1 header frame (COMPUNET logo) as a cell grid, or null → built-in template. Overlay ROWS 0–5 ONLY (§7.7) — it is a full 24-row grid and blitting all of it erases the template's box and divider
  "hasMore": false,             // GENERATED listings only (mailbox, UCAT): more entries follow, and a MORE row is present (§7.6). Always false on an authored directory
  // ⚠ `entries` is NEVER empty: an empty listing carries one placeholder row
  // (§7.3 MUST) whose `page` is 0. Because `page` is listing-scoped, a
  // zero-entry listing would make every open/enter/vote fail with a plausible
  // `not_found` until the user escaped with `goto`. Treat a `page: 0` entry as
  // "nothing selectable" and disable the selection-dependent commands (§4.8).
  "entries": [
    { "index": 0, "page": 101, "title": "NEWS", "type": "T", "size": null, "hasSubdir": true,
      "values": ["", "ADMIN", "    -", "", "   99"] }   // parallel to columns; already justified (§7.3)
    // … up to 11 …
  ]
}
```

**Overflow, not paging.** An authored directory shows 11 entries and **does not paginate**
(§7.6): overflow is a user-created `D` entry, conventionally titled `MORE`, which the user enters
like any other. `hasMore` is therefore `false` on every authored listing.

Only **generated** listings — the mailbox and UCAT — can overflow, because their owner cannot
author a `MORE` entry into them. Those carry the synthetic row as an **ordinary entry** with
`page: -1`; `enter`/`open` on it returns the next page. There is deliberately **no paging
command**: adding one would put a word in Binding B that Binding A has no counterpart for, which
§1.8 forbids.

> *(An earlier revision of this document described server-side paging and introduced
> `dir.more`/`dir.back` to drive it. Both were wrong: the model has no such thing, and the
> commands were invented vocabulary. VALIDATION.md, F15/F26/F35.)*

`page` is an **integer in every listing**, including the mailbox, where it is the message id.
(`mail.read` addresses messages by `index`, not `page`, so the id is never sent back.)

`type` is the base entry type (`T`/`D`/`P`/`PP`/`S`/`L`, spec §7.4); `size` is the K/page count
or null; `hasSubdir` is the `+` marker. The client dispatches SHOW vs DIR from these. `columns`
and each entry's `values` are **parallel arrays** carrying the strings **verbatim**, with the
server's per-column justification already applied (§7.3) — the leading spaces on `" PRICE"` /
`" AUTHOR"` / `" LIFE"` and the right-justified values are the positioning. The client draws
`columns[i]` (header) and `values[i]` (value) as-is from the pane's base column (screen col 31);
it does **not** re-justify. It renders one column at a time and cycles locally (§7.7).

### 5.2 `frame`

**`lower`** reports the character set in force at the **end** of the stream (`true` = the
lowercase/mixed set, §5.3). A client needs it to draw its command row, which shares the screen
and so uses the same set (§4.9.3). It is reported rather than left to inference because blank
cells carry whatever set was in force when they were last cleared, which need not be the final
state — a page can end lowercase with most of its blanks recorded as uppercase.


Server-rendered 40×24 grid, RLE / charset / control codes already expanded. The client just
paints each cell (glyph from the appendix font, `fg`/`bg` from the palette).

```jsonc
{
  "type": "frame", "id"?: …,
  "border": 4, "background": 15,   // low-nibble palette indices from the 4-byte header (§6.2)
  "morePages": true,               // flags bit 7 — another frame follows (§6.5)
  "rows": 24, "cols": 40,
  "cells": [ /* row-major, rows*cols entries */
    { "g": 0, "fg": 6, "bg": 15, "rv": 0 }   // bg is READ-ONLY — see the note under §5.4
    // g   = glyph index 0–255 (0–127 = uppercase/graphics set, 128–255 = lowercase set; 128 glyphs each, §5.2/§5.4)
    // fg,bg = palette index 0–15 (§5.5)
    // rv  = reverse-video flag 0|1 (§5.7)
  ],
  "raw": "AAD0/w4T…"               // base64 of the exact §6 bytes this grid was rendered from
}
```

*(Compact encodings — parallel typed arrays, run-length, or base64 — are a later optimization;
this binding fixes the logical shape first.)*

### 5.3 Others

- `account` → `{ "type":"account", "creditText":"999.00", "credit": 999.0 }` (§4.4).
- **Mail** (§8.2) reuses the shapes above: `mail.list` → a `directory` carrying
  `"context":"mail"`, its own Part-5 set `[" SENDER"," DATE"," STATUS"]`, and entries whose
  `page` is the message id; `mail.read` → a `frame`; `mail.done` → a `directory`, the one the
  user was in before entering Courier. An empty mailbox still returns one `(NO MAIL)` placeholder
  entry (§7.3). A client **MUST** take the columns from the response — they differ from a content
  directory's (§7.2).

  **⚠ `mail.done` exists because `DONE` is a real command, not a sequence of `back`s.** §4.8's
  `DONE` is `N` on the wire and leaves Courier in one step; a binding without an equivalent
  forces its clients to emulate it by repeating `back` until mail mode happens to clear, which
  reaches the same state but is a workaround, and one that has to *watch* for the end condition.
  This is the §1.8 rule in practice: every command of the shared model needs a way to be
  expressed, or the binding pushes the difference into every client.
- `idlookup` → `{ "type":"idlookup", "users":[{"id":"ADMIN","name":"MR SYSTEM ADMIN"}, …] }`;
  `name` is `null` when the user does not exist (§4.4).
- **Download** (§8.3.1) is two steps, mirroring the ROM's proceed token: selecting a
  program entry replies `{ "type":"download", "page":…, "title":…, "size":…, "machine":"c64"|"amiga" }`
  (a *descriptor* — nothing is transferred yet); the client then sends `download.fetch` and
  receives `{ "type":"download.data", "title":…, "size":…, "bytes": "<base64>" }`. Splitting it
  this way lets the client confirm with the user before pulling the payload, exactly as the
  `$40`/`$41` proceed/abort choice does in Binding A.
- `ack` → `{ "type":"ack", "id"?:…, "of":"vote" }` for state-changers that just confirm (§4.3).
  `vote` requires a score of 1–9 and `life` a day count; both target the page by number and are
  validated server-side, returning an `error` (`invalid` / `not_found`) rather than a silent
  no-op.

### 5.4 Tier-3 shapes

**Editor pages.** The client never produces PETSCII (that is the point of this binding), so a
composed page is submitted **structurally** and the server encodes the §6 frame:

```jsonc
{ "lines": ["HELLO", "", "SECOND LINE"], "colour": 5, "border": 6, "background": 0 }
```

`colour` is a palette index (§5.5) applied as the frame's text colour; `border`/`background`
become the frame header (§6.2). Lines are truncated to 40 columns and 23 rows.

**That text form is the *simple* path, not the only one.** It cannot express per-cell colour,
reverse video or graphics characters, so it is insufficient for anything captured from Compunet
(§8.4.2, where capture must be **verbatim**). Two further forms exist, and a Tier-3 client
**MUST** support them:

```jsonc
{ "cells": [ {"g":24,"fg":1,"bg":15,"rv":0}, … ], "border": 4, "background": 15 }
{ "raw": "AAD0/w4TDx8…" }
```

- **`cells`** — a full 40×24 grid, the same shape the server sends in a `frame` (§5.1). The
  server encodes it to §6 bytes, emitting the colour, reverse (`$12`/`$92`) and charset
  (`$0E`/`$8E`) codes needed to reproduce it. This is how an **edited** page is submitted.

  > **⚠ `bg` is a FRAME-level property, not a per-cell one.** On submission every cell's `bg` is
  > ignored and the frame's `background` is used. The C64 has a single screen background colour,
  > so §6 has nowhere to put a per-cell value and **Binding A cannot express one either** — the
  > §1.8 invariant is intact; it is this *schema* that promises more than the model has, by
  > carrying a writable-looking `bg` on all 960 cells.
  >
  > An editor **MUST** therefore treat background as a property of the page (which is what
  > §8.4.3's `f7`/`f8` "screen and border colour" already implies) and **MUST NOT** offer
  > per-cell background painting: it would appear to work and then vanish on upload — the
  > §8.3.2 silent-failure pattern, in the editor. When writing `cells`, stamp every cell's `bg`
  > with the frame background.
  >
  > Everything else round-trips exactly. Measured over a grid exercising **all 256 glyph codes
  > in both character sets, again with reverse video, and all 16 foreground colours**: 0
  > mismatches in 960 cells. (VALIDATION.md, F25.)
- **`raw`** — the exact §6 bytes, base64. Used to re-upload a captured page the user has **not**
  edited, so it is republished byte-for-byte rather than re-encoded. Opaque to the client: it
  never parses PETSCII, it just hands back what it was given.

This is what **`raw`** on the `frame` message (§5.2) is for: the bytes the grid was rendered
from, carried so a client can hand them back unchanged. It is **opaque** — a client that does
not implement the editor ignores it, and one that does never parses it. Carrying PETSCII here
is not a breach of this binding's "no PETSCII" principle for exactly that reason: the client
treats it as a token, not as content.

Precedence when a page carries more than one form: **`raw` wins, then `cells`, then `lines`.**

**Upload** (`upload`) carries `title`, `kind` (`"T"`/`"P"`), `price`, `life`, and `frames`.
Unlike Binding A's multi-step wire dance (`U` → validation → frame DATs → finishing `P`), it is
**one message**: the server performs the same commit through the same core routine and replies
with the **refreshed directory** (the equivalent of the finishing `P`). For `kind: "P"` the
frames are base64 program blobs rather than editor pages.

> **The program blob, precisely** (⚠ this is not guessable — follow it exactly).
> Each element of `frames` is a **bare base64 string**, not a `{raw}` page object — the server
> discriminates on the JSON type, so an object takes the editor-page path and never reaches the
> program writer. Decoded, the blob is an **8-byte header followed by the body**:
>
> | Byte | Meaning |
> |---|---|
> | 0 | machine type — `0` = C64, `1` = Amiga |
> | 1–3 | reserved, `0` |
> | 4–5 | **C64 load address**, little-endian (`0` for Amiga) |
> | 6–7 | body size, little-endian — informational here, since the blob's length is known |
>
> ⚠ **This is the Binding-B *upload* blob; do not implement anything else from it.** The size
> here is inert because the blob carries its own length. Binding A's **download descriptor** is
> machine-dependent and its size field is load-bearing — 16-bit at 6–7 for the C64, 32-bit
> big-endian at 4–7 for Amiga and ST (§8.3.1) — and Binding A's *upload* header differs again
> (§8.3.2). Three similar-looking headers; copying one into another's place has caused a
> shipped bug in each direction.
>
> For a **C64** `.prg`, bytes 4–5 are the file's own first two bytes and the body is the file
> **from offset 2**: the server rebuilds the stored program as `header[4:6] + blob[8:]`, so this
> reproduces the original file exactly. For an **Amiga** executable the body is the whole file
> and the load field is `0`; the server stores `blob[8:]` verbatim.
>
> ⚠ This follows §8.3.1's field map. §8.3.2 describes bytes 4–7 as a big-endian body size for
> Binding A's streamed transfer — see the unresolved-conflict note there before changing
> anything here. Binding B does not stream, so it needs no size to know where the body ends. The checks Binding A applies silently
become **typed errors** — `permission_denied` (not your directory / not your page to replace)
and `directory_full` (11-entry cap, §8.3.2) — so a client learns *why* an upload was refused
instead of discovering a missing entry afterwards.

**Mail send** (`mail.send`) carries `to` (up to five IDs), `subject`, and `frames`; unknown
recipients produce a `not_found` error listing them, rather than silently dropping them.

**Partyline** (§8.5) does **not** drop out of the protocol as Binding A must. The socket stays a
gateway. **Joining is only ever done by activating an `L`-type entry** with `open` (§7.4/§8.5) —
there is deliberately **no** "join partyline" command, because Binding A has none either and a
client must not offer a route the original lacks. `open` on an `L` entry replies
**`partyline.entering`** (answering the `open`), then **`partyline.entered`** once the join
completes — wait for the latter before showing the chat UI. Then:
every chat/system line arrives as a `partyline` push; `partyline.send` / `partyline.command`
carry input; `partyline.leave` (or `*quit`) replies `partyline.left` and normal commands resume
immediately. Rooms, `*`-commands, bans, and broadcast are the server's existing partyline
subsystem — this binding only adapts the transport.

## 6. Push events (server → client, no `id`)

- `{ "type":"partyline", "line":"…" }` — a raw Partyline chat/system line (§8.5). On entry the
  server pushes the join broadcast **and** the initial who-listing (§8.5).
- `{ "type":"notice", "kind":"mail", … }` — unsolicited notices (e.g. new mail), replacing the
  ROM's in-band `MAIL` marker for realtime clients.

Partyline is why the gateway is WebSocket: it is a live, server-pushed, line-based session
(§8.5). Entering an `L`-type entry via `open` transitions the socket into Partyline mode; the
server then streams `partyline` events and accepts `partyline.*` commands until `partyline.leave`.

## 7. Rendering split (client responsibilities)

- **Frames from the server:** blit the `cells` grid — glyph `g` from the appendix font (§A.5),
  colours from the palette (§A.3), invert on `rv`. No PETSCII/RLE logic needed; the server did it.
- **Directories:** compose locally from the built-in template (§A.6) + the display rules
  (§7.5–§7.7) — this is the only real client-side layout work, and it is what keeps selection,
  scrolling, and column-cycling instant (no server round-trip).

> **⚠ A Binding-B client still needs a full §6 frame decoder.** "The server did it" is true of
> *server content* and false of the client's **own assets**, which are raw PETSCII frames the
> server never sends and a conforming client cannot do without:
>
> | Asset | Required by |
> |---|---|
> | §A.6 directory template | §7.5 — every directory screen is drawn on it |
> | §A.8 HELP frame | §4.7 — "a client that omits it leaves `HELP` doing nothing" |
> | §A.9 editor help | §8.4.1 |
> | §A.10 COURIER, §A.11 COURIER SEND | §8.2.1 |
>
> So implement §5.3 (screen codes), §5.6 (control codes), §6.3 (the processing loop) and §6.4
> (RLE) regardless. The upside: §A.9, §A.10 and §A.11 each print their expected render in the
> specification, so a decoder can be **verified against the document before it ever touches the
> server** — including §A.10's colon at column 12. ⚠ Note that **every** appendix frame asset
> carries its own 4-byte header and is rendered raw; none of them is body-only (§A).
>
> *(A clean-room build called this "the single biggest thing this document gets wrong about its
> own client's obligations" — VALIDATION.md, F24.)*

## 8. Mapping to Binding A / the shared model

Every message above is a projection of the same semantics Binding A carries as ROM bytes:
directories ↔ §7's six-part stream; frames ↔ §6's PETSCII+RLE; commands ↔ §4's byte set;
subsystems ↔ §8. The **model sections (§3, §4, §8, §5-screen-model) are authoritative**; this
binding must never expose behaviour Binding A cannot (spec §1.8), so a C64 and a browser stay in
sync.

## 9. Status and open items

Tiers 1–3 are implemented (`server/api_binding.py`) and clean-room validated — an isolated
builder produced a full Tier-3 Electron client from this document plus the model sections, twice,
and both runs' findings are folded in. See [VALIDATION.md](../VALIDATION.md).

Verified by measurement rather than assertion: the `frame` cell grid against an independent §6
decoder (14,400 of 14,400 cells), the `cells` submission form over all 256 glyph codes in both
character sets with and without reverse video, `raw` round-tripping byte-identically, `lines`
truncation at 23 rows × 40 columns, and the documented error codes.

**Open:**

- Deploying port 6404 to the live server.
- A compact frame-grid encoding (the 960-cell array is verbose on the wire).
- Token lifetime / refresh, and rate limits.

*(This section was a phase-by-phase build log. It is deliberately short now: a stale log in a
normative document eventually contradicts it — this one still claimed the gateway auto-sends a
directory after `ready`, which §2 forbids and the server has never done. VALIDATION.md, F4.)*
