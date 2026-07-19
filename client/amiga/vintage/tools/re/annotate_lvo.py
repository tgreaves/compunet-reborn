"""Resolve LVO indirect calls in recon.c to named Amiga OS calls.

Produces two outputs (canonical recon.c is left untouched):

  recon_annotated.c   - copy of recon.c with an inline /* = LibBase.Func */ comment
                        appended to every resolved `(**(code **)(base + -0xNN))()`
                        call, for human reading.
  lvo_callsites.txt    - machine-readable index: file line, base global, offset,
                        resolved library.function (or UNRESOLVED for local-register
                        bases that need per-function dataflow).

Only the four known library-base globals are resolved directly. Calls through
local copies (iVar1/iVar9/unaff_A6 = a register holding a base) are listed as
UNRESOLVED with their offset so they can be resolved per-function later.
"""
import re
import lvo

CALL_RE = re.compile(r'\(\*\*\(code \*\*\)\(([_A-Za-z][_A-Za-z0-9]*) \+ (-0x[0-9a-f]+)\)\)')

def main():
    libs = lvo.load_all()
    lines = open('recon.c', encoding='latin-1').read().split('\n')
    out = []
    idx = []
    resolved = unresolved = 0
    for n, line in enumerate(lines, 1):
        m = CALL_RE.search(line)
        if m:
            base, off_s = m.group(1), m.group(2)
            off = int(off_s, 16)
            libname, func = lvo.resolve(base, off, libs)
            if func:
                out.append(line + f'    /* = {libname}.{func}() */')
                idx.append(f'{n}\t{base}\t{off_s}\t{libname}.{func}')
                resolved += 1
            else:
                base_disp = lvo.LIB_DISPLAY.get(lvo.BASE_TO_LIB.get(base, ''), '')
                tag = f'{base_disp}?off{off_s}' if base_disp else f'UNRESOLVED(base={base})off{off_s}'
                out.append(line)
                idx.append(f'{n}\t{base}\t{off_s}\t{tag}')
                unresolved += 1
        else:
            out.append(line)
    # Quick win: substitute known global variables (confirmed library bases) with
    # readable names throughout the annotated output. Longest names first so e.g.
    # DAT_001200e8 is not shadowed by a shorter prefix. Word-boundary anchored.
    text = '\n'.join(out)
    glob_subs = 0
    for g, name in sorted(lvo.KNOWN_GLOBALS.items(), key=lambda kv: -len(kv[0])):
        pat = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(g) + r'(?![A-Za-z0-9_])')
        text, k = pat.subn(name, text)
        glob_subs += k
    open('recon_annotated.c', 'w', encoding='latin-1').write(text)
    with open('lvo_callsites.txt', 'w') as f:
        f.write('# line\tbase\toffset\tresolved\n')
        f.write('\n'.join(idx) + '\n')
    print(f'resolved {resolved} calls, {unresolved} unresolved (local-register bases)')
    print(f'substituted {glob_subs} known-global references (library bases)')
    print('wrote recon_annotated.c, lvo_callsites.txt')

if __name__ == '__main__':
    main()
