# Compunet Client Specification

> **Status:** Written and validated. All section files (§§1–8 + appendices) are complete,
> and the spec has been independently verified by **five** source-isolated clean-room builds
> (see [VALIDATION.md](VALIDATION.md)). Tracking: issue #111.
>
> This document is **Binding A** — the X.25-over-TCP wire protocol, and the binding the C64 and
> Amiga clients use. The modern **JSON API (Binding B)** is specified separately in
> [api/README.md](api/README.md) (draft; tracking issue #91).

This is the normative, platform-agnostic specification for building a **Compunet Reborn**
client that connects to the modern server over **TCP/IP**. It is the single source of
truth: an implementer (human or LLM) should be able to build a working client **from this
spec alone**, without reading the C64 or Amiga source.

Every normative claim is derived from the server (`server/compunet_server.py`, the live
protocol authority) and verified against both reference clients (C64, Amiga) — which
triangulate the protocol: a claim must match the bytes on the wire *and* explain both
clients' behaviour.

## Architecture: one model, multiple bindings

Compunet Reborn separates **what** the service does from **how** it is carried on the wire:

- **The application model** (transport-agnostic): the content model (pages, directories,
  frames), the command and navigation semantics, and the subsystems (mail, downloads,
  uploads, editor, Partyline, LIFE/VOTE). This is the *meaning* of the service, identical
  for every client.
- **Transport bindings** (how the model is carried): concrete wire formats.

  | Binding | Wire format | Port | Clients | Spec |
  |---|---|---|---|---|
  | **A** | X.25-over-TCP + PETSCII | 6400 | C64, Amiga (ROM) | **this document** |
  | **B** | JSON over WebSocket / HTTP | 6404 | web, Electron desktop, mobile | [api/README.md](api/README.md) |

Bindings exist because clients differ in capability. The **C64 and Amiga ROM clients** lack
the memory and compute for JSON or a WebSocket, so they stay on **Binding A permanently** —
it is frozen, not deprecated. Because both bindings project one model, a C64 and a browser see
the same Compunet, and Binding B must never expose behaviour Binding A cannot.

**This document is Binding A.** Its *wire-format* sections (§2 framing, §6 frame bytes, §7
directory stream, and the PETSCII encoding within §5) are specific to this binding; its
*semantic* sections (§3 session, §4 commands, §8 subsystems, and the abstract screen model in
§5) are the shared application model that Binding B reuses. Each section is tagged in the
index below; §1.8 gives the full map.

## Scope

- **In scope:** the Reborn protocol over TCP — transport framing, session lifecycle,
  command protocol, the PETSCII display contract, frame and directory formats, and the
  application subsystems.
- **Out of scope (platform notes, not spec):** C64/Amiga hardware (ACIA, the "brick"
  modem, AT commands, `cnet.device`), toolchains, memory maps, and UI/input/local-storage
  choices — these live in platform notes and are non-normative.

## How to read this spec

- **Normative language** (RFC 2119): **MUST / SHOULD / MAY**. Used for the protocol and
  for the key display constraints (window character dimensions, PETSCII look & feel).
  Pragmatic prose is used elsewhere and is explicitly marked non-normative where it matters.
- **Conformance tiers** let a client be useful without implementing everything. Tiers are
  **per-binding**: a client states its binding *and* its tier (e.g. "Binding A, Tier 1").

  | Tier | Name | A conforming client at this tier can… | Requires §§ |
  |---|---|---|---|
  | **1** | **Browse** | connect, identify, log in, navigate directories, render frames | 2, 3, 4, 5, 6, 7 |
  | **2** | **Interact** | Tier 1 + read/send mail, download, LIFE/VOTE | + relevant 8.x |
  | **3** | **Full** | Tier 2 + uploads, editor, Partyline | + all of 8 |

## Sections

The **Layer** column marks whether a section is shared **model** (semantics reused by every
binding), this binding's **wire** format (X.25-over-TCP / PETSCII), or **mixed**.

| § | File | Layer | Contents |
|---|---|---|---|
| 1 | [01-overview.md](01-overview.md) | model | Purpose, architecture & bindings, scope, conformance tiers, conventions |
| 2 | [02-transport.md](02-transport.md) | **wire** | X.25-over-TCP framing — delimiters, byte-stuffing, tokens, CRC, sequencing, flow control |
| 3 | [03-session.md](03-session.md) | model | Session lifecycle — connect → identification / machine-type detection → login → online → disconnect |
| 4 | [04-commands.md](04-commands.md) | model | Command protocol — command semantics, request/response shapes, ack conventions (`@`/`A`/`B`) |
| 5 | [05-display.md](05-display.md) | mixed | Display contract — screen model & palette (model); PETSCII screen-code→glyph mapping, control codes, RLE (wire) |
| 6 | [06-frame-format.md](06-frame-format.md) | **wire** | Frame (SEQ) format — on-the-wire encoding of a page |
| 7 | [07-directory-format.md](07-directory-format.md) | **wire** | Directory listing wire format, entry types, paging |
| 8 | [08-subsystems.md](08-subsystems.md) | model | Content/paging, Mail (Courier), downloads & uploads, Editor, Partyline, UCAT/LIFE/VOTE |
| A | [99-appendices.md](99-appendices.md) | mixed | Command table, token table, PETSCII charset + palette, minimal end-to-end session trace |

## Companion documents (kept beside the spec)

- **[api/](api/README.md)** — **Binding B**, the modern JSON API for web / desktop / mobile
  clients, as its own document set:
  - [api/README.md](api/README.md) — the binding spec: endpoints, auth, message schema,
    directory/frame shapes, push events. Draft until clean-room-validated.
  - [api/RATIONALE.md](api/RATIONALE.md) — why it is shaped that way, what was rejected, and the
    invariants it must keep (e.g. never expose behaviour Binding A cannot reach).
- [xref.md](xref.md) — implementation cross-reference: spec § → server location, so the
  spec and server can't silently drift apart.
- [VALIDATION.md](VALIDATION.md) — validation record: the cross-checks against both
  reference clients, the contradictions resolved, and the honest residual gaps.
- [CLEANROOM.md](CLEANROOM.md) — how to validate the spec by having a fresh, source-isolated
  agent build a client from `docs/spec/` alone (the honest "buildable from the spec?" test).
- [AUDIT.md](AUDIT.md) — the documentation audit & coverage matrix that scoped this work
  (Phase 1); kept for provenance.

## Relationship to other docs

This spec **supersedes** the protocol/display content currently spread across
`docs/PROTOCOL.md` and `docs/partyline.md`; those are folded in and then retired or
relabelled (see AUDIT.md → *Document inventory*). `docs/TERMINAL.md` is **not** superseded
— it documents a separate client we built (the server-rendered PETSCII terminal, port
6401) and is out of this spec's scope. Platform-specific and reverse-engineering documents
remain as **non-normative** platform notes / provenance and are cited, not duplicated, here.
