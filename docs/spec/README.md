# Compunet Client Specification

> **Status:** Written and validated. All section files (§§1–8 + appendices) are complete,
> and the spec has been independently verified by a source-isolated clean-room build (see
> [VALIDATION.md](VALIDATION.md)). Tracking: issue #111.

This is the normative, platform-agnostic specification for building a **Compunet Reborn**
client that connects to the modern server over **TCP/IP**. It is the single source of
truth: an implementer (human or LLM) should be able to build a working client **from this
spec alone**, without reading the C64 or Amiga source.

Every normative claim is derived from the server (`server/compunet_server.py`, the live
protocol authority) and verified against both reference clients (C64, Amiga) — which
triangulate the protocol: a claim must match the bytes on the wire *and* explain both
clients' behaviour.

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
- **Conformance tiers** let a client be useful without implementing everything:

  | Tier | Name | A conforming client at this tier can… | Requires §§ |
  |---|---|---|---|
  | **1** | **Browse** | connect, identify, log in, navigate directories, render frames | 2, 3, 4, 5, 6, 7 |
  | **2** | **Interact** | Tier 1 + read/send mail, download, LIFE/VOTE | + relevant 8.x |
  | **3** | **Full** | Tier 2 + uploads, editor, Partyline | + all of 8 |

## Sections

| § | File | Contents |
|---|---|---|
| 1 | [01-overview.md](01-overview.md) | Purpose, scope, conformance tiers, normative conventions |
| 2 | [02-transport.md](02-transport.md) | TCP, ports; X.25-over-TCP framing — delimiters, byte-stuffing, tokens, CRC, sequencing, flow control |
| 3 | [03-session.md](03-session.md) | Session lifecycle — connect → identification / machine-type detection → login → online → disconnect |
| 4 | [04-commands.md](04-commands.md) | Command protocol — single-letter commands, request/response shapes, ack conventions (`@`/`A`/`B`) |
| 5 | [05-display.md](05-display.md) | Display contract (PETSCII) — screen model, window character dimensions, screen-code→glyph mapping, 16-colour palette, control codes, RLE |
| 6 | [06-frame-format.md](06-frame-format.md) | Frame (SEQ) format — on-the-wire encoding of a page |
| 7 | [07-directory-format.md](07-directory-format.md) | Directory listing format, entry types, paging |
| 8 | [08-subsystems.md](08-subsystems.md) | Content/paging, Mail (Courier), downloads & uploads, Editor, Partyline, UCAT/LIFE/VOTE |
| A | [99-appendices.md](99-appendices.md) | Command table, token table, PETSCII charset + palette, minimal end-to-end session trace |

## Companion documents (kept beside the spec)

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
