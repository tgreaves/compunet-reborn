# Terminal Linking — Investigation & Feasibility

## Issue #73: Re-implement on-demand terminal download

## Background

The original Compunet ROM (8K at $8000-$9FFF) downloaded the "terminal" portion
of the software from the server during the "LINKING" phase immediately after login.
This allowed the system to update terminal software without requiring users to
physically swap cartridges.

Our current client bundles everything into a single PRG:
- ROM code at $8000-$9FFF (8K)
- Terminal code at $A000+ 
- ACIA driver at $C900+
- **Total: 20,482 bytes** (20K)

## Original Architecture (from `vintage/modem_bootstrap.asm`)

### Memory Map
```
$8000-$9FFF  ROM (8K cartridge, copied to RAM on boot)
$9FF0        Phone number storage / CNLOAD flag
$A000-$A001  End address of downloaded terminal code
$A005        Terminal entry point (JMP target after LINKING)
$C100-$C1FF  Terminal workspace / session state
$C200-$C2FF  Protocol state
$C800+       Code extensions (JMP $C800 in dispatch table)
```

### LINKING Phase Flow

1. Client sends login packet including `cnload_bytes` at offset 25-26
2. Server checks these bytes:
   - `$30/$30` = terminal already loaded (skip LINKING)  
   - Other values = terminal needs downloading
3. If not skipping, server sends terminal code via `MODEM_INIT_DOWNLOAD`:
   - 4-byte header: jump address (2 bytes) + load address (2 bytes)
   - 2 padding bytes
   - Raw code bytes streamed until end-of-stream
4. Client stores bytes at load address, then `JMP ($001F)` to entry point
5. `$8036/$8037` updated with end address (for CNSAVE)

### CNLOAD Detection Logic

The client sends two bytes at login packet offset 25-26:
- These are `$A000` and `$A001` — the terminal end address markers
- If both are `$30` (`'0'` in ASCII), it means "no terminal loaded"
- If they contain a valid end address, terminal is present (skip download)

At `$8335` in the ROM (the init routine), these are set:
```
LDA #$00
STA $9FF0       ; clear phone number length
LDA #$30
STA $A000       ; marker: no terminal loaded
STA $A001
```

### CNLOAD / CNSAVE Commands

**CNSAVE** (`*$91B2` in ROM, vintage line 1966+):
- Saves from `$9FF0` to `$A000/$A001` (end address) as `@0:CNET` on drive 8
- Preserves phone number + entire downloaded terminal

**CNLOAD** (`vintage line 266+`):
- Loads `CNET` from drive 8 back to `$9FF0`
- Restores terminal code + phone number
- Updates `$8036/$8037` with end address

## Current Client Layout

```
$8000-$9FFF  ROM equivalent (disassembled + modified, 8K)
$A000-$BFFF  Terminal/directory handling code (~7.5K)
$C900-$CFFF  ACIA driver + NMI handler (~1.8K)
```

Segments from `compunet.cfg`:
- HEADER: $8000 (PRG load address)
- CODE: $8000+ (ROM code)
- TERMINAL: $A000+ (terminal functionality)
- ACIA: $C900+ (SwiftLink driver)

## Feasibility: Re-implementing On-Demand Download

### What would need to change

**Client (8K cartridge target):**
1. Strip TERMINAL segment from the PRG/CRT
2. Keep only ROM ($8000-$9FFF) + ACIA ($C900-$CFFF) = ~10K
3. ACIA driver could potentially move back into the ROM space if we can fit it
4. Re-enable `MODEM_INIT_DOWNLOAD` to receive terminal from server
5. Restore CNLOAD/CNSAVE commands for disk caching
6. Send real `$A000/$A001` values in login packet instead of hardcoded `$30/$30`

**Server:**
1. When `cnload_bytes` indicate no terminal loaded, send the terminal binary
   during the LINKING phase (before the welcome frame)
2. Store the terminal binary as a file (e.g. `server/cfg/terminal.bin`)
3. Stream it using the 4-byte header format the ROM expects

### Size Analysis

| Component | Current Size | Target (8K CRT) |
|-----------|-------------|-----------------|
| ROM code ($8000-$9FFF) | 8,192 bytes | 8,192 bytes |
| Terminal ($A000+) | ~7,500 bytes | Downloaded on-demand |
| ACIA ($C900+) | ~1,800 bytes | Must fit somewhere |
| **Total in CRT** | — | **~10K max** |

The ACIA driver currently lives at $C900. For an 8K cartridge ($8000-$9FFF only),
it would need to either:
- Fit within the 8K ROM space (tight — ROM is nearly full)
- Be part of the downloaded terminal (downloaded with it)
- Live in a small RAM stub that the ROM copies on boot (like the NMI handler at $CF00)

### Key Challenges

1. **ACIA driver must exist before LINKING** — it's needed to receive the download.
   So it must be in the ROM/CRT itself, not part of the downloaded terminal.

2. **8K space budget**: ROM is currently ~8K. Adding ACIA (~1.8K) would overflow.
   Options:
   - Optimise ROM code to free 1.8K (significant effort)
   - Use a 16K cartridge (EXROM=0, GAME=0) giving $8000-$BFFF
   - Copy ACIA stub to RAM during ROM init (uses RAM, not ROM space)

3. **First-connect experience**: First time a user connects, there's no cached
   terminal — full download needed (~7.5K). `MODEM_INIT_DOWNLOAD` reads a raw
   stream (not ACK-paced packets), so it runs at TCP delivery speed limited
   only by the C64's byte processing rate. Estimated ~2 seconds based on
   similar-sized ACK-paced downloads taking 1.4s for 3.2K. Subsequent connects
   use CNLOAD from disk (instant).

4. **Version management**: Server needs to know which terminal version the client
   has. Could use the existing `cnload_bytes` mechanism (terminal version hash
   instead of just "present/absent").

### Proposed Approach

**Phase 1: Separate terminal into a downloadable binary**
- Split `compunet.s` TERMINAL segment into a standalone file
- Server sends it during LINKING when client reports no terminal
- Client stores at $A000+, jumps to $A005
- CNLOAD/CNSAVE cache it to disk

**Phase 2: Fit ROM + ACIA into 8K for CRT**
- ACIA driver is ~1.8K — needs to fit alongside 8K ROM
- Option A: 16K CRT (easy, but overkill)
- Option B: Optimise ROM to free space (hard)
- Option C: ACIA in RAM, copied from ROM on boot (~200 bytes of ROM for the copy
  routine + ACIA code stored compressed or at end of ROM)

**Phase 3: Version-aware linking (future optimisation)**
- Terminal binary has a version byte at a fixed address (e.g. $A002)
- Client sends it in the login packet alongside $A000/$A001
- Server compares and only sends if outdated
- For initial implementation: always link (no version check)

## Decisions Made

1. **Target 8K CRT** — remove unused original modem code to make space for ACIA
2. **Download time acceptable** — ~3 seconds via ACK-paced packets, same mechanism
   as program downloads (BUY)
3. **Always link during testing** — no version checking initially. Every connect
   downloads the terminal. Add version-aware skipping later as optimisation.
4. **CNLOAD/CNSAVE** — re-implement for disk caching (future phase)

## Note on cnload_bytes Logic

The original protocol:
- Client sends `$A000/$A001` in the login packet (bytes 25-26)
- `$30/$30` (init values) = no terminal loaded → server MUST send LINKING
- Real address values = terminal cached → server skips LINKING

Our current server has this **inverted** (`skip_linking` when `$30/$30`) because
the bundled client always sends `$30/$30` and never needs linking. When we
re-implement, the server should: always send LINKING data (phase 1), or check
a version byte (phase 3).
