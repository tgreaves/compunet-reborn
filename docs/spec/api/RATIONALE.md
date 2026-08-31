# Binding B — design rationale

> Part of the [Compunet Client Specification](../README.md). This is the **companion to
> [api/README.md](README.md)**: that document specifies *what* the JSON API is, this one records
> *why* it is shaped that way — why a second binding exists at all, why WebSocket, why the server
> decodes PETSCII, and what was deliberately **not** built.
>
> Non-normative. Nothing here overrides the binding spec. It exists so that a future change
> cannot quietly undo reasoning that is no longer obvious — if you are about to alter a decision
> below, read why it was made first.

## 1. Why a second binding exists

Compunet Reborn carries one application model over multiple wire formats (§1.8). Binding A —
X.25-over-TCP with PETSCII — is the original protocol, preserved exactly so the C64 and Amiga
ROM clients keep working. But a *modern* client built on it has to reimplement a stack of things
that exist **only because a 1980s ROM expected them**:

- **Transport ceremony TCP already makes redundant** — `$01`/`$02` frame markers, byte-stuffing,
  CRC-CCITT, the `$20`–`$5F` sequence window, ACK-paced flow control (§2). TCP already guarantees
  reliable ordered delivery; for a from-scratch client this is pure legacy tax.
- **ROM-shaped payloads** — the six-part comma-delimited directory stream (§7), PETSCII frames
  with RLE, charset switches and control-code tables (§5–§6), the dual C64/Amiga
  fixed-width-vs-comma parsing constraint. Five clean-room builds spent most of their effort
  here, and the display bugs clustered here too ([VALIDATION.md](../VALIDATION.md)).

**The insight that makes a second binding cheap:** the service already has a transport-agnostic
core that every binding shares — `CompunetPage`/`CompunetDirectory` (content) and
`CompunetSession.handle_command` (command and subsystem semantics). Binding A's `_make_*`
builders are *just its serializer* on top of that core.

So Binding B is **not new behaviour**. It is a second serializer over the same core, doing the
PETSCII/RLE/six-part work **once on the server** instead of in every client. That is also why
the two bindings cannot drift: `api_binding.py` drives the same authoritative handlers and
serializes the resulting state (see [xref.md](../xref.md)).

## 2. The decisions, and why

| Decision | Choice | Why |
|---|---|---|
| **Shape of the contract** | A **JSON message schema**, transport-independent | The schema is the durable asset; transports are envelopes around it. This is what lets one API serve browser, desktop and mobile without forking |
| **Transport** | **Hybrid**: WebSocket gateway + REST reads | The Discord/Slack model (§4). Partyline *requires* server push; browse/read benefits from HTTP caching. Each subsystem lands on the transport that suits it |
| **Reference envelope** | **WebSocket** | The only full-duplex transport a **browser** can use, so it is the common denominator across browser and native. Native clients use it happily too |
| **Payload encoding** | **Structured JSON**; directories as entry lists, frames as a **40×24 cell grid** | This is the whole point: the client never parses PETSCII or the six-part stream. Directories-as-JSON removes the single largest and most error-prone chunk of client work |
| **Fidelity** | **Cell grid only** — pixel-faithful | The goal is the authentic Compunet look. Styled text runs (HTML-friendly, reflowable) and a server-rendered image mode were considered and **not** built |
| **Auth** | **Token-first**: `POST /v1/session` → bearer token | The password is sent once, never over the long-lived socket; tokens expire and revoke. Separate from the admin API's auth — this is end-user auth |
| **Port** | **Dedicated 6404** | Clean isolation from the admin API (6403) and X.25 (6400); simple to firewall and reason about |
| **Versioning** | `/v1/` prefix | Lets the binding evolve without a ROM-style hash gate |
| **Reference client** | TypeScript → `<canvas>` | One codebase serves a browser tab and, in an Electron shell, the desktop app |

Two consequences worth stating, because they are easy to lose:

- **Selection and column-cycling stay client-side.** Directory JSON carries every Part-5 column
  value per entry, so highlighting a row or cycling `F7`/`F8` needs no round-trip.
- **Silent failures became typed errors.** Binding A discards an upload into a full directory
  with no signal at all; Binding B returns `directory_full` / `permission_denied`. The binding may
  report *more* than Binding A, but must never *do* more (§1.8).

## 3. What was rejected, and why

Recording the alternatives matters more than recording the choice — the choice is visible in the
code, the reasoning is not.

| Rejected | Why not |
|---|---|
| **Raw-byte passthrough** (the old port-6502 tunnel: X.25 payloads wrapped in WebSocket frames) | It does not solve the actual problem. Clients still reimplement the entire ROM decode; only the framing changes. This was the removed web client's design, and it is why that client was so hard to finish |
| **REST-only** | No server push, so **Partyline cannot work** and a client can never reach Tier 3. Stateful navigation would also have to be encoded as explicit parameters |
| **gRPC / protobuf** | Better typing and codegen for native clients, but browsers need a proxy and lose real streaming. It would trade away the browser — the very environment the API exists for — and add a toolchain our payloads do not need |
| **Server-rendered images per frame** | Pixel-exact and trivial to display, but not selectable or inspectable, heaviest server cost, largest payloads |
| **Styled text runs** (lines of `{text,fg,bg}`) | HTML-friendly and reflowable, but loses the exact PETSCII graphics glyphs and fixed geometry. Rejected in favour of fidelity; the cell grid can always gain this as an *additional* mode later without breaking anything |
| **A custom binary protocol as the primary interface** | What WhatsApp/Telegram did, for scale and E2E-encryption reasons that do not apply here. JSON is what Discord and Slack move enormous volume on; binary is an optimisation, never the base |

**Held in reserve, deliberately not built:** a **raw-TCP, length-prefixed envelope** carrying the
*identical* JSON messages, for a future bespoke native client that wants the leanest path. It is
an add-on, not a fork — possible precisely because the schema is transport-independent. Do not
build it unless a real client needs it.

## 4. Prior art

The web/desktop/mobile split is a solved problem, and the dominant answers agree.

- **Discord** — a WebSocket **"Gateway"** carries realtime JSON events with heartbeats,
  per-event sequence numbers and session resume; a separate **REST API** handles actions. One API
  serves web, the **Electron** desktop app, and mobile. This is almost exactly Compunet's shape:
  **Partyline is the gateway; everything else is REST-style actions.**
- **Slack** — the same hybrid (REST Web API + a realtime WebSocket channel); desktop is Electron.
- **Telegram** — **MTProto** run over **TCP, HTTP *and* WebSocket**: native desktop uses TCP, web
  uses WS, the *same* messages either way. The purest example of schema decoupled from transport.
- **WhatsApp / Signal** — native mobile on a custom persistent-TCP protocol, web and desktop
  (Electron) on WebSocket. Native *can* skip WS, but the web path still needed it.
- **WebGL / Unity games** — identical netcode, but browser builds are **forced** onto WebSocket.
  The clearest proof that the browser is the binding constraint, not the native client.
- **VS Code / LSP** — **JSON-RPC** over stdio *or* sockets: durable evidence that decoupling a
  JSON message schema from its transport ages well.

## 5. Invariants (these still bind)

Constraints fixed before the build, which remain rules rather than history:

- **The X.25 binding is frozen, not deprecated.** The C64 and Amiga ROM clients keep speaking
  X.25-over-TCP on port 6400 unchanged. Binding B is strictly **additive** (§1.8).
- **Do not disturb the admin API.** The website depends on an aiohttp HTTP API on **port 6403**
  (`/api/auth`, `/api/users`, `/api/pending`, `/api/broadcast`, `/api/audit`, and
  `/ws/partyline` — a WebSocket, registered outside the `/api` prefix). That is
  account/admin management — a different concern. The client API
  **must not** rename, move, reshape, or share a route namespace with those `/api/*` routes;
  it uses `/v1/*` on its own port.
- **No duplicated content logic.** Binding B must remain a *serializer* over
  `CompunetDirectory`/`CompunetSession`. If it ever needs behaviour the core cannot express, the
  fix belongs in the core, where both bindings inherit it.
- **Never expose behaviour Binding A cannot reach**, or a C64 and a browser stop seeing the same
  Compunet.

## 6. Lessons from building it

Two things only surfaced once a *faithful* client existed, and both are now normative in the
binding spec:

- **CORS is not optional.** The API is consumed cross-origin by definition — a web client on its
  own host, and a desktop shell serving its page from a scheme of its own. Serving client and
  API from one origin in development hid this until the desktop build failed with a bare
  "failed to fetch", which looks exactly like a dead server.

  *(The reference deployment has since gone the other way and serves the client from the API's
  own origin — §1. That does not make CORS optional: it removes the requirement for THAT
  deployment while leaving it for every client hosted anywhere else, including the desktop app.)*
- **Building a real renderer found genuine errors in Binding A's spec** — directory geometry that
  five clean-room runs had not caught, because those clients silently compensated with their own
  offsets. Recorded in [VALIDATION.md](../VALIDATION.md). A second, independent implementation is
  a better spec test than another reading of it.

**Still outstanding:** deploying port 6404 to the live service, and a clean-room validation of
this binding of the kind Binding A had ([CLEANROOM.md](../CLEANROOM.md)). Tracking: **#91**.
