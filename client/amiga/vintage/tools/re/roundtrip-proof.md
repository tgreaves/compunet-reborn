# Round-trip proof — decompile → reconstruct → recompile

Goal: prove that the decompiled C can be reconstructed and recompiled into
functionally-equivalent Amiga code, before committing to a full reconstruction.

Toolchain: **vbcc** (m68k-amigaos), `vc` + `vasmm68k_mot` + `vlink`, config
`aos68k`. See [toolchain.md](toolchain.md) for setup.

## Test subject

`FUN_001051de` — a self-contained cursor-advance routine (no OS calls). It steps a
column (struct +6, wraps at 40) and row (struct +4, capped at 23) on a 40×24
screen, then clears a field at +10.

### Original (Ghidra decompile)

```c
void FUN_001051de(int param_1) {
  *(short *)(param_1 + 6) = *(short *)(param_1 + 6) + 1;
  if (*(short *)(param_1 + 6) == 0x28) {
    *(short *)(param_1 + 6) = 0;
    if (*(short *)(param_1 + 4) < 0x17)
      *(short *)(param_1 + 4) = *(short *)(param_1 + 4) + 1;
  }
  *(short *)(param_1 + 10) = 0;
}
```

### Original machine code (from the binary)

```
1051de: link.w   a5,#$0
1051e6: movea.l  $8(a5),a0
1051ea: addq.w   #$1,$6(a0)          ; col++
1051ee: move.w   $6(a0),d0
1051f2: cmpi.w   #$28,d0             ; == 40 ?
1051f6: bne.b    $105212
1051fa: move.w   d0->#0,$6(a0)       ; col = 0
1051fe: move.w   $4(a0),d1 / ext.l
105204: cmpi.l   #$17,d1             ; row < 23 ?
10520a: bge.b    $105212
10520c: addq.l   #$1,d1 / move.w d1,$4(a0)   ; row++
105212: clr.w    $a(a0)              ; +10 = 0
10521a: unlk a5 / rts
```

### Reconstructed C ([cursor.c](cursor.c))

```c
struct T { char pad0[4]; short row; short col; char pad8[2]; short w10; };
void cursor_advance(struct T *c) {
    c->col++;
    if (c->col == 40) { c->col = 0; if (c->row < 23) c->row++; }
    c->w10 = 0;
}
```

### vbcc `-O2` output

```
_cursor_advance
    move.l  (4+l9,a7),a2
    lea     (6,a2),a0
    addq.w  #1,(a0)         ; col++
    cmp.w   #40,(a0)        ; == 40 ?
    bne     l6
    move.w  #0,(a0)         ; col = 0
    lea     (4,a2),a1
    move.w  (a1),d0
    cmp.w   #23,d0          ; row < 23 ?
    bge     l6
    moveq   #1,d1 / add.w d0,d1 / move.w d1,(a1)   ; row++
l6  move.w  #0,(10,a2)      ; +10 = 0
    rts
```

## Result

Functionally identical: same struct offsets (4/6/10), same constants (40/23), same
control flow. Differences are register allocation (a2/a1 vs a0/d1) and vbcc omitting
the `link a5` frame — codegen variation only, not behaviour.

**Conclusion:** the reconstruction workflow is viable. A C reconstruction will not be
byte-identical to the SAS/C original (different compiler), so fidelity is verified
per-function by comparing generated code / behaviour, not by binary diff.
