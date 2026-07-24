# Documentation Audit & Coverage Matrix

> **Status:** Phase 1 deliverable for the Compunet Client Specification (issue #111).
> This is a working document — it maps what the spec must cover to where that content
> lives today, and flags gaps, contradictions, and staleness to resolve while writing.
> It is retired/folded into the spec once §-by-§ writing is complete.

## Purpose

The spec (`docs/spec/`) becomes the single normative source of truth for building a
Compunet Reborn client over TCP. Today that knowledge is scattered across ~20 files
written for different audiences (C64-ROM RE, Amiga RE, terminal-mode, partyline design).
This audit answers three questions per spec section:

1. **Where does the authoritative content live now?**
2. **What is missing** (gaps the server implements but no doc states)?
3. **What is wrong or stale** (contradictions between docs, or facts overtaken by later RE)?

**Authority order** when sources disagree: (1) `server/compunet_server.py` — the live
protocol the client must satisfy; (2) disasm-verified RE (both clients triangulate);
(3) prose docs. A prose doc that contradicts the server is stale, not authoritative.

---

## Document inventory (by role)

Every existing doc is classified into one of the three roles the spec effort separates.
"Fold" = authoritative content moves into the spec; "Platform" = stays as a platform note;
"Provenance" = kept as RE/historical record, relabelled as non-normative.

| Document | Role | Disposition |
|---|---|---|
| `docs/PROTOCOL.md` | **Spec backbone** (heavily C64/ROM-framed) | **Fold** app-layer + wire framing → spec; strip C64 hardware (ACIA/NMI/memory-map) to platform note |
| `docs/TERMINAL.md` | **Product doc** — describes the server-rendered PETSCII terminal *client* (port 6401), not the protocol | **Keep as-is** — a separate client we built, out of spec scope. Do *not* fold; §5 sources the display contract from the frame format + native client instead |
| `docs/partyline.md` | Spec (subsystem) + design | **Fold** protocol + UX → §8; keep C64/Amiga memory-map bits as platform notes |
| `docs/MODEM.md` | C64 platform (ACIA hardware) | **Platform** — out of spec scope (hardware layer) |
| `docs/ROM-REWRITE.md` | C64 platform (ROM/PRG build) | **Platform** — out of spec scope |
| `docs/ultimate-investigation.md` | C64 historical (SwiftLink debugging) | **Provenance** — move to `docs/historical/` |
| `docs/amiga-client.md` | Amiga platform + status | **Platform** — trim status log, keep as Amiga note |
| `docs/amiga-modern-ux.md` | Amiga proposal (aspirational) | **Provenance** — non-normative, unchanged |
| `docs/historical/*` | Historical investigations | **Provenance** — already segregated, leave |
| `client/amiga/vintage/tools/re/*.md` | Amiga RE provenance | **Provenance** — triangulation source; relabel non-normative, do not delete |

---

## Coverage matrix — spec section → current sources

Legend: **A** = authoritative content exists · **P** = partial · **—** = gap ·
**⚠** = contradiction/staleness to resolve.

| Spec § | Topic | Server (authority) | Existing prose | RE / triangulation | State |
|---|---|---|---|---|---|
| 1 | Overview & conformance tiers | — | README intro | — | **—** new writing; tiers do not exist yet |
| 2 | Transport — framing, tokens, CRC, stuffing, seq, flow | `compunet_server.py` framing | PROTOCOL.md §Packet Structure / Wire Format / CRC / Flow Control | `protocol-analysis.md` (cnet.device field-by-field), `cnet-device-re.md` | **A** but **⚠** two framing write-ups to reconcile |
| 3 | Session lifecycle — connect→identify→login→online→disconnect | identification parse (~L2566), login | PROTOCOL.md §Connection/Login/Linking | `identification-and-commands.md`, `login-connect-flow.md` | **P / ⚠** — C64 vs Amiga identification differ; not unified anywhere |
| 4 | Command protocol — single-letter cmds, `@`/`A`/`B` acks | `_cmd_*` handlers | PROTOCOL.md §Client Command Codes / BUY/SHOW/LIFE/SEND | `identification-and-commands.md` (decoded command table) | **A** — strong; needs a single canonical command table |
| 5 | Display contract (PETSCII) — screen model, screen-code→glyph, palette, control codes, RLE, window dims | frame serving | PROTOCOL.md §Frame Display ('D') | `petscii-frame-format.md` (native-client PETSCII path + font) | **P** — window char-dimensions & palette not stated normatively. *(TERMINAL.md is a separate product, not a source — see note below.)* |
| 6 | Frame (SEQ) format | frame serving | PROTOCOL.md §Frame Display ('D') | `petscii-frame-format.md` | **P** — no single field-level spec of the frame encoding yet |
| 7 | Directory format | DIR/SHOW response builder | PROTOCOL.md §DIR/SHOW Response Format, §Directory Entry Types, §Paging | — | **A** — well documented |
| 8 | Subsystems — content/paging, Mail, downloads/uploads, Editor, Partyline, LIFE/VOTE/UCAT | per-subsystem handlers | PROTOCOL.md (telesoftware, Courier, upload, LIFE, VOTE); partyline.md | `coverage-census.md` (53-cmd census), `cnettty-re.md` | **P** — coverage scattered; census is the completeness check |
| 9 | Appendices — command table, token table, charset+palette, end-to-end trace | — | tokens/commands scattered in PROTOCOL.md | command table in `identification-and-commands.md` | **—** — no consolidated tables or captured session trace |

---

## Contradictions & staleness to resolve (verified)

1. **PROTOCOL.md is framed as C64-ROM RE, not Reborn-over-TCP.**
   Title: *"Reverse Engineered from ROM v1.22"*; opens with 1200/75 baud modem, ACIA
   registers, NMI, memory maps. The **application-layer** content is authoritative and
   must survive; the hardware framing must move to a C64 platform note. *(Confirmed:
   PROTOCOL.md:1–15, §Hardware Architecture, §Memory Map.)*

2. **Identification handshake differs C64 vs Amiga — no doc unifies it.**
   C64/Reborn sends `C CNET\r {hash}/100\r ADP\r NO\r RUN\r`; Amiga sends `C CNET\r`
   **twice** then `00000000000000\r`. The server currently parses field[1] as
   `{hash}/100` and rejects anything else. §3 must specify both signatures and the
   server's detection branch as one normative flow. *(Confirmed:
   `identification-and-commands.md`:3–46 vs PROTOCOL.md §Login Sequence.)*

3. **Two independent framing write-ups.**
   PROTOCOL.md §Packet Wire Format (C64 ROM view) and `protocol-analysis.md` /
   `cnet-device-re.md` (Amiga cnet.device view) describe the *same* wire framing from
   two clients. They triangulate — §2 must be written once, citing both, with any
   field-width/CRC detail verified against the server. `cnet-device-re.md` also records
   "one incompatibility this RE exposes" — must be checked against current server.

4. **The PETSCII terminal (`TERMINAL.md`, port 6401) is a *separate client*, not a
   protocol source.** It is a server-rendered terminal product we built — the server
   does the PETSCII rendering and streams it to a dumb terminal; it does not speak the
   X.25 protocol this spec describes. The display contract (§5/§6) is therefore sourced
   from the **frame wire format** (what the server serves) + the **native-client** path
   in `petscii-frame-format.md` (with the embedded C64 char-ROM font) — *not* from
   TERMINAL.md. §2 may mention port 6401 only as an out-of-scope alternative endpoint.
   The RE doc's own earlier "PARTIAL / not confirmed" notes are marked superseded
   in-file — do not carry those forward.

5. **In-RE-doc superseded sections.**
   `identification-and-commands.md` §"(superseded)" and `protocol-analysis.md`
   §"(earlier notes) PARTIAL" retain wrong/older conclusions inline. When folding, take
   only the CONFIRMED sections; leave the superseded text in the provenance doc.

6. **Window character dimensions & 16-colour palette are not stated normatively anywhere.**
   The user explicitly wants these in the spec (RFC-style). Neither the 40×25 screen
   model's *content-window* dimensions nor the exact palette are pinned in any doc —
   **must be derived from the client/server and written fresh** (flagged GAP-1, GAP-2).

---

## Gaps — spec content with no current home (must be written fresh)

- **GAP-1** Conformance tiers (Tier 1 browse / Tier 2 interact / Tier 3 full) — new concept.
- **GAP-2** Compunet window character dimensions + look-and-feel, stated normatively.
- **GAP-3** Canonical 16-colour palette (screen-code colour semantics) as a table.
- **GAP-4** Consolidated command table & token table (currently scattered/duplicated).
- **GAP-5** A minimal, captured **end-to-end session trace** (connect→login→browse→frame)
  as the worked example an implementer follows. None exists.
- **GAP-6** Unified identification/machine-type detection (see contradiction #2).
- **GAP-7** Implementation cross-reference (spec § → `compunet_server.py` location),
  kept beside the spec so it can't drift again.

---

## Triangulation sources (keep as provenance, cite from spec)

The spec's normative claims are backed by these disasm-verified RE artefacts. They are
*evidence*, not spec — relabelled non-normative but never deleted:

- `identification-and-commands.md` — decoded single-letter command table (Amiga side).
- `coverage-census.md` — 53-command census; the **completeness check** for §8.
- `protocol-analysis.md`, `cnet-device-re.md` — framing engine, field-by-field.
- `petscii-frame-format.md` — native-client PETSCII path + embedded font.
- `login-connect-flow.md`, `cnettty-re.md` — connect/login + partyline viewer.
- `audit-findings.md`, `coverage-census.md` — reconstruction fidelity record.

---

## Next step

Phase 2 skeleton is drafted alongside this in [README.md](README.md) (section TOC +
conformance tiers). On approval, write §-by-§ (Phase 3): each section derived from the
server, verified against both clients, resolving the flags above as it goes.
