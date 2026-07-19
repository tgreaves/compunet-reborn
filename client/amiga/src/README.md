# Compunet Amiga client — C reconstruction

A from-scratch, **readable and compilable** reconstruction of the original 1989
SAS/Lattice C client, rebuilt module-by-module and verified against the decompiled
reference in [../vintage/tools/re/recon_annotated.c](../vintage/tools/re/recon_annotated.c).

Goal: source that reads like the original (real names, Amiga system includes, real
struct types — not the decompiler's raw offset arithmetic) and compiles for
Kickstart 1.3, so it can eventually be built in SAS/C as it originally was, and so
the transport can be swapped for TCP (Compunet Reborn).

## Status

| Module | File | State |
|--------|------|-------|
| Shared types/decls | `compunet.h` | in progress |
| Transport (cnet.device serial IO) | `transport.c` | **reconstructed + compiles** (serial_read/serial_write) |
| Connect / login | (todo) | do_connect, open_transport |
| Frame display (PETSCII) | (todo) | render_char, build_font, blit_char_cell |
| Directory / show / goto | (todo) | |
| Download / upload | (todo) | |
| Mail / editor | (todo) | |

Each function is reconstructed from `recon_annotated.c` and cross-checked field-by-field
(struct offsets → real Amiga struct fields; `(**(base-LVO))()` → real OS prototypes).

## Building (vbcc, Kickstart 1.3 target)

The reconstruction compiles with **vbcc** (period-appropriate m68k Amiga C compiler)
using the KS1.3 NDK headers. vbcc is not committed — see
[../vintage/tools/re/toolchain.md](../vintage/tools/re/toolchain.md) to build/assemble it.
Once assembled at `$VBCC` with a `kick13` config pointing at the KS1.3 include/lib:

```
VBCC=/path/to/vbcc PATH=$VBCC/bin:$PATH \
  vc +kick13 -c -I. transport.c -o transport.o
```

`transport.c` currently compiles clean (only harmless `#endif !FOO` warnings from the
vintage 1.3 headers). The result is a genuine Amiga HUNK object with `_serial_read` /
`_serial_write`.

SAS/C note: the source targets standard Amiga includes, so a `SMakefile` for real
SAS/C is a drop-in later; vbcc is the modern-host proxy for the compile/verify loop.
