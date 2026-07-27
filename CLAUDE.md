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

1. The client must ALWAYS be rebuilt after any change to `client/c64/src/compunet.s`. Build with `make` in `client/c64/src/`. The output is `client/c64/compunet-reborn.prg`.
2. The client embeds a hash of `compunet.s` at build time and the server verifies it matches `server/cfg/client_version.txt`. The build script (`gen_version.py`) derives both from the source file content, so they stay in sync automatically. The hash only changes when the client source changes — server-only commits don't require a client rebuild. When client code changes: `make clean && make` in `client/c64/src/`, then commit source + binaries + `server/cfg/client_version.txt` together.
3. To test a development client against a production server without deploying, override the hash: `make HASH=6fc715` (use the hash from the production `server/cfg/client_version.txt`).
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

## Git Rules

1. Only ever commit when instructed to do so by a human.
2. On any commit, ensure [README.md](README.md) and [docs/PROTOCOL.md](docs/PROTOCOL.md) are fully up to date and reflect any changes made.
3. **NEVER create a git tag.** Not as housekeeping, not "to match VERSION", not as part of
   finishing a piece of work — only when a human explicitly asks for that tag. A tag is a
   production release: it is what people install and what the version numbers in the tree
   claim. **A human decides when a release happens.** Bumping `VERSION` or a `package.json`
   is not a release and does not imply one; leaving the tree at a version with no matching
   tag is a normal, intended state.
4. **NEVER add a `Co-Authored-By:` trailer, or any other authorship credit, to a commit
   message.** Not for Claude, not for any tool. The commit author is the human running the
   commit; the message describes the change and nothing else. This rule exists here in writing
   because assistants are instructed BY DEFAULT to append that trailer — an unwritten
   preference loses to a default every time, which is how 132 commits acquired one before
   anybody noticed.
