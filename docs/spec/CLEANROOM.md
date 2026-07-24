# Clean-room validation brief

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
> `docker.lan:6400`, user `ADMIN`, password `ADMIN`. (Development server; only browse — do
> not upload, vote, buy, or delete.) Iterate: build, connect, observe what breaks, consult
> the spec, fix, repeat.
>
> **Stage 1 — Tier 1 client (protocol/format correctness).** Use raw TCP sockets; a text-mode
> 40×24 render printed to the terminal is enough here. It must: (1) connect, complete the
> handshake and identification, and log in; (2) show the directory and let the user navigate
> it (list, select/open an entry, go back, page); (3) render frames correctly — colour,
> character set, run-length compression; (4) let the user invoke the applicable commands and
> leave cleanly. This stage proves the wire protocol and the content formats.
>
> **Stage 2 — Visual client (display + UX correctness).** Once Stage 1 works, build a
> **graphical** version that reproduces the Compunet look and feel: render the 40×24 screen
> with **pixel-accurate C64 glyphs and the 16-colour palette from the appendix**, and give the
> user a **visual way to invoke commands** (e.g. buttons, a menu, or the on-screen command
> bar). Use whatever rendering is available with least friction — `tkinter` (Python standard
> library), `pygame` if installed, or emit an image (PPM/PNG) per screen. The point of this
> stage is to expose **user-experience** aspects the spec implies but does not fully pin down:
> how commands are surfaced and named, how the directory and the current selection look, the
> colours, the on-screen layout and margins, the border/background, and the overall
> look-and-feel of the Compunet window. Whenever you have to *invent* a presentation or
> interaction choice because the spec did not specify it, that is a **UX finding** — log it.
>
> **Findings log (the main deliverable).** Keep a running list across both stages. Every time
> the spec is silent, ambiguous, contradictory, or contradicted by the server, write down: the
> spec section, exactly what you needed, what you had to assume, and whether your assumption
> worked (against the live server for protocol items; visually for UX items). Tag each finding
> **[PROTOCOL]** or **[UX]**. Be specific.
>
> **Deliver:** the Stage 1 client, the Stage 2 visual client, and the findings log. If you can
> save a few screenshots (or rendered image files) of the visual client, include them.

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
