# Amiga LVO / library-base analysis

Working notes for the readability pass on `recon.c`. Goal: turn
`(**(code **)(base + -0xNN))()` indirect calls into named OS calls.

## Library base globals (confirmed from OpenLibrary/OpenDevice sites)

| Global | Library base | Evidence |
|--------|--------------|----------|
| address `4` / `_DAT_00000004` | **ExecBase** (`SysBase`) | Absolute address 4 is the Amiga ExecBase pointer. |
| `DAT_0011d040` | **ExecBase** (copy) | `DAT_0011d040 = _DAT_00000004` at startup (recon.c line 27). Used for `OpenLibrary` (`-0x228`). |
| `DAT_001200d8` | **DOSBase** (`dos.library`) | Set in `FUN_001001c4` (strings: "dos.library") via ExecBase `-0x228` OpenLibrary. |
| `DAT_001200e8` | **IntuitionBase** (`intuition.library`) | `DAT_001200e8 = OpenLibrary("intuition.library", 0x21)` (recon.c line 1358). |
| `DAT_001200ec` | **GfxBase** (`graphics.library`) | `DAT_001200ec = OpenLibrary("graphics.library", 0x21)` (recon.c line 1362). |

`OpenLibrary` wrapper chain: `FUN_0011a290` → `FUN_001291b8` →
`(**(code **)(ExecBase + -0x228))()`. `-0x228` (LVO -552) = **OpenLibrary**. ✓
This confirms the LVO decoding method against a known vector.

## Authoritative LVO tables — Kickstart 1.3 FD files

Fetched the **Kickstart 1.3** `.fd` set (from `asig/vbcc` NDK, `fd1.3/`) into
[fd1.3/](fd1.3/). This binary is 1989 (WB 1.2/1.3 era), so the 1.3 vectors are the
correct reference. Core exec/dos/intuition/graphics LVOs are stable across OS
versions (later releases only append), so these offsets are authoritative here.

FD format: `##bias N` sets the first function offset to `-N` (usually 30); each
subsequent public function is another `-6`. Parse gives offset → name.

### Verified against in-binary evidence
`OpenLibrary` parses to **-0x228 (-552)** — exactly matching the traced
OpenLibrary wrapper chain in the binary. Method confirmed correct.

### exec.library (ExecBase / _SysBase) — offsets seen in the census, now pinned
| Offset | Function |
|--------|----------|
| -0x84  | Forbid |
| -0x8a  | Permit |
| -0xc6  | AllocMem |
| -0xd2  | FreeMem |
| -0x126 | FindTask |
| -0x16e | PutMsg |
| -0x174 | GetMsg |
| -0x17a | ReplyMsg |
| -0x180 | WaitPort |
| -0x19e | CloseLibrary |
| -0x1bc | OpenDevice |
| -0x1c2 | CloseDevice |
| -0x1c8 | DoIO |
| -0x1ce | SendIO |
| -0x228 | OpenLibrary ✓ (confirmed in-binary) |

> Correction: earlier hand-guesses had AllocMem/FreeMem swapped and DoIO at the
> wrong offset. The FD files resolved these — the reason we fetched them rather
> than guessing.

The message-port calls (GetMsg/PutMsg/WaitPort/ReplyMsg) on `DAT_0011d040`
(=ExecBase) are the `cnet.device` IORequest handling — the transport touch-points
that TCP will replace.

## Next

- Write an FD parser + Ghidra prescript that applies these names so the decompiler
  emits real calls (`OpenDevice(...)`, `DoIO(...)`, etc.).
- Re-export and diff to confirm only intended calls changed.
