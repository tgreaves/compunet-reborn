"""Amiga LVO resolver for the Compunet client recon.

Parses Kickstart 1.3 .fd files (fd1.3/) into per-library offset->name tables and
maps the recon's library-base globals to their libraries, so indirect calls
`(**(code **)(base + -0xNN))()` can be resolved to real OS calls
(e.g. IntuitionBase -0x72 -> OpenWindow).

Library-base globals (confirmed from OpenLibrary/OpenDevice sites — see
lvo-notes.md):

  _DAT_00000004   ExecBase (absolute address 4)
  DAT_0011d040    ExecBase (copy of address 4, set at startup)
  DAT_001200d8    DOSBase        (dos.library)
  DAT_001200e8    IntuitionBase  (intuition.library)
  DAT_001200ec    GfxBase        (graphics.library)

The .fd format: `##bias N` sets the first vector offset to -N (default 30);
each subsequent public function is another -6. Lines beginning with `*` are
comments; `##private`/`##public` toggle sections (private vectors still consume
offset slots). A function line is `Name(args)(regs)`.
"""
import os
import re

FD_DIR = os.path.join(os.path.dirname(__file__), 'fd1.3')

# recon global (as it appears in recon.c) -> fd file basename (library)
BASE_TO_LIB = {
    '_DAT_00000004': 'exec_lib',
    'DAT_0011d040':  'exec_lib',
    'DAT_001200d8':  'dos_lib',
    'DAT_001200e8':  'intuition_lib',
    'DAT_001200ec':  'graphics_lib',
}

# Friendly library-base name for annotations
LIB_DISPLAY = {
    'exec_lib':      'SysBase',
    'dos_lib':       'DOSBase',
    'intuition_lib': 'IntuitionBase',
    'graphics_lib':  'GfxBase',
    'console_lib':   'ConsoleBase',
    'layers_lib':    'LayersBase',
    'diskfont_lib':  'DiskfontBase',
    'timer_lib':     'TimerBase',
    'icon_lib':      'IconBase',
    'expansion_lib': 'ExpansionBase',
}


def parse_fd(path):
    """Return {negative_offset: function_name} for one .fd file."""
    bias = 30
    off = None
    table = {}
    for raw in open(path, encoding='latin-1'):
        line = raw.strip()
        if not line:
            continue
        if line.startswith('##'):
            parts = line.split()
            tag = parts[0][2:].lower()
            if tag == 'bias':
                bias = int(parts[1])
                off = bias
            elif tag == 'base':
                off = bias  # base precedes bias in some files; reset when bias seen
            # ##public / ##private / ##end: sections still consume offsets
            continue
        if line.startswith('*'):
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*\(', line)
        if not m:
            continue
        if off is None:
            off = bias
        table[-off] = m.group(1)
        off += 6
    return table


def load_all():
    """Return {lib_basename: {offset: name}} for every fd file present."""
    libs = {}
    if not os.path.isdir(FD_DIR):
        return libs
    for fn in os.listdir(FD_DIR):
        if fn.endswith('.fd'):
            libs[fn[:-3]] = parse_fd(os.path.join(FD_DIR, fn))
    return libs


def resolve(base_expr, offset, libs):
    """Resolve (base global, negative offset) -> (library_display, func_name).

    Returns (None, None) if the base global is not a known library base.
    """
    lib = BASE_TO_LIB.get(base_expr)
    if lib is None:
        return None, None
    name = libs.get(lib, {}).get(offset)
    return LIB_DISPLAY.get(lib, lib), name


if __name__ == '__main__':
    libs = load_all()
    for lib in sorted(libs):
        print(f'{lib}: {len(libs[lib])} vectors')
    # self-check: OpenLibrary must be -0x228
    ol = {v: k for k, v in libs['exec_lib'].items()}.get('OpenLibrary')
    print(f'\nexec OpenLibrary offset = {ol} (0x{-ol:x})  expect -0x228')
    assert ol == -0x228, 'OpenLibrary offset mismatch — fd parse wrong!'
    print('OK: fd parser verified against OpenLibrary=-0x228')
