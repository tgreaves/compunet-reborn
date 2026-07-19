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
| Connect / transport bring-up | `connect.c` | **reconstructed + compiles** (open_transport: ports, requests, OpenDevice, 1275 baud) |
| Login / do_connect | (todo) | dial + login sequence (calls open_transport) |
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

`transport.c` and `connect.c` compile clean (only harmless `#endif !FOO` warnings from
the vintage 1.3 headers), producing genuine Amiga HUNK objects.

**Struct-offset verification.** `struct CnetRequest` field offsets are asserted at
compile time (via `offsetof`) to match the decompiled reference exactly:
`io_Command`=0x1c, `io_Error`=0x1f, `io_Actual`=0x20, `io_Length`=0x24,
`io_Data`=0x28, `io_Device`=0x14, `io_Offset`=0x2c. So the reconstruction reads/writes
the same bytes the original did — faithfulness is proven, not assumed.

SAS/C note: the source targets standard Amiga includes, so a `SMakefile` for real
SAS/C is a drop-in later; vbcc is the modern-host proxy for the compile/verify loop.
