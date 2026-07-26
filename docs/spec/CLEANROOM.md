# Clean-room validation brief

> **Scope: this is the procedure for validating [Binding A](README.md)** (X.25-over-TCP), and it
> has been run five times — see [VALIDATION.md](VALIDATION.md). For **[Binding B](api/README.md)**
> (the JSON API), follow this document with the changes in *Validating Binding B* below.

## Validating Binding B

Same method, three differences:

**The isolated set is different.** Copy `api/README.md` plus the **shared model** sections and
the appendix — and **exclude `02-transport.md` and `03-session.md`**, which are Binding-A wire
detail that a JSON client neither needs nor should be reading:

```
README.md  01-overview.md  04-commands.md  05-display.md  06-frame-format.md
07-directory-format.md  08-subsystems.md  99-appendices.md  api/README.md
```

`05` and `06` stay in despite the API delivering rendered cell grids: the client still carries
the **embedded frames** of §A.6/§A.8–§A.11 as raw PETSCII and must parse them itself.

Sections will now reference §2/§3, which the builder does not have. That is intended — tell them
a reference into a missing section is itself worth logging.

**⚠ Do not point the builder at `run_api_dev.py`.** That launcher serves `client/web` on the same
origin as the API, so the builder can fetch our reference implementation — `index.html`,
`dist/app.bundle.js`, even `src/` — and the run is **void**. Use `server/run_api_only.py`
(default port 6414), which exposes `/v1/*` and nothing else. Verify before starting:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:6414/dist/app.bundle.js   # must be 404
```

**Findings are tagged differently:** `[API]`, `[MODEL]`, `[UX]`, `[BUG]` — the API surface, the
shared model beneath it, invented presentation, and outright faults.

This document defines how to validate that the [Compunet Client Specification](README.md)
is **sufficient to build a working client from the spec alone**. It exists because the spec
author cannot validate their own spec: they carry the codebase and its assumptions in their
head, so when they "build from the spec" they unconsciously fill gaps from memory — which
both hides real gaps and lets their own mistakes masquerade as spec findings. A trustworthy
test needs a reader who genuinely has *only* the spec.

## What a valid clean-room guarantees

1. **No memory contamination.** The builder must be a *fresh* agent with no knowledge of this
   project, its source, or any prior conversation about it.
2. **No source contamination.** The builder must not be able to read `server/`, the C64/Amiga
   client source, or any existing client. Its **only** reference is `docs/spec/`.
3. **Live proof.** The client is tested against a running server, so "it works" is
   demonstrated, not assumed.
4. **A findings log.** Every point where the spec is silent, ambiguous, or wrong is recorded
   against its section — that log is the actual deliverable.

## Setup (isolate the spec)

Copy **only the normative spec** into a neutral directory that contains nothing else and is
**not inside the repository**, so the builder cannot reach the source even by accident. Copy
the README, the numbered section files, and the appendix — and **deliberately exclude** the
companion docs, because they would contaminate the test: `VALIDATION.md` lists the findings
(the answers), `xref.md` gives server source locations (an invitation to cheat), and
`AUDIT.md` / this file are meta.

macOS / Linux / Git-Bash:

```bash
CR=/tmp/cleanroom            # any path OUTSIDE the repo
rm -rf "$CR" && mkdir -p "$CR"
cp docs/spec/README.md docs/spec/0*.md docs/spec/99-appendices.md "$CR/"
git rev-parse HEAD > "$CR/SPEC-COMMIT.txt"
```

Windows (PowerShell):

```powershell
$CR = "$HOME\cleanroom"      # any path OUTSIDE the repo
Remove-Item -Recurse -Force $CR -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $CR | Out-Null
Copy-Item docs\spec\README.md, docs\spec\0*.md, docs\spec\99-appendices.md $CR
git rev-parse HEAD | Out-File -Encoding ascii "$CR\SPEC-COMMIT.txt"
```

The copied set must be exactly: `README.md`, `01`–`08`, `99-appendices.md` (plus the commit
stamp). Then start a **brand-new** agent session (a fresh `claude` in that directory, or an
otherwise isolated agent) — not a continuation of any session that has seen the codebase —
and give it the brief below.

## The brief (paste this to the fresh agent)

> You are building a client from a protocol specification. The **only** reference material
> is the set of Markdown files in this directory. You **must not** read, search for, open, or
> infer from any other source — no server code, no other client, no external Compunet
> documentation. If something you need is not in these files, that is a finding: **do not go
> hunting for it** — record it, make a documented assumption, and continue.
>
> Build in Python and test everything against the live server as you go:
> `docker.lan:6400`, user `ADMIN`, password `ADMIN`.
>
> **Scope: Tier 3 ("Full").** Implement Tier 1 (Browse), Tier 2 (Interact) *and* Tier 3 (Full)
> as the spec defines them: connect/identify/login, directory navigation and frame rendering,
> the Tier-2 subsystems (mail read/send, content download, LIFE/VOTE/BUY), **and the Tier-3
> subsystems — content upload (The Jungle), the frame editor, and Partyline.** For the editor,
> a minimal one is enough: let the user compose a PETSCII page (text + colour) and submit it
> through the upload path. For Partyline, use the link-activation and raw line protocol the
> spec describes.
>
> **Server-write policy (this is a live dev server).** You may exercise the **full command
> set**, including all state-changing operations — mail send, VOTE, BUY, LIFE-extend, **and
> content uploads to the Jungle** (uploads create pages; that is fine). Keep it reasonable: a
> handful of representative operations is enough, not hundreds — e.g. upload one or two small
> test pages, not dozens. The one hard rule: **never delete anything.**
>
> **Stage 1 — Text-mode client (protocol/format correctness).** Use raw TCP sockets; a
> text-mode 40×24 render printed to the terminal is enough here. Cover: (1) connect, handshake,
> identification, login; (2) directory navigation (list, select/open, back, page) and frame
> rendering (colour, character set, RLE); (3) the Tier-2 and Tier-3 flows above — including
> composing and **uploading** a page, and **Partyline** (activate the link, run the raw
> line-based chat, exit cleanly and resume the framed protocol); (4) let the user invoke the
> applicable commands and leave cleanly. This stage proves the wire protocol and formats.
>
> **Stage 2 — Visual client (display + UX correctness).** Once Stage 1 works, build a
> **graphical** version that reproduces the Compunet look and feel: render the 40×24 screen
> with **pixel-accurate C64 glyphs and the 16-colour palette from the appendix**, and give the
> user a **visual way to invoke commands** (buttons, a menu, or the on-screen command bar /
> duckshoot). Use whatever rendering is least friction — `tkinter` (Python standard library),
> `pygame` if installed, or emit an image (PPM/PNG) per screen. Expose **user-experience**
> aspects the spec implies but does not fully pin down: how commands are surfaced and named,
> the directory layout and colours, how the current selection looks, the border/background, the
> Tier-2 screens (mailbox, a mail message, a download prompt), the **Tier-3 screens (the frame
> editor, the upload flow, the Partyline chat window)**, and the overall look-and-feel.
> Whenever you have to *invent* a presentation or interaction choice because the spec did not
> specify it, that is a **UX finding** — log it.
>
> **Findings log (the main deliverable).** Keep a running list across both stages. Every time
> the spec is silent, ambiguous, contradictory, or contradicted by the server, write down: the
> spec section, exactly what you needed, what you had to assume, and whether your assumption
> worked (against the live server for protocol items; visually for UX items). Tag each finding
> **[PROTOCOL]** or **[UX]**. Be specific.
>
> **Deliver, and prepare for a human reviewer to try it.** Deliver: the Stage 1 client, the
> Stage 2 visual client, and the findings log. The Stage 2 client will be **run and tried by a
> person** afterwards, so make it **runnable out of the box** (prefer the Python standard
> library / `tkinter` so there is nothing to install; if you use `pygame`, note the one-line
> install). Include a short **HOW-TO-RUN** (the exact command, the keys/buttons, and what to
> try — browse, open a page, read mail, view a download) and, if you can, a few **screenshots**
> of the main screens.

## Rules that keep the test valid

- The builder works from the **committed** spec only; do not feed it patches mid-run.
- The builder never sees `server/`, `client/`, or this conversation. If, in a driven
  (subagent) run, its transcript shows it opened anything outside the spec directory, the
  run is **void** — restart it clean.
- The builder is told to **log and assume**, never to go find the answer elsewhere. A build
  that "succeeds" by reading the source proves nothing about the spec.
- Stage 1 uses text-mode rendering (fast protocol/format coverage); Stage 2 adds a graphical
  client to expose display and UX gaps. Both stages share one findings log, tagged
  `[PROTOCOL]` / `[UX]`.

## After the run — reconcile

Bring the clean-room findings back and diff them against the known state:

- **Genuine spec gaps** — things the fresh reader could not determine from the spec. These
  are real; fold the fix into the spec and record it in [VALIDATION.md](VALIDATION.md).
- **Non-issues** — things the reader assumed correctly with no trouble; confirms those areas
  are clear.
- **Author-error check** — compare against fixes made in non-clean-room sessions. If a past
  "finding" was really the author contradicting the spec (not a spec gap), note that: the
  spec may already have been correct, and the lesson is about process, not the spec.

The first fully clean-room run is the honest baseline for "can someone build a Compunet
client from this spec alone?" Re-run it after any significant spec change.
