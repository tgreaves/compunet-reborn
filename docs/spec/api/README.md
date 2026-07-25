# Binding B — Client API (DRAFT)

> **Status: DRAFT — non-normative, not yet validated.** This is the modern **JSON API binding**
> (Binding B) introduced by the [Compunet Client Specification](../README.md) §1.8. It carries
> the **same application model** (§3 session, §4 commands, §8 subsystems, and §5's screen model)
> as the legacy X.25 binding (Binding A), in structured JSON instead of the ROM wire format.
> Design rationale — why it is shaped this way, and what was rejected — is in
> [RATIONALE.md](RATIONALE.md). It becomes normative once built and
> validated the way Binding A was (a clean-room build). Until then, shapes may change.

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

| Method | Path | Purpose | Phase |
|---|---|---|---|
| `POST` | `/v1/session` | log in with credentials → bearer token | 1 |
| `GET`  | `/v1/gateway` (WebSocket upgrade) | the interactive session | 1 |
| `GET`  | `/v1/dir/{page}` | a directory as JSON (cacheable, bearer auth) | done |
| `GET`  | `/v1/frame/{page}[?index=N]` | a frame as a cell grid (bearer auth) | done |

`/v1/` is the version prefix so the binding can evolve without a ROM-style hash gate.

**CORS is required (normative).** This binding exists to be called by clients served from a
**different origin** — a web client on its own host, and the Electron shell, which serves its
page from an ephemeral `127.0.0.1` port. The server therefore **MUST** send
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

| `type` | Fields | Model | Meaning |
|---|---|---|---|
| `auth` | `token` | §3.5 | first message; authenticate the socket |
| `dir` | — | §4.7 DIR (bare `P`) | show the **current** directory — this is how the welcome screen reaches the root (§2 step 3). Also the "refresh" after an action |
| `enter` | `page` | §4.7 DIR (`P`+idx) | enter the entry as a directory (opens a latent one if none) |
| `open` | `page` | §4.7 SHOW (`D`+idx) | read the entry's frame(s); or download/activate a program/link |
| `more` | — | §4.7 MORE | next frame of a multi-frame item |
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
| `mail.send` | `to` (array), `subject`, `frames` (editor pages, §5.4) | §8.3.2 | send mail |
| `upload` | `title`, `kind` (`"T"`\|`"P"`), `price`, `life`, `frames` | §8.3.2 | content upload; **`kind` and `price` are required** (§8.3.2) |
| `download.fetch` | — | §8.3.1 | after a `download` descriptor, pull the payload (the ROM's `$40` proceed) |
| `partyline.send` | `text` | §8.5 | send a chat line |
| `partyline.command` | `text` (e.g. `*who`) | §8.5 | a Partyline `*`-command |
| `partyline.leave` | — | §8.5 | leave Partyline (`*quit`) → normal commands resume |
| `leave` | — | §4.4 LEAVE | log off |

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
  "advert": ["V1.00: OUR FIRST OFFICIAL RELEASE!", "THANKS FOR MAKING THIS POSSIBLE"], // Part 2
  "mailWaiting": true,          // the red MAIL marker (§7.2)
  "header": <frame|null>,       // Part 1 header frame (COMPUNET logo) as a cell grid, or null → built-in template
  "hasMore": false,             // paging (>11 entries, §7.6)
  "entries": [
    { "index": 0, "page": 101, "title": "NEWS", "type": "T", "size": null, "hasSubdir": true,
      "values": ["", "ADMIN", "    -", "", "   99"] }   // parallel to columns; already justified (§7.3)
    // … up to 11 …
  ]
}
```

`type` is the base entry type (`T`/`D`/`P`/`PP`/`S`/`L`, spec §7.4); `size` is the K/page count
or null; `hasSubdir` is the `+` marker. The client dispatches SHOW vs DIR from these. `columns`
and each entry's `values` are **parallel arrays** carrying the strings **verbatim**, with the
server's per-column justification already applied (§7.3) — the leading spaces on `" PRICE"` /
`" AUTHOR"` / `" LIFE"` and the right-justified values are the positioning. The client draws
`columns[i]` (header) and `values[i]` (value) as-is from the pane's base column (screen col 31);
it does **not** re-justify. It renders one column at a time and cycles locally (§7.7).

### 5.2 `frame`

Server-rendered 40×24 grid, RLE / charset / control codes already expanded. The client just
paints each cell (glyph from the appendix font, `fg`/`bg` from the palette).

```jsonc
{
  "type": "frame", "id"?: …,
  "border": 4, "background": 15,   // low-nibble palette indices from the 4-byte header (§6.2)
  "morePages": true,               // flags bit 7 — another frame follows (§6.5)
  "rows": 24, "cols": 40,
  "cells": [ /* row-major, rows*cols entries */
    { "g": 0, "fg": 6, "bg": 15, "rv": 0 }
    // g   = glyph index 0–255 (0–127 = uppercase/graphics set, 128–255 = lowercase set; 128 glyphs each, §5.2/§5.4)
    // fg,bg = palette index 0–15 (§5.5)
    // rv  = reverse-video flag 0|1 (§5.7)
  ]
}
```

*(Compact encodings — parallel typed arrays, run-length, or base64 — are a later optimization;
the draft fixes the logical shape first.)*

### 5.3 Others

- `account` → `{ "type":"account", "creditText":"999.00", "credit": 999.0 }` (§4.4).
- **Mail** (§8.2) reuses the shapes above: `mail.list` → a `directory` carrying
  `"context":"mail"`, its own Part-5 set `[" SENDER"," DATE"," STATUS"]`, and entries whose
  `page` is the message id; `mail.read` → a `frame`. An empty mailbox still returns one
  `(NO MAIL)` placeholder entry (§7.3). A client **MUST** take the columns from the response —
  they differ from a content directory's (§7.2).
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

**⚠ Known model gap — one colour per page.** A Binding-A frame changes colour **mid-line** via
embedded control codes (§5.4/§A.4); the shape above cannot express that, so pages composed
through this binding are monochrome. This is a **violation of the §1.8 invariant** in the making
— Binding B must never be able to express *more* than Binding A, but neither should it express
meaningfully *less* of what the editor (§8.4) exists to produce. It is recorded here rather than
silently tolerated.

The intended fix is a **spans** form alongside the flat one, so both remain valid:

```jsonc
{ "lines": [ [ {"t":"HELLO ","c":5}, {"t":"WORLD","c":2} ], "PLAIN LINE" ] }
```

— a line is either a string (whole line takes the page `colour`) or an array of
`{t, c}` runs. Until a server implements it, clients **MUST** send the flat form, and a
server that does not understand spans **MUST** reject them with `invalid` rather than
dropping the colour information.

**Upload** (`upload`) carries `title`, `kind` (`"T"`/`"P"`), `price`, `life`, and `frames`.
Unlike Binding A's multi-step wire dance (`U` → validation → frame DATs → finishing `P`), it is
**one message**: the server performs the same commit through the same core routine and replies
with the **refreshed directory** (the equivalent of the finishing `P`). For `kind: "P"` the
frames are base64 program blobs rather than editor pages. The checks Binding A applies silently
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

- **Frames:** blit the `cells` grid — glyph `g` from the appendix font (§A.5), colours from the
  palette (§A.3), invert on `rv`. No PETSCII/RLE logic in the client; the server did it.
- **Directories:** compose locally from the built-in template (§A.6) + the display rules
  (§7.5–§7.7) — this is the only real client-side layout work, and it is what keeps selection,
  scrolling, and column-cycling instant (no server round-trip).

## 8. Mapping to Binding A / the shared model

Every message above is a projection of the same semantics Binding A carries as ROM bytes:
directories ↔ §7's six-part stream; frames ↔ §6's PETSCII+RLE; commands ↔ §4's byte set;
subsystems ↔ §8. The **model sections (§3, §4, §8, §5-screen-model) are authoritative**; this
binding must never expose behaviour Binding A cannot (spec §1.8), so a C64 and a browser stay in
sync.

## 9. Build plan & open items

- **Phase 1a — DONE (server):** `POST /v1/session` (token), the WebSocket gateway
  (`auth`→`ready`→auto `directory`), and directory navigation (`enter`/`back`/`goto`/`more`/
  `finish`/`dir`) with the `directory` serializer. Implemented in `server/api_binding.py` as a
  serializer over the existing `CompunetSession`/`CompunetDirectory` core (it drives the
  authoritative `handle_command` for its side-effects, then serializes model state), on port
  6404, isolated from the admin API. Validated locally end-to-end (HTTP token + WS round-trip +
  navigation). `open` currently returns a not-implemented error pending the frame renderer.
- **Phase 1b — DONE (server):** the `frame` cell-grid renderer (`frame_to_cells`) implements the
  §6.3 processing loop with §5 control codes (colour, charset `$0E`/`$8E`, reverse, cursor,
  the §5.6.1 auto-wrap guard) and §6.4 RLE, producing a 40×24 grid of `{g,fg,bg,rv}`. `ready`
  now carries the welcome frame; `open`/`more` return real frames. Verified by rendering the
  welcome frame and a page to text.
- **Phase 1 client — DONE:** the canvas reference client (`client/web/`) — login, WS gateway,
  faithful directory composition (template chrome + red-first / blue-selection bar + column
  cycling) and frame rendering (font + palette from the appendix). Verified end-to-end in a
  browser against the dev server (`server/run_api_dev.py`): token, gateway, welcome, directory,
  arrow-select, DIR into a sub-directory, BACK, and SHOW a page. Written as runnable ES-module
  JS (ports to TypeScript); assets extracted from the appendix by `client/web/gen_assets.py`.
  **This completes Phase 1 (Tier 1) end-to-end.**
- **Next:** Tier 2 (account, mail, download, vote/life) and Tier 3 (upload, editor, Partyline),
  then the REST read path (hybrid).
- **Phase 2 (Tier 2) — server + client DONE except mail *send*:** `account`, `mail.list` /
  `mail.read`, `idlookup`, `vote`, `life`, `ucat`, and the two-step `download` /
  `download.fetch`. Verified in-browser (credit, mailbox with its own columns, ID lookup,
  vote + life persisting). **Mail send** is deferred with the editor (Phase 3) since it
  submits composed frames through the same upload path (§8.3.2). The download payload path is
  implemented but not yet exercised against a real program page.
- **Phase 3 (Tier 3) — DONE.** Partyline over the gateway (push events, no raw session);
  one-message `upload` with the permission / directory-full checks surfaced as typed errors;
  `mail.send`; and a client-side editor that submits structured pages the server encodes.
  Verified end-to-end: two-user Partyline chat and commands; a page composed in the browser,
  uploaded, stored and rendered back; mail delivered and read from the mailbox.
- **Phase 4 — hybrid + packaging.** REST reads (`GET /v1/dir/{page}`, `GET /v1/frame/{page}`)
  are live, bearer-authenticated and stateless, carrying the same JSON shapes as the gateway —
  the hybrid target architecture is complete. The legacy raw-bytes WebSocket (port 6502) is
  retired and the `websockets` dependency dropped. An Electron shell (`client/electron/`) wraps
  the same web client for desktop. **Outstanding:** deploying port 6404 to the live server, and
  a clean-room validation of this binding (as Binding A had, #111).
- **Open:** compact frame-grid encoding; token lifetime/refresh; rate limits; retire the legacy
  WS 6502 handler once this lands.
