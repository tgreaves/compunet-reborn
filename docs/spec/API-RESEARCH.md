# Client API — research & options (planning only)

> **Status: research / planning. Nothing here is built or normative.** This document scopes a
> *modern client API* for Compunet Reborn — a clean binding that lets web, mobile, and desktop
> clients talk to the service **without** reimplementing the X.25 framing or PETSCII decoding
> that exist today only to satisfy the original ROM. It is written to be decided on, not
> followed: it lays out options, trade-offs, and a recommendation, and ends with the open
> questions that need your call before any build.
>
> It is a companion to the [Compunet Client Specification](README.md), which specifies the
> **existing** protocol (X.25-over-TCP + PETSCII). This is the plan for a *second* way in.

## 0. Constraints fixed up front

- **Start from scratch.** The previous browser experiment (`client/web/`) and its
  binary-over-WebSocket tunnel (server `ws_handler`, port 6502) are **disregarded** as prior
  art — `client/web/` has been removed (recoverable from git history). The old WS tunnel just
  wrapped the raw ROM byte-stream in WebSocket frames, which is exactly the design this research
  rejects. Treat WS 6502 as **legacy to be retired**, not a foundation.
- **Do not disturb the admin API.** The website depends on an **aiohttp HTTP API on port 6403**
  (`/api/auth`, `/api/users`, `/api/pending`, `/api/broadcast`, `/api/audit`,
  `/api/ws/partyline`). It is a *different* concern (account/admin management) and is out of
  scope here. Any client API **must not** rename, move, reshape, or share a route namespace with
  those `/api/*` routes. (A new client API should use its own namespace — e.g. `/client/*` or
  `/v1/*` — or its own port.)
- **The wire protocol for native clients stays.** The C64 and Amiga ROM clients keep speaking
  X.25-over-TCP on port 6400 unchanged. The new API is *additive*.

## 1. Why an API at all

The current spec is one protocol carried three ways today:

| Port | Binding | Consumer |
|---|---|---|
| 6400 | X.25-over-TCP, raw PETSCII responses | C64 / Amiga ROM clients |
| 6401 | server-rendered PETSCII stream | dumb PETSCII terminals (SyncTerm, CCGMS…) |
| 6502 | X.25 payloads tunnelled in WebSocket frames | the (removed) web client — **to retire** |
| 6403 | aiohttp HTTP JSON | the **website admin** — *untouched, unrelated* |

A modern client built on 6400/6502 has to reimplement a stack of things that exist **only
because a 1980s ROM expected them**:

- **Transport ceremony that TCP already makes redundant** — `$01/$02` frame markers,
  `$01–$03` byte-stuffing, CRC-CCITT, the `$20–$5F` sequence window, and ACK-paced flow control
  (§2). TCP already guarantees reliable, ordered delivery; none of this adds anything for a
  from-scratch client. It is pure legacy tax.
- **ROM-shaped payload formats** — the six-part comma-delimited directory stream (§7), PETSCII
  frames with RLE + charset switches + control-code tables (§5–6), the dual C64/Amiga
  fixed-width-vs-comma parsing constraint, screen-code conversion, and so on. Every clean-room
  build we ran (six of them) spent most of its effort *here*, and the display bugs clustered
  here too.

**The insight that shapes every option below:** the service already has a clean, transport-
agnostic core that all bindings share —

- **Content model:** `CompunetPage` (page number, title, type, author, price, life, vote,
  frames, children) and `CompunetDirectory` (the tree), in `server/compunet_server.py`.
- **Command semantics:** `CompunetSession.handle_command` dispatches the command set and the
  subsystems; the `_make_*` builders are *just the X.25 serializer* on top of that core.

So an API is not new behaviour — it is a **new binding** that projects the *same* session/content
core into a modern, structured wire format, letting the server do the PETSCII/RLE/six-part work
once (server-side) instead of every client redoing it.

## 2. The two design axes

Every option is a point on two independent axes. Decide these two and the rest follows.

### Axis A — transport envelope

The JSON message schema (Axis B) is **transport-independent** — the same messages can ride any
of the envelopes below. So this axis is not "what is the API"; it is "which envelope(s) carry
it". The **binding constraint is the browser**: it cannot open a raw TCP socket or speak gRPC
natively, so any client set that includes a browser makes **WebSocket the common denominator**.
Native desktop/mobile clients can use WebSocket perfectly well too — mature libraries in every
language, built-in message framing, and `wss://` over 443 even traverses corporate proxies that
block custom TCP ports — and many "native" desktop apps are Electron/Tauri/Flutter shells that
reach for WS/HTTP by default anyway.

| Envelope | Shape | Browser | Native | Notes |
|---|---|---|---|---|
| **WebSocket** | one stateful session; client sends command messages, server pushes responses **and** unsolicited events | ✅ | ✅ | The common denominator; realtime/push are natural; built-in framing |
| **HTTP / REST** | stateless request→response; token auth | ✅ | ✅ | Cacheable, scriptable; **no server push** → Partyline/notifications don't fit alone |
| **Raw TCP + length-prefixed JSON** | the *same* messages in a `[len][payload]` frame | ❌ | ✅ | Leanest for a *bespoke* native client; browser can't use it — an optional add, never the base |
| **gRPC (HTTP/2 + protobuf)** | typed, codegen, bidi streaming | ⚠️ grpc-web only | ✅ | Only if native-first and browser demoted; adds a protobuf toolchain our payloads don't need |

Because the schema is the contract, the choice is **not either/or**: pick one *reference*
envelope (**WebSocket**) and, if wanted, add a second (REST for cacheable reads, or a raw-TCP
frame for a lean native client) carrying the **identical** messages. What you must **not** do is
fork the *schema* per environment — that is the mistake the removed web client's raw-byte tunnel
baked in. This is the "bindings over a shared model" idea (§5) applied one level down: the JSON
schema is the model; WebSocket / REST / raw-TCP are envelopes around it.

### Axis B — how much the server decodes (payload encoding)

This is the axis that actually determines whether the API is worth having.

| Choice | Directory | Frame | Client work | Fidelity |
|---|---|---|---|---|
| **B0 Passthrough** | raw six-part bytes | raw PETSCII + 4-byte header | client reimplements the whole ROM decode (this is what the old WS did) | exact, but no easier than 6400 |
| **B1 Structured data** | JSON: `entries[]` with number/title/type/size/has_subdir/column-values, breadcrumb, advert, column set | JSON: **expanded cell grid** (40×24 of `{code,fg,bg,reverse}`) *and/or* **styled text runs** (`{text,fg,bg}`), server having already applied RLE, charset, and control codes | client just draws cells / text; server owns all PETSCII plumbing | exact if cell-grid; "modernised" if text-runs |
| **B2 Image** | JSON entries (for interaction) | server renders a **PNG/WebP** of the 40×24 screen | client blits an image | pixel-exact, but not selectable/reflowable, heaviest server, largest payload |

The high-value default is **B1**: the six-part stream and PETSCII decoding are ROM artifacts;
turning them into JSON is the single biggest reduction in client complexity. Directories as
JSON is an unambiguous win. For frames, offering **both** an expanded **cell grid** (for a
faithful 40×24 renderer using the appendix font/palette) *and* **styled text runs** (for a
DOM/HTML client that wants selectable, reflowable text) covers both kinds of client cheaply —
the server already has to walk the frame to expand RLE, so emitting either representation is
nearly free.

### Prior art — how comparable multi-environment apps solve this

The web/desktop/mobile split is a solved problem, and the dominant answers all point the same
way — a JSON message schema, WebSocket for realtime, and the schema kept independent of the
transport.

- **Discord** — a **hybrid**: a WebSocket **"Gateway"** carries realtime JSON events (messages,
  presence, typing) with heartbeats, per-event **sequence numbers**, and **session resume**
  (reconnect and replay from the last seq); a separate **REST API** handles actions (send, fetch
  history, upload files). One API serves web, the **Electron desktop app** (literally the web
  client in a shell), and mobile; voice/video is a third WebRTC path. This is almost exactly
  Compunet's shape — **Partyline is the gateway; everything else is REST-style actions.**
- **Slack** — the same hybrid (REST Web API + a WebSocket realtime / Socket-Mode channel);
  desktop is Electron again.
- **Telegram** — **MTProto**, a single message protocol run over **TCP, HTTP, *and*
  WebSocket**: the native desktop client (C++/Qt) uses TCP, the web client uses WS, the *same*
  messages either way. The purest example of *schema decoupled from transport* — our
  envelope-swappable model in production.
- **WhatsApp / Signal** — native mobile has used a custom persistent-TCP protocol while web and
  desktop (Electron) use WebSocket. Native *can* skip WS with a bespoke envelope, but the web
  path still needed one, and the custom binary path carried real complexity — chosen for scale
  and end-to-end-encryption reasons that do **not** apply to Compunet.
- **WebGL / Unity games** — identical netcode, but browser builds are **forced** onto WebSocket
  because a browser cannot use raw sockets. The clearest proof that the **browser** is the
  binding constraint, not the native client.
- **VS Code / Language Server Protocol** — **JSON-RPC** carried over stdio *or* sockets: a
  durable demonstration that decoupling a JSON message schema from its transport ages well.

Two lessons carry over directly: (1) the **hybrid WebSocket-gateway + REST** model is the
industry-standard answer to exactly this multi-client situation, and (2) when a bespoke native
transport is ever justified, the winners **share one message schema across transports** rather
than forking the protocol. And note what none of them do at consumer scale: make a **custom
binary protocol the *primary* interface** — that is reserved for scale/encryption needs Compunet
lacks, and JSON is what Discord and Slack move enormous volume on (binary is a later
*optimization*, never the base).

## 3. The options (transport × encoding)

### Option 1 — JSON-over-WebSocket session API  ·  *Phase-1 core; the "gateway" half of the recommended hybrid*

A stateful WS session mirroring how a client actually behaves. Axis A = WebSocket, Axis B = B1.

- Client connects, sends `{type:"login", user, pass}`, gets `{type:"welcome", frame:…, account:…}`.
- Client sends command messages naming the *intent*, not the ROM byte:
  `{type:"open", page}` (SHOW), `{type:"enter", page}` (DIR), `{type:"back"}`,
  `{type:"more"}`, `{type:"goto", keyword|page}`, `{type:"vote", page, score}`,
  `{type:"life", page, days}`, `{type:"mail.list"}`, `{type:"mail.read", id}`,
  `{type:"mail.send", to[], subject, frames[]}`, `{type:"upload", title, kind, price, life, frames[]}`.
- Server replies with typed messages: `directory`, `frame`, `ack`, `error`, `download`,
  `account`, `mail`, and — crucially — **pushes** `partyline` lines and `notice`
  (e.g. unread-mail) without a request.
- Selection is client-local (as in the spec); the client just names the page it acts on, so
  the fiddly "highlighted index" wire detail disappears.

*Why gateway-first:* it fits the interaction model (a live session with push), makes Partyline
and notifications natural rather than bolted on, and lets the server own all PETSCII/six-part
work. It is the smallest conceptual surface for a full-featured client, and it is exactly the
gateway half of the recommended hybrid (§7) — so building it first commits to nothing that a
later REST read path would undo.

### Option 2 — REST + JSON

Axis A = HTTP, Axis B = B1. `POST /v1/session` (login → token), then
`GET /v1/dir/{page}`, `GET /v1/frame/{page}?page=n`, `GET /v1/account`,
`GET /v1/mail`, `POST /v1/mail`, `POST /v1/upload`, `POST /v1/vote`, etc.

*Strength:* trivially cacheable, scriptable, and stateless; great for read-only / integration
use (a "browse Compunet" widget, bots, monitoring). *Weakness:* **Partyline and push don't
exist over plain REST** — you'd still need WebSocket/SSE for those, so a pure-REST client can't
reach Tier 3. Stateful navigation (current directory, paging, latent-directory creation) has to
be encoded as explicit parameters rather than session state.

### Option 3 — Hybrid: WebSocket gateway + REST  ·  **recommended target architecture**

Axis A = Hybrid, Axis B = B1. A WebSocket **gateway** carries the interactive session and all
server push (Partyline, notices) — Option 1 — while **REST** endpoints (Option 2) serve the
cacheable request→response reads and actions. This is the **Discord/Slack model** (§2 prior
art): gateway for realtime, REST for actions, one JSON schema shared by both.

*Strength:* each subsystem lands on the transport that suits it; the read path gets HTTP caching
and scriptability; realtime gets a proper push channel; and web, Electron/Tauri desktop, and
mobile are all served by the same two endpoints. *Cost:* two mechanisms to build and document,
with auth spanning both — mitigated because they share the Axis-B message shapes verbatim, so
the *schema* is written once. Reaching it is incremental: **build the gateway first (Option 1),
add REST reads later**; the JSON payloads are identical, so nothing is thrown away.

### Option 4 — Thin length-prefixed passthrough  ·  *not recommended*

Axis A = WebSocket or TCP, Axis B = B0. Replace `$01…$02`+CRC+seq with a trivial
`[uint32 length][type][payload]` frame, but keep the **payload** as today's raw PETSCII / six-
part bytes. This is the old WS tunnel, tidied. *Why it's here:* it's the least server work and
keeps byte-exact fidelity. *Why not:* it does **not** solve the actual problem — clients still
reimplement the entire ROM decode. Only worth it if the goal were a second *native-fidelity*
client rather than an easy-to-build one.

## 4. Cross-cutting concerns (independent of the option chosen)

- **Auth & session.** Login reuses `CompunetSession.handle_login`. For WS, the socket *is* the
  session. For REST, issue a bearer token and keep per-token session state server-side (current
  directory, paging, purchases, pending upload). Either way, **do not** reuse the admin API's
  auth — this is end-user auth, separate from admin.
- **Frame rendering fidelity.** B1's cell-grid keeps the *option* of pixel-exact rendering
  (client uses the appendix font + palette). The styled-text-runs form is for clients that want
  HTML/selectable text and accept "faithful-ish". Decide whether pixel-exact is a requirement
  for the first client or a later mode.
- **Directory is the easy win.** Regardless of option, emit directories as JSON
  (`entries[]` + column set + breadcrumb + advert + optional header-frame). This alone removes
  the largest and most error-prone chunk of client work (the six-part stream and the
  comma/fixed-width dual-parse constraint).
- **Subsystem fit.** Mail (list/read/send), download, upload, editor-submit, VOTE/LIFE, UCAT,
  ID-lookup all map cleanly to request→response. **Partyline is the outlier** — it is a raw,
  line-based, bidirectional session and *requires* a push-capable transport (WS/SSE). This is
  the single strongest argument for WebSocket being in the mix (Options 1 or 3).
- **Directory creation & uploads.** The DIR→latent-directory→upload-materialises model (spec
  §7.4/§8.3.2) maps to `enter(page)` returning an empty directory then `upload(...)`; the
  server-side checks (permission, ≤11 entries) are unchanged. The API should surface the
  full-directory condition as an explicit error rather than the silent discard the ROM path has.
- **Versioning.** A JSON API should carry an explicit version (`/v1/…` or a `version` field) so
  it can evolve without a ROM-style hash gate.
- **Content model reuse.** All options are a thin binding over the existing
  `CompunetDirectory` + `CompunetSession`. No content logic is duplicated; the server gains a
  *serializer* (session core → JSON) and, for B1 frames, a *decoder* (PETSCII/RLE → cells/runs)
  that it can reuse from the existing render path.

## 5. What this means for the specification

The cleanest structural outcome — and the one that makes the API a first-class citizen rather
than a bolt-on — is to **refactor the spec into a layered shape**:

```
Application model (transport-agnostic)
  · content model (pages, directories, frames)
  · command / navigation semantics
  · subsystems (mail, download, upload, editor, Partyline, VOTE/LIFE)
  · the display contract (PETSCII, palette, RLE)   ← needed only by faithful renderers

Bindings (how the model is carried on the wire)
  · Binding A — legacy X.25-over-TCP + raw PETSCII   (today's §§2, 6, 7 wire detail)   → ROM/native
  · Binding B — modern JSON API                       (new)                             → web/mobile/desktop
```

Most of the current spec's *semantics* (§3 session, §4 commands, §8 subsystems) are already
transport-agnostic and would move up into the application-model layer largely unchanged; only
the *wire-format* parts (§2 framing, §6 frame bytes, §7 six-part stream) are binding-specific.
The conformance tiers (Browse / Interact / Full) stay, but become **per-binding** (a client
declares its tier *and* its binding). This mirrors what the server already does internally
(one session/content core, multiple serializers), so the spec would finally describe the system
as it is actually built.

*Lighter-touch alternative:* leave the current spec as the "X.25 binding" and add a **new
sibling document** (`docs/spec/API/…`) for the JSON binding that references the shared semantics
sections. Less disruption now, some duplication later. The full refactor is cleaner long-term;
the sibling doc is faster to start.

## 6. Server implementation shape (when we do build)

- Add a **new binding module** (e.g. `server/api_binding.py`) that imports and reuses
  `CompunetDirectory` and `CompunetSession`. No fork of content logic.
- Add a **JSON serializer** for the session core (directory→JSON, account→JSON, mail→JSON) and,
  for B1 frames, reuse/extract the existing frame-expansion logic to emit a cell grid and/or
  styled runs.
- **Listener:** either a new port, or new routes on a **separate** aiohttp app — but **never**
  under the admin `/api/*` namespace. Recommend `/v1/*` on a dedicated client-API port (keeps it
  clearly separate from admin 6403 and from X.25 6400).
- **Retire** the orphaned `ws_handler` / WS 6502 once the new binding lands (nothing consumes it
  after `client/web/` removal).
- Add API request/response logging to the existing audit trail.

## 7. Recommendation

The through-line: **the JSON message schema is the contract; the transport is a swappable
envelope.** That single decision is what lets one API serve browser, native desktop, and mobile
without forking.

1. **Schema-first (Axis B = B1).** Commit to structured JSON as *the* deliverable — directories
   as entry lists; frames as a cell grid *and* styled text runs; commands named by intent. Every
   envelope carries these same shapes. This is the whole point of the exercise and the asset that
   outlives any transport choice.
2. **Target architecture = Hybrid gateway + REST (Option 3), the Discord/Slack model.** A
   **WebSocket gateway** for the interactive session and all server push (Partyline, notices),
   plus **REST** for cacheable reads and actions. WebSocket is the reference envelope because it
   is the **browser-and-native common denominator**; native Windows/Mac clients use it happily
   (and if any are Electron/Tauri, it is their default). Keep the door open — but do not build yet
   — to a **raw-TCP length-prefixed envelope** for a future bespoke native client: it carries the
   *identical* messages, so it is an add-on, not a fork. Do **not** adopt gRPC/protobuf unless
   browser support is ever dropped.
3. **Build incrementally, gateway-first.** Ship **Option 1 (the WebSocket gateway)** first — it
   is a complete full-featured client on its own and is literally the gateway half of Option 3 —
   then add REST reads to reach the hybrid. Nothing is thrown away because the JSON payloads are
   shared.
4. **Spec:** do the **layered refactor** (application model + transport bindings). If that is too
   much to take on at once, start with the **sibling-document** approach and refactor later.
5. **Phase 1 scope:** login + directory browse + frame render (Tier 1 over the gateway), proving
   the JSON shapes against the live content model with a tiny reference client. Then layer Tier 2
   (mail/download/VOTE/LIFE) and Tier 3 (upload/editor/Partyline), then add REST reads.

## 8. Open questions for you

*Transport is now settled (see §7): schema-first JSON, a **WebSocket gateway** built first,
growing into a **hybrid gateway + REST**, with a raw-TCP envelope held in reserve for a future
bespoke native client. gRPC/protobuf is ruled out unless browser support is ever dropped. The
questions below are the decisions still genuinely open.*

1. **Build order:** gateway-only for Phase 1 and add REST reads later (recommended), or stand up
   the REST read path alongside the gateway from the start?
2. **Frame encoding:** ship the **cell grid** (pixel-faithful), **styled text runs**
   (HTML-friendly), or **both**? Is pixel-exact fidelity a Phase-1 requirement or a later mode?
   (Is an image/B2 mode ever wanted — e.g. a share-a-screenshot feature?)
3. **Spec structure:** full **layered refactor** now, or a **sibling API document** first?
4. **Auth:** simple bearer token issued from the existing user store? Any need for
   OAuth/third-party, or is username/password → token sufficient?
5. **Namespace/port:** dedicated **client-API port**, or namespaced routes alongside (but
   separate from) the website's aiohttp app? (Admin `/api/*` stays untouched regardless.)
6. **Fidelity vs. modernisation:** should the API preserve the exact Compunet look (40×24,
   PETSCII, palette) as the contract, or also permit "modern" clients that reflow/restyle
   content? This decides how much of §5's display contract is normative for the API binding.
7. **Reference client:** what should the first API client be (a small web browse client? a CLI?)
   so the API is validated the way the clean-room runs validated the spec?
