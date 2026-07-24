# CRT Cartridge Build Target — Implementation Plan

## Context

The client currently requires loading from D64, typing `LOAD "COMPUNET",8,1` and
`SYS 33184`. A .CRT (16KB cartridge) would let users simply insert and power on.
The binary is currently ~20KB but only 16,920 bytes of actual code — 536 bytes over
the 16KB limit. Approximately 450-500 bytes of dead legacy modem code can be removed
to fit.

## Approach

### Phase 1: Remove dead code to fit in 16KB

Remove the following unreachable legacy protocol routines from `compunet.s`:

| Routine | Line | Est. Size | Reason Dead |
|---------|------|-----------|-------------|
| PROTO_RECV_FRAME | ~2879 | ~250 bytes | Replaced by NMI_HANDLER |
| PROTO_START_SESSION | ~2779 | ~30 bytes | Only called from PROTO_RECV_FRAME |
| PROTO_ERROR_RECOVERY | ~3085 | ~60 bytes | Dispatch table never called |
| PROTO_FLOW_CONTROL | ~3375 | ~50 bytes | Replaced by ACIA_FLOW_CONTROL |
| PROTO_RECV_PACKET | ~3422 | ~25 bytes | Dispatch table never called |
| PROTO_SEND_PACKET | ~3410 | ~20 bytes | Replaced by ACIA_SEND_PACKET |
| PROTO_CONNECT | ~3805 | ~100 bytes | Replaced by ACIA_PROTO_CONNECT |
| PROTO_INIT_REGS | ~2769 | ~15 bytes | Dispatch table never called |

**Total estimated savings: ~550 bytes** (enough to fit under 16KB)

The dispatch table JMPs that point to dead routines should be replaced with
`JMP` to their ACIA equivalents or `RTS` stubs (preserving the table structure
since the ROM code uses computed offsets into it).

After removal, rebuild and verify binary size < 16,384 bytes.

### Phase 2: Create CRT build target

A standard 16KB C64 cartridge:
- Maps ROM at $8000-$BFFF (GAME=0, EXROM=0)
- Has CBM80 signature at $8004-$8008
- Cold-start vector at $8000-$8001 points to init code

**Boot sequence for CRT (EasyFlash type 32):**
1. C64 powers on, detects cartridge via CBM80 signature
2. Jumps to our boot stub
3. Boot stub copies $8000-$BFFF from ROM to underlying RAM
   (reads from ROM overlay, writes go to RAM beneath on the 6510)
4. Disables cartridge: `LDA #$04 / STA $DE02` (GAME=0, EXROM=0, no freeze)
5. Now running from RAM — LOAD/SAVE work, ACIA at $DE00 accessible
6. JMP to MAIN_INIT (existing entry point)

**EasyFlash control registers:**
- $DE00: Bank register (bits 0-5 = bank number, bit 7 = LED)
- $DE02: Control register (bit 0 = GAME, bit 1 = EXROM, bit 2 = No Freeze)

To disable cartridge and run from RAM:
```
LDA #$04        ; bit 2 = no freeze, GAME=0, EXROM=0 → normal mode
STA $DE02       ; Cart ROM disappears, RAM visible
```

**Note on $DE00 conflict:** EasyFlash uses $DE00 for its bank register, which
conflicts with the ACIA data register at $DE00. This is only a problem while the
cartridge is active — once we write $DE02 to disable, the $DE00 space reverts to
the ACIA. The boot stub must not touch ACIA before disabling the cart.

### Phase 3: Build system changes

**New files:**
- `client/c64/src/crt_boot.s` — small boot stub (copies ROM to RAM, banks out)
- `client/c64/src/compunet_crt.cfg` — linker config for CRT layout
- `client/c64/src/Makefile` — add `crt` target

**Output:** `client/c64/compunet-reborn.crt`

The CRT file format:
- 64-byte header (magic "C64 CARTRIDGE", version, type=32, EXROM=0, GAME=0)
- CHIP packet header (16 bytes: type, size, bank, load address)
- 16KB ROM data at $8000

A Python script (`gen_crt.py`) will wrap the raw binary in the CRT header format.

### Phase 4: Keep PRG/D64 build working

The PRG build remains unchanged. The Makefile gets a new `crt` target alongside
the existing `all` target. Both share the same source and linker output.

## CRT Type Decision

**EasyFlash (type 32)** — supported by VICE, C64 Ultimate, and real EasyFlash
hardware. Bank-out via `STA $DE02`. The Ultimate loads CRT files directly from
its file browser.

## Implementation Order

1. Remove dead code from `compunet.s` → rebuild PRG → verify still works
2. Check if binary fits in 16KB
3. If yes: write CRT boot stub + linker config + Makefile target
4. If no: use compression (e.g. exomizer/zx0) with a small decompressor stub
5. Test CRT in VICE and on Ultimate

## Findings (2026-05-24)

### EasyFlash CRT: Working but unusable

The EasyFlash CRT boots and decompresses successfully. However, **EasyFlash and
SwiftLink both use $DE00** — they cannot coexist. In VICE, enabling both causes
the SFX decompressor to JAM because reads from $DE00 hit the SwiftLink ACIA
instead of the EasyFlash bank register (or vice versa).

On real hardware (C64 Ultimate), the same conflict would apply: the modem
emulation uses DE00/NMI mode, which conflicts with EasyFlash's bank register.

### Options to eliminate SYS 33184

The goal is to simplify the user experience — no manual `SYS 33184` needed.

**Option A: BASIC loader stub**
Add a small BASIC program at $0801 that auto-runs and calls SYS 33184. The PRG
would load at $0801 with a BASIC `RUN` line, followed by the program at $8000+.
But PRG files can only have one load address — can't load to both $0801 and $8000.

**Option B: Two-file D64 (loader + main)**
D64 contains a BASIC loader ("COMPUNET") that does:
```basic
10 LOAD "COMPUNET.BIN",8,1
20 SYS 33184
```
User just types `LOAD "COMPUNET",8` then `RUN`. The loader loads the binary and
starts it. Downside: two LOADs (slow on real hardware).

**Option C: Self-extracting PRG with exomizer**
Use `exomizer sfx` to create a PRG that loads at $0801, auto-starts via BASIC
RUN, decompresses to $8000+, and jumps to the entry point. Single file, single
LOAD, auto-starts with RUN. This works and was validated during CRT testing.

**Option D: Cartridge with non-$DE00 type**
Use a cartridge format that doesn't conflict with SwiftLink:
- Generic type 0 (no registers, but can't disable ROM)
- A custom approach with I/O at $DF00 range
- Requires moving SwiftLink to $DF00 in both VICE and client code

**Option E: D64 with autoboot**
Some D64 loaders (like Epyx FastLoad, JiffyDOS) support autoboot sectors.
The C64 Ultimate can also auto-run programs from D64. Not universal though.

### Recommended: Option C (SFX PRG)

The exomizer SFX approach works — it was validated during testing. The user
experience:
- `LOAD "COMPUNET",8` then `RUN` (standard BASIC workflow)
- Program decompresses and starts automatically
- No SYS command needed
- Single file, works everywhere

This can be offered alongside the existing PRG+D64 for users who prefer
direct loading.

## Files to modify

| File | Change |
|------|--------|
| `client/c64/src/compunet.s` | Remove dead protocol routines (~550 bytes) |
| `client/c64/src/crt_boot.s` | New: boot stub for CRT |
| `client/c64/src/compunet_crt.cfg` | New: linker config for CRT layout |
| `client/c64/src/gen_crt.py` | New: wraps binary in CRT file format |
| `client/c64/src/Makefile` | Add `crt` target |

## Verification

1. Build PRG — verify it still works in VICE (same as before, just smaller)
2. Build CRT — verify VICE loads it as a cartridge (File → Attach CRT image)
3. Verify auto-start: power on with CRT attached → Compunet starts automatically
4. Verify LOAD/SAVE still work (code runs from RAM, not ROM)
5. Verify ACIA at $DE00 is accessible (not shadowed by cartridge ROM)
6. Test on C64 Ultimate (load CRT via Ultimate menu)
