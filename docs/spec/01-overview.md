# §1 — Overview

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.

## 1.1 Purpose

This document specifies how to build a client for **Compunet Reborn** — the modern
recreation of the Compunet online service — that connects to the server over **TCP/IP**.
It is written to be complete on its own: an implementer should be able to build a working
client from this specification without reading the C64 or Amiga client source.

The protocol described here is the original Compunet application protocol, preserved on
the wire. The modern server implements it over TCP; TCP supplies the reliable transport
the original phone line could not, while the X.25-derived framing (§2) supplies the packet
boundaries and sequencing the protocol expects.

## 1.2 Authority and provenance

The **server** (`server/compunet_server.py` and `server/x25_protocol.py`) is the
normative authority: a conforming client is one whose bytes the server accepts and whose
behaviour matches what the server sends. Where a historical document disagrees with the
server, the server wins.

Every normative claim in this specification has been verified against the server and,
where possible, corroborated against the two reference clients (Commodore 64 and Amiga),
which independently implement the same protocol and therefore triangulate it. Reverse-
engineering notes cited in passing (under `client/*/vintage/`) are **provenance, not
normative** — they record how a fact was established, not the requirement itself.

## 1.3 Scope

**In scope.** The Reborn protocol over TCP: transport framing (§2), session lifecycle
(§3), the command protocol (§4), the PETSCII display contract (§5), the frame (§6) and
directory (§7) formats, and the application subsystems (§8).

**Out of scope.** These belong to platform notes, not this specification, and a client
MAY implement them however its environment dictates:

- Physical/link hardware — the original 1200/75 modem (the "brick"), 6551 ACIA /
  SwiftLink emulation, AT dial commands, `cnet.device`. This specification begins at an
  established TCP connection.
- Client-local concerns — user input handling, local caching/storage, and the on-screen
  chrome outside the defined display contract.
- The server-rendered **PETSCII terminal** (TCP port 6401). That is a *separate client*
  that Compunet Reborn also provides: the server renders PETSCII and streams it to a dumb
  terminal, which does not speak the protocol in this specification. It is documented on
  its own in `docs/TERMINAL.md` and is not covered here.

## 1.4 Conformance tiers

A client need not implement every subsystem to be useful. This specification defines three
cumulative conformance tiers. A client **MUST** state the highest tier it claims, and
**MUST** implement every requirement of that tier and all lower tiers.

| Tier | Name | A conforming client at this tier can… | Requires |
|---|---|---|---|
| **1** | **Browse** | connect, identify, log in, navigate directories, and render frames | §§2, 3, 4, 5, 6, 7 |
| **2** | **Interact** | everything in Tier 1, plus read/send mail, download content, and use LIFE / VOTE | Tier 1 + the relevant parts of §8 |
| **3** | **Full** | everything in Tier 2, plus uploads, the frame editor, and Partyline | Tier 1 + all of §8 |

Tier 1 is the meaningful minimum: a Tier 1 client is a working read-and-navigate
Compunet client. Tiers 2 and 3 add optional application subsystems that ride on the same
transport, command, and display machinery; a client MAY implement any subset of §8 at
Tier 2 but MUST implement all of it to claim Tier 3.

## 1.5 Requirement conventions

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**,
**SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as
described in RFC 2119 — but only where they appear in **UPPERCASE**. The same words in
lowercase carry their ordinary English meaning.

Requirement language is used for the protocol (§§2–4, §§6–7) and for the display
constraints in §5 that a user-visible client must honour to look and behave like Compunet.
Explanatory and background prose is non-normative.

## 1.6 Notation

- Byte values are hexadecimal with a `$` or `0x` prefix (`$01`, `0x43`); the two forms are
  interchangeable. Bit 7 is the most-significant bit of a byte.
- `CR` is the carriage return `$0D`; `SP` is the space `$20`.
- "Screen code" refers to a C64 screen (display) code, distinct from a PETSCII code — the
  distinction is defined in §5.
- Wire diagrams show the bytes **between** the frame markers unless the `$01`/`$02` markers
  are drawn explicitly.

## 1.7 Document map

| § | Section |
|---|---|
| 2 | [Transport](02-transport.md) — framing, tokens, CRC, sequencing, flow control |
| 3 | [Session lifecycle](03-session.md) — connect, identify, log in, disconnect |
| 4 | [Command protocol](04-commands.md) — commands and ack conventions |
| 5 | [Display contract (PETSCII)](05-display.md) — screen model, palette, control codes, RLE |
| 6 | [Frame (SEQ) format](06-frame-format.md) |
| 7 | [Directory format](07-directory-format.md) |
| 8 | [Subsystems](08-subsystems.md) — mail, downloads, uploads, editor, Partyline, LIFE/VOTE |
| A | [Appendices](99-appendices.md) — command & token tables, charset + palette, session trace |
