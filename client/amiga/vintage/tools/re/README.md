# Compunet Amiga client — reverse-engineering pipeline

> **Reverse-engineering provenance (non-normative).** The analysis notes in this directory
> record *how* the Amiga client's behaviour was established. They are evidence, not the
> specification. The normative, authoritative protocol lives in
> [docs/spec/](../../../../../docs/spec/README.md); these notes are cited from it as
> provenance. Some sections here are marked superseded in-file — trust the spec over any
> note that disagrees with it.

Tooling to disassemble/decompile the vintage `Compunet` client
([../../decrunched/Compunet](../../decrunched/Compunet)) so it can be understood
and, ultimately, modified to work with Compunet Reborn.

The client is a **SAS/Lattice C** program: ~34 object modules, a4-relative
small-data model, a5 stack frames, fully stripped (no symbols). See
[docs/amiga-client.md](../../../../../docs/amiga-client.md) for the wider analysis.

## Pipeline

1. **`flatten.py`** — parse the HUNK executable, place every hunk at a fixed
   address (`BASE=0x100000`), and apply all RELOC32 fixups so absolute references
   are correct. Produces a single pre-relocated raw image importable into any
   68000 tool with no Amiga HUNK loader:

   ```
   python flatten.py ../../decrunched/Compunet compunet_flat
   ```
   → `compunet_flat.bin` + `compunet_flat.map` (hunk→address, entry, sizes).

2. **Ghidra headless** — import the flat image as raw `68000:BE:32`, seed code,
   set `A4=0x11d000` (the small-data base), auto-analyse, apply confirmed symbol
   names, then decompile every function:

   ```
   RECON_OUT=<out> RECON_SRC=$(pwd) analyzeHeadless <proj> compunet \
     -import compunet_flat.bin \
     -processor 68000:BE:32:default -loader BinaryLoader -loader-baseAddr 0x100000 \
     -scriptPath ghidra_scripts -preScript SeedCode.java \
     -postScript ApplySymbols.java -postScript ExportRecon.java
   ```
   Requires `JAVA_HOME=/opt/homebrew/opt/openjdk@21` (Ghidra 12.1.2 needs JDK 21).

   - `SeedCode.java` — sets A4; seeds hunk starts; scans CODE ranges for `link.w`
     prologues; then iteratively seeds `jsr`/`bsr`/`jmp` call targets until the
     function set is stable. Recovers functions reached only via indirect calls
     (e.g. `do_connect` @0x10343c) that the original hunk-start-only seeding missed
     — **444 → 781 functions**, 0 decompile failures.
   - `ApplySymbols.java` — applies confirmed names from `symbols.json` (functions +
     globals) to the DB so `recon.c` decompiles with real identifiers (`do_connect`,
     `serial_write`, `SysBase`, `g_write_req`, …).
   - `ExportRecon.java` — writes `recon.c` and `recon_functions.txt`.

3. **`a4xref.py`** — capstone scan of the CODE hunks for a4-relative operands,
   resolved against the small-data string table. Fills the gap where Ghidra did
   not auto-create references for some `disp(a4)` string loads; maps strings →
   referencing functions.

## Verifying a reconstruction against the original

- **`disasm_fn.py <name|0xADDR>`** — dump a function's **correctly-relocated** m68k
  disassembly from `compunet_flat.bin` (the ground truth the CPU executes: real
  offsets, constants, and `jsr -$NN(a6)` annotated with the OS call). Add `--our` to
  also compile our reconstruction (`vc -S`) and print it beside the original for
  eyeball comparison. This is the reliable check — the bugs this project hits
  (SetWindowTitles arg order, editor msg+0x14 command offset, menu-table field widths,
  the g_data ×4 type mismatch) are all cases where reading the *lossy Ghidra decompile*
  misled us; a relocated disassembly is 1:1 with the binary. NOTE: for a foreign
  binary (e.g. `decrunched/CnetEditor`) always `flatten.py` it FIRST — disassembling
  un-relocated hunk bytes decodes garbage (mid-instruction / `jmp $0`).
  Requires `$VBCC` for the `--our` side.

## Current outputs (checked in)

- `recon.c` — decompiled C, all 781 functions, with confirmed names baked in
  (`symbols.json`). 0 decompile failures. Canonical Ghidra output — never hand-edited;
  regenerate via the pipeline. New names go in `symbols.json`, not this file.
- `recon_functions.txt` — function index.
- `symbols.json` — confirmed address→name map (functions + globals), applied by
  ApplySymbols. **This is where naming knowledge lives.**
- `compunet_flat.map` — hunk layout of the flat image.

## LVO naming (OS-call readability)

The decompiler emits OS calls as indirect calls `(**(code**)(libbase + -0xNN))()`.
These are resolved to named Amiga calls using authoritative **Kickstart 1.3** `.fd`
files (this binary is 1989; core LVOs are stable across OS versions).

- `fd1.3/` — KS1.3 function-descriptor files (exec/dos/intuition/graphics/…),
  fetched from the `asig/vbcc` NDK. Parser self-verifies against `OpenLibrary=-0x228`.
- `lvo.py` — parses `.fd` files → offset→name tables; maps the recon's library-base
  globals (see `lvo-notes.md`) to their libraries.
- `annotate_lvo.py` — resolves every LVO callsite; writes:
  - `recon_annotated.c` — copy of `recon.c` with inline `/* = LibBase.Func() */`
    comments (188/210 calls resolved; the 22 via local-register bases need
    per-function dataflow and are listed, not guessed).
  - `lvo_callsites.txt` — machine-readable callsite index.
- `lvo-notes.md` — analysis notes: base→library map, verified offsets, transport
  touch-points.

`recon.c` is left untouched; annotation is a separate, regenerable artifact.

```
python3 lvo.py            # self-check the fd parser
python3 annotate_lvo.py   # produce recon_annotated.c + lvo_callsites.txt
```

## Program map (partial)

| Function | Role (by referenced strings) |
|----------|------------------------------|
| `FUN_00100000` | C startup (argc/argv, a4 setup) |
| `FUN_00102000` | load `cnet-configuration` |
| `FUN_00112000` | save `cnet-configuration` |
| `~0x10343c` | connection setup: open device / "Modem error" / "Can't open cnet.device" / "Can't open logon window" |
| `0x1192b6` | the actual `cnet.device` open helper (via thunk `0x10381a`) |
| `FUN_001025de` | launch `CnetEditor` |
| `FUN_001026ae` | launch `CnetTty` |
| `FUN_001023ec` | connection-state display (offline/logging-on/online/courier/upload/directory) |
| `FUN_0010b000` | file download (Download filename / File download / Action download / Invalid link) |
| `FUN_0010e0fc` | login validation ("*** No Such User ***") |
| `FUN_0010a1e2` | Goto Page |

## Not the build system

These tools are for *understanding*. The recompilable rebuild chain (vasm/vlink or
vbcc) is a separate decision — see [docs/amiga-client.md](../../../../../docs/amiga-client.md).
