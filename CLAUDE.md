# Compunet Reborn — Project Rules

## Protocol Rules

The original X.25-derived packet protocol is preserved on the wire. The ROM's protocol engine ($96C0-$9BFF) handles framing, CRC, sequencing, and flow control unchanged. The server implements the same protocol over TCP — TCP provides the reliable transport that the phone line couldn't, while the X.25 framing provides packet boundaries and sequencing that the ROM expects.

Only the hardware layer ($94E4/$94F0/$94FA) is replaced: the original Compunet modem registers are swapped for 6551 ACIA (SwiftLink) equivalents with NMI-driven receive.

The application-layer protocol (command bytes, response types, directory format, frame format, linking sequence) must be preserved exactly as documented in [docs/PROTOCOL.md](docs/PROTOCOL.md). Do not invent new application-layer commands or alter existing response formats.

## Behaviour Rules

The client and server must always behave like the original Compunet system. All functionality must be verified against the disassembly before implementation. Do not guess or assume behaviour — check the code first.

## NEVER Infer — Verify Everything

NEVER infer, guess, approximate, or "reason about what it probably does". Every fact
you rely on MUST be confirmed against ground truth before you write or change code:

1. **Ground truth is the relocated disassembly of the original binary**, not the Ghidra
   decompile. The decompile (`recon_annotated.c`) is lossy — it drops operands, guesses
   types and field widths, and mislabels data as `PTR_`. Use it only as a guide; confirm
   every detail against the actual machine code.
2. **Always disassemble a RELOCATED image.** Disassembling un-relocated hunk bytes decodes
   garbage (mid-instruction, `jmp $0`). Run `flatten.py` first, then `disasm_fn.py`
   (`client/amiga/vintage/tools/re/`) — it dumps a function's correctly-relocated
   disassembly and, with `--our`, our compiled `vc -S` beside it for comparison.
3. **Verify EVERY magic value**: struct-field offsets, field widths (byte vs word vs long),
   command bytes, flag masks, argument order, table strides and terminators, and which
   memory a global actually aliases. These are exactly where reconstruction bugs hide
   (e.g. a command at msg+0x14 not +0x15; `SetWindowTitles(win,-1,text)` arg order; a
   config block that is ONE shared record, not separate globals).
4. **If you cannot confirm something, say so and go find out** — read the bytes, ask the
   user to run the emulator/monitor, or build a tool. Do NOT proceed on a plausible guess.
   State plainly what is verified versus what remains unconfirmed.
5. A comment like "recon FUN_xxxxxx" is a claim of fidelity — only write it once you have
   actually checked that function's disassembly and the reconstruction matches it.

## Debugging Rules

1. When investigating client behaviour, check `client/c64/src/compunet.s` source directly — do not disassemble the PRG binary.
2. The user can run VICE monitor commands (breakpoints, memory dumps, register inspection) to debug client-side issues at runtime.
3. The C64 Ultimate has a remote debug stream with the following commands:
   - `m` — memory view (`m` | `m c000` | `m c000 c100`)
   - `h` — hunt memory (`h c000 c100 4a 30 00`)
   - `f` — fill memory (`f c000 c100 00`)
   - `d` — disassemble (`d` | `d c000` | `d c000 c100`)

## Client Rules

**The C64 client is FEATURE-LOCKED. Read this before proposing any change to it.** The reference
C64 client (`client/c64/src/compunet.s`) is era-accurate and **complete**: it stands for the
1980s ROM client, whose behaviour is a fixed historical fact. It receives **correctness fixes
only** — bugs that make it diverge from what the original actually did — and **NO new features,
ever**. Its rough edges are part of the record and are kept, not smoothed: e.g. it garbage-renders
a directory entry type it does not implement and runs an `A` (action) payload with no machine
guard (`docs/spec/07-directory-format.md` §7.4.1). When a new capability needs behaviour the C64
does not already have, the answer is **not** to extend `compunet.s` — it lands in the modern
clients (web / Electron) and, where the frozen wire format allows, the Amiga client, or its safety
lives server-side. "The C64 would need to…" means the feature stops at the C64, by design. This is
normative in the spec too (§1.8) and in CONFORMANCE (a new client must degrade safely where the
era C64 does not). If a task appears to require a C64 feature, STOP and raise it — do not build it.

0. **Before building anything, read [REQUIREMENTS.md](REQUIREMENTS.md).** It lists the toolchain
   each component needs and how to check it is present — a build that fails for a missing
   `ca65`, `make` or `c1541` is a component to install, not a bug to debug. It also carries the
   platform traps that cost an afternoon each: the Windows CRLF line endings that change the C64
   version hash, electron-builder's `winCodeSign` symlink failure, and the file lock that makes
   packaging hang silently.

1. The client must ALWAYS be rebuilt after any change to `client/c64/src/compunet.s`. Build with `make` in `client/c64/src/`. The output is `client/c64/compunet-reborn.prg`.
2. The client embeds a hash of `compunet.s` at build time and the server verifies it matches `server/cfg/client_version.txt`. The build script (`gen_version.py`) derives both from the source file content, so they stay in sync automatically. The hash only changes when the client source changes — server-only commits don't require a client rebuild. When client code changes: `make clean && make` in `client/c64/src/`, then commit source + binaries + `server/cfg/client_version.txt` together.
3. To test a development client against a production server without deploying, override the hash: `make HASH=6fc715` (use the hash from the production `server/cfg/client_version.txt`).

   ⚠ **The override is also how you rebuild WITHOUT forcing every user to re-download.** The
   hash is a compatibility token, not a build fingerprint, and `gen_version.py` rewrites
   `client_version.txt` unconditionally — so a plain `make` publishes a new value and every
   existing C64 client is told it is out of date. `compunet.s` has had comment-only edits since
   the shipped binaries were built, so its current hash (`1A6A04`) deliberately differs from the
   published `800CAD`. **Build with `make HASH=800cad`** unless you actually intend to break
   compatibility, and check `git status server/cfg/client_version.txt` is clean afterwards.
4. **The Electron app must ALWAYS be rebuilt IN FULL after any change under `client/web/src/`**,
   so every artefact anyone might pick up is current. Run in `client/electron/`:

   ```bash
   npm run dist:win
   ```

   **Always `dist:win`, never `pack:win`.** `pack:win` writes only `dist/win-unpacked/` and
   leaves `Compunet Reborn Setup <version>.exe` and `Compunet Reborn <version> (portable).exe`
   sitting at the previous build. Whoever tests next reaches for the installer or the portable
   exe — the two things `pack:win` does not touch — and runs old code while believing they are
   testing the fix. Rebuilding all three costs about a minute; a stale artefact costs a whole
   round of "the fix didn't work".

   Every script there (`start`, `pack:win`, `dist*`) rebuilds the web bundle first, because the
   shell only *copies* `client/web/dist/app.bundle.js`. Without that it packages whatever bundle
   is lying on disk: it builds cleanly, launches cleanly, and runs stale code — which has
   already happened once, and reads as "the fix didn't work" rather than "the artifact is old".
   Committing a client change without repackaging leaves the same trap for the next test.
5. **`Compunet Reborn Setup <version>.exe` is an INSTALLER, not the app.** Running it installs
   the client rather than starting it. It is no longer one-click (`oneClick: false`): it asks
   where to install and can go on any drive. To simply RUN the client, use
   `dist/win-unpacked/Compunet Reborn.exe`, or the portable build,
   `Compunet Reborn <version> (portable).exe`, which keeps its settings and editor pages in
   `Compunet Reborn Data` beside the exe.

## Server Rules

1. The server must ALWAYS be restarted after any change to server Python code. It does not hot-reload. Use `./server.sh restart`. Content files (SEQ frames, directory JSON files, adverts.json) in `server/data/` are re-read on each request and do not require a restart.
2. **On Windows `./server.sh` does not work** — see *Running the server locally* in [REQUIREMENTS.md](REQUIREMENTS.md) for the PowerShell equivalent. Do not run `compunet_server.py` directly without loading `.env` first: the server starts fine and silently serves the **wrong content tree**, because `COMPUNET_CONTENT_DIR` lives in `.env` and `server.sh` is what loads it.

## Audit Rules

**Any feature that lets a user or an admin DO something must be audited, in the same
change that adds it.** Not afterwards, not in a follow-up — a feature that ships
unaudited is invisible for as long as it takes someone to notice, which was three
releases last time.

1. **Audit inside the function that PERFORMS the action, never in the command
   handler that reached it.** This is the rule the whole design rests on. Auditing
   used to sit at the call site, so whether an action was recorded depended on which
   client the user came through: mail sent from a C64 was logged and the same mail
   from the web client was not, because Binding B calls the shared
   `_complete_mail_send` directly. `_complete_content_upload` had its call *inside*
   it and never had the gap. Put it in the shared function and every present and
   future binding inherits it for free.

2. **Declare the event in `AUDIT_EVENTS` (`server/compunet_server.py`) with its
   `kind`.** `audit_log` raises on an undeclared name and `POST /api/audit` returns
   400 — deliberately. An undeclared event would be written happily and then be
   invisible to every filter that knows the vocabulary: a record that exists but
   cannot be found.

3. **Name it `noun_verbed`, past tense** — `page_uploaded`, `header_set`,
   `user_updated`. The vocabulary grew ad hoc before this and had to be renamed
   across the whole history to fix it.

4. **Pass `session=` so `via` and `ip` are derived**, rather than passing them by
   hand. Where there is no session (the admin REST routes), pass `via=` and `ip=`
   explicitly. They were per-call-site arguments before, which is why they appeared
   on every terminal event and almost no Binding-A one.

5. **Record enough to be useful a month later.** "ADMIN edited ZARD" answers
   nothing; `user_updated` carries `changed` with `field: old -> new`. Never log
   credential material — name the field, not the value.

6. **Update [docs/audit-log.md](docs/audit-log.md) in the same change.** A test
   asserts the document and the registry agree, in both directions, so drift fails
   the build rather than misleading whoever trusts it.

7. **Add a test that the event is actually written.** Nothing covered auditing
   before 1.4.0, which is precisely how the gap shipped: the JSON API was added,
   every suite passed, and no test asked. See `server/tests/test_audit.py`.

## Git Rules

1. Only ever commit when instructed to do so by a human.
2. On any commit, ensure [README.md](README.md), [docs/PROTOCOL.md](docs/PROTOCOL.md) **and the
   client specification under [docs/spec/](docs/spec/)** are fully up to date and reflect any
   changes made. The spec is normative — people build clients from it without reading this
   code, so a behaviour that exists only in the implementation is a behaviour they cannot
   reproduce, and a spec that still describes the old behaviour actively misleads them.
   In particular:
   - a fix to observable behaviour usually means a spec section was **wrong**, not merely
     silent — say so where it was wrong, rather than quietly editing the text;
   - if the fix revealed something the spec never defined, add it (that gap is why the bug
     shipped);
   - update [docs/spec/CONFORMANCE.md](docs/spec/CONFORMANCE.md) when the mistake is one
     another client would plausibly repeat;
   - if the change adds or alters something a user or an admin can **do**, it must be
     audited and documented in the same commit — see **Audit Rules** above. A feature
     that ships unaudited is invisible until someone happens to look for it.
3. On any commit, ensure [CHANGELOG.md](CHANGELOG.md) reflects anything a **user** would
   notice. **Its entries describe what differs from the LAST RELEASE — not what happened
   during development.** Two consequences, and they are the ones that get this wrong:
   - **A component shipping for the first time gets capabilities, never "fixes".** Bugs found
     and fixed while building it never existed for anyone outside this repository; listing
     them describes the development, not the release, and makes a new component read as
     unreliable.
   - **A fix only counts if the broken behaviour was RELEASED.** Check with
     `git tag --contains <commit>`: if a tag contains the commit that introduced the bug,
     users met it and the fix belongs here. If not, it was never theirs to notice.

   Write for someone using Compunet, not for someone reading the diff: what changed on their
   screen, and what it used to do instead.
4. **NEVER create a git tag.** Not as housekeeping, not "to match VERSION", not as part of
   finishing a piece of work — only when a human explicitly asks for that tag. A tag is a
   production release: it is what people install and what the version numbers in the tree
   claim. **A human decides when a release happens.** Bumping `VERSION` or a `package.json`
   is not a release and does not imply one; leaving the tree at a version with no matching
   tag is a normal, intended state.
5. **NEVER add a `Co-Authored-By:` trailer, or any other authorship credit, to a commit
   message.** Not for Claude, not for any tool. The commit author is the human running the
   commit; the message describes the change and nothing else. This rule exists here in writing
   because assistants are instructed BY DEFAULT to append that trailer — an unwritten
   preference loses to a default every time, which is how 132 commits acquired one before
   anybody noticed.
