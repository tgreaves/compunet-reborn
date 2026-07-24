#!/usr/bin/env python3
"""
make_lha.py - build the Compunet Reborn Amiga client distribution as an LHA archive.

Produces a `Compunet` Workbench drawer (with a drawer icon) containing the TCP client and
its support files (the client itself carries the authentic vintage icon). Output:
    client/amiga/dist/CompunetReborn-Amiga-<ver>.lha

No host `lha` tool is required: this writes standard LHA **level-1, -lh0- (stored)** headers
directly (directory via extended-header type 0x02 with 0xff separators, CRC-16/ARC, 1-byte
header checksum), then validates the result by reading it back with the `lhafile` library.

Icons are standard AmigaOS planar .info files (max compatibility, KS2.1+ with no palette or
icon-system dependency): the client reuses the genuine 1989 CNet.info (WBTOOL); the drawer
icon is derived from it (WBDRAWER + DrawerData).
"""
import os, struct, datetime, sys, subprocess, tempfile, shutil

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
HDD      = os.path.join(HERE, 'hdd')
VINTAGE  = os.path.join(HERE, '..', 'vintage')
DIST     = os.path.join(HERE, '..', 'dist')
VER      = open(os.path.join(ROOT, 'VERSION')).read().strip()

DRAWER   = 'Compunet'

# Two builds: the public release (points at the live server) and a dev build (local server).
PROD_HOST = 'vme.compunet.live:6400'
DEV_HOST  = 'docker.lan:6400'
PROD_ARCHIVE = os.path.join(DIST, f'CompunetReborn-Amiga-{VER}.lha')
DEV_ARCHIVE  = os.path.join(DIST, f'CompunetReborn-Amiga-{VER}-dev.lha')

# The public (live) archive is also published to the website's static downloads under a
# stable name (matching the .crt/.prg naming) so the Connecting page can link to it.
WEBSITE_LHA  = os.path.join(ROOT, 'website', 'static', 'compunet-reborn-amiga.lha')

# The drawer icon is a genuine standard Workbench 2.1 drawer icon, extracted from the WB ADF
# at build time (so no Cloanto content lives in the repo). Override the ADF with $WB_ADF.
DEFAULT_WB_ADF = os.environ.get(
    'WB_ADF',
    r'C:\Users\Public\Documents\Amiga Files\Shared\adf\amiga-os-210-workbench.adf')
WB_DRAWER_ICON = 'Devs.info'        # a plain 632-byte standard drawer icon on the WB disk

# Fixed timestamp (Date.now/new Date() unavailable in some sandboxes; use the release date).
STAMP = datetime.datetime(2026, 7, 24, 12, 0, 0)

README_TEMPLATE = os.path.join(HERE, 'README.template')

def readme(host):
    """Render the archive README from README.template. Placeholders {VERSION}/{HOST}/{PORT}
    are substituted (via replace, so any other braces in the text are safe to edit).
    Line endings are normalised to LF (Amiga text convention)."""
    text = open(README_TEMPLATE, encoding='utf-8').read()
    port = host.split(':', 1)[1] if ':' in host else '6400'
    text = (text.replace('{VERSION}', VER)
                .replace('{HOST}', host)
                .replace('{PORT}', port))
    return text.replace('\r\n', '\n').replace('\r', '\n')


# ---- LHA level-1, -lh0- (stored) writer ------------------------------------------------

def crc16(data):
    """CRC-16/ARC (poly 0xA001 reflected, init 0x0000) - the LHA file CRC."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if (crc & 1) else 0)
    return crc & 0xffff

def dos_time(dt):
    """4-byte MS-DOS packed time+date, little-endian (matches lhafile's decoder)."""
    t = (dt.hour << 11) | (dt.minute << 5) | (dt.second // 2)
    d = ((dt.year - 1980) << 9) | (dt.month << 5) | dt.day
    return struct.pack('<HH', t, d)

def lha_entry(method, name, data, directory=None):
    """One LHA level-1 entry. `directory` (e.g. 'Compunet') -> type-0x02 ext header."""
    name_b = name.encode('latin1')
    comp   = data                              # -lh0- : stored
    crc    = crc16(data)

    # Extended headers (each: [size:2][type:1][payload][next_size:2]); dir uses 0xff sep.
    if directory:
        dir_b   = directory.encode('latin1') + b'\xff'      # trailing 0xff per convention
        ext_sz  = 3 + len(dir_b)                            # type(1)+payload+next(2)
        first_ext = ext_sz                                  # size lives in the base header
        ext_block = b'\x02' + dir_b + struct.pack('<H', 0)  # [type][payload][next_size=0]
        sum_ext   = ext_sz
    else:
        first_ext = 0
        ext_block = b''
        sum_ext   = 0

    skip_size   = len(comp) + sum_ext          # lhafile: compress_size = skip_size - sum_ext
    header_size = 25 + len(name_b)             # level-1 base header size byte
    os_id       = ord('A')                     # Amiga

    # base header from offset 2 (method) .. first_ext_size (inclusive) = header_size bytes
    body = (method +
            struct.pack('<I', skip_size) +
            struct.pack('<I', len(data)) +
            dos_time(STAMP) +
            bytes([0x20]) +                    # reserved / attribute
            bytes([0x01]) +                    # level 1
            bytes([len(name_b)]) +
            name_b +
            struct.pack('<H', crc) +
            bytes([os_id]) +
            struct.pack('<H', first_ext))
    assert len(body) == header_size, (len(body), header_size)
    checksum = sum(body) & 0xff
    return bytes([header_size, checksum]) + body + ext_block + comp


# ---- Amiga icon (.info) helpers --------------------------------------------------------

def drawerdata():
    """56-byte OldDrawerData (NewWindow[48] + CurrentX[4] + CurrentY[4])."""
    nw = struct.pack('>hhhh', 60, 40, 400, 120)      # Left, Top, Width, Height
    nw += bytes([255, 255])                          # DetailPen, BlockPen
    nw += struct.pack('>II', 0, 0)                   # IDCMPFlags, Flags
    nw += struct.pack('>IIIII', 0, 0, 0, 0, 0)       # FirstGadget, CheckMark, Title, Screen, BitMap
    nw += struct.pack('>hhHH', 90, 40, 0xffff, 0xffff)  # Min/Max W/H
    nw += struct.pack('>H', 1)                       # Type = WBENCHSCREEN
    assert len(nw) == 48, len(nw)
    return nw + struct.pack('>ii', 0, 0)             # CurrentX, CurrentY

def make_drawer_icon(tool_info):
    """FALLBACK drawer icon: derive a WBDRAWER .info from the vintage WBTOOL icon (set
    do_Type=WBDRAWER, do_DrawerData non-zero, insert a 56-byte DrawerData). Used only when the
    Workbench ADF isn't available to extract the real drawer icon."""
    d = bytearray(tool_info)
    assert struct.unpack('>H', d[0:2])[0] == 0xe310, 'not a DiskObject'
    d[48] = 0x02                                     # do_Type = WBDRAWER
    struct.pack_into('>I', d, 66, 0x00000064)        # do_DrawerData = non-zero (WB fills real ptr)
    return bytes(d[:78]) + drawerdata() + bytes(d[78:])

_drawer_cache = None
def drawer_icon(fallback_tool_icon):
    """The archive's drawer icon: a genuine standard Workbench 2.1 drawer icon extracted from
    the WB ADF at build time (kept out of the repo). do_CurrentX/Y are reset to
    NO_ICON_POSITION so Workbench auto-places it on extract. Falls back to a derived icon if
    the ADF or xdftool is unavailable."""
    global _drawer_cache
    if _drawer_cache is not None:
        return _drawer_cache
    if os.path.exists(DEFAULT_WB_ADF):
        try:
            with tempfile.TemporaryDirectory() as td:
                out = os.path.join(td, WB_DRAWER_ICON)
                subprocess.run([sys.executable, '-m', 'amitools.tools.xdftool',
                                DEFAULT_WB_ADF, 'read', WB_DRAWER_ICON, out],
                               check=True, capture_output=True)
                d = bytearray(open(out, 'rb').read())
                assert struct.unpack('>H', d[0:2])[0] == 0xe310 and d[48] == 0x02, 'not a WBDRAWER'
                struct.pack_into('>II', d, 58, 0x80000000, 0x80000000)  # do_CurrentX/Y = NO_ICON_POSITION
                _drawer_cache = bytes(d)
                print(f"  drawer icon: extracted {WB_DRAWER_ICON} from {os.path.basename(DEFAULT_WB_ADF)}")
                return _drawer_cache
        except Exception as e:
            print(f"  drawer icon: WB ADF extract failed ({e}); using derived icon")
    else:
        print(f"  drawer icon: WB ADF not found at {DEFAULT_WB_ADF}; using derived icon")
    _drawer_cache = make_drawer_icon(fallback_tool_icon)
    return _drawer_cache


# ---- build -----------------------------------------------------------------------------

def read(path):
    with open(path, 'rb') as f:
        return f.read()

def build(host, archive_path):
    """Build one archive with the given TCPHOST default. Returns the entries list."""
    tool_icon = bytearray(read(os.path.join(VINTAGE, 'CNet.info')))   # authentic WBTOOL icon
    # do_StackSize (offset 74): the vintage icon has 0 (=> Workbench's ~4KB default, too small
    # for the client's deep call chains when launched from WB). Give it a comfortable stack.
    struct.pack_into('>I', tool_icon, 74, 16384)
    tool_icon = bytes(tool_icon)

    # (archive-name, on-disk source bytes, directory-or-None)
    entries = []
    def add(name, data, directory):
        entries.append((name, data, directory))

    # Root: the drawer icon (genuine WB2.1 drawer icon; derived fallback if no ADF).
    add(f'{DRAWER}.info', drawer_icon(tool_icon), None)
    # Inside the Compunet drawer:
    add('Compunet',            read(os.path.join(HDD, 'Compunet')),           DRAWER)
    add('Compunet.info',       tool_icon,                                     DRAWER)
    add('CnetEditor',          read(os.path.join(HDD, 'CnetEditor')),         DRAWER)
    add('CnetTty',             read(os.path.join(HDD, 'CnetTty')),            DRAWER)
    add('cnet-configuration',  read(os.path.join(HDD, 'cnet-configuration')), DRAWER)
    add('TCPHOST',             (host + '\n').encode('latin1'),                DRAWER)
    add('README',              readme(host).encode('latin1'),                 DRAWER)

    blob = b''
    for name, data, directory in entries:
        blob += lha_entry(b'-lh0-', name, data, directory)
    blob += b'\x00'                                          # archive terminator

    with open(archive_path, 'wb') as f:
        f.write(blob)
    print(f"wrote {os.path.relpath(archive_path, ROOT)} "
          f"({len(blob)} bytes, {len(entries)} entries, TCPHOST={host})")
    return entries

def main():
    """Build BOTH archives (always), and publish the live one to the website. Returns
    {archive_path: entries} for validation."""
    os.makedirs(DIST, exist_ok=True)
    built = {
        PROD_ARCHIVE: build(PROD_HOST, PROD_ARCHIVE),   # public release -> live server
        DEV_ARCHIVE:  build(DEV_HOST,  DEV_ARCHIVE),    # dev build      -> local server
    }
    # Publish the LIVE archive to the website's static downloads (stable name).
    if os.path.isdir(os.path.dirname(WEBSITE_LHA)):
        shutil.copyfile(PROD_ARCHIVE, WEBSITE_LHA)
        print(f"published live archive -> {os.path.relpath(WEBSITE_LHA, ROOT)}")
    return built

if __name__ == '__main__':
    main()
