# Binding B — Client API (DRAFT)

> **Status: DRAFT — non-normative, not yet validated.** This is the modern **JSON API binding**
> (Binding B) introduced by the [Compunet Client Specification](../README.md) §1.8. It carries
> the **same application model** (§3 session, §4 commands, §8 subsystems, and §5's screen model)
> as the legacy X.25 binding (Binding A), in structured JSON instead of the ROM wire format.
> Scoped in [../API-RESEARCH.md](../API-RESEARCH.md). It becomes normative once built and
> validated the way Binding A was (a clean-room build). Until then, shapes may change.

## Locked decisions

- **Transport:** WebSocket **gateway** first (interactive session + server push), growing into a
  **hybrid** (gateway + REST reads) later. The Discord/Slack model.
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

Dedicated listener on **6404**. Two surfaces (REST arrives with the hybrid phase; the gateway is
Phase 1):

| Method | Path | Purpose | Phase |
|---|---|---|---|
| `POST` | `/v1/session` | log in with credentials → bearer token | 1 |
| `GET`  | `/v1/gateway` (WebSocket upgrade) | the interactive session | 1 |
| `GET`  | `/v1/dir/{page}` | a directory as JSON (cacheable) | later (hybrid) |
| `GET`  | `/v1/frame/{page}` | a frame as a cell grid | later (hybrid) |

`/v1/` is the version prefix so the binding can evolve without a ROM-style hash gate.

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
| `enter` | `page` | §4.7 DIR (`P`+idx) | enter the entry as a directory (opens a latent one if none) |
| `open` | `page` | §4.7 SHOW (`D`+idx) | read the entry's frame(s); or download/activate a program/link |
| `more` | — | §4.7 MORE | next frame of a multi-frame item |
| `finish` | — | §4.7 FINISH | leave the frame → its directory |
| `back` | — | §4.4 BACK | parent directory |
| `goto` | `target` (page # or keyword) | §4.4 GOTO | jump; reply is always a directory (§4.4) |
| `account` | — | §4.4 ACCOUNT | credit balance |
| `vote` | `page`, `score` (1–9) | §8.6 | vote on the entry |
| `life` | `page`, `days` | §8.6 | extend the entry's life |
| `idlookup` | `ids` (array of 8-char) | §4.4 | user-ID → real-name lookup |
| `mail.list` | — | §8.2 | mailbox as a directory |
| `mail.read` | `id` | §8.2 | read a message |
| `mail.send` | `to` (array), `subject`, `frames` (array of cell grids / editor pages) | §8.3.2 | send mail |
| `upload` | `title`, `kind` (`"T"`\|`"P"`), `price`, `life`, `frames` | §8.3.2 | content upload; **`kind` and `price` are required** (§8.3.2) |
| `partyline.send` | `text` | §8.5 | send a chat line |
| `partyline.command` | `text` (e.g. `*who`) | §8.5 | a Partyline `*`-command |
| `partyline.leave` | — | §8.5 | leave Partyline (`*quit`) → framed session resumes |
| `leave` | — | §4.4 LEAVE | log off |

Note there is **no** column-cycle command: directory JSON carries every Part-5 column value per
entry (§5 below), so the client cycles the visible column locally (the `F7`/`F8` behaviour of
spec §7.7) with no round-trip.

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
- `mail` list/read reuse `directory` (list) and `frame` (a message body), matching §8.2.
- `download` → program/telesoftware: `{ "type":"download", "filename":…, "machine":…, "bytes": <base64|url> }` (§8.3.1).
- `ack` → `{ "type":"ack", "id"?:…, "of":"vote" }` for state-changers that just confirm (§4.3).

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
- **Phase 2 (Tier 2):** account, mail read/send, download, vote/life, id-lookup.
- **Phase 3 (Tier 3):** upload (with `kind`/`price`), the editor path, Partyline.
- **Then hybrid:** add the REST read endpoints (§1), reusing these exact JSON shapes.
- **Open:** compact frame-grid encoding; token lifetime/refresh; rate limits; retire the legacy
  WS 6502 handler once this lands.
