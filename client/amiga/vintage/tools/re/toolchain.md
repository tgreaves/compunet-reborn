# Amiga C cross-toolchain (vbcc) — setup

The reconstruction target is C recompiled for AmigaOS. We use **vbcc** (Volker
Barthelmann's C compiler) — the period-appropriate, lightweight m68k Amiga C
compiler — with its bundled `vasmm68k_mot` assembler and `vlink` linker.

This tree is **not committed** (prebuilt binaries, ~10 MB, and platform-specific).
Reproduce it on any host — the pipeline is otherwise OS-agnostic (Python + Ghidra).

## Components

| Piece | Source | Notes |
|-------|--------|-------|
| vbcc binaries | vbcc downloads page: `sun.hasenbraten.de/vbcc/` → **Binaries** | Pick your platform: `vbcc_bin_win64.zip` (Windows), the macOS build, or build from source on Linux. Contains `vc`, `vbccm68k`, `vasmm68k_mot`, `vlink` + configs. |
| m68k-amigaos target | `phoenix.owl.de/vbcc/2022-05-22/vbcc_target_m68k-amigaos.lha` | `startup.o`, `vc.lib`, `amiga.lib`, C-library headers, config `aos68k` (platform-independent) |
| Kickstart 1.3 NDK includes | `github.com/asig/vbcc` → `ndks/amiga/m68k-kick13/` and `targets/m68k-kick13/` | OS struct/proto headers (exec/, intuition/, graphics/, …) for our 1989 (KS1.2/1.3-era) client |

Extract with Python (`zipfile`; `pip install lhafile` for `.lha`). Assemble into one
tree (binary names are `.exe` on Windows, extensionless on macOS/Linux):

```
vbcc/
  bin/           vc vbccm68k vasmm68k_mot vlink
  config/        aos68k  (and kick13* if using the KS1.3 target)
  targets/m68k-amigaos/{lib,include}/
```

Set `VBCC=<abs>/vbcc` and put `vbcc/bin` on `PATH` (`chmod +x vbcc/bin/*` on
macOS/Linux).

### Python analysis deps (any platform)

```
pip install capstone lhafile amitools
```
Ghidra 11+/12 (any OS) with Java 17+ for the decompile step.

## Build

```
vc +aos68k -c99 -O2 file.c -o file          # link an executable
vc +aos68k -c99 -O2 -S file.c -o file.asm   # emit assembly (for round-trip diff)
```

Verified: `vc +aos68k` compiles a C program into a valid HUNK executable
(`00 00 03 F3`). See [roundtrip-proof.md](roundtrip-proof.md).

## Header note

The stock vbcc m68k-amigaos target ships only C-library headers (`stdio.h`, …) plus
`proto/`+`inline/`. The Amiga OS **struct** headers (`exec/`, `dos/`, `intuition/`,
`graphics/`, …) come from the NDK. For our KS1.3-era client, the `asig/vbcc` repo's
`m68k-kick13` includes are the right vintage. When reconstructing OS-calling modules,
merge the NDK struct headers alongside vbcc's `proto/`/`inline/`/`clib/`.

## Verified reconstruction build (KS1.3) — reproducible recipe

Building vbcc from source on macOS + assembling the KS1.3 headers, used to compile the
`client/amiga/src/` reconstruction:

1. Build tools from source (host clang):
   - vbcc: `http://www.ibaug.de/vbcc/vbcc.tar.gz` → `cd vbcc && yes '' | make TARGET=m68k`
     → `bin/vc`, `bin/vbccm68k`
   - vasm: `http://sun.hasenbraten.de/vasm/release/vasm.tar.gz` → `make CPU=m68k SYNTAX=mot`
     → `vasmm68k_mot`
   - vlink: `http://sun.hasenbraten.de/vlink/release/vlink.tar.gz` → `make` → `vlink`
2. Target libs/C-headers: `http://phoenix.owl.de/vbcc/2022-05-22/vbcc_target_m68k-amigaos.lha`
   (extract with `lha x`; provides `targets/m68k-amigaos/{lib,include}` + `config/aos68k*`).
3. KS1.3 OS headers: from `github.com/asig/vbcc` tarball, merge into the target include dir:
   - `ndks/amiga/m68k-kick13/includes1.3/include.h/*` (exec/, devices/, intuition/, graphics/, libraries/, …)
   - `targets/m68k-kick13/include/*` (clib/, proto/)
4. Custom config `kick13` = copy of `aos68k` with `vincludeos3:` / `vlibos3:` replaced by
   the concrete `targets/m68k-amigaos/include` and `.../lib` paths.
5. **Force old-style relocations (required for a Kickstart 1.3-loadable executable).**
   In `$VBCC/config/kick13`, the link-without-debug line must use `-Rstd`, not the
   default `-Rshort`:
   ```
   -ldnodb=-s -Rstd
   ```
   vlink's default `-Rshort` emits `RELOC32SHORT` hunks (type `0x3f7`), a Kickstart
   2.0+ format. The 1.3 loader doesn't understand it and refuses the binary with
   **AmigaDOS error 121 ("... is not an object module")**. `-Rstd` emits classic
   `RELOC32` (`0x3ec`) hunks, which load on 1.3. (The executable is a little larger.)

Compile a reconstruction module:
```
VBCC=/path/to/vbcc PATH=$VBCC/bin:$PATH \
  vc +kick13 -c -I. transport.c -o transport.o
```
`transport.c` compiles clean (only harmless `#endif !FOO` warnings from the vintage
1.3 headers). Output: genuine Amiga HUNK object (`0x3e7` HUNK_UNIT) with `_serial_read`
/ `_serial_write`.
