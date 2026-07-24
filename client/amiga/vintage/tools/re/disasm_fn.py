#!/usr/bin/env python3
"""
disasm_fn.py — dump the ORIGINAL Compunet client's machine code for a function, as a
correctly-RELOCATED m68k disassembly.

This is the ground-truth reference for verifying a reconstruction. It exists because
the bugs this project hits come from reading the *lossy Ghidra decompile*
(recon_annotated.c) instead of the actual instructions. A relocated disassembly is
1:1 faithful to the loaded binary: every offset, constant, and call target is exactly
what the CPU executes. Compare it by eye against the reconstructed C (or its `vc -S`
output) — that manual comparison is what has reliably caught the real bugs
(SetWindowTitles arg order, msg+0x14 command offset, menu-table field widths).

Address resolution:
  - reads compunet_flat.bin (pre-relocated flat image from flatten.py, BASE 0x100000)
  - a function's [addr,size] comes from recon_functions.txt
  - a name is resolved to an address via symbols.json

USAGE:
  disasm_fn.py <name|0xADDR> [...]        # dump each function's relocated disasm
  disasm_fn.py --our <name>               # ALSO compile our reconstruction (vc -S)
                                          # and print it beside the original
Examples:
  disasm_fn.py account
  disasm_fn.py 0x10c582
  disasm_fn.py --our account
"""
import sys, os, re, json, struct, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.normpath(os.path.join(HERE, "../../../src"))
FLAT = os.path.join(HERE, "compunet_flat.bin")
FUNCS= os.path.join(HERE, "recon_functions.txt")
SYMS = os.path.join(HERE, "symbols.json")
VBCC = os.environ.get("VBCC", "/tmp/vbcc")
BASE = 0x100000

from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000
MD = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)

# Exec/Intuition/Graphics/Dos LVO names, so `jsr -$NN(a6)` reads as the OS call.
LVO = {
 -0x126:"exec.FindTask", -0x228:"exec.OpenLibrary", -0x19e:"exec.CloseLibrary",
 -0xc6:"exec.AllocMem", -0x210:"exec.FreeMem", -0x17a:"exec.ReplyMsg",
 -0x174:"exec.GetMsg", -0x180:"exec.WaitPort", -0x16e:"exec.PutMsg",
 -0x84:"exec.Forbid", -0x8a:"exec.Permit", -0xfc:"exec.Remove",
 -0x1c8:"exec.DoIO", -0x1ce:"exec.SendIO", -0x234:"exec.ObtainSemaphore",
 -0x23a:"exec.ReleaseSemaphore", -0x37e:"exec.OpenDevice",
 -0x114:"intuition.SetWindowTitles", -0xd8:"intuition.PrintIText",
 -0x6c:"intuition.DrawBorder", -0x10e:"intuition.SetPointer",
 -0x3c:"intuition.ClearPointer", -0xba:"intuition.OnGadget",
 -0xae:"intuition.OffGadget", -0xc0:"intuition.OnMenu", -0xb4:"intuition.OffMenu",
 -0x14a:"intuition.IntuiTextLength", -0x22e:"intuition.OpenScreen",
 -0x42:"intuition.CloseScreen", -0x1de:"intuition.OpenWindow",
 -0x48:"intuition.CloseWindow", -0xd2:"intuition.DrawImage",
 -0xba:"intuition.OnGadget", -0x96:"intuition.ModifyIDCMP",
 -0x150:"intuition.AddGList", -0x11a:"intuition.RefreshGList",
 -0x156:"gfx.SetAPen", -0x162:"gfx.SetBPen", -0x174:"gfx.?", -0x132:"gfx.RectFill",
 -0x108:"gfx.Move", -0xf6:"gfx.Text", -0x30:"gfx.LoadRGB4", -0x2f4:"gfx.SetDrMd",
}

def load_ext():
    ext={}
    for line in open(FUNCS):
        if line.startswith("#") or not line.strip(): continue
        p=line.split()
        if len(p)>=3:
            a=int(p[0],16); ext["0x%x"%a]=(a,int(p[1])); ext[p[2]]=(a,int(p[1]))
    return ext

def load_syms():
    j=json.load(open(SYMS))["functions"]
    return {v:int(k,16) for k,v in j.items()}, {int(k,16):v for k,v in j.items()}

def resolve(tok, ext, n2a):
    if tok.startswith("0x"):
        a=int(tok,16); return a, ext.get("0x%x"%a,(a,256))[1]
    if tok in n2a:
        a=n2a[tok]; return a, ext.get("0x%x"%a,(a,256))[1]
    if tok in ext:
        return ext[tok]
    return None, None

def dump_original(name, a, sz, a2n):
    data=open(FLAT,"rb").read()
    print("==== ORIGINAL  %s  @ %#x  (%d bytes) ====" % (name, a, sz))
    for ins in MD.disasm(data[a-BASE:a-BASE+sz], a):
        note=""
        m=re.search(r'(-?\$[0-9a-f]+)\(a6\)', ins.op_str)
        if m and ins.mnemonic in ("jsr","jmp"):
            v=int(m.group(1).replace("$","0x"),16)
            if v>0x7fffffff: v-=0x100000000
            note="   ; "+LVO.get(v,"LVO %d"%v)
        # resolve pc-relative call targets to a named function if known
        m2=re.match(r'\$([0-9a-f]+)\(pc\)', ins.op_str)
        if m2 and ins.mnemonic in ("jsr","bsr","jmp"):
            tgt=int(m2.group(1),16)
            if tgt in a2n: note="   ; -> "+a2n[tgt]
        print("  %06x  %-9s %s%s"%(ins.address,ins.mnemonic,ins.op_str,note))
    print()

def dump_ours(name):
    module=None
    pat=re.compile(r'^\s*(?:LONG|void|APTR|UBYTE|BYTE|ULONG|UWORD|WORD|int|char|struct \w+ \*?)\s+'+re.escape(name)+r'\s*\(')
    for fn in sorted(os.listdir(SRC)):
        if fn.endswith(".c") and any(pat.match(l) for l in open(os.path.join(SRC,fn))):
            module=os.path.join(SRC,fn); break
    if not module:
        print("  (no reconstructed definition of %s in src/)"%name); return
    env=dict(os.environ, VBCC=VBCC, PATH=VBCC+"/bin:"+os.environ.get("PATH",""))
    asm="/tmp/disfn_%s.asm"%os.path.basename(module)[:-2]
    subprocess.run(["vc","+kick13","-S","-I"+SRC,module,"-o",asm],env=env,
                   capture_output=True,text=True)
    if not os.path.exists(asm):
        print("  (compile -S failed)"); return
    print("==== OURS  %s  (compiled from %s) ===="%(name,os.path.basename(module)))
    emit=False
    for line in open(asm):
        if re.match(r'^_'+re.escape(name)+r'\b',line): emit=True
        elif re.match(r'^_[A-Za-z_]\w*\b',line) and emit: break
        if emit: print("  "+line.rstrip())
    print()

def main():
    args=sys.argv[1:]
    if not args:
        print(__doc__); return
    show_ours = "--our" in args
    args=[a for a in args if a!="--our"]
    ext=load_ext(); n2a,a2n=load_syms()
    for tok in args:
        a,sz=resolve(tok,ext,n2a)
        if a is None:
            print("  ?? cannot resolve %s\n"%tok); continue
        name=a2n.get(a,tok)
        dump_original(name,a,sz,a2n)
        if show_ours:
            dump_ours(name)

if __name__=="__main__":
    main()
