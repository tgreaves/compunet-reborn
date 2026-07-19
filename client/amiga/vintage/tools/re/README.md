# Compunet Amiga client — reverse-engineering pipeline

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

2. **Ghidra headless** — import the flat image as raw `68000:BE:32`, seed each
   CODE-hunk start, set `A4=0x11d000` (the small-data base) so a4-relative globals
   and strings resolve, auto-analyse, then decompile every function:

   ```
   analyzeHeadless <proj> compunet -import compunet_flat.bin \
     -processor 68000:BE:32:default -loader BinaryLoader -loader-baseAddr 0x100000 \
     -scriptPath ghidra_scripts -preScript SeedCode.java -postScript ExportRecon.java
   ```
   `ghidra_scripts/SeedCode.java` seeds + sets A4; `ghidra_scripts/ExportRecon.java`
   writes `recon.c` (decompiled C for all functions) and `recon_functions.txt`
   (per-function address/size/callcount/strings).

3. **`a4xref.py`** — capstone scan of the CODE hunks for a4-relative operands,
   resolved against the small-data string table. Fills the gap where Ghidra did
   not auto-create references for some `disp(a4)` string loads; maps strings →
   referencing functions.

## Current outputs (checked in)

- `recon.c` — decompiled C, all 222 functions. 0 decompile failures, 0 unrecovered
  control flow. Main readability gap: OS/library calls appear as unnamed indirect
  calls `(**(code**)(libbase + LVO))()` (Amiga LVO naming not yet applied).
- `recon_functions.txt` — function index.
- `compunet_flat.map` — hunk layout of the flat image.

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
