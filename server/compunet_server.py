"""
Compunet Server - Recreated from reverse-engineered protocol.

Both WebSocket and TCP clients speak the same binary protocol:

  Client -> Server: COM packets
    Byte 0: Command letter (A, B, C, D, E, I, M, P, U, V)
    Bytes 1+: Parameters (variable length)

  Server -> Client: Response packets
    Byte 0: Response type
      $41 'A' = ACK / proceed (followed by data)
      $4C 'L' = Linking required (followed by terminal software)
      $44 'D' = Directory data follows
      $46 'F' = Frame data follows
      $45 'E' = Error (followed by message)
    Byte 1+: Payload

  Frame data format (same as SEQ files):
    $00 = end of frame
    $06 <N> = repeat space N times
    $07 <char> <count> = RLE
    $0D = carriage return
    Standard PETSCII control codes for colours, reverse, charset

Transport:
  TCP (port 6400): raw protocol bytes over stream (X.25 binding)
  Client API (port 6404): JSON over WebSocket/HTTP (see api_binding.py)
"""

import asyncio
import base64
import hashlib
import json
import os
import re
import glob
import logging
import secrets
import shutil
import datetime
from pathlib import Path
import markdown
import aiohttp
import header_frame
import header_preview
import partyline
import terminal

try:
    from aiohttp import web as aiohttp_web
except ImportError:
    aiohttp_web = None

# Log level is env-configurable (LOG_LEVEL); default INFO for production. Set
# LOG_LEVEL=DEBUG in the environment to restore full debug output.
_LOG_LEVEL = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(level=_LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('compunet')

# Load .env file if present (allows restart without rebuild).
#
# In the container this file sits at /app, so the first path IS the root .env
# that docker-compose mounts to /app/.env — server and website read one file.
# A source checkout is not flattened that way: server/.env usually does not
# exist, and the file the tree actually documents (.env.example, and what
# website/config.py reads) is at the repository root. Without the fallback the
# server silently started with no configuration at all, which shows up as an
# empty COMPUNET_API_KEY — and _api_check_auth fails closed, so every call the
# website makes to the admin API returns 401 while both processes look healthy.
_env_file = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(_env_file):
    _env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_file):
    with open(_env_file, 'r') as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _key, _val = _line.split('=', 1)
            os.environ.setdefault(_key.strip(), _val.strip())

# Audit log
AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), 'data', 'audit.jsonl')

#: Every audit event, mapped to the `kind` it belongs to. THE AUTHORITATIVE LIST —
#: `audit_log` refuses an event that is not here, so a typo or an undeclared event
#: fails loudly at the call site instead of appearing in the log as a name nothing
#: filters on. Documented in docs/audit-log.md.
#:
#: Names are `noun_verbed`, past tense, throughout. The vocabulary previously grew
#: ad hoc — `page_deleted` and `header_removed` against `upload` and `vote` — with
#: no documented set for a new feature to conform to.
#:
#: `kind` exists so the viewer can separate the signal from the volume: `browse` is
#: every page view from three surfaces and dominates the log, while `admin` is the
#: handful of events anyone auditing actually wants.
AUDIT_KINDS = ('content', 'mail', 'session', 'admin', 'partyline', 'browse',
               'operational')

AUDIT_EVENTS = {
    # Reading. High volume, deliberately its own kind so it can be excluded.
    'page_read':            'browse',
    'mail_opened':          'browse',

    # Content changes.
    'page_uploaded':        'content',
    'page_bought':          'content',
    'page_voted':           'content',
    'page_life_extended':   'content',
    'page_downloaded':      'content',
    'page_renamed':         'content',
    'page_moved':           'content',
    'page_reordered':       'content',
    'page_deleted':         'content',
    'directory_created':    'content',
    'directory_settings_changed': 'content',
    'header_set':           'content',
    'header_removed':       'content',

    # Mail.
    'mail_sent':            'mail',

    # Sessions and accounts.
    'session_started':      'session',
    'session_ended':        'session',
    'login_succeeded':      'session',
    'login_failed':         'session',
    'signup_completed':     'session',
    'password_changed':     'session',
    'password_reset_requested': 'session',
    'password_reset':       'session',

    # Administration. The events an audit log exists for.
    'user_updated':         'admin',
    'user_deleted':         'admin',
    'broadcast_sent':       'admin',
    'registration_requested': 'admin',
    'registration_rejected': 'admin',

    # Partyline.
    'partyline_entered':    'partyline',
    'partyline_kicked':     'partyline',
    'partyline_banned':     'partyline',
    'partyline_unbanned':   'partyline',

    # Server faults, not user actions. No `user`.
    'missing_frame':        'operational',
}


def audit_log(event, user=None, session=None, **details):
    """Append an event to the audit log (JSON-lines format).

    ⚠ CALL THIS FROM THE FUNCTION THAT PERFORMS THE ACTION, not from the command
    handler that reached it. Auditing used to sit at the caller, so whether an
    action was recorded depended on which door the user came through: mail sent
    from a C64 or the terminal was logged, and the same mail sent through the JSON
    API was not, because Binding B calls the shared `_complete_mail_send` directly.
    `_complete_content_upload` had it right and uploads were recorded everywhere.
    Same file, seventy lines apart (#127).

    Pass `session` and both `ip` and `via` are derived from it, so a new call site
    cannot omit them — they were previously per-call-site arguments, present on all
    ten of terminal.py's events and on almost none of Binding A's.
    """
    kind = AUDIT_EVENTS.get(event)
    if kind is None:
        # Loud, not silent: an unknown name would be written and then be invisible
        # to every filter that knows the vocabulary.
        raise ValueError(
            'unknown audit event %r — add it to AUDIT_EVENTS with its kind' % event)

    entry = {
        'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'event': event,
        'kind': kind,
    }
    if user:
        entry['user'] = user
    if session is not None:
        if user is None and getattr(session, 'user_id', None):
            entry['user'] = session.user_id
        ip = getattr(session, 'client_ip', None)
        if ip and 'ip' not in details:
            entry['ip'] = ip
        via = audit_via(session)
        if via and 'via' not in details:
            entry['via'] = via
    entry.update(details)
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except OSError:
        log.warning('Failed to write audit log entry: %s', entry)


#: Never written to the audit log, whatever an admin changed.
_AUDIT_SECRET_FIELDS = frozenset(('password',))


def _audit_diff(before, after):
    """`['credit: 10.0 -> 25.0', 'editor: False -> True']` for what an edit changed.

    Secrets are named but never valued: recording a password hash — before or
    after — would put credential material in a log an admin reads in a browser.
    """
    changes = []
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old == new:
            continue
        if key in _AUDIT_SECRET_FIELDS:
            changes.append('%s: changed' % key)
        else:
            changes.append('%s: %r -> %r' % (key, old, new))
    return changes


def identify_binding_a_client(session, is_amiga):
    """Record WHICH machine a Binding-A session turned out to be.

    ⚠ Both fields, in one place, on purpose. `is_amiga` drives behaviour (packet
    size, LINKING, the IFF guard) and `audit_via` drives the log, and they were set
    at different points by different code: the socket set `audit_via = 'c64'` before
    identification could know better, and the handler then set only `is_amiga`. Since
    audit_via() returns an explicit value before consulting is_amiga, the label never
    caught up and EVERY Amiga session was logged as a C64 (#127 shipped that).
    Setting one without the other is the bug, so nothing may set just one.
    """
    session.is_amiga = bool(is_amiga)
    session.audit_via = 'amiga' if is_amiga else 'c64'


def audit_via(session):
    """Which surface an action came through: c64, amiga, terminal, api, web, admin.

    Without this the log cannot answer "what did this user do, and from where" — a
    `page_read` from a C64 was indistinguishable from one through the web client
    except by whether `ip` happened to be present.

    `audit_via` is set explicitly where a session is created.

    ⚠ AN EXPLICIT VALUE WINS, so a session that sets it must KEEP IT TRUE. The
    is_amiga fallback below is a safety net for sessions that never set one — it is
    NOT a correction. A Binding-A session sets `audit_via = 'c64'` the moment the
    socket opens, before it can know better, so setting `is_amiga` later did nothing
    and every Amiga was recorded as a C64. The identification handler now updates
    `audit_via` itself; this reading order is why it has to.
    """
    if session is None:
        return None
    explicit = getattr(session, 'audit_via', None)
    if explicit:
        return explicit
    if getattr(session, 'is_amiga', False):
        return 'amiga'
    return None

# Server configuration
TCP_PORT = 6400
API_PORT = 6403
TERM_PORT = 6401
CLIENT_API_PORT = 6404   # Binding B — modern JSON client API (see api_binding.py)
SERVER_DIR = os.path.dirname(__file__)
CFG_DIR = os.path.join(SERVER_DIR, 'cfg')

# Data locations are overridable so a run can be pointed at a fixture tree
# (server/data/content.test) without touching live content — see
# docs/spec/CLEANROOM.md. COMPUNET_DATA_DIR moves everything together, which is
# what a validation run wants: test uploads and test mail then land in the
# fixture tree instead of polluting real data.
DATA_DIR = os.environ.get('COMPUNET_DATA_DIR') or os.path.join(SERVER_DIR, 'data')
CONTENT_DIR = os.environ.get('COMPUNET_CONTENT_DIR') or os.path.join(DATA_DIR, 'content')
ROOT_DIR = os.path.join(CONTENT_DIR, 'root')
#: The reference web client, served from the client API's own origin when built
#: into the image (see server/Dockerfile). Empty in a source checkout, where
#: run_api_dev.py serves it instead.
WEB_CLIENT_DIR = os.environ.get('COMPUNET_WEB_CLIENT_DIR') or os.path.join(SERVER_DIR, 'web')
MAIL_DIR = os.environ.get('COMPUNET_MAIL_DIR') or os.path.join(DATA_DIR, 'mail')
VOTES_PATH = os.path.join(DATA_DIR, 'votes.json')


def _compute_terminal_hash():
    """Compute a 2-byte checksum of terminal.bin for version-aware LINKING."""
    terminal_path = os.path.join(CFG_DIR, 'terminal.bin')
    if not os.path.exists(terminal_path):
        return 0x30, 0x30  # No terminal = same as "not loaded"
    with open(terminal_path, 'rb') as f:
        data = f.read()
    # Simple 16-bit additive checksum (fast, sufficient for change detection)
    checksum = 0
    for b in data:
        checksum = (checksum + b) & 0xFFFF
    hi = (checksum >> 8) & 0xFF
    lo = checksum & 0xFF
    # Avoid $30/$30 which means "no terminal"
    if hi == 0x30 and lo == 0x30:
        lo = 0x31
    return lo, hi


TERMINAL_HASH = _compute_terminal_hash()
log.info('Terminal hash: $%02X/$%02X', TERMINAL_HASH[0], TERMINAL_HASH[1])

# Active session tracking
_online_users = set()  # user IDs currently online


def _user_connect(user_id):
    """Mark a user as online (called on login and any activity)."""
    _online_users.add(user_id)


def _user_disconnect(user_id, session=None):
    """Mark a user as offline (called on LEAVE, disconnect, or timeout).

    ⚠ Audits the session end HERE so every surface records it. Binding A audited
    it in tcp_handler and the terminal in its own teardown; Binding B did neither,
    so a web-client session simply stopped appearing (#127). It also never called
    this at all, which left those users listed on WHO IS ONLINE indefinitely —
    the same omission, with a second symptom.
    """
    if user_id and user_id in _online_users:
        audit_log('session_ended', user=user_id, session=session)
    _online_users.discard(user_id)

WHO_PAGE_DIR = os.path.join(ROOT_DIR, 'who-is-online')  # slug of "WHO IS ONLINE?"
WHO_PAGE_NUM = 800


def _regenerate_who_frame():
    """Regenerate the WHO IS ONLINE frame SEQ file from current sessions."""
    import partyline as pl
    import datetime
    os.makedirs(WHO_PAGE_DIR, exist_ok=True)

    users = sorted(_online_users)
    partyline_users = set(pl._users.keys()) if hasattr(pl, '_users') else set()
    now = datetime.datetime.now().strftime('%H:%M')

    frame = bytearray()
    frame.append(0x00)  # frame flags
    frame.append(0x06)  # repeat space...
    frame.append(0x0F)  # ...15 times (clear line)
    frame.append(0x8E)  # uppercase mode
    frame.append(0x0D)  # CR
    # Red header with time (matches original format)
    frame.append(0x1C)  # red
    frame.extend(ascii_to_petscii(f'   CNETTERS ON THE SYSTEM AT {now}'))
    frame.append(0x0D)
    frame.extend(ascii_to_petscii('   * INDICATES A USER IN PARTYLINE'))
    frame.append(0x0D)
    frame.append(0x0D)

    # Cyan user list in 3 columns
    frame.append(0x1F)  # cyan
    col_width = 13
    cols = 3
    row_count = (len(users) + cols - 1) // cols

    for row in range(row_count):
        line = ''
        for col in range(cols):
            idx = row + col * row_count
            if idx < len(users):
                uid = users[idx]
                star = '*' if uid in partyline_users else ' '
                entry = ' ' + uid + star
                line += entry.ljust(col_width)
        frame.extend(ascii_to_petscii(line.rstrip()))
        frame.append(0x0D)

    with open(os.path.join(WHO_PAGE_DIR, 'frame-1.seq'), 'wb') as f:
        f.write(bytes(frame))


def _populate_whats_new(page, directory):
    """Populate the WHAT'S NEW? dynamic directory with most recent uploads."""
    # Collect all pages that have an uploaded timestamp
    all_pages = [p for p in directory.pages.values()
                 if getattr(p, 'uploaded', None) and p.page_num != page.page_num]
    # Sort by uploaded date, newest first
    all_pages.sort(key=lambda p: p.uploaded, reverse=True)
    # Take top 11 (one page of directory entries)
    page.children = all_pages[:11]
    log.info("WHAT'S NEW: found %d pages with uploaded, showing %d",
             len(all_pages), len(page.children))


# Protocol constants
RESP_ACK = 0x41       # 'A' - acknowledge/proceed
RESP_LINKING = 0x4C   # 'L' - linking required
RESP_DIR = 0x44       # 'D' - directory data
RESP_FRAME = 0x46     # 'F' - frame data
RESP_ERROR = 0x45     # 'E' - error

# Program-file machine type. Stored human-readably on the page ('c64'/'amiga') and mapped
# to the download header's byte-0 machine code the client reads (0=C64, 1=Amiga, 2=Atari
# ST). Uploaded 'P' pages record their uploader's platform; absent/unknown -> C64 (0), so
# all pre-existing content serves exactly as before.
MACHINE_CODES = {'c64': 0, 'amiga': 1, 'st': 2}
#: The reverse, for storing what a client declared on upload. An unknown code
#: falls back to C64, which is also what an absent machine_type means.
MACHINE_NAMES = {code: name for name, code in MACHINE_CODES.items()}

CMD_ACCNT = 0x41      # 'A'
CMD_BACK = 0x42       # 'B' (was incorrectly 'C' — verified from terminal disassembly)
CMD_UCAT = 0x43       # 'C' (user catalogue)
CMD_DIR = 0x44        # 'D'
CMD_EDITR = 0x45      # 'E'
CMD_ID = 0x49         # 'I'
CMD_MAIL = 0x4D       # 'M'
CMD_SHOW = 0x50       # 'P'
CMD_UPLD = 0x55       # 'U'
CMD_VOTE = 0x56       # 'V'
CMD_BUY = 0x58        # 'X'

# Shared locks for multi-client safety (asyncio single-threaded, but
# prevents interleaving of read-modify-write sequences across await points)
_lock_users = asyncio.Lock()
_lock_content = asyncio.Lock()
_lock_mail = asyncio.Lock()

# PETSCII helpers
PETSCII_RETURN = 0x0D
PETSCII_RED = 0x1C
PETSCII_BLUE = 0x1F
PETSCII_WHITE = 0x05
PETSCII_GREEN = 0x1E
PETSCII_PURPLE = 0x9C
PETSCII_LRED = 0x96
PETSCII_CYAN = 0x9F
PETSCII_YELLOW = 0x9E
PETSCII_LBLUE = 0x9A
PETSCII_LGREY = 0x9B
PETSCII_DGREY = 0x97
PETSCII_BLACK = 0x90
PETSCII_RVS_ON = 0x12
PETSCII_RVS_OFF = 0x92
PETSCII_UPPER = 0x8E
PETSCII_LOWER = 0x0E
PETSCII_CLR = 0x93


def ascii_to_petscii(text):
    """Convert ASCII string to PETSCII bytes (uppercase, $41-$5A range)."""
    result = bytearray()
    for ch in text:
        code = ord(ch)
        if 65 <= code <= 90:      # A-Z -> PETSCII $41-$5A
            result.append(code)
        elif 97 <= code <= 122:   # a-z -> PETSCII $41-$5A
            result.append(code - 32)
        elif 32 <= code <= 63:    # space, digits, punctuation
            result.append(code)
        else:
            result.append(code & 0x7F)
    return bytes(result)


def make_space_run(count):
    """Encode a run of spaces using $06 <count>."""
    if count <= 0:
        return b''
    if count == 1:
        return b'\x20'
    # $06 <count> for runs of 2-31
    result = bytearray()
    while count > 0:
        run = min(count, 31)
        if run == 1:
            result.append(0x20)
        else:
            result.append(0x06)
            result.append(run)
        count -= run
    return bytes(result)


class CompunetPage:
    """A page in the Compunet directory tree."""
    
    def __init__(self, page_num, title, page_type='T', size=0, author='SYSTEM', price=0.0, life=0, vote=0, keyword=None):
        self.page_num = page_num
        self.title = title
        self.page_type = page_type
        self.size = size
        self.author = author
        self.price = price
        self.life = life
        self.vote = vote
        self.keyword = keyword
        self.uploaded = None     # ISO timestamp when content was uploaded
        self.children = []
        self.frames = []    # list of bytes objects (raw frame data)
        self.parent = None
    
    def has_subdir(self):
        if len(self.children) > 0:
            return True
        return self.page_type == 'D' and getattr(self, 'dynamic', None) is not None
    
    def type_string(self):
        """Generate the type suffix shown in directory listings."""
        s = self.page_type
        if self.page_type != 'L' and self.size > 0:
            if not (self.page_type == 'T' and self.size == 1):
                s += str(self.size)
        if self.has_subdir():
            s += '+'
        return s


class CompunetDirectory:
    """The content tree, loaded fresh from per-directory JSON files on each access."""

    def __init__(self):
        self.pages = {}
        #: Numbers found on more than one entry while loading. Empty is the
        #: normal case; anything in here is a content defect that makes those
        #: entries unaddressable (see _register_page).
        self.duplicate_page_nums = set()
        self.root = None
        self.global_adverts = []
        self.reload()

    def reload(self):
        """Reload the entire tree from disk."""
        self.pages = {}
        self.duplicate_page_nums = set()
        self.root = None
        self.global_adverts = []
        self._load_tree()
        self._apply_votes()

    def _load_tree(self):
        """Load directory structure from root/root.json (new flat format)."""
        json_path = os.path.join(ROOT_DIR, 'root.json')
        if not os.path.exists(json_path):
            self.root = CompunetPage(1, 'COMPUNET', 'D')
            self.pages[1] = self.root
            return

        with open(json_path, 'r') as f:
            data = json.load(f)

        # Root page (virtual container)
        self.root = CompunetPage(page_num=100, title='WELCOME', page_type='D', author='SYSTEM')
        self.root.header = data.get('header', None)
        self.root._adverts = data.get('adverts', [])
        self.root.shortcuts = data.get('shortcuts', None)
        self.root._dir_path = ROOT_DIR
        self.pages[100] = self.root

        for page_data in data.get('pages', []):
            page = self._build_flat_page(page_data, self.root, ROOT_DIR)
            self.root.children.append(page)

        # Load global fallback adverts
        adverts_path = os.path.join(CONTENT_DIR, 'adverts.json')
        if os.path.exists(adverts_path):
            with open(adverts_path, 'r') as f:
                self.global_adverts = json.load(f).get('adverts', [])

    def _register_page(self, page):
        """Add a page to the number lookup, refusing to let a duplicate hide one.

        ⚠ A page number is the tree's identity: `GOTO <n>` resolves through this
        table, and the website addresses every edit by number. Nothing enforced
        uniqueness here — it was a plain `self.pages[num] = page`, so a repeated
        number silently overwrote the earlier entry and made it unreachable while
        it still rendered in its listing. `data.example` shipped exactly that
        (page 700 was both DEMOS and FEBREVIEW FOUR), and an edit addressed by
        number would have acted on whichever loaded second — you ask to move one
        page and a different one moves.

        The duplicate is NOT auto-renumbered. That would change a user-visible
        identifier without anyone asking, break any bookmark or GOTO pointing at
        it, and differ from what is on disk. Instead: the FIRST occurrence wins,
        so behaviour is deterministic rather than dependent on load order, and the
        collision is logged as an error naming both entries so it gets fixed.
        `duplicate_page_nums` carries them to the API, which marks them
        uneditable.
        """
        existing = self.pages.get(page.page_num)
        if existing is not None and existing is not page:
            self.duplicate_page_nums.add(page.page_num)
            log.error('CONTENT: page number %d used twice — "%s" and "%s". '
                      'Keeping "%s"; the other is unreachable by number until '
                      'one is renumbered.',
                      page.page_num, existing.title, page.title, existing.title)
            return
        self.pages[page.page_num] = page

    def next_page_num(self):
        """A page number no entry in the tree is using.

        ⚠ Derived from the whole tree rather than `max(self.pages)`: the lookup
        table cannot see a duplicate that was refused, so a number could be
        handed out that is already in use further down. Walking the tree is cheap
        and cannot be wrong.
        """
        used = set()

        def walk(page):
            used.add(page.page_num)
            for child in page.children:
                walk(child)

        if self.root is not None:
            walk(self.root)
        used |= set(self.pages)
        return (max(used) + 1) if used else 1000

    @staticmethod
    def _make_slug(title):
        """Convert a page title to a filesystem-safe directory slug."""
        slug = title.lower().replace(' ', '-')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        return slug.strip('-') or 'untitled'

    def _build_flat_page(self, node, parent, base_dir):
        """Build a page from flat JSON node, resolving paths from its folder."""
        if 'directory' in node:
            dir_json_path = os.path.join(ROOT_DIR, node['directory'])
            page_dir = os.path.dirname(dir_json_path)
        else:
            page_slug = self._make_slug(node['title'])
            page_dir = os.path.join(base_dir, page_slug)

        page = CompunetPage(
            page_num=node['page_num'],
            title=node['title'],
            page_type=node.get('type', 'T'),
            size=len(node.get('frames', [])),
            author=node.get('author', 'SYSTEM'),
            price=node.get('price', 0),
            life=node.get('life', 0),
            keyword=node.get('keyword', None),
        )
        page.parent = parent
        page._dir_path = page_dir
        page.dynamic = node.get('dynamic', None)
        page.uploaded = node.get('uploaded', None)
        page.machine_type = node.get('machine_type', 'c64')  # absent -> C64 (existing content)
        self._register_page(page)

        # Load frames from page folder
        page._frame_files = node.get('frames', [])
        for frame_file in page._frame_files:
            frame_path = os.path.join(page_dir, frame_file)
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    page.frames.append(f.read())
            else:
                # Missing frame file — insert error frame and log
                error_frame = b'\x00\x06\x0F\x8E\x0D\x1C FRAME NOT FOUND\x0D\x0D'
                error_frame += ascii_to_petscii(f' {frame_file}') + b'\x0D\x00'
                page.frames.append(error_frame)
                log.warning('CONTENT: missing frame file: %s', frame_path)
                audit_log('missing_frame', path=frame_path,
                          page=page.page_num, title=page.title)

        # For program pages, calculate size in KB from file data
        if page.page_type == 'P' and page.frames:
            page.size = (len(page.frames[0]) - 2 + 1023) // 1024
        # An IFF picture ('F') is stored whole — no 2-byte load address to discount.
        elif page.page_type == 'F' and page.frames:
            page.size = (len(page.frames[0]) + 1023) // 1024

        # If page is also a directory, load sub-directory JSON
        if 'directory' in node:
            dir_json_path = os.path.join(ROOT_DIR, node['directory'])
            sub_base_dir = os.path.dirname(dir_json_path)
            if os.path.exists(dir_json_path):
                with open(dir_json_path, 'r') as f:
                    sub_data = json.load(f)
                page._adverts = sub_data.get('adverts', [])
                page.shortcuts = sub_data.get('shortcuts', None)
                if sub_data.get('header'):
                    page.header = sub_data['header']
                # Store the flag only when the key is PRESENT, so that an
                # explicit `false` is distinguishable from "not set" — the
                # former stops inheritance, the latter defers to the ancestor
                # (see _can_upload_here).
                if 'open_upload' in sub_data:
                    page.open_upload = bool(sub_data['open_upload'])
                for child_data in sub_data.get('pages', []):
                    child = self._build_flat_page(child_data, page, sub_base_dir)
                    page.children.append(child)
        else:
            page._adverts = []

        return page

    def _apply_votes(self):
        """Populate vote averages from votes.json."""
        votes_path = VOTES_PATH
        if not os.path.exists(votes_path):
            return
        with open(votes_path, 'r') as f:
            votes = json.load(f)
        for page_key, user_votes in votes.items():
            page_num = int(page_key)
            if page_num in self.pages and user_votes:
                self.pages[page_num].vote = round(
                    sum(user_votes.values()) / len(user_votes))


def directory_json_path(page, root_dir):
    """Where this directory's own JSON lives.

    The root is the exception: `root.json` at the top of the tree rather than a
    `directory.json` in a sub-folder. A page is the root when it has no parent.
    """
    if getattr(page, 'parent', None) is None:
        return os.path.join(root_dir, 'root.json')
    return os.path.join(getattr(page, '_dir_path', ''), 'directory.json')


def _write_json_atomic(path, data):
    """Write JSON so a concurrent reader can never see it half-written.

    ⚠ `_load_tree` re-reads every `directory.json` on EVERY directory render, and
    a plain `open(path, 'w')` truncates the file before the new bytes land — so a
    reader arriving in that window gets a partial file and the tree fails to
    parse. Writing beside it and renaming is atomic on both POSIX and Windows.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def build_directory_json(page, root_dir):
    """The JSON for ONE directory: its own settings, plus its child entries.

    ⚠ THE ONLY serializer for the content tree. There used to be two — this and a
    copy in `terminal.py` — and they drifted apart in both directions, each
    dropping a key the other kept: `shortcuts` (so root.json's F-key block
    disappeared on the first upload), an explicit `open_upload: false` (reopening
    a directory its owner had closed), `machine_type` (turning Amiga pages into
    C64 ones), and the `directory` key on an authored-but-empty directory (making
    a whole sub-tree unreachable). Which keys survived a save depended on which
    subsystem the user happened to be using.
    """
    data = {}
    # Round-trip the flag whenever it is set, including an explicit
    # `false` — writing back only the truthy case would silently drop a
    # directory's opt-out and reopen it to everyone (_can_upload_here).
    if hasattr(page, 'open_upload'):
        data['open_upload'] = bool(page.open_upload)
    if hasattr(page, 'header') and page.header:
        data['header'] = page.header
    if getattr(page, 'shortcuts', None):
        data['shortcuts'] = page.shortcuts
    if hasattr(page, '_adverts') and page._adverts:
        data['adverts'] = page._adverts

    pages_list = []
    for child in page.children:
        node = {
            'page_num': child.page_num,
            'title': child.title,
            'type': child.page_type,
            'author': child.author,
            'price': child.price,
            'life': child.life,
        }
        if child.keyword:
            node['keyword'] = child.keyword
        if getattr(child, 'dynamic', None):
            node['dynamic'] = child.dynamic
        if getattr(child, 'uploaded', None):
            node['uploaded'] = child.uploaded
        if getattr(child, 'machine_type', 'c64') != 'c64':
            node['machine_type'] = child.machine_type  # only write non-default
        frame_files = getattr(child, '_frame_files', [])
        if frame_files:
            node['frames'] = frame_files
        child_dir = getattr(child, '_dir_path', '')
        dir_json_path = os.path.join(child_dir, 'directory.json')
        # ⚠ Keep the sub-directory whenever one EXISTS, not only while it
        # currently holds children. An authored-but-empty directory is
        # real — §7.3 lists it with the (EMPTY) placeholder — and the
        # narrower `if child.children` test DELETED it: the next save
        # wrote the entry back without its `directory` key, so the
        # sub-tree became unreachable while its files sat on disk. Found
        # in the fixture tree after clean-room run 9, where JUNGLE's
        # GRAPHICS entry lost its directory to an unrelated upload.
        if not getattr(child, 'dynamic', None) and (
                child.children or os.path.exists(dir_json_path)):
            # Forward slashes: os.path.relpath yields backslashes on
            # Windows, and those do not resolve on the Linux host that
            # actually serves this tree.
            node['directory'] = os.path.relpath(
                dir_json_path, root_dir).replace(os.sep, '/')
        pages_list.append(node)
    data['pages'] = pages_list
    return data


def save_one_directory(page, root_dir):
    """Write ONE directory's JSON, and nothing else.

    ⚠ THIS, not `save_directory_tree`, is what a mutation should call.
    Rewriting the whole tree to change one directory is how uploads went missing:
    every session holds its own `CompunetDirectory`, so a whole-tree write
    republishes that session's entire view of the content and silently discards
    whatever another session committed since it loaded. The writer is not racing
    another writer — within one event loop these calls cannot interleave — it is
    publishing stale data over fresh data. A lock would not have helped; writing
    only what changed does.

    Callers must therefore know which directories they actually altered. That is
    a small burden and it is the whole fix.
    """
    _write_json_atomic(directory_json_path(page, root_dir),
                       build_directory_json(page, root_dir))


def save_directory_tree(root_page, root_dir):
    """Rewrite the WHOLE tree from this in-memory copy.

    ⚠ Prefer `save_one_directory`. This is only correct when the caller's tree is
    known to be current — a freshly loaded one, or the tests. Used against a
    session's long-lived copy it discards other sessions' work (see
    `save_one_directory`).
    """
    def walk(page):
        save_one_directory(page, root_dir)
        for child in page.children:
            if getattr(child, 'dynamic', None):
                continue
            if child.children or os.path.exists(
                    os.path.join(getattr(child, '_dir_path', ''),
                                 'directory.json')):
                walk(child)

    walk(root_page)


#: Longest title an entry may carry — the same limit uploads apply (§7.3 gives the
#: title field 17 columns; the upload path truncates to 16).
MAX_TITLE = 16


class RelocateError(Exception):
    """A move or rename that must not proceed, with a reason for the user."""


def archive_page(page, data_dir, reason='replaced', timestamp=None):
    """Copy a page's files and metadata aside before it is removed.

    ⚠ THE ONLY archiver, and it RECURSES. There were two copies of this — here
    and in `terminal.py` — and neither descended into a directory's contents: they
    copied `_frame_files` and stopped. So reducing a *directory* page's life to
    zero removed it and left its whole subtree on disk, unreachable and
    unarchived. Content silently lost, from a command users already had.

    That mattered more once a directory's owner could delete the directory with
    other people's pages inside it (#121): without recursion the safety net does
    not cover the material most likely to be missed.

    Each page gets its own folder under `archive/`, so a subtree arrives as a set
    of entries rather than one opaque blob, and each carries the `metadata.json`
    that says what it was and why it went. Nothing reads the archive back — it is
    a safety net for an operator, not an undo button — so the metadata has to be
    enough to rebuild an entry by hand.

    Returns the archive directories written, newest-first order irrelevant.
    """
    stamp = timestamp or datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    written = []
    for node in _subtree(page):
        slug = CompunetDirectory._make_slug(node.title)
        dest = os.path.join(data_dir, 'archive',
                            '%d-%s-%s' % (node.page_num, slug, stamp))
        os.makedirs(dest, exist_ok=True)

        node_dir = getattr(node, '_dir_path', '')
        for frame_file in getattr(node, '_frame_files', []):
            src = os.path.join(node_dir, frame_file)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dest, frame_file))

        # A directory's header is its own artwork and would otherwise be the one
        # thing not recoverable.
        header = getattr(node, 'header', None)
        if header:
            src = os.path.join(ROOT_DIR, *header.split('/'))
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dest, os.path.basename(src)))

        metadata = {
            'page_num': node.page_num,
            'title': node.title,
            'type': node.page_type,
            'author': node.author,
            'price': node.price,
            'life': node.life,
            'uploaded': getattr(node, 'uploaded', None),
            'archived': stamp,
            'reason': reason,
        }
        if node is not page:
            # So an operator can see where a descendant sat, and rebuild the
            # shape rather than just the files.
            metadata['was_inside'] = node.parent.title
            metadata['was_inside_page'] = node.parent.page_num
        with open(os.path.join(dest, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)

        log.info('ARCHIVE: page %d "%s" by %s -> %s (%s)',
                 node.page_num, node.title, node.author, dest, reason)
        written.append(dest)
    return written


def delete_page(directory, page, data_dir, root_dir, reason='deleted'):
    """Archive a page and everything beneath it, then remove it from the tree.

    Follows the path negative `LIFE` already takes — archive, then remove — so the
    same act through two interfaces has the same effect. Returns
    `(archived_dirs, refunds)`, where refunds is `{user_id: units}` for the caller
    to credit: storage is refunded to each page's OWN author, never to whoever
    pressed the button, so an admin clearing a directory does not credit or charge
    the wrong person.
    """
    parent = page.parent
    if parent is None:
        raise RelocateError('the root directory cannot be deleted')

    doomed = _subtree(page)
    refunds = {}
    for node in doomed:
        frames = len(node.frames) if node.frames else 1
        units = frames * max(0, node.life)
        if units:
            refunds[node.author] = refunds.get(node.author, 0) + units

    archived = archive_page(page, data_dir, reason=reason)

    page_dir = getattr(page, '_dir_path', '')
    if page_dir and os.path.isdir(page_dir):
        shutil.rmtree(page_dir, ignore_errors=True)

    if page in parent.children:
        parent.children.remove(page)
    for node in doomed:
        if directory.pages.get(node.page_num) is node:
            del directory.pages[node.page_num]

    return archived, refunds


def _subtree(page):
    """This page and every descendant, parents before children."""
    out = [page]
    for child in page.children:
        out.extend(_subtree(child))
    return out


def _rehome_header(page, old_root, new_root, root_dir):
    """Fix a directory's header path after its folder has moved.

    ⚠ The one thing about a move that breaks silently. A header is stored as a
    path relative to ROOT_DIR (`jungle/the-zoo/header.seq`, #120), not relative to
    the directory that owns it — so once the folder moves, the stored path points
    at nothing and the header simply stops appearing, in every binding, with no
    error anywhere.

    Only headers that live INSIDE the moved folder are rewritten. A directory
    whose header points somewhere else entirely — the root's own `header.seq`, say
    — still resolves, because that file did not move.
    """
    header = getattr(page, 'header', None)
    if not header:
        return
    absolute = os.path.normpath(os.path.join(root_dir, header))
    old_root = os.path.normpath(old_root)
    if not (absolute == old_root or absolute.startswith(old_root + os.sep)):
        return                      # outside the moved folder; still valid
    moved = os.path.join(new_root, os.path.relpath(absolute, old_root))
    page.header = os.path.relpath(moved, root_dir).replace(os.sep, '/')


def relocate_page(directory, page, root_dir, new_parent=None, new_title=None):
    """Move a page to another directory, rename it, or both.

    ⚠ ONE function for both, because they are one operation on disk: a page's
    folder is named from its title and sits under its parent
    (`<parent>/<slug(title)>`), so changing either moves the folder. Implementing
    them separately would mean two chances to forget the descendants, the header
    paths, or the collision check.

    Returns the set of directories whose JSON now needs writing. The caller saves
    them, because only it knows whether anything else changed too.

    Raises RelocateError with a reason the user can act on.
    """
    parent = new_parent if new_parent is not None else page.parent
    if parent is None:
        raise RelocateError('the root directory cannot be moved or renamed')

    title = (new_title if new_title is not None else page.title).strip()[:MAX_TITLE]
    if not title:
        raise RelocateError('a title cannot be empty')
    slug = CompunetDirectory._make_slug(title)

    old_parent = page.parent
    moving = parent is not old_parent

    # ⚠ A directory cannot be moved inside itself: the folder would be moved into
    # its own child, and the subtree would be unreachable from the root while
    # still existing on disk.
    if moving and parent in _subtree(page):
        raise RelocateError('a directory cannot be moved into itself')

    # Two entries in one directory cannot share a folder, and the folder name
    # comes from the title — so this is a real constraint, not a nicety.
    for sibling in parent.children:
        if sibling is page:
            continue
        if CompunetDirectory._make_slug(sibling.title) == slug:
            raise RelocateError(
                '"%s" already holds an entry that would use the same folder '
                'as "%s"' % (parent.title, title))

    if moving and len(parent.children) >= 11:
        raise RelocateError('"%s" is full (11 entries maximum)' % parent.title)

    old_dir = getattr(page, '_dir_path', '')
    new_dir = os.path.join(getattr(parent, '_dir_path', ''), slug)

    if os.path.normpath(old_dir) != os.path.normpath(new_dir):
        if os.path.exists(new_dir):
            raise RelocateError(
                'there is already something at %s'
                % os.path.relpath(new_dir, root_dir).replace(os.sep, '/'))
        if os.path.exists(old_dir):
            os.makedirs(os.path.dirname(new_dir), exist_ok=True)
            # Carries the frames and the whole subtree beneath in one operation.
            shutil.move(old_dir, new_dir)

    # --- in-memory tree ------------------------------------------------
    if moving:
        if page in old_parent.children:
            old_parent.children.remove(page)
        parent.children.append(page)
        page.parent = parent
    page.title = title

    # Every descendant's folder is derived from the parent chain, so all of them
    # move with it — and each carries its own header path to fix.
    for node in _subtree(page):
        if node is page:
            node._dir_path = new_dir
        else:
            node._dir_path = os.path.join(
                node.parent._dir_path,
                CompunetDirectory._make_slug(node.title))
        _rehome_header(node, old_dir, new_dir, root_dir)

    # --- what needs saving ---------------------------------------------
    #
    # Both parents (their entry lists and the `directory` relpaths in them), and
    # every directory inside the moved subtree, because the paths stored in those
    # files — `header`, and each child's `directory` — are relative to ROOT_DIR
    # and have all just changed.
    affected = [parent]
    if old_parent is not parent:
        affected.append(old_parent)
    for node in _subtree(page):
        if node.children or os.path.exists(
                os.path.join(getattr(node, '_dir_path', ''), 'directory.json')):
            affected.append(node)
    return affected


def reorder_child(parent, page, index):
    """Move `page` to position `index` among its siblings.

    The listing order IS the JSON order — the client renders
    `children[offset:offset+11]` — so this is the whole operation, and it touches
    no files on disk.
    """
    if page not in parent.children:
        raise RelocateError('"%s" is not in "%s"' % (page.title, parent.title))
    if index < 0 or index >= len(parent.children):
        raise RelocateError('position must be between 1 and %d'
                            % len(parent.children))
    parent.children.remove(page)
    parent.children.insert(index, page)


class CompunetSession:
    """A client session - same logic for WebSocket and TCP clients."""

    def __init__(self, directory):
        self.directory = directory
        self.user_id = None
        self.authenticated = False
        self.is_admin = False
        self.is_editor = False
        self.current_page = directory.root
        self.selected_entry = 0
        self.credit = 0.0
        self.purchased = set()
        self.show_page = None
        self.show_frame_index = 0
        self.dir_page_offset = 0
        self.dir_displayed = False
        self._program_download_pending = False
        self._program_download_data = None
        self.mail_mode = False
        self.mail_messages = []
        self.mail_show_msg = None
        self.mail_frame_index = 0
        self.pending_send = None
        self.last_response_type = None  # Set by response methods for WS prefix detection
        # Which surface this session belongs to, for the audit log's `via` field.
        # Set by whoever creates the session; Binding A refines 'c64' to 'amiga'
        # once identification tells it which (see audit_via).
        self.audit_via = None
        self.client_ip = None
        self._users = self._load_users()
    
    def _load_users(self):
        users_file = os.path.join(CFG_DIR, 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _hash_password(self, password):
        """Hash a password with SHA-256."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def handle_login(self, user_id, password):
        """Process login. Returns response bytes or None on failure."""
        self.last_response_type = None  # Reset per-command for WS prefix detection
        user_id = user_id.upper().strip()
        password = password.upper().strip()
        
        user = self._users.get(user_id)
        if user is None:
            log.info('Login failed (unknown user): %s', user_id)
            return self._make_error(ascii_to_petscii('INVALID ID OR PASSWORD'))
        
        # Compare hashed password
        if user['password'] != self._hash_password(password):
            log.info('Login failed (bad password): %s', user_id)
            return self._make_error(ascii_to_petscii('INVALID ID OR PASSWORD'))
        
        self.user_id = user_id
        self.authenticated = True
        self.credit = user.get('credit', 0.0)
        self.purchased = set(user.get('purchased', []))
        self.is_admin = user.get('admin', False)
        self.is_editor = user.get('editor', False)
        log.info('Login OK: %s (credit=%.2f, purchased=%s)', user_id, self.credit, self.purchased)
        audit_log('session_started', session=self)
        _user_connect(user_id)
        return self._make_welcome_frame(user)
    
    def handle_command(self, data):
        """
        Process a command packet from the client.
        data[0] = command byte
        data[1:] = parameters
        Returns response bytes to send back.
        """
        self.last_response_type = None  # Reset per-command for WS prefix detection
        self.tcp_ack_prefix = False     # TCP: prepend '@' ack before the frame (ID / mail-send)
        if len(data) == 0:
            return self._make_error(b'NO COMMAND')
        
        cmd = data[0]
        params = data[1:] if len(data) > 1 else b''
        
        log.info('Command: %s (%02X) params=%s', chr(cmd), cmd, params.hex() if params else '')
        
        if cmd == CMD_DIR:
            return self._cmd_dir(params)
        elif cmd == CMD_SHOW:
            return self._cmd_show(params)
        elif cmd == CMD_ACCNT:
            return self._cmd_accnt()
        elif cmd == CMD_BACK:
            return self._cmd_back()
        elif cmd == CMD_UCAT:
            return self._cmd_ucat()
        elif cmd == CMD_VOTE:
            return self._cmd_vote(params)
        elif cmd == CMD_MAIL:
            return self._cmd_mail()
        elif cmd == CMD_BUY:
            return self._cmd_buy(params)
        elif cmd == CMD_UPLD:
            return self._cmd_upload(params)
        elif cmd == ord('I'):
            return self._cmd_id(params)
        elif cmd == ord('E'):
            return self._cmd_leave()
        elif cmd == ord('L'):
            return self._cmd_goto(params)
        elif cmd == ord('N'):
            return self._cmd_more(params)
        else:
            return self._make_error(ascii_to_petscii('UNKNOWN COMMAND'))
    
    def _can_upload_here(self):
        """May the current user upload / create directories in the current page?

        Order matters:

        1. Admins and editors may write anywhere.
        2. The **owner** of a directory may always write to it, whatever the
           open-upload setting says — a user cannot be locked out of their own
           space by an inherited `false`.
        3. Otherwise the **nearest explicit** `open_upload` decides. The flag is
           INHERITED: setting it on The Jungle opens everything beneath it, so
           each sub-directory does not have to repeat it. A child that sets it
           explicitly to `false` **stops** that inheritance for itself and its
           own descendants — which is how a user keeps their own Jungle
           directory private while the Jungle around it stays open.
        4. With no setting anywhere on the path, uploads are refused.
        """
        if self.is_admin or self.is_editor:
            return True
        if self.current_page.author == self.user_id:
            return True
        page = self.current_page
        while page is not None:
            if hasattr(page, 'open_upload'):      # present => authoritative
                return bool(page.open_upload)
            page = page.parent
        return False

    def _pick_advert(self):
        """Pick a random advert for the current directory."""
        import random
        adverts = getattr(self.current_page, '_adverts', [])
        if not adverts:
            adverts = self.directory.global_adverts
        if adverts:
            return random.choice(adverts)
        return None

    def _cmd_goto(self, params):
        """GOTO command ('L') — navigate by page number or keyword."""
        self.last_response_type = None
        self._ucat_active = False
        if not params:
            return self._make_dir_response()

        target = params.decode('ascii', errors='replace').strip()
        log.info('GOTO: target="%s"', target)

        # Try numeric page number first
        try:
            page_num = int(target)
            return self._goto_page(page_num)
        except ValueError:
            pass

        # Built-in virtual pages
        if target.upper() == 'WHO':
            return self._make_who_frame()

        # Try keyword lookup
        for page in self.directory.pages.values():
            if page.keyword and page.keyword.upper() == target.upper():
                return self._goto_page(page.page_num)

        # Not found — reload current directory (error responses crash GOTO)
        return self._make_dir_response()

    def _goto_page(self, page_num):
        """Navigate to a page by number.

        GOTO always returns a directory response — the client parses the
        response as a 6-part directory (L_A358). Sending frame data crashes.
        For frame pages: navigate to their parent directory.
        For directories: navigate into them.
        """
        page = self.directory.pages.get(page_num)
        if page is None:
            return self._make_dir_response()

        # Dynamic directory: populate on navigation
        if getattr(page, 'dynamic', None) == 'new':
            _populate_whats_new(page, self.directory)

        self.selected_entry = 0
        self.dir_page_offset = 0
        if page.has_subdir():
            self.current_page = page
        elif page.parent:
            self.current_page = page.parent
        else:
            self.current_page = page
        return self._make_dir_response()

    def handle_goto(self, page_num):
        """Handle GOTO for WebSocket clients."""
        self.last_response_type = None
        return self._goto_page(page_num)
    
    def handle_select(self, index):
        """Handle selection of a directory entry by index."""
        if 0 <= index < len(self.current_page.children):
            self.selected_entry = index
        return b''  # No response needed for selection change
    
    def _cmd_dir(self, params):
        """'D' command — show frame or advance to next page.

        The client sends 'D' for both SHOW (first frame) and MORE (next frame).
        If already viewing frames (show_page set), advance to next frame.
        Otherwise, show the selected entry's first frame or enter sub-directory.
        Params: 2 ASCII digits = selected entry index (from $C004).
        """
        # Mail mode: show mail message or advance frame
        if self.mail_mode:
            return self._cmd_mail_show(params)

        # If already viewing a frame:
        # - No params = MORE (advance to next frame)
        # - Params present = fresh SHOW from directory (reset state)
        if hasattr(self, 'show_page') and self.show_page:
            if params:
                self.show_page = None
                self.show_frame_index = 0
            elif self.show_frame_index < len(self.show_page.frames) - 1:
                self.show_frame_index += 1
                return self._send_current_frame()
            else:
                self.show_page = None
                return self._make_dir_response()

        if params:
            try:
                self.selected_entry = int(params.decode('ascii'))
            except (ValueError, UnicodeDecodeError):
                pass
        offset = getattr(self, 'dir_page_offset', 0)
        visible_children = self.current_page.children[offset:offset+11]

        if self.selected_entry < len(visible_children):
            child = visible_children[self.selected_entry]
            if child.page_type == 'L' and child.frames:
                if getattr(self, 'is_amiga', False):
                    # Amiga: the CnetTty viewer ("Scrollback v1.0") is resident and does NOT
                    # load 6502 code. Send only the 8-byte link header its download_link
                    # validates (LONG 0x01000001 then a zero LONG) — no program payload.
                    # RESP_ACK suppresses the trailing EOS: the viewer switches to raw reads
                    # immediately after the 8 bytes, so an EOS empty-DAT would be misread as
                    # raw link-preamble bytes. The raw session (preamble handshake + ASCII
                    # chat + 0x02 teardown) runs in partyline.handle_amiga_session, entered
                    # below via _enter_partyline. serial_io_c peeks the header's first byte
                    # (0x01), sees it is not an ack char, and pushes it back for serial_read,
                    # so no '@' ack prefix is needed.
                    log.info('LINK(amiga): user=%s activating link page %d "%s"',
                             self.user_id, child.page_num, child.title)
                    self.tcp_ack_prefix = False
                    self.last_response_type = RESP_ACK
                    self._enter_partyline = True
                    self._amiga_partyline = True
                    return bytes([0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])
                # Type L: send MODEM_INIT_DOWNLOAD format for the linked program (C64)
                log.info('LINK: user=%s activating link page %d "%s" (%d bytes)',
                         self.user_id, child.page_num, child.title, len(child.frames[0]))
                prg_data = child.frames[0]
                load_addr = 0x2000
                exec_addr = 0x2000
                header = bytes([
                    0x00, 0x00,
                    exec_addr & 0xFF, (exec_addr >> 8) & 0xFF,
                    load_addr & 0xFF, (load_addr >> 8) & 0xFF,
                    0x00, 0x00,
                ])
                self.last_response_type = RESP_FRAME
                self._enter_partyline = True
                return header + prg_data
            # Dynamic pages: regenerate content on each view
            if getattr(child, 'dynamic', None) == 'who':
                _regenerate_who_frame()
                frame_path = os.path.join(WHO_PAGE_DIR, 'frame-1.seq')
                if os.path.exists(frame_path):
                    with open(frame_path, 'rb') as f:
                        child.frames = [f.read()]
            if child.frames:
                # Deduct credit for paid, unpurchased pages (allows overdraft)
                if child.price > 0 and child.page_num not in self.purchased:
                    self.credit -= child.price
                    self.purchased.add(child.page_num)
                    self._save_user()
                    log.info('BUY: user=%s page=%d ("%s") price=%.2f credit=%.2f',
                             self.user_id, child.page_num, child.title,
                             child.price, self.credit)
                    audit_log('page_bought', session=self, page=child.page_num,
                              title=child.title, price=child.price)
                self.show_page = child
                self.show_frame_index = 0
                audit_log('page_read', session=self, page=child.page_num,
                          title=child.title, type=child.page_type)
                return self._send_current_frame()
            # No frames: SHOW is INERT (spec §7.4). It must NOT fall back to
            # entering the sub-directory — that is DIR ('P'+index, _cmd_show),
            # and collapsing them would make SHOW and DIR the same command on
            # exactly the entries where they are meant to differ (§4.7). A 'D'
            # entry normally has no frames, so this is its ordinary outcome.
            #
            # Inert means the screen does not change, so re-send the CURRENT
            # listing: same page, same highlight (_make_dir_response preserves
            # both). Answering 'D' with a directory response is an established
            # path the client already handles — MORE past the last frame does
            # exactly this a few lines above. An error frame would instead paint
            # 'NO CONTENT' over the screen, which is a visible change.
            return self._make_dir_response()
        else:
            self.dir_page_offset = offset + 11
            self.selected_entry = 0
            return self._make_dir_response()
    
    def _cmd_show(self, params):
        """SHOW/DIR command ('P') - show current page.

        The 'P' command is sent by both DIR and SHOW duckshoot commands.
        Also sent by FINISH to return to directory from frame viewing.
        If we're already viewing the directory and the selected entry has a
        sub-directory, enter it. Otherwise show the current page directory.
        """
        # FINISH clears frame viewing state
        self.show_page = None
        self.show_frame_index = 0
        self._program_download_pending = False
        self._program_download_data = None

        # Complete pending upload if client returned to directory
        if self.pending_send is not None and self.pending_send.get('mode') == 'upload':
            if self.pending_send['frames']:
                self._complete_content_upload(self.pending_send)
            self.pending_send = None
            self.dir_displayed = False
        if self.dir_displayed and params:
            try:
                selected = int(params.decode('ascii'))
            except (ValueError, UnicodeDecodeError):
                selected = None
            if selected is not None:
                offset = getattr(self, 'dir_page_offset', 0)
                visible = self.current_page.children[offset:offset+11]
                log.info('P cmd: dir_displayed=%s selected=%d visible=%d',
                         self.dir_displayed, selected, len(visible))
                if selected < len(visible):
                    child = visible[selected]
                    log.info('P cmd: child="%s" has_subdir=%s', child.title, child.has_subdir())
                    if not child.has_subdir():
                        if not self._can_upload_here():
                            log.info('P cmd: DIR creation denied for user=%s on page owned by %s',
                                     self.user_id, self.current_page.author)
                            return self._make_dir_response()
                        log.info('P cmd: creating new sub-directory under "%s" (page %d)',
                                 child.title, child.page_num)
                        # Was recorded nowhere, on any surface (#127). A page
                        # becoming a directory is how ownership of a branch is
                        # established, so it is worth knowing who did it and when.
                        audit_log('directory_created', session=self,
                                  page=child.page_num, title=child.title)
                    self.current_page = child
                    self.selected_entry = 0
                    self.dir_page_offset = 0
                    self.dir_displayed = False
                    return self._make_dir_response()
        else:
            log.info('P cmd: dir_displayed=%s params=%s (not entering subdir)',
                     self.dir_displayed, params.hex() if params else 'none')
        if getattr(self, '_ucat_active', False):
            if params:
                try:
                    selected = int(params.decode('ascii'))
                except (ValueError, UnicodeDecodeError):
                    selected = 0
                last_visible = getattr(self, '_ucat_last_visible', [])
                if selected >= len(last_visible):
                    return self._cmd_ucat_more()
            return self._render_ucat()
        return self._make_dir_response()
    
    def _cmd_more(self, params):
        """MORE/DONE command - show next frame, or complete upload."""
        if self.pending_send is not None:
            if self.pending_send['frames']:
                return self._complete_upload()
            else:
                # Cancelled send (said NO) — clear pending, no response.
                # Client sent this N via L_A784 + JMP (no L96D2 wait),
                # so any response would be stale when DONE is pressed.
                self.pending_send = None
                return b''
        if self.mail_mode:
            self.mail_mode = False
            self.mail_show_msg = None
            return self._make_dir_response()
        if hasattr(self, 'show_page') and self.show_page:
            if self.show_frame_index < len(self.show_page.frames) - 1:
                self.show_frame_index += 1
                return self._send_current_frame()
        return bytes([RESP_ACK])
    
    def _send_current_frame(self):
        """Send the current frame being viewed.

        Frame byte 0 (flags → $8035): bit 7 = more pages follow.
        Client checks BPL after rendering to decide "press any key" vs "MORE" duckshoot.

        For program pages (type 'P'), sends an 8-byte binary header instead:
          [4 padding bytes] [load_lo] [load_hi] [size_lo] [size_hi]
        The client then sends a token $40 packet to request the actual data.
        """
        self.last_response_type = RESP_FRAME
        if self.show_page and self.show_frame_index < len(self.show_page.frames):
            page_type = self.show_page.page_type
            # ⚠ 'A' (action) IS REFUSED, DELIBERATELY — and refusing is not the same as
            # not implementing it. Until this guard, an A entry fell through to the frame
            # path below and was sent as an ordinary text frame, while the CLIENT
            # dispatched on the type letter into its action handler, which expects the
            # 8-byte descriptor and then Execute()s what arrives. The two ends disagreed
            # completely: the Amiga read the frame's first bytes as the descriptor and
            # bailed on the machine check (guarded only by whatever that byte happened to
            # be), and the feature-locked C64 — which has NO machine guard — zeroes three
            # bytes at $0801 and executes the received data as 6502 code.
            #
            # An A cannot be created by upload (kind is gated to T/P/F), so this needs a
            # hand-edited directory.json, an import, or a migration. Unlikely; but the
            # failure mode is arbitrary code execution on a client that cannot be fixed,
            # and "unlikely" is not a guard. See §7.4.1 for why A is not served at all:
            # it downloads and immediately runs native, CPU-specific code.
            if page_type == 'A':
                log.warning('ACTION REFUSED: page=%d "%s" — type A is not served (§7.4.1)',
                            self.show_page.page_num, self.show_page.title)
                return self._make_error(ascii_to_petscii('NOT AVAILABLE'))
            # 'P' (program) and 'F' (IFF picture) both download through the 8-byte
            # descriptor and the $40 proceed handshake. Verified: the Amiga's F handler
            # action_download_run reuses the SAME file_download_xfer() that programs use
            # (client/amiga/src/download.c / transfer.c) — identical negotiation and
            # descriptor. They differ only in what the client does with the delivered
            # bytes: a P is saved, an F is fed to the ILBM decoder.
            if page_type in ('P', 'F'):
                # §7.4.1 guard. An F is Amiga content by definition. A client that cannot
                # render it must NOT be handed the descriptor: the feature-locked C64 has
                # no IFF decoder and would garbage-render the bitmap through its frame
                # interpreter (§7.4.1). Refuse it a message the C64 paints as a page. The
                # native Amiga (is_amiga) and Binding B — our own client, which carries the
                # renderer, audit_via 'api' — can display it and proceed.
                if page_type == 'F':
                    can_render_iff = (getattr(self, 'is_amiga', False)
                                      or getattr(self, 'audit_via', None) == 'api')
                    if not can_render_iff:
                        return self._make_error(ascii_to_petscii('PICTURE - AMIGA ONLY'))
                prg_data = self.show_page.frames[self.show_frame_index]
                # Header byte 0 = machine type (0=C64, 1=Amiga, 2=ST). A program carries its
                # stored platform (absent/unknown -> C64); an F is always Amiga. The client's
                # download dialog keys off it.
                if page_type == 'F':
                    machine = 1
                else:
                    machine = MACHINE_CODES.get(getattr(self.show_page, 'machine_type', 'c64'), 0)
                # ⚠ BYTES 4-7 ARE MACHINE-DEPENDENT, exactly as they are on upload (§8.3.2).
                # Verified against the relocated disassembly of the original Amiga client's
                # file_download_xfer (FUN_0010b174), which reads the body size from a
                # DIFFERENT field per machine:
                #     C64   (0): 16-bit WORD at header+6   (10b21c: moveq #6,d0; move.w (a0,d0.l),d1)
                #     Amiga (1): 32-bit LONG at header+4   (10b22e: move.l $45ec(a4),-$a(a5))
                #     ST    (2): 32-bit LONG at header+4   (10b268: same instruction)
                # g_dl_header is $45e8(a4), so $45ec is header+4. The split is by CPU: both
                # 68k machines take a big-endian longword, the 6502 a 16-bit word — and a C64
                # cannot use 4-7 for a size because 4-5 carry its load address.
                is_68k = machine in (1, 2)
                if is_68k:
                    # No C64-style 2-byte load address to strip: serve the stored body whole.
                    # The Amiga client LoadSeg/Execute()s it; the load field does not exist.
                    program_bytes = prg_data
                    size = len(program_bytes)
                    # Big-endian 32-bit size at 4-7. A 16-bit field cannot even express the
                    # size of a typical Amiga program, so this is the wrong field, not a
                    # rounding error: a 169,966-byte module read as 4-7 little-endian/16-bit
                    # came back as 61,079.
                    header = bytes([machine, 0x00, 0x00, 0x00]) + size.to_bytes(4, 'big')
                else:
                    load_lo = prg_data[0]
                    load_hi = prg_data[1]
                    program_bytes = prg_data[2:]
                    size = len(program_bytes)
                    header = bytes([machine, 0x00, 0x00, 0x00,
                                    load_lo, load_hi, size & 0xFF, (size >> 8) & 0xFF])
                self._program_download_pending = True
                self._program_download_data = program_bytes
                self._download_page_num = self.show_page.page_num
                self._download_title = self.show_page.title
                # 68k machines have no load address, so report the descriptor rather than a
                # field that does not exist for them (and load_lo/load_hi are unbound there).
                log.info('%s: page=%d "%s" %s size=%d bytes (%dK), header sent [%s]',
                         'PICTURE' if page_type == 'F' else 'PROGRAM',
                         self.show_page.page_num, self.show_page.title,
                         'no load addr' if is_68k else 'load=$%02X%02X' % (load_hi, load_lo),
                         size, (size + 1023) // 1024, header.hex())
                return header

            frame_data = bytearray(self.show_page.frames[self.show_frame_index])
            has_more = self.show_frame_index < len(self.show_page.frames) - 1
            if has_more:
                frame_data[0] |= 0x80  # Set bit 7 of flags byte
            # Find the source filename from root.json frames list
            frame_files = getattr(self.show_page, '_frame_files', [])
            frame_file = frame_files[self.show_frame_index] if self.show_frame_index < len(frame_files) else '?'
            log.info('FRAME: page=%d "%s" frame=%d/%d file=%s (%d bytes, more=%s)',
                     self.show_page.page_num, self.show_page.title,
                     self.show_frame_index + 1, len(self.show_page.frames),
                     frame_file, len(frame_data), has_more)
            return bytes(frame_data)
        return b'\x00'
    
    def _cmd_accnt(self):
        """ACCNT command - return credit balance as ASCII text.

        Client prints "YOU ARE [value] IN CREDIT/DEBIT" itself.
        Client reads response into $C100 until carry set, then prints
        chars from first non-space until X reaches 10 (CPX #$0A).
        Payload must be exactly 10 bytes to prevent fake terminator
        garbage from appearing (ACIA_PROCESS_CMD returns $2C after stream ends).
        """
        self.last_response_type = RESP_FRAME
        credit_str = '{:.2f}'.format(abs(self.credit))
        if self.credit < 0:
            credit_str = '-' + credit_str
        return ascii_to_petscii(credit_str.ljust(10))
    
    def _cmd_id(self, params):
        """ID command ('I') — look up user IDs.

        Params: one or more 8-byte user IDs. Response uses same validation
        stream format as MAIL: [8-byte ID] [real_name or nothing] $1E per ID.
        """
        self.last_response_type = RESP_DIR
        data = bytearray()
        users = self._load_users()
        offset = 0
        while offset + 8 <= len(params):
            user_id = params[offset:offset+8].decode('latin-1').strip().upper()
            log.info('ID: lookup user=%s', user_id)
            data.extend(ascii_to_petscii(user_id.ljust(8)[:8]))
            if user_id in users:
                real_name = users[user_id].get('name', user_id)
                data.extend(ascii_to_petscii(real_name))
            data.append(0x1E)
            offset += 8
        # TCP/Amiga: the client reads a command ack via serial_io_c before the frame, so send
        # a leading '@'. Without it, serial_io_c mis-reads the frame's first byte (an id char,
        # e.g. 'A' from ADMIN) as an ack and renders "Host error". (WS path is unaffected.)
        self.tcp_ack_prefix = True
        return bytes(data)

    def _cmd_leave(self):
        """LEAVE command ('E') — disconnect from Compunet.

        Client sends 'E', waits for a goodbye frame, displays it,
        waits for keypress, then clears screen and returns to BASIC.
        """
        self.last_response_type = RESP_FRAME
        self._leaving = True
        goodbye_path = os.path.join(CONTENT_DIR, 'templates', 'goodbye.seq')
        if os.path.exists(goodbye_path):
            with open(goodbye_path, 'rb') as f:
                return f.read()
        # Fallback if file missing
        frame = bytearray(b'\x00\x06\x0F\x8E\x0D\x0D')
        frame.extend(b'\x06\x06\x1F')
        frame.extend(b'GOODBYE')
        frame.append(0x0D)
        frame.append(0x00)
        return bytes(frame)

    def _cmd_buy(self, params):
        """LIFE/EXTEND command ('X') — extend life or activate link.

        For type 'L' pages: streams the linked program via MODEM_INIT_DOWNLOAD format.
        For other pages: extend life (original behaviour).

        Params: entry_index (2 ASCII digits) + extension (up to 4 ASCII digits).

        Every path returns b'\x40' ('@'), a *recognised* ack byte. (It used to return
        b'\x00': the C64 client keys success off the DAT token so it didn't care, but the
        Amiga client's serial_io_c only recognises '@'/'A'/'B' as acks — an unrecognised
        0x00 fell through to its frame-data pushback path and left a stale byte in the RX
        stream that corrupted the *next* command's read. '@' is consumed cleanly by both.)
        """
        self.last_response_type = RESP_ACK
        if len(params) < 2:
            return bytes([0x40])

        try:
            entry_idx = int(params[0:2].decode('ascii'))
            extend_by = int(params[2:].decode('ascii').strip()) if len(params) > 2 else 0
        except (ValueError, UnicodeDecodeError):
            return bytes([0x40])

        # Find the page from current directory (or UCAT if active)
        if getattr(self, '_ucat_active', False):
            visible_children = getattr(self, '_ucat_last_visible', [])
        else:
            offset = getattr(self, 'dir_page_offset', 0)
            visible_children = self.current_page.children[offset:offset+11]
        if entry_idx >= len(visible_children):
            return bytes([0x40])

        child = visible_children[entry_idx]

        # Type 'L' — link: handled by _cmd_dir, BUY just returns ACK
        if child.page_type == 'L':
            return bytes([0x40])

        # Positive extend: any user can extend anyone's content
        # Negative extend: only owner, admin, or editor
        if extend_by < 0:
            if child.author != self.user_id and not self.is_admin and not self.is_editor:
                log.info('EXTEND DENIED: user=%s cannot reduce page %d (author=%s)',
                         self.user_id, child.page_num, child.author)
                return bytes([0x40])

        num_frames = len(child.frames) if child.frames else 1

        if extend_by > 0:
            # Positive extend: deduct from free storage first, overflow to credit
            storage_cost = num_frames * extend_by
            user = self._users.get(self.user_id, {})
            self._check_storage_reset(user)
            free_remaining = self._get_free_storage_remaining(user)

            if storage_cost <= free_remaining:
                user['free_storage_used'] = user.get('free_storage_used', 0) + storage_cost
                log.info('EXTEND: cost=%d units from free storage (remaining=%d)',
                         storage_cost, 2000 - user['free_storage_used'])
            else:
                from_free = free_remaining
                from_credit = storage_cost - from_free
                user['free_storage_used'] = user.get('free_storage_used', 0) + from_free
                self.credit -= from_credit
                log.info('EXTEND: cost=%d units (%d from free, %.2f from credit)',
                         storage_cost, from_free, from_credit)

            child.life += extend_by
            self._save_user()
            # `life` lives in the child's node inside this directory's JSON.
            self._save_directory_containing(self.current_page)
            log.info('EXTEND: user=%s page=%d ("%s") extend_by=%d new_life=%d',
                     self.user_id, child.page_num, child.title, extend_by, child.life)
            audit_log('page_life_extended', session=self, page=child.page_num,
                      title=child.title, extend_by=extend_by, new_life=child.life)

        elif extend_by < 0:
            # Negative extend: reduce life, refund storage
            actual_reduction = min(abs(extend_by), child.life)
            refund = num_frames * actual_reduction
            user = self._users.get(self.user_id, {})
            self._check_storage_reset(user)
            user['free_storage_used'] = max(0, user.get('free_storage_used', 0) - refund)
            child.life -= actual_reduction
            log.info('REDUCE: user=%s page=%d ("%s") reduced_by=%d new_life=%d refund=%d',
                     self.user_id, child.page_num, child.title, actual_reduction, child.life, refund)

            # If life reaches 0, archive and delete the page
            if child.life <= 0:
                self._archive_page(child, reason='expired')
                parent = self.current_page
                if child in parent.children:
                    parent.children.remove(child)
                if child.page_num in self.directory.pages:
                    del self.directory.pages[child.page_num]
                log.info('DELETE: page %d ("%s") removed (life=0, archived)', child.page_num, child.title)

            self._save_user()
            # Reduced life, or the entry's removal — both are edits to this
            # directory's own JSON.
            self._save_directory_containing(self.current_page)

        self.dir_displayed = False
        return bytes([0x40])

    def _get_quarter_start(self):
        """Return the start date of the current calendar quarter."""
        now = datetime.date.today()
        if now.month <= 3:
            return datetime.date(now.year, 1, 1)
        elif now.month <= 6:
            return datetime.date(now.year, 4, 1)
        elif now.month <= 9:
            return datetime.date(now.year, 7, 1)
        else:
            return datetime.date(now.year, 10, 1)

    def _check_storage_reset(self, user):
        """Reset free storage if we've entered a new quarter."""
        current_qs = self._get_quarter_start().isoformat()
        if user.get('storage_quarter_start', '') != current_qs:
            user['free_storage_used'] = 0
            user['storage_quarter_start'] = current_qs

    def _get_free_storage_remaining(self, user):
        """Return remaining free storage units for this quarter."""
        self._check_storage_reset(user)
        return max(0, 2000 - user.get('free_storage_used', 0))

    def _save_user(self):
        """Persist user state to users.json."""
        users_file = os.path.join(CFG_DIR, 'users.json')
        users = self._load_users()
        if self.user_id in users:
            users[self.user_id]['credit'] = self.credit
            users[self.user_id]['purchased'] = sorted(self.purchased)
            mem_user = self._users.get(self.user_id, {})
            if mem_user.get('last_login_date'):
                users[self.user_id]['last_login_date'] = mem_user['last_login_date']
                users[self.user_id]['last_login_time'] = mem_user.get('last_login_time', '')
            if 'free_storage_used' in mem_user:
                users[self.user_id]['free_storage_used'] = mem_user['free_storage_used']
                users[self.user_id]['storage_quarter_start'] = mem_user.get('storage_quarter_start', '')
            with open(users_file, 'w') as f:
                json.dump(users, f, indent=2)

    def _cmd_back(self):
        """BACK command - go to previous page, or parent directory if on first page."""
        if getattr(self, '_ucat_active', False):
            if getattr(self, '_ucat_offset', 0) > 0:
                # Go back to previous UCAT page
                self._ucat_offset = max(0, self._ucat_offset - 10)
                return self._render_ucat()
            self._ucat_active = False
        if self.mail_mode:
            if self.mail_show_msg is not None:
                self.mail_show_msg = None
                return self._make_mail_response()
            if getattr(self, 'mail_page_offset', 0) > 0:
                self.mail_page_offset = max(0, self.mail_page_offset - 11)
                return self._make_mail_response()
            self.mail_mode = False
            return self._make_dir_response()
        if self.dir_page_offset > 0:
            # Go back to previous page of same directory
            self.dir_page_offset = max(0, self.dir_page_offset - 11)
            self.selected_entry = 0
        elif self.current_page.parent:
            # On first page - go up to parent directory
            self.current_page = self.current_page.parent
            self.selected_entry = 0
            self.dir_page_offset = 0
        return self._make_dir_response()
    
    def _cmd_vote(self, params):
        """VOTE command. Params: 2-digit entry index + 1-digit score (1-9).

        Returns b'\x40' ('@' = clean accept). RESP_ACK (0x41 = 'A') must NOT be used as
        the payload here: in the client protocol '@'/'A'/'B' are accept/host-error/fatal-
        error, so the Amiga client's serial_io_c renders an 'A' reply as a "Host error"
        requester (verified against the original at 0x119870: `pea $41` ->
        show_status_message(0x41) -> "Host error"). The C64 client keys off the DAT token
        and ignores the payload, so '@' is correct for both.
        """
        if len(params) < 3:
            log.warning('VOTE: params too short: %s', params.hex())
            self.last_response_type = RESP_ACK
            return bytes([0x40])

        try:
            index = int(params[:2].decode('ascii'))
            score = int(params[2:3].decode('ascii'))
        except (ValueError, UnicodeDecodeError):
            log.warning('VOTE: invalid params: %s', params.hex())
            self.last_response_type = RESP_ACK
            return bytes([0x40])

        offset = getattr(self, 'dir_page_offset', 0)
        visible_children = self.current_page.children[offset:offset+11]

        if index >= len(visible_children) or score < 1 or score > 9:
            log.warning('VOTE: out of range index=%d score=%d', index, score)
            self.last_response_type = RESP_ACK
            return bytes([0x40])

        page = visible_children[index]
        page_key = str(page.page_num)

        votes = self._load_votes()
        if page_key not in votes:
            votes[page_key] = {}
        votes[page_key][self.user_id] = score
        self._save_votes(votes)
        audit_log('page_voted', session=self, page=page.page_num,
                  title=page.title, score=score)

        avg = round(sum(votes[page_key].values()) / len(votes[page_key]))
        page.vote = avg
        # ⚠ No directory save here, deliberately. Votes live in votes.json
        # (_save_votes, above) and `page.vote` is repopulated from there by
        # _load_votes on every load; the directory serializer has never written a
        # `vote` key at all. So the whole-tree write that used to be here
        # persisted NOTHING, and its only effect was to republish this session's
        # stale copy of the content over everyone else's committed changes — on a
        # command ordinary users issue constantly.

        log.info('VOTE: user=%s page=%d (%s) score=%d avg=%d',
                 self.user_id, page.page_num, page.title, score, avg)

        self.last_response_type = RESP_ACK
        return bytes([0x40])

    def _get_vote_count(self, page_num):
        votes = self._load_votes()
        page_votes = votes.get(str(page_num), {})
        return len(page_votes)

    def _load_votes(self):
        votes_path = VOTES_PATH
        if os.path.exists(votes_path):
            with open(votes_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_votes(self, votes):
        votes_path = VOTES_PATH
        with open(votes_path, 'w') as f:
            json.dump(votes, f, indent=2)
    
    def _cmd_mail(self):
        """MAIL command - show mailbox or advance mail page.

        When already in mail mode, 'M' acts as MORE (next page).
        """
        if self.mail_mode:
            self.mail_page_offset = getattr(self, 'mail_page_offset', 0) + 11
            if self.mail_page_offset >= len(self.mail_messages):
                self.mail_page_offset = 0
            return self._make_mail_response()
        self.mail_mode = True
        self.mail_messages = self._load_mail()
        self.mail_frame_index = 0
        self.mail_show_msg = None
        self.mail_page_offset = 0
        return self._make_mail_response()

    def _load_mail(self):
        """Load mail metadata for the current user, excluding expired messages."""
        mail_file = os.path.join(MAIL_DIR, self.user_id + '.json')
        if os.path.exists(mail_file):
            with open(mail_file, 'r') as f:
                data = json.load(f)
            return self._filter_expired_mail(data.get('messages', []))
        return []

    def _filter_expired_mail(self, messages):
        """Exclude messages read more than 2 days ago."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=2)
        result = []
        for msg in messages:
            if msg.get('read') and msg.get('read_date'):
                try:
                    read_dt = datetime.datetime.strptime(msg['read_date'], '%Y-%m-%d')
                    if read_dt < cutoff:
                        continue
                except ValueError:
                    pass
            result.append(msg)
        return result

    def _make_mail_response(self):
        """Build mailbox listing as 6-part directory response."""
        self.mail_mode = True
        self.last_response_type = RESP_DIR
        self.dir_displayed = True
        data = bytearray()

        # Part 1: Courier header frame
        data.append(0x8E)
        courier_path = os.path.join(CONTENT_DIR, 'courier-header.seq')
        if os.path.exists(courier_path):
            with open(courier_path, 'rb') as f:
                data.extend(f.read())
        data.append(0x00)

        # Part 2: footer (empty)
        data.append(0x0D)
        data.append(0x0D)

        # Part 3: field definitions (stored at $D580+)
        # Format: [field_id_nibble] '=' [value] $0D ... $00
        # Field 3 ($D588) = DATE, Field 4 ($D5A8) = TIME
        now = datetime.datetime.now()
        date_str = now.strftime('%d-%m-%y')
        time_str = now.strftime('%H:%M')
        data.append(0x03)  # field ID 3 = DATE
        data.append(0x3D)  # '='
        data.extend(ascii_to_petscii(date_str))
        data.append(0x0D)
        data.append(0x04)  # field ID 4 = TIME
        data.append(0x3D)  # '='
        data.extend(ascii_to_petscii(time_str))
        data.append(0x0D)
        data.append(0x00)

        # Part 4: breadcrumb + metadata
        # Stored at $D400. SEND screen reads from $D40B (offset 11).
        # Prints CR-separated lines at col 10 for FROM/DATE/TIME fields.
        # First 11 bytes must be padding to align offset correctly.
        now = datetime.datetime.now()
        users = self._load_users()
        real_name = users.get(self.user_id, {}).get('name', self.user_id)
        data.extend(ascii_to_petscii(' USER ID : ' + self.user_id))
        data.append(0x0D)
        data.extend(ascii_to_petscii(real_name))
        if not getattr(self, 'is_amiga', False):
            # C64 ONLY: its SEND screen reads FROM/DATE/TIME from here ($D40B) to stamp
            # outgoing mail. The Amiga has no date/time handling — it stamps server-side and
            # never reads these — yet its info-line renderer (FUN_00109a5e) draws these extra
            # CR-separated lines down into the body rows (rows 10-11), overwriting the
            # message-number column (e.g. 100041 -> 1000412). Omit them for the Amiga so the
            # breadcrumb stays within its cleared region (rows 7-8).
            data.append(0x0D)
            data.append(0x0D)
            data.extend(ascii_to_petscii(now.strftime('%d-%m-%y')))
            data.append(0x0D)
            data.extend(ascii_to_petscii(now.strftime('%H:%M')))
        data.append(0x00)

        # Part 5: column headers
        data.extend(ascii_to_petscii(' SENDER'))
        data.append(0x2C)
        data.extend(ascii_to_petscii(' DATE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii(' STATUS'))
        data.append(0x0D)
        data.append(0x00)

        # Part 6: mail entries (max 11 per page)
        offset = getattr(self, 'mail_page_offset', 0)
        visible = self.mail_messages[offset:offset+11]

        if not self.mail_messages:
            # Full-width first field (27 chars) so the Amiga's fixed-width body-row parser
            # (col A 6 + col B 16 + sep 1 = 23, then col C scans for a comma) finds a comma
            # instead of letting col B swallow the commas + CR — a short field makes col C run
            # past end-of-stream and spin forever (no EOF guard, faithful to FUN_00109a5e) →
            # 'Waiting' hang. Mirrors the DIR empty-placeholder fix (77c84a6); the mail
            # placeholder was missed.
            first_field = '0'.rjust(6) + ' ' + '(NO MAIL)'.ljust(17) + '   '   # 27 chars
            data.extend(ascii_to_petscii(first_field))
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x0D)
        else:
            for i, msg in enumerate(visible):
                subject = msg.get('subject', '')[:18]
                num_frames = len(msg.get('frames', []))
                type_str = ('T' + str(num_frames)).ljust(3)
                msg_id = msg.get('id', str(offset + i + 1))
                page_str = str(msg_id).rjust(6) + ' '
                title_field = subject[:16].ljust(17) + type_str
                data.extend(ascii_to_petscii(page_str + title_field))
                data.append(0x2C)
                # Column 1: SENDER
                sender = msg.get('from', '?')[:8]
                data.extend(ascii_to_petscii(sender))
                data.append(0x2C)
                # Column 2: DATE as DD-MM-YY
                raw_date = msg.get('date', '')
                if len(raw_date) == 10:
                    date_str = raw_date[8:10] + '-' + raw_date[5:7] + '-' + raw_date[2:4]
                else:
                    date_str = raw_date[:8]
                data.extend(ascii_to_petscii(date_str))
                data.append(0x2C)
                # Column 3: STATUS
                status = 'NEW' if not msg.get('read', False) else 'READ'
                data.extend(ascii_to_petscii(status))
                data.append(0x0D)

        log.info('MAIL response: %d messages (offset=%d, visible=%d), %d bytes',
                 len(self.mail_messages), offset, len(visible), len(data))
        return bytes(data)

    def _cmd_mail_show(self, params):
        """Handle 'D' command while in mail mode — show message or advance frame."""
        # If already viewing a mail message, advance to next frame
        if self.mail_show_msg is not None:
            msg = self.mail_messages[self.mail_show_msg]
            frames = msg.get('frames', [])
            if self.mail_frame_index < len(frames) - 1:
                self.mail_frame_index += 1
                return self._send_mail_frame()
            else:
                # Last frame — return to mail listing
                self.mail_show_msg = None
                if not params:
                    return self._make_mail_response()

        # Select message by index
        if params:
            try:
                selected = int(params.decode('ascii'))
            except (ValueError, UnicodeDecodeError):
                selected = 0
        else:
            selected = 0

        offset = getattr(self, 'mail_page_offset', 0)
        visible = self.mail_messages[offset:offset+11]

        if selected < len(visible):
            actual_index = offset + selected
            self.mail_show_msg = actual_index
            self.mail_frame_index = 0
            # Mark as read with timestamp for auto-expiry
            if not self.mail_messages[actual_index].get('read'):
                audit_log('mail_opened', session=self,
                          from_user=self.mail_messages[actual_index].get('from', ''),
                          subject=self.mail_messages[actual_index].get('subject', ''))
            self.mail_messages[actual_index]['read'] = True
            if not self.mail_messages[actual_index].get('read_date'):
                self.mail_messages[actual_index]['read_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
            self._save_mail()
            return self._send_mail_frame()
        elif not self.mail_messages:
            # Empty mailbox: DOWNLOAD landed on the (NO MAIL) placeholder row, which the client
            # counts as a real body row. mail_download (FUN_0010e0fc) expects a FRAME back and
            # loops on the frame header's more-bit; answering with a directory makes frame_display
            # misparse it (its 0x8E first byte sets the more-bit) into an endless D/MORE loop that
            # advances the mail page each time -> Guru. Return a single frame with the more-bit
            # (byte 0, bit 7) CLEAR so the client displays it and stops. Same format as the
            # goodbye/not-found frames; C64-safe (it also expects a frame from 'D').
            self.last_response_type = RESP_FRAME
            frame = bytearray(b'\x00\x06\x0f\x8e\x0d\x0d')
            frame.extend(b'YOU HAVE NO MAIL')
            frame.append(0x0d)
            frame.append(0x00)
            return bytes(frame)
        else:
            # Non-empty mailbox: real paging past the visible entries.
            self.mail_page_offset = offset + 11
            return self._make_mail_response()

    def _send_mail_frame(self):
        """Send current mail message frame."""
        self.last_response_type = RESP_FRAME
        msg = self.mail_messages[self.mail_show_msg]
        frames = msg.get('frames', [])
        frame_file = frames[self.mail_frame_index]
        mail_dir = os.path.join(MAIL_DIR, self.user_id)
        frame_path = os.path.join(mail_dir, frame_file)

        if os.path.exists(frame_path):
            with open(frame_path, 'rb') as f:
                frame_data = bytearray(f.read())
        else:
            frame_data = bytearray(b'\x00\x06\x0f\x8e\x0d\x0d  MESSAGE NOT FOUND\x0d\x00')

        has_more = self.mail_frame_index < len(frames) - 1
        if frame_data:  # guard: pre-existing mail may hold an empty frame (see accumulator fix)
            if has_more:
                frame_data[0] |= 0x80
            else:
                frame_data[0] &= 0x7F
        log.info('MAIL FRAME: msg=%d frame=%d/%d file=%s (%d bytes, more=%s)',
                 self.mail_show_msg, self.mail_frame_index + 1, len(frames),
                 frame_file, len(frame_data), has_more)
        return bytes(frame_data)

    def _save_mail(self):
        """Persist mail metadata (read status etc)."""
        os.makedirs(MAIL_DIR, exist_ok=True)
        mail_file = os.path.join(MAIL_DIR, self.user_id + '.json')
        data = {'messages': self.mail_messages}
        with open(mail_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _next_message_number(self):
        """Get and increment the global message sequence number."""
        # MAIL_DIR is runtime data and may not exist on a fresh install; this runs
        # before _complete_mail_send's per-recipient makedirs, so create it here.
        os.makedirs(MAIL_DIR, exist_ok=True)
        seq_file = os.path.join(MAIL_DIR, 'sequence.json')
        if os.path.exists(seq_file):
            with open(seq_file, 'r') as f:
                seq_data = json.load(f)
            seq_num = seq_data.get('next', 100000)
        else:
            seq_num = 100000
        with open(seq_file, 'w') as f:
            json.dump({'next': seq_num + 1}, f)
        return seq_num

    def _generate_mail_header(self, msg_seq, sender_id, subject, dest_ids, timestamp, users):
        """Generate COURIER header frame (page 0) from template.

        Loads courier-envelope.seq and replaces placeholders with actual values.
        """
        MONTHS = ['JAN','FEB','MAR','APR','MAY','JUN',
                  'JUL','AUG','SEP','OCT','NOV','DEC']
        date_str = f'{timestamp.day:02d}-{MONTHS[timestamp.month-1]}-{timestamp.strftime("%y")}'
        time_str = timestamp.strftime('%H:%M')
        sender_name = users.get(sender_id, {}).get('name', sender_id).upper()

        # Build destination slot lines
        dest_lines = []
        for i in range(5):
            if i < len(dest_ids):
                did = dest_ids[i]
                dest_name = users.get(did, {}).get('name', '').upper()
                # cyan ID + red colon + cyan name
                line = b'\x20\x20\x1F' + did.ljust(8)[:8].encode('ascii') + b'\x1C: \x1F' + dest_name.encode('ascii')
            else:
                # empty slot: spaces + red colon
                line = b'\x20\x20\x06\x08\x1C:'
            dest_lines.append(line)

        # Load template
        template_path = os.path.join(CONTENT_DIR, 'templates', 'courier-envelope.seq')
        with open(template_path, 'rb') as f:
            frame = f.read()

        # Replace placeholders
        frame = frame.replace(b'{MSG_NO}', str(msg_seq).encode('ascii'))
        frame = frame.replace(b'{SENDER_ID}', sender_id.encode('ascii'))
        frame = frame.replace(b'{SENDER_NAME}', sender_name.encode('ascii'))
        frame = frame.replace(b'{DATE}', date_str.encode('ascii'))
        frame = frame.replace(b'{TIME}', time_str.encode('ascii'))
        frame = frame.replace(b'{SUBJECT}', subject[:24].encode('ascii'))
        for i in range(5):
            frame = frame.replace(f'{{DEST_{i}}}'.encode('ascii'), dest_lines[i])

        return frame

    def _cmd_upload(self, params):
        """Handle 'U' command — mail SEND or content upload.

        Mail SEND params: subject(16) + type(1) + dest_ids(8 each)
        Content UPLOAD params: title(16) + type(1) + price(8) + lifetime(1)
        Distinguish by: price field contains '.' → upload; otherwise → mail.
        """
        # Second 'U' (no params) = ready to send a frame, just ACK it.
        # Reply '@' (0x40 = clean accept), NOT RESP_ACK (0x41='A'): the Amiga's put_frame_xfer
        # reads this via serial_io_c, where 'A' means host-error (renders a requester and
        # counts as failure). C64 keys off the DAT token so the payload byte is irrelevant.
        if len(params) == 0:
            log.info('UPLOAD: frame-ready signal, sending ACK')
            self.last_response_type = RESP_ACK
            return bytes([0x40])

        if len(params) < 17:
            return self._make_error(ascii_to_petscii('INVALID SEND'))

        subject = params[0:16].decode('latin-1').strip()
        msg_type = chr(params[16])
        rest = params[17:]

        # Detect UPLOAD vs MAIL: price field contains '.'
        if b'.' in rest[:8]:
            return self._cmd_upload_content(subject, msg_type, rest)
        else:
            return self._cmd_mail_send(subject, msg_type, rest)

    def _cmd_mail_send(self, subject, msg_type, rest):
        """Handle MAIL SEND — validate destinations and prepare for frame upload."""
        # Parse destination IDs (8 bytes each)
        dest_ids = []
        offset = 0
        while offset + 8 <= len(rest):
            did = rest[offset:offset+8].decode('latin-1').strip()
            if did:
                dest_ids.append(did.upper())
            offset += 8

        log.info('MAIL SEND: from=%s to=%s subject="%s" type=%s',
                 self.user_id, dest_ids, subject, msg_type)
        # Audited by _complete_mail_send, which every binding reaches.

        self.pending_send = {
            'mode': 'mail',
            'to': dest_ids,
            'subject': subject,
            'type': msg_type,
            'frames': [],
        }

        # Validation response: [8-byte ID] [real_name or nothing] $1E per dest
        self.last_response_type = RESP_DIR
        data = bytearray()
        users = self._load_users()
        for did in dest_ids:
            data.extend(ascii_to_petscii(did.ljust(8)[:8]))
            if did in users:
                real_name = users[did].get('name', did)
                data.extend(ascii_to_petscii(real_name))
            data.append(0x1E)
        log.info('MAIL: validation response %d bytes: %s', len(data), data.hex())
        # TCP/Amiga: leading '@' ack so serial_io_c doesn't misread the first recipient-id
        # byte as an ack (see _cmd_id). WS path is unaffected.
        self.tcp_ack_prefix = True
        return bytes(data)

    def _cmd_upload_content(self, title, page_type, rest):
        """Handle content UPLOAD — store metadata for frame upload."""
        price_str = rest[0:6].decode('latin-1').strip()
        lifetime_str = rest[6:9].decode('latin-1').strip() if len(rest) > 6 else '0'

        # Parse price: round to 2 decimal places (only valid precision)
        try:
            price = round(float(price_str), 2)
        except ValueError:
            price = 0.0

        try:
            lifetime = int(lifetime_str)
        except ValueError:
            lifetime = 0

        log.info('CONTENT UPLOAD: user=%s title="%s" type=%s price=%.2f life=%d',
                 self.user_id, title, page_type, price, lifetime)

        self.pending_send = {
            'mode': 'upload',
            'title': title,
            'type': page_type,
            'price': price,
            'lifetime': lifetime,
            'frames': [],
        }

        # Validation response — echo back the price field + $1E
        # No EOS — client proceeds immediately to send frame data after L96D2
        self.last_response_type = RESP_ACK
        data = bytearray()
        data.extend(ascii_to_petscii(price_str.ljust(6)[:6]))
        data.append(0x1E)
        log.info('UPLOAD: validation response %d bytes: %s', len(data), data.hex())
        return bytes(data)

    def _recv_upload_frame(self, params):
        """Receive frame data from client during SEND/upload.

        The 'D' command in upload context contains frame data as payload.
        Store it and ACK for the next frame (or completion).
        """
        if params:
            self.pending_send['frames'].append(bytes(params))
            log.info('UPLOAD: received frame %d (%d bytes)',
                     len(self.pending_send['frames']), len(params))
        self.last_response_type = RESP_ACK
        return bytes([RESP_ACK])

    def _complete_upload(self):
        """Complete a SEND/upload — deliver mail or add page to directory."""
        send = self.pending_send
        self.pending_send = None

        if not send or not send.get('frames'):
            log.info('UPLOAD: completed (no frames)')
            if send and send.get('mode') == 'mail':
                return self._make_mail_response()
            return b''

        if send.get('mode') == 'upload':
            return self._complete_content_upload(send)
        else:
            return self._complete_mail_send(send)

    def take_program_download(self):
        """Hand over the staged program bytes, clear the pending state, and audit it.

        ⚠ The one place a download is recorded, for every surface. The three
        bindings deliver the bytes very differently — Binding A streams DAT
        packets, the terminal runs XMODEM, Binding B returns base64 over the
        WebSocket — so there was no shared function and each did its own
        bookkeeping. Two audited it and Binding B did not (#127); this gives them
        the one thing they genuinely share, which is the moment the user accepts.

        Returns the bytes, or None if nothing was pending. A DECLINED download is
        deliberately not recorded: the user obtained nothing.
        """
        data = self._program_download_data
        if data is None:
            return None
        page_num = getattr(self, '_download_page_num', 0)
        title = getattr(self, '_download_title', '')
        self._program_download_pending = False
        self._program_download_data = None
        # ⚠ The download is OVER, so the session must stop showing that page.
        # Leaving `show_page` set left the binary page current after its bytes had
        # been handed over, and the next MORE re-entered _send_current_frame and
        # re-sent the 8-byte DESCRIPTOR — the user finished a download and the
        # client was immediately offered the same one again. The abort path (0x41)
        # already cleared it; success did not, so the two ends of the same
        # transfer disagreed about what the session was doing.
        self.show_page = None
        self.show_frame_index = 0
        audit_log('page_downloaded', session=self, page=page_num, title=title,
                  bytes=len(data))
        return data

    def _complete_mail_send(self, send):
        """Deliver mail to recipients."""
        now = datetime.datetime.now()
        mail_dir = MAIL_DIR
        users = self._load_users()
        msg_seq = self._next_message_number()

        for dest_id in send['to']:
            if dest_id not in users:
                continue
            dest_dir = os.path.join(mail_dir, dest_id)
            os.makedirs(dest_dir, exist_ok=True)

            dest_mail_file = os.path.join(mail_dir, dest_id + '.json')
            if os.path.exists(dest_mail_file):
                with open(dest_mail_file, 'r') as f:
                    dest_inbox = json.load(f)
            else:
                dest_inbox = {'messages': []}

            msg_id = str(msg_seq)

            header_frame = self._generate_mail_header(
                msg_seq, self.user_id, send['subject'],
                send['to'], now, users)
            header_file = f'{msg_id}-0.seq'
            header_path = os.path.join(dest_dir, header_file)
            with open(header_path, 'wb') as f:
                f.write(header_frame)

            frame_files = [header_file]
            for i, frame_data in enumerate(send['frames']):
                frame_file = f'{msg_id}-{i+1}.seq'
                frame_path = os.path.join(dest_dir, frame_file)
                with open(frame_path, 'wb') as f:
                    f.write(frame_data)
                frame_files.append(frame_file)

            today = now.date().isoformat()
            dest_inbox['messages'].append({
                'id': msg_id,
                'from': self.user_id,
                'subject': send['subject'],
                'date': today,
                'read': False,
                'frames': frame_files,
            })
            with open(dest_mail_file, 'w') as f:
                json.dump(dest_inbox, f, indent=2)

        # ⚠ HERE, not in the callers. This function is what actually delivers the
        # mail, and every surface reaches it: Binding A and the terminal through
        # their own command handlers, Binding B by calling it directly. Auditing
        # at the call site meant the first two were recorded and the third was
        # not — the same mail, invisible, depending on which client sent it
        # (#127). `_complete_content_upload` always had it right, which is why
        # uploads never had this gap.
        audit_log('mail_sent', session=self, to=send['to'],
                  subject=send['subject'], recipients=len(send['to']))

        log.info('MAIL: delivered from %s to %s subject="%s" frames=%d',
                 self.user_id, send['to'], send['subject'], len(send['frames']))

        for dest_id in send['to']:
            if dest_id in users:
                asyncio.get_event_loop().create_task(
                    _send_mail_notification(dest_id, self.user_id, send['subject'], users))

        return b''

    def _archive_page(self, page, reason='replaced'):
        """Archive a page before removal. See module-level `archive_page`, which
        is shared with the terminal and — unlike the two copies this replaces —
        descends into a directory's contents instead of leaving them orphaned."""
        archive_page(page, DATA_DIR, reason=reason)

    def _complete_content_upload(self, send):
        """Add or replace uploaded page in the current directory."""
        if not self._can_upload_here():
            log.info('UPLOAD DISCARDED: user=%s cannot upload to page owned by %s',
                     self.user_id, self.current_page.author)
            return

        # Check for existing page with same title
        page_slug = CompunetDirectory._make_slug(send['title'])
        existing = None
        for child in self.current_page.children:
            if CompunetDirectory._make_slug(child.title) == page_slug:
                existing = child
                break

        if existing:
            # Check ownership — only author, admin, or editor can replace
            if (existing.author != self.user_id and
                    not self.is_admin and not self.is_editor):
                log.info('UPLOAD REJECTED: user=%s cannot replace "%s" owned by %s',
                         self.user_id, existing.title, existing.author)
                return
            # Archive the old version
            self._archive_page(existing, reason='replaced')
        elif len(self.current_page.children) >= 11:
            log.info('UPLOAD DISCARDED: user=%s directory full (%d entries)',
                     self.user_id, len(self.current_page.children))
            return

        # Determine page number (reuse existing or allocate new)
        if existing:
            page_num = existing.page_num
        else:
            # Unique against the whole tree, not just the lookup table.
            page_num = self.directory.next_page_num()

        # Create page folder
        parent_dir = getattr(self.current_page, '_dir_path', ROOT_DIR)
        page_dir = os.path.join(parent_dir, page_slug)
        os.makedirs(page_dir, exist_ok=True)

        # Save frames into page folder. Binary uploads — a program ('P') or an IFF
        # picture ('F') — arrive as [8-byte header][body]; the header's byte 0 is the
        # machine type (0=C64, 1=Amiga, 2=ST). An F is stored exactly like an Amiga
        # program (whole body, no load address) but with a .iff name and page_type 'F',
        # because on the wire an F download IS an Amiga program download (§7.4.1) — the
        # type letter is all that tells the client to decode rather than save.
        frame_files = []
        is_picture = send['type'] == 'F'
        is_blob = send['type'] in ('P', 'F')
        prog_machine = send['frames'][0][0] if (is_blob and send['frames']) else None

        # ⚠ VALIDATED HERE, IN THE SHARED FUNCTION, so BOTH bindings get it. Binding B
        # checks before calling; Binding A had no check at all, so an Amiga could publish
        # any file as an `F` and it would be stored as a picture that nothing can decode —
        # discovered as a blank screen much later, by someone else. The body follows the
        # 8-byte header, and an ILBM begins "FORM"????"ILBM". Reject rather than sanitise:
        # there is no sensible repair for "this is not the format you said it was".
        if is_picture:
            body = bytes(send['frames'][0][8:]) if send['frames'] else b''
            if body[0:4] != b'FORM' or body[8:12] != b'ILBM':
                log.warning('UPLOAD DISCARDED: user=%s "%s" declared type F but is not '
                            'an IFF ILBM (starts %r)', self.user_id, send['title'], body[:12])
                return
        # ⚠ The split is by CPU, not by brand — 68k machines have no load address,
        # the 6502 does. Upload used to test `== 1` and so folded ST into the C64
        # branch, which would strip two bytes off the front of an ST file and store
        # it as `c64`; the DOWNLOAD side already handled all three correctly
        # (is_68k, verified against the original client's disassembly, #123). This
        # makes the two ends agree. Nothing sends a 2 today, so no behaviour changes
        # — it removes a trap rather than adding a feature.
        prog_is_68k = prog_machine in (1, 2)
        for i, frame_data in enumerate(send['frames']):
            if is_blob:
                if prog_is_68k:
                    # 68k: no C64-style load address to strip. Store the body whole.
                    frame_data = bytes(frame_data[8:])
                else:
                    # C64: prepend the 2-byte load address (header bytes 4-5) to the body.
                    frame_data = bytes(frame_data[4:6]) + bytes(frame_data[8:])
                ext = 'iff' if is_picture else 'prg'
                frame_file = f'{page_slug}.{ext}' if i == 0 else f'{page_slug}-{i+1}.{ext}'
            else:
                frame_file = f'frame-{i+1}.seq'
            frame_path = os.path.join(page_dir, frame_file)
            with open(frame_path, 'wb') as f:
                f.write(frame_data)
            frame_files.append(frame_file)

        if is_blob and send['frames']:
            hdr = send['frames'][0]
            if prog_is_68k:
                size = (len(hdr) - 8 + 1023) // 1024   # raw body length (KB)
            else:
                size = (len(hdr) - 2 + 1023) // 1024   # C64 calc (unchanged)
        else:
            size = len(send['frames'])

        new_page = CompunetPage(
            page_num=page_num,
            title=send['title'],
            page_type=send['type'],
            size=size,
            author=self.user_id,
            price=send['price'],
            life=send['lifetime'],
        )
        new_page.uploaded = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        if is_picture:
            # An IFF picture is Amiga content by definition, whatever the header byte said.
            new_page.machine_type = 'amiga'
        elif is_blob and prog_machine is not None:
            # Program uploads carry their machine type in the header byte (authoritative).
            # Reverse of MACHINE_CODES, so the stored value round-trips whatever the
            # client declared instead of collapsing everything that is not 1 to C64.
            new_page.machine_type = MACHINE_NAMES.get(prog_machine, 'c64')
        else:
            new_page.machine_type = 'amiga' if getattr(self, 'is_amiga', False) else 'c64'
        new_page.parent = self.current_page
        new_page._frame_files = frame_files
        new_page._dir_path = page_dir
        new_page._adverts = []
        for frame_file in frame_files:
            frame_path = os.path.join(page_dir, frame_file)
            with open(frame_path, 'rb') as f:
                new_page.frames.append(f.read())

        if existing:
            # Replace in children list
            idx = self.current_page.children.index(existing)
            self.current_page.children[idx] = new_page
            self.directory.pages[page_num] = new_page
            log.info('CONTENT: replaced page %d "%s" by %s (%d frames, price=%.2f, life=%d)',
                     page_num, send['title'], self.user_id,
                     len(send['frames']), send['price'], send['lifetime'])
        else:
            self.current_page.children.append(new_page)
            self.directory.pages[page_num] = new_page
            log.info('CONTENT: uploaded page %d "%s" by %s (%d frames, price=%.2f, life=%d)',
                     page_num, send['title'], self.user_id,
                     len(send['frames']), send['price'], send['lifetime'])

        # This directory gains (or replaces) an entry — and its PARENT may need
        # the `directory` key added, because a latent directory only becomes real
        # on the first upload into it (§7.3). Two files, not the whole tree.
        self._save_directory_containing(self.current_page,
                                        getattr(self.current_page, 'parent', None))
        audit_log('page_uploaded', session=self, title=send['title'],
                  page=page_num, type=send['type'])
        return b''

    def _save_directory_containing(self, *pages):
        """Persist only the directories this command actually changed.

        ⚠ Replaces a whole-tree save, and the difference is data loss. Every
        session holds its own `CompunetDirectory`; rewriting the entire tree
        republished this session's whole view of the content and discarded
        anything another session had committed since it loaded — someone else's
        upload, gone, with nothing logged. Writing only the changed directory
        cannot do that.

        `None` entries are ignored so callers can pass `page.parent` without
        checking for the root first.
        """
        for page in pages:
            if page is None:
                continue
            save_one_directory(page, ROOT_DIR)
            log.info('DIR: saved "%s"', page.title)

    def _cmd_ucat(self):
        """UCAT command - list all pages owned by the current user.

        Always resets to page 1. Paging (MORE) is handled by _cmd_ucat_more.
        """
        self._ucat_offset = 0
        return self._render_ucat()

    def _cmd_ucat_more(self):
        """Advance UCAT to the next page of entries."""
        self._ucat_offset = getattr(self, '_ucat_offset', 0) + len(getattr(self, '_ucat_last_visible', []))
        return self._render_ucat()

    def _render_ucat(self):
        """Render UCAT page at current offset."""
        self.last_response_type = RESP_DIR
        user_pages = [p for p in self.directory.pages.values()
                      if p.author == self.user_id]

        visible = user_pages[self._ucat_offset:self._ucat_offset + 11]
        has_more = len(user_pages) > self._ucat_offset + 11
        # Reserve one slot for MORE indicator when there are more pages
        if has_more and len(visible) > 10:
            visible = visible[:10]

        data = bytearray()

        # Part 1: header frame (same as root DIR — Compunet logo)
        data.append(0x8E)
        header_file = getattr(self.directory.root, 'header', None)
        if header_file:
            header_path = os.path.join(ROOT_DIR, header_file)
            if os.path.exists(header_path):
                with open(header_path, 'rb') as f:
                    data.extend(f.read())
        data.append(0x00)

        # Part 2: footer/adverts
        advert = self._pick_advert()
        if advert:
            lines = advert.split('\n')
            line1 = lines[0][:40] if len(lines) > 0 else ''
            line2 = lines[1][:40] if len(lines) > 1 else ''
            data.extend(ascii_to_petscii(line1))
            data.append(0x0D)
            data.extend(ascii_to_petscii(line2))
        else:
            data.append(0x0D)
        data.append(0x0D)

        # Part 3: field definitions (none)
        data.append(0x00)

        # Part 4: breadcrumb
        data.extend(ascii_to_petscii('     1 *** COMPUNET ***'))
        data.append(0x0D)
        breadcrumb2 = f'  UPLOADS {self._ucat_offset+1}-{self._ucat_offset+len(visible)}'
        data.extend(ascii_to_petscii(breadcrumb2[:22].ljust(24)))
        data.append(0x00)

        # Part 5: column headers (must match DIR: PRICE, AUTHOR, VOTE/NUM, UPLDDATE, LIFE)
        data.extend(ascii_to_petscii(' PRICE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii(' AUTHOR'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('VOTE/NUM'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('UPLDDATE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii(' LIFE'))
        data.append(0x0D)
        data.append(0x00)

        # Part 6: entries (max 11 per page)
        if not visible:
            # Full-width first field (27 chars) so the Amiga body-row parser (FUN_00109a5e)
            # finds a comma for col C instead of running past end-of-stream and spinning
            # forever (no EOF guard) — matches the DIR/mail empty placeholders (77c84a6). The
            # C64 reads the title up to a comma and is length-tolerant.
            first_field = '0'.rjust(6) + ' ' + '(NO UPLOADS)'.ljust(17) + '   '   # 27 chars
            data.extend(ascii_to_petscii(first_field))
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x0D)
        else:
            for page in visible:
                page_str = str(page.page_num).rjust(6) + ' '
                type_str = page.type_string().ljust(3)
                title_field = page.title[:17].ljust(17) + type_str
                data.extend(ascii_to_petscii(page_str + title_field))
                data.append(0x2C)
                # Column 1: PRICE (must be first — client checks this for SHOW)
                if page.price > 0:
                    data.extend(ascii_to_petscii(' ' + '{:.2f}'.format(page.price).rjust(6)))
                data.append(0x2C)
                # Column 2: AUTHOR
                data.extend(ascii_to_petscii(page.author[:8]))
                data.append(0x2C)
                # Column 3: VOTE/NUM — score right-justified pos 0-3, / at pos 4, count from pos 5
                if page.vote > 0:
                    vote_count = self._get_vote_count(page.page_num)
                    vote_str = str(page.vote).rjust(4) + '/' + str(vote_count)
                    data.extend(ascii_to_petscii(vote_str[:8]))
                else:
                    data.extend(ascii_to_petscii('    -'))
                data.append(0x2C)
                # Column 4: UPLDDATE — "DD-MMM" format, hyphen-aligned
                uploaded = getattr(page, 'uploaded', None)
                if uploaded:
                    import datetime
                    try:
                        dt = datetime.datetime.fromisoformat(uploaded)
                        day = str(dt.day)
                        mon = dt.strftime('%b').upper()
                        data.extend(ascii_to_petscii(f'{day}-{mon}'.rjust(7)))
                    except (ValueError, AttributeError):
                        pass
                data.append(0x2C)
                # Column 5: LIFE (last — ROM uses $C001 for upload LIFE preview)
                if page.life > 0:
                    data.extend(ascii_to_petscii('  ' + str(page.life).rjust(3)))
                data.append(0x0D)

            # If more pages exist, add "MORE    >>>>" indicator
            if has_more:
                data.extend(ascii_to_petscii('        MORE        >>>>'))
                data.append(0x2C)
                data.append(0x2C)
                data.append(0x2C)
                data.append(0x2C)
                data.append(0x2C)
                data.append(0x0D)

        self._ucat_active = True
        self._ucat_last_visible = visible
        log.info('UCAT: user=%s pages=%d showing=%d-%d',
                 self.user_id, len(user_pages),
                 self._ucat_offset + 1, self._ucat_offset + len(visible))
        return bytes(data)
    
    def _make_dir_response(self):
        """Build directory response in the 6-part format for 'P' command."""
        # Reload content tree from disk (picks up changes without restart)
        current_page_num = self.current_page.page_num
        self.directory.reload()
        self.current_page = self.directory.pages.get(current_page_num, self.directory.root)
        # Re-populate dynamic directories after reload
        if getattr(self.current_page, 'dynamic', None) == 'new':
            _populate_whats_new(self.current_page, self.directory)

        self.dir_displayed = True
        self.last_response_type = RESP_DIR
        return self._make_page_response()
    
    def _make_page_response(self):
        """Build the 6-part page response that the terminal client expects.
        
        Format verified from terminal disassembly:
          Part 1: Frame header [PETSCII...] $00 — stored at $D000, displayed
          Part 2: Routing text [line1 $0D line2 $0D] or $00 — stored at $D300
          Part 3: Field definitions [id '=' value $0D]... $00 — stored at $D580+
          Part 4: Column header [text...] $00 — stored at $D400, displayed at row 7
          Part 5: Short entries [f1 ',' f2 $0D]... — stored at $D500 (8 bytes/field)
          Part 6: Extended entries [title ',' type ',' ... $0D]... — stored at $D600+
                  (title padded to 30, type fields 8 each, CR-terminated)
                  Stream ends when ACIA_PROCESS_CMD returns C=1 (no more data)
        """
        page = self.current_page
        log.info('DIR: source=root.json page="%s" (page_num=%d, children=%d)', 
                 page.title, page.page_num, len(page.children))
        data = bytearray()
        
        # --- Part 1: Frame header ---
        # PETSCII frame data stored at $D000, displayed via CHROUT after template.
        # Start with uppercase charset to ensure consistent rendering.
        data.append(0x8E)
        # Inherits from parent if not defined on this page.
        header_file = None
        ancestor = page
        while ancestor:
            header_file = getattr(ancestor, 'header', None)
            if header_file:
                break
            ancestor = getattr(ancestor, 'parent', None)
        if header_file:
            header_path = os.path.join(ROOT_DIR, header_file)
            log.info('DIR: header=%s (exists=%s)', header_path, os.path.exists(header_path))
            if os.path.exists(header_path):
                with open(header_path, 'rb') as f:
                    data.extend(f.read())
                data.append(0x00)  # End of Part 1
            else:
                data.append(0x00)  # File not found, empty
        else:
            log.info('DIR: no header defined for page %s', page.title)
            data.append(0x00)  # No header defined

        # --- Part 2: Footer text / adverts (2 CR-terminated lines at row 22) ---
        advert = self._pick_advert()
        if advert:
            lines = advert.split('\n')
            line1 = lines[0][:40] if len(lines) > 0 else ''
            line2 = lines[1][:40] if len(lines) > 1 else ''
            data.extend(ascii_to_petscii(line1))
            data.append(0x0D)
            data.extend(ascii_to_petscii(line2))
            data.append(0x0D)
        else:
            data.append(0x0D)
            data.append(0x0D)

        # --- Part 3: Field definitions (F-key shortcuts, stored at $D580+) ---
        # Format: [field_id] '=' [value] $0D ... $00
        # field_id 1-6 maps to F1, F3, F5, F2, F4, F6
        shortcuts = getattr(page, 'shortcuts', None)
        if shortcuts:
            fkey_map = {'F1': 1, 'F2': 4, 'F3': 2, 'F4': 5, 'F5': 3, 'F6': 6}
            for key, value in shortcuts.items():
                field_id = fkey_map.get(key)
                if field_id and value:
                    data.append(field_id)
                    data.append(0x3D)  # '='
                    data.extend(ascii_to_petscii(value[:7]))
                    data.append(0x0D)
        data.append(0x00)

        # --- Part 4: Routing/breadcrumb (stored at $D400, displayed at row 7) ---
        # Shows current directory path inside the box, above entries.
        data.extend(ascii_to_petscii('     1 *** COMPUNET ***'))
        data.append(0x0D)
        path_line2 = '   ' + str(page.page_num) + ' ' + (page.title or '')
        data.extend(ascii_to_petscii(path_line2[:22].ljust(24)))
        # Unread mail indicator at column 25 (aligned with type field)
        mail_file = os.path.join(MAIL_DIR, self.user_id + '.json')
        if os.path.exists(mail_file):
            with open(mail_file, 'r') as f:
                inbox = json.load(f)
            if any(not m.get('read', True) for m in inbox.get('messages', [])):
                data.append(0x1C)  # red
                data.extend(ascii_to_petscii('MAIL'))
        data.append(0x00)

        # --- Part 5: Column headers (at $D500, 8 bytes per field) ---
        # Single line: all column headers comma-separated, CR-terminated.
        # F7/F8 cycles through them. $C002 selects which to display.
        data.extend(ascii_to_petscii(' PRICE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii(' AUTHOR'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('VOTE/NUM'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('UPLDDATE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii(' LIFE'))
        data.append(0x0D)

        # Separator byte consumed by L_A448's JSR L96CC (value unused)
        data.append(0x00)

        # --- Part 6: ALL directory entries (at $D600+) ---
        # Format per entry: [title (up to 30 chars)] ',' [type (8 chars)] $0D
        # Title padded to 30 chars, type fields padded to 8 each by client.
        # Stream ends when $96CC returns C=1 (no more data).
        # $C009 counts entries → $C003 for rendering.
        offset = getattr(self, 'dir_page_offset', 0)
        children = page.children[offset:]
        has_more = len(children) > 11
        visible = children[:11] if has_more else children
        
        if not visible:
            # Full-width placeholder entry. The Amiga client parses body rows with
            # FIXED-WIDTH fields (col A 6 + col B 16 + 1 separator = 23 chars before it
            # scans col C for a comma); a short field lets col B swallow the commas + CR
            # so col C runs past end-of-stream and its loop (no EOF guard, faithful to
            # FUN_00109a5e) spins forever -> freeze. Mirror a normal entry's 27-char first
            # field: page_num(6)+space + title(17)+type(3), then the 5 comma columns + CR.
            # Safe for the C64 too: its parser (L_A5F3) reads the title until a comma and
            # pads to 30, so a 27-char field is length-tolerant there.
            # ⚠ The page column is BLANK, not '0'. "(EMPTY)" is a label, not an
            # entry, and a page number beside it invites the user to think there
            # is something at page 0. The type column was already blank (the
            # three spaces below) — the number was the odd one out.
            # The WIDTHS are load-bearing, so this pads rather than shortens.
            first_field = ''.rjust(6) + ' ' + '(EMPTY)'.ljust(17) + '   '   # 27 chars
            data.extend(ascii_to_petscii(first_field))
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x0D)
        else:
            for child in visible:
                # Combined field: [page_num padded to 6] + [title...type right-aligned]
                # First 6 chars = page number (5 right-aligned + space)
                # Then title left-aligned, type right-aligned (20 chars total)
                # Type suffix must start at screen column 25 (SHOW reads $19)
                page_str = str(child.page_num).rjust(6) + ' '
                type_str = child.type_string().ljust(3)
                title = child.title[:17]
                title_field = title.ljust(17) + type_str
                data.extend(ascii_to_petscii(page_str + title_field))
                data.append(0x2C)
                # Column 1: PRICE (0 if already purchased)
                effective_price = 0 if child.page_num in self.purchased else child.price
                if effective_price > 0:
                    data.extend(ascii_to_petscii(' ' + '{:.2f}'.format(effective_price).rjust(6)))
                data.append(0x2C)
                # Column 2: AUTHOR
                data.extend(ascii_to_petscii(child.author[:8]))
                data.append(0x2C)
                # Column 3: VOTE/NUM — score right-justified pos 0-3, / at pos 4, count from pos 5
                if child.vote > 0:
                    vote_count = self._get_vote_count(child.page_num)
                    vote_str = str(child.vote).rjust(4) + '/' + str(vote_count)
                    data.extend(ascii_to_petscii(vote_str[:8]))
                else:
                    data.extend(ascii_to_petscii('    -'))
                data.append(0x2C)
                # Column 4: UPLOADED — "DD-MMM" format, hyphen-aligned
                uploaded = getattr(child, 'uploaded', None)
                if uploaded:
                    import datetime
                    try:
                        dt = datetime.datetime.fromisoformat(uploaded)
                        day = str(dt.day)
                        mon = dt.strftime('%b').upper()
                        date_str = f'{day}-{mon}'.rjust(7)
                        data.extend(ascii_to_petscii(date_str))
                    except (ValueError, AttributeError):
                        pass
                data.append(0x2C)
                # Column 5: LIFE (last — ROM uses $C001 for upload LIFE preview)
                if child.life > 0:
                    data.extend(ascii_to_petscii('  ' + str(child.life).rjust(3)))
                data.append(0x0D)
        
        log.info('PAGE response: %d bytes hex=%s', len(data), data.hex())
        return bytes(data)
    
    def _make_frame_response(self, frame_data):
        """Wrap frame data in a response packet."""
        return bytes([RESP_FRAME]) + frame_data
    
    def _make_info_frame(self, message):
        """Build a simple info frame displaying a message."""
        frame = bytearray()
        frame.append(0x00)  # flags (no more pages)
        frame.append(0x02)  # border = red
        frame.append(0x00)  # bg = black
        frame.append(0x8E)  # uppercase
        frame.append(0x05)  # white text
        frame.append(0x0D)
        frame.append(0x0D)
        frame.extend(ascii_to_petscii('  ' + message))
        frame.append(0x0D)
        frame.append(0x00)  # end
        return bytes(frame)

    def _make_who_frame(self):
        """Build the WHO page — directory response with user list in header."""
        self.last_response_type = RESP_DIR
        self.dir_displayed = True
        now = datetime.datetime.now()

        data = bytearray()

        # Part 1: Header frame showing connected users
        data.append(0x8E)  # uppercase
        data.append(0x0D)
        data.append(0x0D)
        data.extend(ascii_to_petscii(
            f'  CNETTERS ON THE SYSTEM AT {now.strftime("%H:%M")}'))
        data.append(0x0D)
        data.extend(ascii_to_petscii(
            '  * INDICATES A USER ON PARTYLINE'))
        data.append(0x0D)
        data.append(0x0D)

        users = sorted(_online_users)
        for i in range(0, len(users), 4):
            row = users[i:i+4]
            line = '  ' + ''.join(u.ljust(10) for u in row)
            data.extend(ascii_to_petscii(line))
            data.append(0x0D)

        if not users:
            data.extend(ascii_to_petscii('  (NONE)'))
            data.append(0x0D)

        data.append(0x00)  # End Part 1

        # Part 2: empty footer
        data.append(0x0D)
        data.append(0x0D)

        # Part 3: empty
        data.append(0x00)

        # Part 4: breadcrumb
        data.extend(ascii_to_petscii('     1 *** COMPUNET ***'))
        data.append(0x0D)
        data.extend(ascii_to_petscii('  WHO'))
        data.append(0x00)

        # Part 5: column header
        data.extend(ascii_to_petscii(' WHO'))
        data.append(0x0D)
        data.append(0x00)

        # Part 6: user entries (one per line)
        if users:
            for u in users:
                data.extend(ascii_to_petscii('0     ' + u.ljust(18)))
                data.append(0x2C)
                data.append(0x0D)
        else:
            data.extend(ascii_to_petscii('0     (NONE)'))
            data.append(0x2C)
            data.append(0x0D)

        return bytes(data)

    def _make_welcome_frame(self, user):
        """Build the personal information welcome screen from template.

        Returns raw frame data for L89D0 (FRAME_BUF_READ) to consume.
        Template at server/content/templates/welcome.seq with placeholders.
        """
        self.last_response_type = RESP_FRAME

        # Update last login
        now = datetime.datetime.now()
        MONTHS = ['JAN','FEB','MAR','APR','MAY','JUN',
                  'JUL','AUG','SEP','OCT','NOV','DEC']
        prev_date = user.get('last_login_date', '')
        prev_time = user.get('last_login_time', '')
        if not prev_date:
            prev_date = 'NEVER'
            prev_time = ''

        # Save current login as last_login for next time
        user['last_login_date'] = f'{now.day:02d}-{MONTHS[now.month-1]}-{now.strftime("%y")}'
        user['last_login_time'] = now.strftime('%H:%M')
        self._save_user()

        # Check for unread mail
        mail_file = os.path.join(MAIL_DIR, self.user_id + '.json')
        mail_waiting = False
        if os.path.exists(mail_file):
            with open(mail_file, 'r') as f:
                inbox = json.load(f)
            visible = self._filter_expired_mail(inbox.get('messages', []))
            mail_waiting = any(not m.get('read', True) for m in visible)

        # Pillarbox mail indicator (6 lines of graphic or equivalent spaces)
        if mail_waiting:
            pb1 = b'\xa5\x06\x1c\x1c\xaf\xb9\xaf\x20\x20'
            pb2 = b'\x20\xbc\x12\x06\x02\x92\xbe\x20'
            pb3 = b'\x12\x20\x92\xa2\x12\x20\x92\x20\x20'
            pb4 = b'\x06\x1c\x1c\x12\x20\xa6\x20\x92\x20\x20'
            pb5 = b'\x12\x06\x02\x92\x20\x20'
            pb6 = b'\x90\xac\x12\x06\x02\x92\xbb\x20'
        else:
            pb1 = b'\xb4\x06\x21'
            pb2 = b'\x06\x06'
            pb3 = b'\x06\x04'
            pb4 = b'\x06\x21'
            pb5 = b'\x06\x04'
            pb6 = b'\x06\x05'

        # Credit display
        credit = user.get('credit', 0.0)
        if credit >= 0:
            credit_str = f'{credit:.2f} CREDIT'
        else:
            credit_str = f'{abs(credit):.2f} DEBIT'

        # Pages and storage calculations
        self.directory.reload()
        user_pages = [p for p in self.directory.pages.values() if p.author == self.user_id]
        pages_count = len(user_pages)
        near_death = len([p for p in user_pages if 0 < p.life < 5])
        self._check_storage_reset(user)
        free_storage = self._get_free_storage_remaining(user)

        # Next quarter start date
        month = now.month
        if month <= 3:
            nq = datetime.date(now.year, 4, 1)
        elif month <= 6:
            nq = datetime.date(now.year, 7, 1)
        elif month <= 9:
            nq = datetime.date(now.year, 10, 1)
        else:
            nq = datetime.date(now.year + 1, 1, 1)
        next_quarter_str = f'{nq.day:02d}-{MONTHS[nq.month-1]}'

        # Load template
        template_path = os.path.join(CONTENT_DIR, 'templates', 'welcome.seq')
        if os.path.exists(template_path):
            with open(template_path, 'rb') as f:
                frame = f.read()
        else:
            frame = b'\x00\x03\x0F\x8E\x0D\x1F WELCOME\x0D\x00'

        # Replace placeholders with padding adjustment.
        # Each placeholder is followed by $06 $XX (repeat XX spaces).
        # Total field width (value + spaces) must stay constant.
        def replace_padded(frame, placeholder, value, orig_len):
            """Replace placeholder and adjust the $06 $XX space padding that follows."""
            val = value.encode('ascii') if isinstance(value, str) else value
            pos = frame.find(placeholder)
            if pos < 0:
                return frame
            after = pos + len(placeholder)
            if after + 1 < len(frame) and frame[after] == 0x06:
                orig_pad = frame[after + 1]
                total_width = orig_len + orig_pad
                new_pad = max(0, total_width - len(val))
                frame = frame[:pos] + val + bytes([0x06, new_pad]) + frame[after + 2:]
            else:
                frame = frame[:pos] + val + frame[after:]
            return frame

        user_name = user.get('name', self.user_id).upper()
        pages_stats = f'{pages_count}/{near_death}'
        frame = replace_padded(frame, b'{USER_NAME}', user_name, 14)
        frame = replace_padded(frame, b'{LAST_TIME}', prev_time or '', 5)
        frame = replace_padded(frame, b'{PAGES_STATS}', pages_stats, 3)
        frame = replace_padded(frame, b'{FREE_STORAGE}', str(free_storage), 3)
        frame = replace_padded(frame, b'{NEXT_QUARTER}', next_quarter_str, 6)
        frame = frame.replace(b'{LAST_DATE}', prev_date.ljust(9).encode('ascii'))
        frame = frame.replace(b'{PB1}', pb1)
        frame = frame.replace(b'{PB2}', pb2)
        frame = frame.replace(b'{PB3}', pb3)
        frame = frame.replace(b'{PB4}', pb4)
        frame = frame.replace(b'{PB5}', pb5)
        frame = frame.replace(b'{PB6}', pb6)

        return frame
    
    def _make_error(self, message_petscii):
        """Build an error response."""
        return bytes([RESP_ERROR]) + message_petscii + b'\x00'


# ============================================================
# TCP interface - raw protocol for C64 clients
# ============================================================

async def tcp_handler(reader, writer):
    """Handle a TCP connection from a real C64 via WiFi modem/tcpser.
    
    Protocol flow:
    1. Wait for handshake ($20 from client)
    2. Respond with handshake ($20)
    3. Wait for login packet (COM token with 'Z' command)
    4. Authenticate and send linking data via X.25 packets
    5. Enter command loop (receive COM packets, send responses)
    """
    from x25_protocol import X25Connection, TOKEN_COM, TOKEN_ACK, TOKEN_DAT
    import socket

    addr = writer.get_extra_info('peername')
    log.info('TCP client connected: %s', addr)

    # Disable Nagle's algorithm — send packets immediately
    sock = writer.get_extra_info('socket')
    if sock:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # Enable TCP keepalives to prevent NAT/firewall timeout
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'TCP_KEEPIDLE'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 15)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 4)
    
    directory = CompunetDirectory()
    session = CompunetSession(directory)
    session.client_ip = addr[0] if addr else ''
    # 'c64' until identification says otherwise — and identification MUST overwrite
    # this (see the ident handler below). It is not derived: audit_via() returns an
    # explicit value before it consults is_amiga, so leaving this to be "corrected"
    # by setting is_amiga alone silently labelled every Amiga session a C64.
    session.audit_via = 'c64'
    x25 = X25Connection()

    pending_packets = []  # Packets received during ACK wait (non-ACK)

    async def wait_for_ack(timeout=5.0):
        """Wait for client to send an ACK packet. Returns True if received.
        Any non-ACK packets received are stashed in pending_packets for
        the main loop to process."""
        try:
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                remaining = deadline - asyncio.get_event_loop().time()
                data = await asyncio.wait_for(reader.read(32), timeout=remaining)
                if not data:
                    return False
                # Feed into X.25 parser
                packets = x25.feed_data(data)
                got_ack = False
                for token, seq, payload in packets:
                    if token == TOKEN_ACK:
                        log.debug('ACK received: seq=$%02X', seq)
                        got_ack = True
                        # Keep scanning: any non-ACK packets batched in the SAME read
                        # after the ACK (e.g. an upload's 8-byte header arriving right
                        # behind the ACK) must still be stashed, not dropped.
                    else:
                        # Stash non-ACK packet for main loop
                        pending_packets.append((token, seq, payload))
                if got_ack:
                    return True
        except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError):
            log.debug('ACK wait: timeout or disconnect')
        return False

    async def send_pkt_with_ack(pkt):
        """Send a packet and wait for client ACK before returning."""
        writer.write(pkt)
        await writer.drain()
        await wait_for_ack()

    try:
        # ============================================================
        # Phase 1: Connection handshake (auto-detect Hayes vs raw X.25)
        # Hayes (VICE direct): first byte is 'A' ($41/$C1) → handle ATDT
        # Raw X.25 (tcpser): server sends 12×$20, client responds
        # ============================================================
        log.info('TCP: connected, waiting for first byte to auto-detect mode...')

        # Peek at first byte to determine connection type
        try:
            first_data = await asyncio.wait_for(reader.read(1), timeout=5.0)
        except asyncio.TimeoutError:
            log.info('TCP: no data received within 5s, assuming raw X.25')
            first_data = None

        if first_data and (first_data[0] & 0x7F) == 0x41:
            # Hayes mode: consume AT command, send CONNECT response
            log.info('TCP: detected Hayes AT command (byte=$%02X), entering modem emulation', first_data[0])
            at_buf = bytearray(first_data)
            while True:
                try:
                    ch = await asyncio.wait_for(reader.read(1), timeout=5.0)
                except asyncio.TimeoutError:
                    break
                if not ch:
                    break
                at_buf.extend(ch)
                if ch[0] == 0x0D:
                    break
            at_cmd = bytes(b & 0x7F for b in at_buf).decode('ascii', errors='replace').strip()
            log.info('TCP: Hayes command: %s', at_cmd)
            # Send CONNECT response (what tcpser would send)
            await asyncio.sleep(0.5)
            writer.write(b'CONNECT 1200\r')
            await writer.drain()
            log.info('TCP: sent CONNECT 1200 response')

        # Proceed with X.25 handshake (same for both modes)
        log.info('TCP: sending X.25 handshake...')
        await asyncio.sleep(0.05)
        for i in range(12):
            writer.write(bytes([0x20]))
            await writer.drain()
            await asyncio.sleep(0.1)
        log.info('X25 TX: handshake complete - 12 bytes of $20 sent')
        x25.connected = True

        log.info('TCP: handshake complete, entering negotiation phase...')
        
        # ============================================================
        # Phase 2: Protocol negotiation + Login
        #
        # The ROM sends raw bytes (NOT X.25 framed) during connection:
        #   1. Identification: "  C CNET\r<address>\rNO\rRUN\r"
        #   2. After we acknowledge, ROM displays login screen
        #   3. Login data: raw bytes from $C100 buffer (27 bytes):
        #      [0]='Z' [1-8]=UserID [9-14]=Password [15+]=system info
        #
        # The ROM's PROTO_CONNECT post-loop at $9EE3 processes received
        # bytes and sends its identification. It needs the server to
        # keep the connection alive (send periodic bytes) until it
        # finishes and returns to the caller.
        # ============================================================
        
        rx_buffer = bytearray()
        negotiation_done = False
        login_done = False
        ident_received = False
        
        while not login_done:
            try:
                data = await asyncio.wait_for(reader.read(256), timeout=120.0)
            except asyncio.TimeoutError:
                log.info('TCP: timeout during negotiation/login')
                return
            if not data:
                log.info('TCP: connection closed during negotiation/login')
                return
            
            rx_buffer.extend(data)
            
            log.debug('TCP RX: %d bytes: %s', len(data), data.hex())
            
            # Phase 2a: Look for CNET identification
            if not ident_received and b'CNET' in rx_buffer:
                log.info('TCP: *** CNET identification received ***')
                # Parse the identification fields (CR-separated)
                fields = rx_buffer.split(b'\r')
                for i, field in enumerate(fields):
                    printable_field = ''.join(chr(b) if 32 <= b < 127 else f'[{b:02X}]' for b in field)
                    log.info('TCP:   field[%d]: %r (%s)', i, printable_field, field.hex())
                
                # Classify the client. C64/Reborn identify with "{hash}/100" (contains
                # '/'); the native Amiga client sends "C CNET\r" TWICE plus a 14-zero
                # field and has NO '/'. The client may deliver these in separate TCP
                # segments (the two "C CNET" lines, then a 5s pause, then the zeros), so
                # wait until we can actually tell them apart rather than judging a partial
                # identification. Detecting Amiga lets us skip the C64 hash gate + LINKING;
                # this is harmless to C64 clients (their field[1] always carries '/').
                ident_blob = bytes(rx_buffer)
                has_slash = b'/' in ident_blob
                is_amiga  = (ident_blob.count(b'CNET') >= 2
                             or b'00000000000000' in ident_blob)
                if not has_slash and not is_amiga:
                    continue   # identification incomplete — keep buffering

                # Sets is_amiga AND the audit label together — see the function.
                identify_binding_a_client(session, is_amiga)
                ident_received = True
                rx_buffer.clear()

                if is_amiga:
                    log.info('TCP: *** Amiga client detected — skipping hash check + LINKING ***')
                else:
                    # Check client version (field[1] = "{hash}/100") — C64/Reborn clients.
                    field1 = fields[1].decode('ascii', errors='ignore').strip() if len(fields) > 1 else ''
                    client_hash = field1.split('/')[0] if '/' in field1 else ''
                    client_version_path = os.path.join(CFG_DIR, 'client_version.txt')
                    if os.path.exists(client_version_path):
                        expected_hash = open(client_version_path).read().strip().upper()
                        if not client_hash or client_hash.upper() != expected_hash:
                            log.warning('TCP: client version mismatch: got=%r expected=%s',
                                        client_hash, expected_hash)
                            # Send error message and close
                            msg = b'*PLEASE DOWNLOAD LATEST CLIENT\x0d'
                            writer.write(msg)
                            await writer.drain()
                            await asyncio.sleep(3.0)
                            writer.close()
                            return

                # Send MOTD (if present) before *CON
                # Each line must start with '*' to activate client display.
                # The motd.txt already has '*' borders so lines are sent as-is.
                motd_path = os.path.join(CFG_DIR, 'motd.txt')
                if os.path.exists(motd_path):
                    with open(motd_path, 'r') as f:
                        lines = [l.rstrip('\n') for l in f if l.strip()]
                    if lines:
                        _vf = os.path.join(SERVER_DIR, 'VERSION')
                        if not os.path.exists(_vf):
                            _vf = os.path.join(SERVER_DIR, '..', 'VERSION')
                        _ver = open(_vf).read().strip() if os.path.exists(_vf) else '?'
                        for line in lines:
                            line = line.replace('{VERSION}', _ver.upper().center(37))
                            # Convert to PETSCII lowercase mode: A-Z → $C1-$DA
                            raw = bytearray()
                            for ch in line.upper():
                                code = ord(ch)
                                if 0x41 <= code <= 0x5A:
                                    raw.append(code + 0x80)
                                else:
                                    raw.append(code)
                            raw.append(0x0D)
                            writer.write(bytes(raw))
                            await writer.drain()
                            await asyncio.sleep(0.1)
                    log.info('TCP TX: sent MOTD from %s', motd_path)

                # Pause to let user read MOTD, then send "*CON\r"
                await asyncio.sleep(3.0)
                writer.write(b'\x2a\x43\x4f\x4e\x0d')
                await writer.drain()
                log.info('TCP TX: sent "*CON\\r" connection signal')
                login_done = True  # Exit negotiation, enter command loop
                break
        
        log.info('TCP: entering command loop')
        
        # ============================================================
        # Phase 4: Command loop
        # The ROM sends X.25 framed packets. The COM token from the ROM
        # is $43 ('C') — stored at $8034 before sending. The payload
        # contains the command data from $C100 buffer.
        #
        # First packet after *CON handshake is the LOGIN packet:
        #   payload[0] = 'Z' ($5A) = login command
        #   payload[1-8] = User ID (space-padded)
        #   payload[9-14] = Password (space-padded)
        #   payload[15+] = System info
        # ============================================================
        authenticated = False
        
        while True:
            try:
                data = await asyncio.wait_for(reader.read(256), timeout=1200.0)
            except asyncio.TimeoutError:
                log.info('TCP: idle timeout (20 minutes)')
                break
            if not data:
                log.info('TCP: connection closed by client')
                break
            
            log.debug('TCP RX: %d bytes: %s', len(data), data.hex())
            packets = x25.feed_data(data)
            # Prepend any packets stashed during ACK wait
            if pending_packets:
                packets = pending_packets + packets
                pending_packets.clear()

            for token, seq, payload in packets:
                log.info('TCP: packet token=$%02X seq=$%02X payload=%d bytes',
                         token, seq, len(payload))
                
                # ROM COM packets use token $43 ('C')
                if token == 0x43 and len(payload) >= 1:
                    # payload[0] = command byte (Z=$5A, etc.)
                    # (flags byte $FF is now parsed as seq by the packet parser)
                    cmd_byte = payload[0]
                    cmd_payload = payload  # command + parameters
                    log.info('TCP: COM seq=$%02X cmd=$%02X (%s) data=%s',
                             seq, cmd_byte, chr(cmd_byte) if 32 <= cmd_byte < 127 else '?',
                             cmd_payload.hex())
                    
                    if cmd_byte == 0x5A and not authenticated:
                        # LOGIN packet: cmd_payload = [Z, user(8), pass(6), sysinfo...]
                        log.info('TCP: *** PROCESSING LOGIN ***')
                        user_id = bytes(cmd_payload[1:9]).decode('latin-1').strip()
                        password = bytes(cmd_payload[9:15]).decode('latin-1').strip()
                        
                        # CNLOAD flag at offset 25-26 from start of cmd_payload
                        # These are the terminal version hash stored at $A000/$A001
                        cnload_1 = cmd_payload[25] if len(cmd_payload) > 25 else 0
                        cnload_2 = cmd_payload[26] if len(cmd_payload) > 26 else 0
                        # Skip LINKING if client's hash matches current terminal
                        skip_linking = (cnload_1 == TERMINAL_HASH[0] and
                                        cnload_2 == TERMINAL_HASH[1])

                        log.info('TCP: *** LOGIN ***')
                        log.info('TCP:   user=%r cnload_bytes=$%02X/$%02X (skip=%s, server_hash=$%02X/$%02X)',
                                 user_id, cnload_1, cnload_2, skip_linking,
                                 TERMINAL_HASH[0], TERMINAL_HASH[1])
                        
                        async with _lock_users:
                            response = session.handle_login(user_id, password)
                        if not session.authenticated:
                            log.info('TCP: login FAILED - sending error frame and closing')
                            # Send a proper frame (flags/border/bg + message + $00)
                            # so L89D0 (FRAME_BUF_READ) can display it correctly
                            error_frame = bytearray()
                            error_frame.append(0x00)  # flags (no more pages)
                            error_frame.append(0x00)  # border (black)
                            error_frame.append(0x00)  # background (black)
                            error_frame.append(0x0D)
                            error_frame.append(0x0D)
                            error_frame.extend(ascii_to_petscii('  INVALID ID OR PASSWORD'))
                            error_frame.append(0x0D)
                            error_frame.append(0x00)  # end of frame
                            MAX_PAYLOAD = 100
                            offset = 0
                            while offset < len(error_frame):
                                chunk = error_frame[offset:offset + MAX_PAYLOAD]
                                pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                                await send_pkt_with_ack(pkt)
                                offset += MAX_PAYLOAD
                            eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                            writer.write(eos_pkt)
                            await writer.drain()
                            await asyncio.sleep(2.0)
                            writer.close()
                            await writer.wait_closed()
                            return
                        
                        authenticated = True
                        _user_connect(session.user_id)
                        log.info('TCP: login OK!')

                        # Send welcome frame — L89D0 reads this after login
                        if response:
                            MAX_PAYLOAD = 100
                            offset = 0
                            while offset < len(response):
                                chunk = response[offset:offset + MAX_PAYLOAD]
                                pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                                await send_pkt_with_ack(pkt)
                                offset += MAX_PAYLOAD
                            eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                            writer.write(eos_pkt)
                            await writer.drain()
                            log.info('TCP: sent welcome frame (%d bytes + EOS)', len(response))

                        # LINKING: the native Amiga client has its own terminal and does
                        # NOT load 6502 code, so skip LINKING entirely for it (sending even
                        # a header-only stream would desync its frame reader). C64/Reborn
                        # clients get the terminal binary or header-only stream as before.
                        if getattr(session, 'is_amiga', False):
                            log.info('LINKING: skipped (Amiga native client)')
                        else:
                            terminal_path = os.path.join(CFG_DIR, 'terminal.bin')
                            linking_header = bytes([TERMINAL_HASH[0], TERMINAL_HASH[1],
                                                   0x05, 0xA0, 0x00, 0xA0, 0x00, 0x00])
                            if not skip_linking and os.path.exists(terminal_path):
                                with open(terminal_path, 'rb') as f:
                                    terminal_data = f.read()
                                linking_stream = linking_header + terminal_data
                            else:
                                # Header + 1 padding byte — avoids EOS pre-fetch timeout.
                                # The 1 byte writes $00 to $A000 but the hash PLA overwrites it after.
                                linking_stream = linking_header + b'\x00'
                                if skip_linking:
                                    log.info('LINKING: skipped (client has current terminal)')
                            MAX_PAYLOAD = 100
                            offset = 0
                            pkt_num = 0
                            while offset < len(linking_stream):
                                chunk = linking_stream[offset:offset + MAX_PAYLOAD]
                                pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                                await send_pkt_with_ack(pkt)
                                pkt_num += 1
                                offset += MAX_PAYLOAD
                            eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                            writer.write(eos_pkt)
                            await writer.drain()
                            if not skip_linking:
                                log.info('LINKING: sent terminal (%d bytes, %d packets)',
                                         len(linking_stream), pkt_num)
                    
                    elif cmd_byte == 0x5A and authenticated:
                        # Retransmitted login packet — ignore it
                        log.debug('TCP: ignoring retransmitted login packet')
                    
                    elif authenticated:
                        # Any activity from user confirms they're online
                        _user_connect(session.user_id)
                        log.info('TCP: dispatching command (authenticated=True)')
                        async with _lock_content:
                            cmd_response = session.handle_command(cmd_payload)
                        if cmd_response:
                            # AMIGA ONLY: some commands (ID, mail-send) return frame data whose
                            # first byte can collide with an ack char ('A'/'B'/'@'). The Amiga
                            # reads a command ack via serial_io_c before the frame, so prepend
                            # '@'. Gated on is_amiga so the C64 stream is byte-for-byte unchanged
                            # (the C64 keys off the DAT token and reads the frame directly).
                            if (getattr(session, 'tcp_ack_prefix', False)
                                    and getattr(session, 'is_amiga', False)):
                                cmd_response = bytes([0x40]) + cmd_response
                            log.info('CMD: sending %d bytes in %d-byte chunks', len(cmd_response), 100)
                            MAX_PAYLOAD = 100
                            offset = 0
                            pkt_num = 0
                            while offset < len(cmd_response):
                                chunk = cmd_response[offset:offset + MAX_PAYLOAD]
                                pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                                await send_pkt_with_ack(pkt)
                                pkt_num += 1
                                log.info('CMD: sent pkt %d (%d payload, %d wire)', pkt_num, len(chunk), len(pkt))
                                offset += MAX_PAYLOAD
                            # EOS only for streamed responses (not single-packet ACKs)
                            if session.last_response_type != RESP_ACK:
                                eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                                writer.write(eos_pkt)
                                await writer.drain()
                                log.info('CMD: sent EOS pkt (%d wire)', len(eos_pkt))

                            # Close connection after LEAVE
                            if getattr(session, '_leaving', False):
                                log.info('TCP: LEAVE — closing connection')
                                await asyncio.sleep(2.0)
                                writer.close()
                                await writer.wait_closed()
                                return

                            # Enter partyline mode after LINK download
                            if getattr(session, '_enter_partyline', False):
                                session._enter_partyline = False
                                if getattr(session, '_amiga_partyline', False):
                                    # Amiga: the 8-byte link header was just sent (no EOS).
                                    # Run the raw preamble + ASCII chat + 0x02 teardown.
                                    session._amiga_partyline = False
                                    log.info('TCP: entering AMIGA partyline for user=%s', session.user_id)
                                    await partyline.handle_amiga_session(reader, writer, session.user_id)
                                    log.info('TCP: exited AMIGA partyline, resuming X.25 for user=%s', session.user_id)
                                    continue
                                log.info('TCP: entering partyline mode for user=%s', session.user_id)
                                await asyncio.sleep(1.0)
                                await partyline.handle_session(reader, writer, session.user_id)
                                log.info('TCP: exited partyline mode, resuming X.25 for user=%s', session.user_id)
                                continue

                elif token == 0x40 and session._program_download_pending:
                    # Client confirms download proceed — send program data.
                    # take_program_download clears the pending state and audits.
                    program_data = session.take_program_download()
                    log.info('DOWNLOAD: proceed received, sending %d bytes of program data', len(program_data))
                    # ⚠ THE COST HERE IS PER ROUND TRIP, NOT PER BYTE. Every packet waits
                    # for the client's ACK, and on an emulated Amiga that wait costs one
                    # ~20 ms tick: measured over 1700 packets, 1589 of the 1700 inter-ACK
                    # gaps fell in 19-21 ms, hard-clustered on 20 ms — 50 Hz, the host's
                    # frame boundary, because bsdsocket.library emulation services socket
                    # I/O once per frame. 1700 x 20 ms = the 34 s a 166K download took.
                    #
                    # So the only lever is FEWER packets. (Buffering the client's per-byte
                    # reads was tried first and bought 10%: the syscalls were never the
                    # bottleneck.) The upload direction has always used 4000-byte blocks,
                    # which is why uploading the same file takes 0.18 s.
                    #
                    # Amiga only. The C64 ROM's receive path expects 100-byte packets, so
                    # its stream stays byte-for-byte unchanged.
                    #
                    # 4000 is the client's own send size and its safe ceiling: net_recv_frame
                    # collects into raw[NET_FRAME_MAX + 2] = 8302, and worst-case stuffing
                    # (every byte in $01-$03) doubles 4005 to 8010, which still fits. The
                    # single-byte length field wraps at this size and is advisory only —
                    # both parsers frame on the $01/$02 markers, which is what makes the
                    # existing 4000-byte uploads work.
                    MAX_PAYLOAD = 4000 if getattr(session, 'is_amiga', False) else 100
                    offset = 0
                    pkt_num = 0
                    while offset < len(program_data):
                        chunk = program_data[offset:offset + MAX_PAYLOAD]
                        pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                        await send_pkt_with_ack(pkt)
                        pkt_num += 1
                        offset += MAX_PAYLOAD
                    eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                    writer.write(eos_pkt)
                    await writer.drain()
                    log.info('DOWNLOAD: sent %d packets of %d + EOS (%d bytes total)',
                             pkt_num, MAX_PAYLOAD, len(program_data))

                elif token == 0x41 and session._program_download_pending:
                    # Client aborted download (no room in RAM)
                    session._program_download_pending = False
                    session._program_download_data = None
                    session.show_page = None
                    log.info('DOWNLOAD: client aborted (no room in RAM)')

                elif token == TOKEN_ACK:
                    log.debug('TCP: received ACK seq=$%02X', seq)

                elif (session.pending_send is not None and token != 0x43
                        and session.pending_send.get('type') in ('P', 'F')):
                    # BINARY upload — a program ('P') or an IFF picture ('F'): 8-byte
                    # header then the file.
                    #
                    # ⚠ 'F' BELONGS HERE TOO. The Amiga's publish dialog has always
                    # offered it — put_frame's jump table at 0x10c3c2 routes 'A','S','P'
                    # and 'F' alike to upload_file — and it uses this identical
                    # header-then-body format. Gating on 'P' alone sent an IFF upload to
                    # the PETSCII frame accumulator below, which chopped it at the first
                    # short chunk; _complete_content_upload then read byte 0 as the
                    # machine type (it is $46, the 'F' of "FORM"), concluded "not 68k",
                    # and stripped a C64 load address off data that has none. A corrupted
                    # file, stored under the wrong shape, with no error anywhere.
                    #
                    # The gap came from adding F to Binding B first and treating picture
                    # upload as a web-client feature — the Amiga could already VIEW them,
                    # so uploading from a modern client felt like the whole story. It was
                    # not: the 1989 dialog offers F, so the 1989 client can send one.
                    #
                    # ⚠ THE HEADER IS MACHINE-DEPENDENT, and so is how the body ENDS.
                    # Byte 0 selects (§8.3.2):
                    #
                    #   Amiga (1): no load address, so bytes 4-7 are a big-endian body
                    #              SIZE. The client sends the header as its own DAT and
                    #              then blasts the body; a HUNK body rarely ends on a
                    #              short chunk, so the size is what terminates it.
                    #   C64   (0): bytes 4-5 are the LOAD ADDRESS (4-7 is therefore NOT a
                    #              size). The client streams header and body continuously
                    #              and a chunk < 100 bytes ends the transfer, exactly as a
                    #              PETSCII frame does.
                    #
                    # Reading 4-7 as a size for BOTH machines is a regression introduced
                    # 2026-07-22 while fixing the Amiga path: a C64 load address of $0801
                    # reads as a demand for ~17 MB, so the upload never completes. C64
                    # program upload worked before that date (mission-monday.prg,
                    # 2026-06-05, 18381 bytes, stored opening 01 08) and was not exercised
                    # afterwards, so nothing caught it.
                    #
                    # The C64 terminator is deliberately the ORIGINAL chunk rule rather
                    # than a size read from bytes 6-7: that the C64 client populates 6-7
                    # on UPLOAD is unverified, whereas chunk-termination is proven by the
                    # uploads that worked.
                    ps = session.pending_send
                    if '_prog_header' not in ps:
                        hdr = bytes(payload[:8])
                        ps['_prog_header'] = hdr
                        ps['_prog_amiga'] = (hdr[0] == 1)
                        ps['_prog_size'] = int.from_bytes(hdr[4:8], 'big') if ps['_prog_amiga'] else None
                        # ⚠ Keep body bytes that arrived in the SAME packet as the header.
                        # The C64 streams them together, so discarding the remainder here
                        # silently truncated the first ~92 bytes of every C64 program.
                        ps['_prog_body'] = bytearray(payload[8:])
                        log.info('UPLOAD: program header machine=%d (%s) body_size=%s carried=%d',
                                 hdr[0], 'amiga' if ps['_prog_amiga'] else 'c64',
                                 ps['_prog_size'] if ps['_prog_amiga'] else 'chunk-terminated',
                                 len(ps['_prog_body']))
                        complete = (not ps['_prog_amiga']) and len(payload) < 100
                    else:
                        ps['_prog_body'].extend(payload)
                        log.info('TCP: program body +%d (%d/%s)', len(payload),
                                 len(ps['_prog_body']),
                                 ps['_prog_size'] if ps['_prog_amiga'] else '?')
                        complete = (len(ps['_prog_body']) >= ps['_prog_size']
                                    if ps['_prog_amiga'] else len(payload) < 100)

                    if complete:
                        body = (bytes(ps['_prog_body'][:ps['_prog_size']]) if ps['_prog_amiga']
                                else bytes(ps['_prog_body']))
                        frame_data = ps['_prog_header'] + body
                        ps['frames'].append(frame_data)
                        log.info('UPLOAD: program complete (%d bytes = 8 header + %d body)',
                                 len(frame_data), len(body))
                        ack_data = bytes([0x40]) + b'\x00' * 10  # '@' clean accept (not 'A'=host-error on Amiga)
                        ack_pkt = x25.make_data_packet(ack_data, TOKEN_DAT)
                        await send_pkt_with_ack(ack_pkt)
                        await writer.drain()
                        log.info('UPLOAD: sent final program ACK (%d wire)', len(ack_pkt))

                elif session.pending_send is not None and token != 0x43:
                    # Any non-COM packet during a NON-program upload = PETSCII frame chunk
                    log.info('TCP: upload chunk token=$%02X seq=$%02X payload=%d bytes',
                             token, seq, len(payload))
                    # Accumulate chunks into current frame buffer
                    if '_current_frame' not in session.pending_send:
                        session.pending_send['_current_frame'] = bytearray()
                    session.pending_send['_current_frame'].extend(payload)
                    # Final chunk (< 100 bytes) = end of this frame
                    if len(payload) < 100:
                        frame_data = bytes(session.pending_send['_current_frame'])
                        session.pending_send['_current_frame'] = bytearray()
                        # A non-empty buffer is a real frame (its <100 last chunk, or an
                        # exact-multiple-of-100 frame terminated by the EOS). An EMPTY buffer
                        # here is the Amiga's trailing empty-DAT EOS arriving after the frame
                        # already completed on its <100 chunk: store nothing and send no second
                        # ACK (the client reads exactly one ACK per frame). The C64 ends a frame
                        # with its <100 data chunk and never sends an empty EOS, so it is
                        # unaffected. (Without this guard the EOS was stored as an empty trailing
                        # frame, which crashed _send_mail_frame on DNLD.)
                        if frame_data:
                            session.pending_send['frames'].append(frame_data)
                            log.info('UPLOAD: frame %d complete (%d bytes)',
                                     len(session.pending_send['frames']), len(frame_data))
                            ack_data = bytes([0x40]) + b'\x00' * 10  # '@' clean accept (not 'A'=host-error on Amiga)
                            ack_pkt = x25.make_data_packet(ack_data, TOKEN_DAT)
                            await send_pkt_with_ack(ack_pkt)
                            await writer.drain()
                            log.info('UPLOAD: sent frame ACK (%d wire)', len(ack_pkt))

                else:
                    log.debug('TCP: other token=$%02X seq=$%02X', token, seq)
    
    except (ConnectionResetError, BrokenPipeError) as e:
        log.info('TCP: connection error: %s', e)
    finally:
        if session.user_id:
            _user_disconnect(session.user_id, session)   # audits the session end
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        log.info('TCP client disconnected: %s', addr)


# ============================================================
# REST API — User Management
# ============================================================

_USERID_RE = re.compile(r'^[A-Z0-9]{1,8}$')
_PASSWORD_RE = re.compile(r'^[A-Z0-9]{1,6}$')


def _api_check_auth(request):
    api_key = os.environ.get('COMPUNET_API_KEY', '')
    if not api_key:
        return False
    auth = request.headers.get('Authorization', '')
    return auth == f'Bearer {api_key}'


def _api_load_pending():
    pending_file = os.path.join(CFG_DIR, 'pending.json')
    if os.path.exists(pending_file):
        with open(pending_file, 'r') as f:
            return json.load(f)
    return {}


async def _send_mail_notification(recipient_id, sender_id, subject, users):
    """Send email notification when a user receives in-game mail."""
    recipient = users.get(recipient_id, {})
    email = recipient.get('email')
    if not email:
        return
    api_key = os.environ.get('POSTMARK_API_KEY')
    if not api_key:
        return
    template_path = os.path.join(CFG_DIR, 'mail-notification.md')
    if not os.path.exists(template_path):
        return

    recipient_name = recipient.get('name', recipient_id)
    sender_name = users.get(sender_id, {}).get('name', sender_id)
    email_from = os.environ.get('EMAIL_FROM', 'Compunet Reborn <noreply@compunet.live>')

    template = open(template_path).read()
    body_md = (template
               .replace('{{recipient_name}}', recipient_name)
               .replace('{{sender_name}}', sender_name)
               .replace('{{sender_id}}', sender_id)
               .replace('{{subject}}', subject))
    body_html = markdown.markdown(body_md)

    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.post('https://api.postmarkapp.com/email',
                headers={'X-Postmark-Server-Token': api_key,
                         'Content-Type': 'application/json'},
                json={
                    'From': email_from,
                    'To': email,
                    'Subject': f'New mail on Compunet from {sender_id}',
                    'HtmlBody': body_html,
                    'MessageStream': 'outbound'
                })
            if resp.status == 200:
                log.info('MAIL: notification sent to %s (%s)', recipient_id, email)
            else:
                log.warning('MAIL: notification failed for %s: %s', recipient_id, await resp.text())
    except Exception as e:
        log.warning('MAIL: notification error for %s: %s', recipient_id, e)


def _api_save_pending(pending):
    pending_file = os.path.join(CFG_DIR, 'pending.json')
    with open(pending_file, 'w') as f:
        json.dump(pending, f, indent=2)


def _api_load_users():
    users_file = os.path.join(CFG_DIR, 'users.json')
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            return json.load(f)
    return {}


def _api_save_users(users):
    users_file = os.path.join(CFG_DIR, 'users.json')
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)


def _api_user_public(user_id, user_data):
    return {
        'user_id': user_id,
        'name': user_data.get('name', ''),
        'email': user_data.get('email', ''),
        'account_type': user_data.get('account_type', 'BASIC'),
        'credit': user_data.get('credit', 0.0),
        'admin': user_data.get('admin', False),
        'editor': user_data.get('editor', False),
        'subscribed': user_data.get('subscribed', True),
    }


async def api_health(request):
    return aiohttp_web.json_response({'status': 'ok'})


async def api_auth(request):
    """Verify user credentials. Returns user info on success, 401 on failure."""
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    user_id = body.get('user_id', '').upper().strip()
    password = body.get('password', '').upper().strip()

    async with _lock_users:
        users = _api_load_users()

    # ⚠ BOTH failure branches audit. Only logging a wrong password misses the
    # attack that matters most: someone working through a list of user ids,
    # every attempt of which lands on the unknown-user branch and would leave
    # no trace at all.
    client_ip = body.get('ip') or request.remote
    user = users.get(user_id)
    if user is None:
        audit_log('login_failed', user=user_id, ip=client_ip, reason='no such user')
        return aiohttp_web.json_response({'error': 'invalid credentials'}, status=401)

    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    if user['password'] != password_hash:
        audit_log('login_failed', user=user_id, ip=client_ip, reason='bad password')
        return aiohttp_web.json_response({'error': 'invalid credentials'}, status=401)

    # ⚠ The website's own sign-in was not audited AT ALL: of 6,567 entries there
    # was no login event of any kind, so managing an account — changing a
    # password, an email address — left no trace. Every other way into Compunet
    # records a `connect`.
    #
    # `ip` comes from the WEBSITE, because the server cannot see the browser:
    # its peer here is the website container. The website resolves the real
    # address from its own forwarded headers and passes it; `request.remote` is
    # only the fallback, and names the website itself.
    audit_log('login_succeeded', user=user_id, ip=client_ip)
    return aiohttp_web.json_response(_api_user_public(user_id, user))


async def api_list_users(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    async with _lock_users:
        users = _api_load_users()
    return aiohttp_web.json_response({
        'users': [_api_user_public(uid, data) for uid, data in users.items()]
    })


async def api_get_user(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    user_id = request.match_info['user_id'].upper()
    async with _lock_users:
        users = _api_load_users()
    if user_id not in users:
        return aiohttp_web.json_response({'error': 'not found'}, status=404)
    return aiohttp_web.json_response(_api_user_public(user_id, users[user_id]))


async def api_create_user(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    user_id = body.get('user_id', '').upper().strip()
    password = body.get('password', '').upper().strip()
    name = body.get('name', '').strip()
    email = body.get('email', '').strip()
    account_type = body.get('account_type', 'BASIC').upper().strip()

    if not _USERID_RE.match(user_id):
        return aiohttp_web.json_response(
            {'error': 'user_id must be 1-8 chars, A-Z and 0-9 only'}, status=400)
    if not _PASSWORD_RE.match(password):
        return aiohttp_web.json_response(
            {'error': 'password must be 1-6 chars, A-Z and 0-9 only'}, status=400)
    if not name:
        return aiohttp_web.json_response(
            {'error': 'name is required'}, status=400)

    async with _lock_users:
        users = _api_load_users()
        if user_id in users:
            return aiohttp_web.json_response(
                {'error': 'user already exists'}, status=409)
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        users[user_id] = {
            'password': password_hash,
            'name': name,
            'email': email,
            'credit': 0.0,
            'account_type': account_type,
            'last_login_date': '',
            'last_login_time': '',
        }
        _api_save_users(users)

    log.info('API: created user %s', user_id)
    audit_log('signup_completed', user=user_id, ip=request.remote)
    return aiohttp_web.json_response(
        _api_user_public(user_id, users[user_id]), status=201)


async def api_update_user(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    user_id = request.match_info['user_id'].upper()
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    async with _lock_users:
        users = _api_load_users()
        if user_id not in users:
            return aiohttp_web.json_response({'error': 'not found'}, status=404)

        # ⚠ Record WHAT CHANGED, old -> new. "ADMIN edited ZARD" is close to
        # useless a month later, and this is the endpoint where credit is
        # adjusted and editor rights are granted.
        before = dict(users[user_id])

        if 'password' in body:
            password = body['password'].upper().strip()
            if not _PASSWORD_RE.match(password):
                return aiohttp_web.json_response(
                    {'error': 'password must be 1-6 chars, A-Z and 0-9 only'}, status=400)
            users[user_id]['password'] = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if 'name' in body:
            users[user_id]['name'] = body['name'].strip()
        if 'email' in body:
            users[user_id]['email'] = body['email'].strip()
        if 'credit' in body:
            try:
                users[user_id]['credit'] = float(body['credit'])
            except (ValueError, TypeError):
                return aiohttp_web.json_response(
                    {'error': 'credit must be a number'}, status=400)
        if 'account_type' in body:
            users[user_id]['account_type'] = body['account_type'].upper().strip()
        if 'editor' in body:
            users[user_id]['editor'] = bool(body['editor'])

        _api_save_users(users)

    changes = _audit_diff(before, users[user_id])
    log.info('API: updated user %s (%s)', user_id, ', '.join(changes) or 'no change')
    # ⚠ Two different acts share this endpoint. A user changing their own password
    # is not an administrative edit, and recording it as one would put routine
    # self-service in among the credit adjustments and editor grants — the events
    # this log exists to make findable. The caller says which it is.
    if body.get('self_service'):
        audit_log('password_changed', user=user_id, via='web', ip=request.remote)
    else:
        audit_log('user_updated', user=user_id, via='admin', ip=request.remote,
                  changed=changes or None)
    return aiohttp_web.json_response(_api_user_public(user_id, users[user_id]))


async def api_delete_user(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    user_id = request.match_info['user_id'].upper()

    async with _lock_users:
        users = _api_load_users()
        if user_id not in users:
            return aiohttp_web.json_response({'error': 'not found'}, status=404)
        del users[user_id]
        _api_save_users(users)

    log.info('API: deleted user %s', user_id)
    audit_log('user_deleted', user=user_id, via='admin', ip=request.remote)
    return aiohttp_web.json_response({'status': 'deleted'})


async def api_list_pending(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    async with _lock_users:
        pending = _api_load_pending()
    entries = []
    for token, entry in pending.items():
        entries.append({
            'token': token,
            'user_id': entry.get('user_id', ''),
            'email': entry.get('email', ''),
            'name': entry.get('name', ''),
            'created': entry.get('created', 0),
        })
    return aiohttp_web.json_response({'pending': entries})


async def api_create_pending(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    import time
    token = secrets.token_urlsafe(32)
    entry = {
        'user_id': body.get('user_id', ''),
        'password': body.get('password', ''),
        'email': body.get('email', ''),
        'name': body.get('name', ''),
        'created': time.time(),
    }

    async with _lock_users:
        pending = _api_load_pending()
        pending[token] = entry
        _api_save_pending(pending)

    log.info('API: created pending registration for %s', entry['user_id'])
    audit_log('registration_requested', user=entry['user_id'] or None,
              via='web', ip=request.remote, email=entry.get('email') or None)
    return aiohttp_web.json_response({'token': token}, status=201)


async def api_get_pending(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    token = request.match_info['token']

    async with _lock_users:
        pending = _api_load_pending()
        if token not in pending:
            return aiohttp_web.json_response({'error': 'not found'}, status=404)
        entry = pending[token]

    return aiohttp_web.json_response(entry)


async def api_consume_pending(request):
    """Retrieve and delete a pending registration (used after verification)."""
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    token = request.match_info['token']

    async with _lock_users:
        pending = _api_load_pending()
        if token not in pending:
            return aiohttp_web.json_response({'error': 'not found'}, status=404)
        entry = pending.pop(token)
        _api_save_pending(pending)

    # ⚠ This one endpoint serves BOTH approve and reject: the website consumes the
    # token, then creates the user only if approving. `signup_completed` records
    # the approval, so recording an approval here too would double-count. The
    # caller says which it is; absent that, treat it as a rejection, because a
    # token consumed and no account created is exactly what a rejection is.
    outcome = request.query.get('outcome', 'rejected')
    if outcome != 'approved':
        audit_log('registration_rejected', user=entry.get('user_id') or None,
                  via='admin', ip=request.remote)
    return aiohttp_web.json_response(entry)


async def api_broadcast(request):
    """Send a broadcast email to subscribers."""
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    subject = body.get('subject', '').strip()
    html_body = body.get('body', '').strip()
    test_mode = body.get('test_mode', False)

    if not subject or not html_body:
        return aiohttp_web.json_response({'error': 'subject and body required'}, status=400)

    # Collect recipient emails
    async with _lock_users:
        users = _api_load_users()

    recipients = []
    for uid, data in users.items():
        email = data.get('email', '')
        if not email:
            continue
        if test_mode:
            if data.get('admin', False):
                recipients.append(email)
        else:
            if data.get('subscribed', True):
                recipients.append(email)

    # Load public subscribers
    subscribers_file = os.path.join(CFG_DIR, 'subscribers.json')
    if not test_mode and os.path.exists(subscribers_file):
        with open(subscribers_file, 'r') as f:
            subs = json.load(f)
        for sub in subs.get('subscribers', []):
            if sub.get('email'):
                recipients.append(sub['email'])

    if not recipients:
        return aiohttp_web.json_response({'error': 'no recipients'}, status=400)

    # Send via Postmark broadcast stream
    import aiohttp as aiohttp_client
    postmark_key = os.environ.get('POSTMARK_API_KEY', '')
    email_from = os.environ.get('EMAIL_FROM', 'noreply@compunet.live')

    if not postmark_key:
        log.warning('BROADCAST: POSTMARK_API_KEY not set')
        return aiohttp_web.json_response({
            'status': 'dry_run', 'recipients': len(recipients)
        })

    sent = 0
    errors = []
    async with aiohttp_client.ClientSession() as session:
        for email in recipients:
            payload = {
                'From': email_from,
                'To': email,
                'Subject': subject,
                'HtmlBody': html_body,
                'MessageStream': 'broadcast',
            }
            async with session.post(
                'https://api.postmarkapp.com/email',
                headers={
                    'X-Postmark-Server-Token': postmark_key,
                    'Content-Type': 'application/json',
                },
                json=payload
            ) as resp:
                if resp.status == 200:
                    sent += 1
                else:
                    err_text = await resp.text()
                    errors.append(f'{email}: {resp.status} {err_text[:100]}')
                    log.error('BROADCAST: failed to send to %s: %s', email, err_text[:200])

    log.info('BROADCAST: sent=%d errors=%d test_mode=%s subject="%s"',
             sent, len(errors), test_mode, subject)
    audit_log('broadcast_sent', via='admin', ip=request.remote, subject=subject,
              recipients=len(recipients), sent=sent, errors=len(errors),
              test_mode=test_mode)
    return aiohttp_web.json_response({
        'status': 'sent', 'sent': sent, 'errors': len(errors),
        'test_mode': test_mode
    })


async def api_ws_partyline(request):
    """WebSocket endpoint for admin partyline access."""
    # Auth via query param (WebSocket can't use headers easily)
    api_key = os.environ.get('COMPUNET_API_KEY', '')
    token = request.query.get('token', '')
    if not api_key or token != api_key:
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    user_id = request.query.get('user_id', 'ADMIN').upper()
    ws = aiohttp_web.WebSocketResponse()
    if not ws.can_prepare(request):
        log.warning('WebSocket partyline: cannot prepare (missing upgrade headers)')
        return aiohttp_web.json_response({'error': 'WebSocket upgrade required'}, status=400)
    await ws.prepare(request)
    log.info('WebSocket partyline client connected: user=%s', user_id)
    try:
        await partyline.handle_web_session(ws, user_id)
    except Exception as e:
        log.error('WebSocket partyline error: %s', e)
    log.info('WebSocket partyline client disconnected: user=%s', user_id)
    return ws


async def api_get_audit(request):
    """GET /api/audit — return audit log entries with pagination.

    ⚠ Every other /api route guards itself and this one did not. The audit log
    records `user` and `ip` against connects, page reads, purchases, uploads,
    mail sends and password resets — who read what, from where, and when. On a
    deployment that publishes 6403 (the Cloudflare tunnel exposes it as
    api.compunet.live) an unguarded handler served all of that to anyone who
    guessed the path. It was missed because the endpoint only READS, and a
    read-only endpoint feels harmless right up until you notice what it reads.
    """
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    if not os.path.exists(AUDIT_LOG_PATH):
        return aiohttp_web.json_response(
            {'entries': [], 'total': 0, 'matched': 0, 'events': [], 'kinds': []})

    try:
        page = max(1, int(request.query.get('page', '1')))
        per_page = min(500, max(1, int(request.query.get('per_page', '50'))))
    except ValueError:
        return aiohttp_web.json_response({'error': 'page and per_page must be numbers'},
                                         status=400)

    query = _AuditQuery.from_request(request)
    # ?count=exact asks for the true match count, at the cost of a full scan. The
    # viewer requests it only when it wants to show a total.
    count_all = request.query.get('count') == 'exact'
    result = _audit_search(query, page, per_page, count_all=count_all)
    return aiohttp_web.json_response(result)


class _AuditQuery:
    """The filters a caller may apply. Empty fields match everything."""

    __slots__ = ('user', 'events', 'kinds', 'via', 'ip', 'date_from', 'date_to', 'text')

    def __init__(self, user=None, events=None, kinds=None, via=None, ip=None,
                 date_from=None, date_to=None, text=None):
        self.user = (user or '').strip().upper() or None
        self.events = set(e for e in (events or []) if e) or None
        self.kinds = set(k for k in (kinds or []) if k) or None
        self.via = (via or '').strip().lower() or None
        self.ip = (ip or '').strip() or None
        self.date_from = (date_from or '').strip() or None
        self.date_to = (date_to or '').strip() or None
        self.text = (text or '').strip().lower() or None

    @classmethod
    def from_request(cls, request):
        q = request.query
        # Repeatable: ?event=page_read&event=page_bought, or comma-separated.
        def multi(name):
            values = []
            for raw in q.getall(name, []):
                values.extend(v.strip() for v in raw.split(','))
            return values
        return cls(user=q.get('user'), events=multi('event'), kinds=multi('kind'),
                   via=q.get('via'), ip=q.get('ip'), date_from=q.get('from'),
                   date_to=q.get('to'), text=q.get('q'))

    def is_empty(self):
        return not any((self.user, self.events, self.kinds, self.via, self.ip,
                        self.date_from, self.date_to, self.text))

    def matches(self, entry):
        if self.user and (entry.get('user') or '').upper() != self.user:
            return False
        if self.events and entry.get('event') not in self.events:
            return False
        if self.kinds and entry.get('kind') not in self.kinds:
            return False
        if self.via and (entry.get('via') or '').lower() != self.via:
            return False
        if self.ip and entry.get('ip') != self.ip:
            return False
        # `time` is 'YYYY-MM-DD HH:MM:SS', so a plain string compare against a
        # date is correct and needs no parsing. `to` is inclusive of the whole day.
        stamp = entry.get('time', '')
        if self.date_from and stamp[:10] < self.date_from:
            return False
        if self.date_to and stamp[:10] > self.date_to:
            return False
        if self.text:
            # Across every field, so page titles, mail subjects and the `changed`
            # list of an admin edit are all searchable without naming them.
            haystack = ' '.join(str(v) for v in entry.values()).lower()
            if self.text not in haystack:
                return False
        return True


def _audit_iter_reversed(path, chunk_size=64 * 1024):
    """Yield lines newest-first without loading the file.

    ⚠ Reads BACKWARDS, deliberately. The previous implementation parsed the whole
    file into memory on every request, reversed it and sliced out one page — fine
    at 6,838 entries, and the same cost again once filtering was layered on top.
    Reading from the end means the common case (recent events, however filtered)
    costs a couple of chunks regardless of how large the log grows, so this does
    not need revisiting at 100k entries.
    """
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        remaining = f.tell()
        tail = b''
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            remaining -= read_size
            f.seek(remaining)
            block = f.read(read_size) + tail
            lines = block.split(b'\n')
            # The first element may be a partial line; carry it to the next block.
            tail = lines.pop(0)
            for line in reversed(lines):
                if line.strip():
                    yield line
        if tail.strip():
            yield tail


def _audit_search(query, page, per_page, count_all=False):
    """Page through the log newest-first, applying `query`.

    ⚠ STOPS AS SOON AS THE PAGE IS FILLED. That is the whole point of reading
    backwards: the cost of "recent events, filtered" stays flat as the log grows,
    instead of parsing every line to serve fifty.

    An exact match count is the one thing that cannot be cheap — knowing how many
    entries match means looking at all of them. So it is not claimed unless it was
    actually established: `matched_exact` is True only when the scan reached the
    start of the file. Otherwise `matched` is a floor and `has_more` says whether
    another page exists, which is what a pager actually needs. `count_all=True`
    asks for the full scan deliberately, for a caller that wants the real total.
    """
    want_end = page * per_page
    want_start = (page - 1) * per_page

    entries, matched, scanned = [], 0, 0
    matched_exact = True                 # unless we break out early

    for raw in _audit_iter_reversed(AUDIT_LOG_PATH):
        scanned += 1
        try:
            entry = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not query.matches(entry):
            continue
        matched += 1
        if want_start < matched <= want_end:
            entries.append(entry)
        elif matched > want_end and not count_all:
            # One past the page proves there is a next one; nothing beyond that
            # changes what we return, so stop reading.
            matched_exact = False
            break

    return {
        'entries': entries,
        'matched': matched,
        'matched_exact': matched_exact,
        'has_more': matched > want_end,
        'scanned': scanned,
        'page': page,
        'per_page': per_page,
        'events': sorted(AUDIT_EVENTS),
        'kinds': list(AUDIT_KINDS),
    }


async def api_post_audit(request):
    """POST /api/audit — record an audit event on behalf of the website.

    ⚠ The website cannot write this file, and should not be able to. It runs in
    its own container with `server/data` mounted READ-ONLY, because it is the
    internet-facing half of the deployment and has no business writing to the
    content, mail or config trees. So it asks the owner of the log to append,
    exactly as it already asks for the log to be READ (GET above).

    Until this existed the website wrote straight to a path of its own, which in
    Docker resolved inside its container and vanished on the next recreate. The
    result: `password_reset_request` and `password_reset` — user and IP, the two
    events you most want when investigating a stolen account — had never once
    been recorded. The GET docstring above claims the log covers password
    resets; it did not, and this is what makes that true.
    """
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except Exception:
        return aiohttp_web.json_response({'error': 'invalid json'}, status=400)
    event = str(body.get('event', '')).strip()
    if not event:
        return aiohttp_web.json_response({'error': 'event is required'}, status=400)
    # ⚠ The vocabulary is enforced at the boundary, not left to blow up inside
    # audit_log. An undeclared name would otherwise 500 here — and before the
    # registry existed it was worse: it was accepted, written, and then invisible
    # to every filter that knows the event set (#127).
    if event not in AUDIT_EVENTS:
        return aiohttp_web.json_response(
            {'error': 'unknown event %r — see AUDIT_EVENTS' % event,
             'known': sorted(AUDIT_EVENTS)}, status=400)
    user = body.get('user')
    # ⚠ Only the caller's own fields — never spread the whole body into the
    # entry, or a caller could overwrite `time` and forge when something
    # happened. `kind` is derived from the registry for the same reason.
    details = {k: v for k, v in (body.get('details') or {}).items()
               if k not in ('time', 'event', 'user', 'kind')}
    audit_log(event, user=user, **details)
    return aiohttp_web.json_response({'ok': True})


# ============================================================
# Directory header frames (#120)
#
# A directory's Part-1 header (§7.2) used to be operator-only, set by hand in a
# directory JSON. These endpoints let the website offer it to the user who OWNS
# the directory — the C64 ROM has no room for an upload command and §4.7's
# vocabulary is closed, so the website is the only place it can live.
#
# ⚠ The website cannot do any of this itself: its container mounts server/data
# READ-ONLY and does not mount server/cfg at all. Same reason POST /api/audit
# exists.
#
# ⚠ Authorization is decided HERE, not by the caller. The API key is
# all-or-nothing with no notion of which person is behind a request, so the
# website passes the signed-in user and the server re-checks that they really
# own the directory. Trusting the caller's word would make the key a
# write-anything-anywhere credential.
# ============================================================

def _api_directory_json_path(directory, page):
    """Where this page's own directory JSON lives.

    The root is the exception: its file is `root.json` at the top of the tree,
    not a `directory.json` in a sub-folder.
    """
    if page is directory.root:
        return os.path.join(ROOT_DIR, 'root.json')
    dir_path = getattr(page, '_dir_path', None)
    return os.path.join(dir_path, 'directory.json') if dir_path else None


def _api_is_directory(directory, page):
    """Does this page act as a directory, i.e. can it draw a header at all?

    Directories are latent (§7.3): a page becomes one when someone descends into
    it, so "has children" is not sufficient — an authored-but-empty directory is
    real and still renders a header.
    """
    if page is directory.root:
        return True
    json_path = _api_directory_json_path(directory, page)
    return bool(json_path) and (page.has_subdir() or os.path.exists(json_path))


def _api_may_configure(page, user_id, user_data):
    """Ownership rule, mirroring _can_upload_here.

    ⚠ `open_upload` grants the right to WRITE somewhere; it is not ownership and
    must never stand in for it here, or anyone able to upload into The Jungle
    could restyle it.
    """
    if user_data.get('admin', False) or user_data.get('editor', False):
        return True
    return page.author == user_id


def _api_breadcrumb(page):
    titles = []
    node = page
    while node is not None:
        titles.append(node.title)
        node = getattr(node, 'parent', None)
    return ' / '.join(reversed(titles))


def _api_header_paths(directory, page):
    """(file to write, value to store in the JSON).

    ⚠ The stored value is ALWAYS generated here and never taken from the
    request. It is joined to ROOT_DIR by five separate readers with no
    sanitisation, and Binding B hands the file's bytes to the browser — so a
    caller-supplied path would be an arbitrary-file-read primitive. Forward
    slashes because the tree is authored on Windows and served from Linux.
    """
    dir_path = getattr(page, '_dir_path', None)
    if not dir_path:
        return None, None
    path = os.path.join(dir_path, 'header.seq')
    return path, os.path.relpath(path, ROOT_DIR).replace(os.sep, '/')


def _api_load_dir_json(path):
    if path and os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _api_write_dir_json(path, data):
    """Edit the one file in place, atomically.

    Deliberately NOT save_directory_tree: that rewrites the whole tree from a
    freshly-loaded copy, and a header change has no business touching every
    other directory's JSON. This is the same principle `save_one_directory` now
    applies to every writer.
    """
    _write_json_atomic(path, data)


def _api_resolve_target(request, body_user):
    """Common lookup: (page, directory, user_id, user_data) or an error response."""
    try:
        page_num = int(request.match_info['page_num'])
    except (KeyError, ValueError):
        return None, aiohttp_web.json_response(
            {'error': 'bad page number'}, status=400)
    user_id = (body_user or '').upper()
    if not user_id:
        return None, aiohttp_web.json_response(
            {'error': 'no user supplied'}, status=400)
    users = _api_load_users()
    if user_id not in users:
        return None, aiohttp_web.json_response(
            {'error': 'unknown user'}, status=404)

    directory = CompunetDirectory()
    page = directory.pages.get(page_num)
    if page is None or not _api_is_directory(directory, page):
        return None, aiohttp_web.json_response(
            {'error': 'no such directory'}, status=404)
    if not _api_may_configure(page, user_id, users[user_id]):
        return None, aiohttp_web.json_response(
            {'error': 'you do not own that directory'}, status=403)
    return (page, directory, user_id), None


# ============================================================
# The directory hierarchy (#121)
#
# A browsable, editable view of the tree for the website. Every signed-in user
# may BROWSE all of it; editing is per-node and decided here.
# ============================================================

def _api_may_edit(page, user_id, user_data):
    """May this user change this entry — move, rename, reorder or delete it?

    Three ways to qualify, and they are deliberately the same three the rest of
    the server already uses (_can_upload_here, the replace check, the negative
    EXTEND check):

      1. admin or editor — anywhere;
      2. the entry's author;
      3. the owner of the directory the entry sits IN. Owning a directory carries
         authority over its contents, whoever wrote them. Without this a user
         cannot tidy their own space once someone else has uploaded into it — and
         since they may delete the whole directory, protecting the individual
         entries inside it would only be decorative.
    """
    if user_data.get('admin', False) or user_data.get('editor', False):
        return True
    if page.author == user_id:
        return True
    parent = getattr(page, 'parent', None)
    return parent is not None and parent.author == user_id


def _api_duplicate_page_nums(directory):
    """Page numbers found on more than one entry.

    Recorded by the loader (`CompunetDirectory._register_page`) rather than
    recounted here: one detector, so the API and the tree cannot come to different
    conclusions about which numbers are safe to act on. Reading `directory.pages`
    instead would find nothing at all — a refused duplicate never reaches it.

    Normally empty. Anything in it is a content defect that makes those entries
    unaddressable, so the API marks them uneditable rather than guessing which
    one a request meant.
    """
    return set(getattr(directory, 'duplicate_page_nums', ()) or ())


def _api_is_editable(directory, page, duplicates=frozenset()):
    """Can this entry be RESTRUCTURED at all — moved, renamed, reordered, deleted?

    ⚠ Structure only. A directory's SETTINGS — its header frame, its owner-only
    flag — are a separate question, answered by `_api_may_configure_dir`. The root
    is the case that forces the distinction: it cannot be moved, renamed or
    deleted, but it does carry a header in root.json and always has.

    Conflating the two hid the root's HEADER control in the tree while
    /directories/settings went on offering it — the tree and the settings page
    disagreeing about the same directory.

    Reported per node rather than filtered out: an admin who knows a page exists
    would otherwise think the tree view had lost it.
    """
    if page is directory.root:
        # No parent, so nowhere to move it and no sibling list to reorder within;
        # and its title is not stored anywhere — "WELCOME" is hardcoded in the
        # loader, root.json holds only `header` and `pages` — so a rename would
        # have nothing to write to.
        return False, 'the top of the tree: it cannot be moved, renamed or deleted'
    if getattr(page, 'dynamic', None):
        # WHAT'S NEW, WHO IS ONLINE and friends are generated on read. There is
        # no folder to move and no file to archive.
        return False, 'generated automatically'
    if page.page_type == 'L':
        return False, 'a link, not content'
    if page.page_num in duplicates:
        return False, ('page number %d is used by more than one entry, so it '
                       'cannot be identified unambiguously' % page.page_num)
    return True, None


def _api_may_configure_dir(directory, page, user_id, user_data):
    """May this user change this DIRECTORY's settings — header, owner-only?

    Deliberately not gated on `_api_is_editable`: that answers whether an entry can
    be restructured, and the root cannot be while still owning a header. Uses the
    same ownership rule as everything else.
    """
    if not _api_is_directory(directory, page):
        return False
    return _api_may_edit(page, user_id, user_data)


def _api_tree_node(directory, page, user_id, user_data, duplicates=frozenset()):
    is_dir = _api_is_directory(directory, page)
    editable, why_not = _api_is_editable(directory, page, duplicates)
    may_edit = editable and _api_may_edit(page, user_id, user_data)
    data = _api_load_dir_json(_api_directory_json_path(directory, page)) if is_dir else {}
    node = {
        'page_num': page.page_num,
        'title': page.title,
        'type': page.page_type,
        'author': page.author,
        'price': page.price,
        'life': page.life,
        'keyword': page.keyword,
        'uploaded': getattr(page, 'uploaded', None),
        'machine_type': getattr(page, 'machine_type', 'c64'),
        'frame_count': len(page.frames) if page.frames else 0,
        'is_directory': is_dir,
        'editable': editable,
        'not_editable_because': why_not,
        'may_edit': may_edit,
        # Separate from may_edit: a directory's settings, not its place in the tree.
        'may_configure': _api_may_configure_dir(directory, page, user_id, user_data),
        # Only a text page has anything to draw; a program offers a download.
        'viewable': page.page_type == 'T' and bool(page.frames),
    }
    if is_dir:
        node['child_count'] = len(page.children)
        # A directory holds at most 11 entries, so a destination picker has to
        # know which ones cannot accept anything more.
        node['full'] = len(page.children) >= 11
        node['has_header'] = bool(data.get('header'))
        node['owner_only'] = data.get('open_upload') is False
        # May the user put something INTO this directory? Mirrors
        # _can_upload_here, including the inherited open_upload walk.
        node['may_add'] = _api_may_add_here(page, user_id, user_data)
        children = [
            _api_tree_node(directory, child, user_id, user_data, duplicates)
            for child in page.children]
        # Where each entry sits in the listing, and how many it shares it with —
        # a reorder control cannot be drawn without both, and the server is the
        # only side that knows the order is the JSON order.
        for position, child in enumerate(children):
            child['position'] = position
            child['sibling_count'] = len(children)
        node['children'] = children
    return node


def _api_may_add_here(page, user_id, user_data):
    """_can_upload_here, for a page the caller is not 'in'.

    ⚠ Kept in step with CompunetSession._can_upload_here deliberately: same
    order, same inheritance rule, same meaning of an explicit `false`. This one
    takes the page as an argument because the website is not sitting in a
    directory the way a client session is.
    """
    if user_data.get('admin', False) or user_data.get('editor', False):
        return True
    if page.author == user_id:
        return True
    node = page
    while node is not None:
        if hasattr(node, 'open_upload'):      # present => authoritative
            return bool(node.open_upload)
        node = getattr(node, 'parent', None)
    return False


async def api_get_tree(request):
    """The whole hierarchy, with per-node permissions worked out here.

    ⚠ The website must not compute these itself. The API key identifies the
    website rather than a person, so every authorisation decision belongs on this
    side — the same rule the header endpoints follow.
    """
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    user_id = request.query.get('user', '').upper()
    if not user_id:
        return aiohttp_web.json_response({'error': 'no user supplied'}, status=400)
    users = _api_load_users()
    if user_id not in users:
        return aiohttp_web.json_response({'error': 'unknown user'}, status=404)

    directory = CompunetDirectory()
    duplicates = _api_duplicate_page_nums(directory)
    if duplicates:
        # Surfaced rather than merely logged: it is a content defect an operator
        # has to fix by renumbering, and until then those entries cannot be
        # edited safely.
        log.warning('TREE: duplicate page numbers in the content tree: %s',
                    sorted(duplicates))
    root = _api_tree_node(directory, directory.root, user_id, users[user_id],
                          duplicates)
    return aiohttp_web.json_response(
        {'tree': root, 'duplicate_page_numbers': sorted(duplicates)})


async def api_page_frame_png(request):
    """One frame of a text page, rendered as a PNG.

    Browsing is open to every signed-in user, so this needs no ownership check —
    the same frame is readable by anyone through any client. It exists so the
    hierarchy view can show what a page holds without leaving the page.
    """
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        page_num = int(request.match_info['page_num'])
        index = int(request.match_info.get('index', 0))
    except (KeyError, ValueError):
        return aiohttp_web.json_response({'error': 'bad page or index'}, status=400)

    user_id = request.query.get('user', '').upper()
    users = _api_load_users()
    if not user_id or user_id not in users:
        return aiohttp_web.json_response({'error': 'unknown user'}, status=404)

    assets = header_preview.load_assets(SERVER_DIR, WEB_CLIENT_DIR)
    if not assets:
        log.warning('FRAME: assets.json not found — no rendering available')
        return aiohttp_web.json_response({'error': 'preview unavailable'}, status=503)

    # See api_directory_header_png: api_binding is a deliberately lazy import.
    try:
        import api_binding
    except ImportError:
        return aiohttp_web.json_response({'error': 'preview unavailable'}, status=503)

    directory = CompunetDirectory()
    page = directory.pages.get(page_num)
    if page is None or not page.frames:
        return aiohttp_web.json_response({'error': 'no such frame'}, status=404)
    if index < 0 or index >= len(page.frames):
        return aiohttp_web.json_response({'error': 'no such frame'}, status=404)
    if page.page_type != 'T':
        return aiohttp_web.json_response(
            {'error': 'only text pages can be rendered'}, status=409)

    session = CompunetSession(directory)
    session.user_id = user_id
    raw = api_binding.page_frame_bytes(session, page, index)
    frame = api_binding.frame_to_cells(raw)
    # The whole 24-row screen this time, not the header's six.
    png = header_preview.cells_to_png(frame['cells'], assets, rows=24)
    return aiohttp_web.Response(
        body=png, content_type='image/png',
        headers={'Cache-Control': 'no-cache, must-revalidate'})


def _api_resolve_editable(request, body):
    """Find the page an edit names, and check the caller may change it.

    Refuses a duplicated number rather than guessing: with two entries sharing it,
    acting on "whichever loaded second" means the user asks to change one page and
    a different one changes.
    """
    try:
        page_num = int(request.match_info['page_num'])
    except (KeyError, ValueError):
        return None, aiohttp_web.json_response(
            {'error': 'bad page number'}, status=400)
    user_id = str(body.get('user') or '').upper()
    if not user_id:
        return None, aiohttp_web.json_response(
            {'error': 'no user supplied'}, status=400)
    users = _api_load_users()
    if user_id not in users:
        return None, aiohttp_web.json_response(
            {'error': 'unknown user'}, status=404)

    directory = CompunetDirectory()
    page = directory.pages.get(page_num)
    if page is None:
        return None, aiohttp_web.json_response(
            {'error': 'no such page'}, status=404)
    editable, why_not = _api_is_editable(
        directory, page, _api_duplicate_page_nums(directory))
    if not editable:
        return None, aiohttp_web.json_response(
            {'error': 'that entry cannot be changed: %s' % why_not}, status=409)
    if not _api_may_edit(page, user_id, users[user_id]):
        return None, aiohttp_web.json_response(
            {'error': 'you may not change that entry'}, status=403)
    return (directory, page, user_id, users[user_id]), None


async def api_rename_page(request):
    """Change an entry's title — which also renames its folder."""
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    resolved, err = _api_resolve_editable(request, body)
    if err:
        return err
    directory, page, user_id, _user_data = resolved

    was = page.title
    try:
        affected = relocate_page(directory, page, ROOT_DIR,
                                 new_title=str(body.get('title', '')))
    except RelocateError as exc:
        return aiohttp_web.json_response({'error': str(exc)}, status=409)
    except OSError as exc:
        log.error('RENAME: %s', exc)
        return aiohttp_web.json_response(
            {'error': 'could not rename the files on disk'}, status=500)

    for node in affected:
        save_one_directory(node, ROOT_DIR)
    audit_log('page_renamed', user=user_id, page=page.page_num,
              title=page.title, was=was)
    log.info('RENAME: %s renamed page %d "%s" -> "%s"',
             user_id, page.page_num, was, page.title)
    return aiohttp_web.json_response({'ok': True, 'title': page.title, 'was': was})


async def api_move_page(request):
    """Move an entry into another directory."""
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    resolved, err = _api_resolve_editable(request, body)
    if err:
        return err
    directory, page, user_id, user_data = resolved

    try:
        dest_num = int(body.get('dest_page_num'))
    except (TypeError, ValueError):
        return aiohttp_web.json_response({'error': 'bad destination'}, status=400)
    dest = directory.pages.get(dest_num)
    if dest is None or not _api_is_directory(directory, dest):
        return aiohttp_web.json_response(
            {'error': 'no such directory to move into'}, status=404)

    # ⚠ TWO permissions, not one. Being allowed to change the entry says nothing
    # about being allowed to put things into the destination — otherwise anyone
    # could file their own pages into someone else's private directory.
    if not _api_may_add_here(dest, user_id, user_data):
        return aiohttp_web.json_response(
            {'error': 'you may not add to "%s"' % dest.title}, status=403)

    was = page.parent.title if page.parent else '?'
    try:
        affected = relocate_page(directory, page, ROOT_DIR, new_parent=dest)
    except RelocateError as exc:
        return aiohttp_web.json_response({'error': str(exc)}, status=409)
    except OSError as exc:
        log.error('MOVE: %s', exc)
        return aiohttp_web.json_response(
            {'error': 'could not move the files on disk'}, status=500)

    for node in affected:
        save_one_directory(node, ROOT_DIR)
    audit_log('page_moved', user=user_id, page=page.page_num, title=page.title,
              was=was, now=dest.title)
    log.info('MOVE: %s moved page %d "%s" from "%s" to "%s"',
             user_id, page.page_num, page.title, was, dest.title)
    return aiohttp_web.json_response(
        {'ok': True, 'title': page.title, 'was': was, 'now': dest.title})


async def api_delete_page(request):
    """Delete an entry — archived first, storage refunded, then removed.

    Deliberately the same shape as reducing an entry's life to zero, which is how
    the C64 has always removed content: the same act through two interfaces should
    leave the same trace.
    """
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        body = {}

    resolved, err = _api_resolve_editable(request, body)
    if err:
        return err
    directory, page, user_id, _user_data = resolved

    doomed = _subtree(page)
    try:
        archived, refunds = delete_page(directory, page, DATA_DIR, ROOT_DIR)
    except RelocateError as exc:
        return aiohttp_web.json_response({'error': str(exc)}, status=409)
    except OSError as exc:
        log.error('DELETE: %s', exc)
        return aiohttp_web.json_response(
            {'error': 'could not remove the files on disk'}, status=500)

    # ⚠ Refunded to each page's OWN author, not to whoever pressed the button. An
    # admin clearing someone's directory must not charge or credit themselves,
    # and the authors are the ones whose quota the content was consuming.
    if refunds:
        async with _lock_users:
            users = _api_load_users()
            for author, units in refunds.items():
                if author in users:
                    used = users[author].get('free_storage_used', 0)
                    users[author]['free_storage_used'] = max(0, used - units)
            _api_save_users(users)

    save_one_directory(page.parent, ROOT_DIR)
    audit_log('page_deleted', user=user_id, page=page.page_num, title=page.title,
              entries=len(doomed), refunds=refunds)
    log.info('DELETE: %s deleted page %d "%s" (%d entries archived)',
             user_id, page.page_num, page.title, len(doomed))
    return aiohttp_web.json_response(
        {'ok': True, 'title': page.title, 'entries': len(doomed),
         'archived': len(archived), 'refunds': refunds})


async def api_reorder_page(request):
    """Move an entry up or down the listing its directory shows."""
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    resolved, err = _api_resolve_editable(request, body)
    if err:
        return err
    directory, page, user_id, _user_data = resolved

    parent = page.parent
    if parent is None:
        return aiohttp_web.json_response(
            {'error': 'the root cannot be reordered'}, status=409)
    try:
        index = int(body.get('index'))
    except (TypeError, ValueError):
        return aiohttp_web.json_response({'error': 'bad position'}, status=400)

    try:
        reorder_child(parent, page, index)
    except RelocateError as exc:
        return aiohttp_web.json_response({'error': str(exc)}, status=409)

    save_one_directory(parent, ROOT_DIR)
    audit_log('page_reordered', user=user_id, page=page.page_num,
              title=page.title, index=index)
    return aiohttp_web.json_response({'ok': True, 'index': index})


async def api_list_directories(request):
    """Directories this user may put a header on."""
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    user_id = request.query.get('user', '').upper()
    if not user_id:
        return aiohttp_web.json_response({'error': 'no user supplied'}, status=400)
    users = _api_load_users()
    if user_id not in users:
        return aiohttp_web.json_response({'error': 'unknown user'}, status=404)
    user_data = users[user_id]

    directory = CompunetDirectory()
    out = []
    for page_num, page in sorted(directory.pages.items()):
        if not _api_is_directory(directory, page):
            continue
        if not _api_may_configure(page, user_id, user_data):
            continue
        data = _api_load_dir_json(_api_directory_json_path(directory, page))
        out.append({
            'page_num': page_num,
            'title': page.title,
            'breadcrumb': _api_breadcrumb(page),
            'author': page.author,
            # Only a header set on THIS directory counts as removable; an
            # inherited one belongs to an ancestor the user may not own.
            'has_header': bool(data.get('header')),
            'owner_only': data.get('open_upload') is False,
        })
    return aiohttp_web.json_response({'directories': out})


async def api_set_directory_header(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    resolved, err = _api_resolve_target(request, body.get('user'))
    if err:
        return err
    page, directory, user_id = resolved

    try:
        raw = base64.b64decode(body.get('data', ''), validate=True)
    except Exception:
        return aiohttp_web.json_response({'error': 'invalid base64'}, status=400)

    # Accept what the client's editor actually saves — a page frame — rather than
    # demanding a hand-stripped header body (#126). Anything adjusted is reported
    # back in `notes`, so this is not silent sanitising: the author is told.
    raw, notes = header_frame.normalise_header_frame(raw)

    reasons = header_frame.validate_header_frame(raw)
    if reasons:
        # Still rejecting what would corrupt the screen, rather than guessing at
        # a repair: the author gets to know what is wrong with their artwork
        # instead of quietly receiving something else back.
        return aiohttp_web.json_response(
            {'error': 'invalid header frame', 'reasons': reasons}, status=400)

    path, stored = _api_header_paths(directory, page)
    if not path:
        return aiohttp_web.json_response(
            {'error': 'directory has no folder on disk'}, status=409)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(raw)
    json_path = _api_directory_json_path(directory, page)
    data = _api_load_dir_json(json_path)
    data['header'] = stored
    _api_write_dir_json(json_path, data)

    audit_log('header_set', user=user_id, page=page.page_num,
              title=page.title, bytes=len(raw))
    log.info('HEADER: %s set header on page %d "%s" (%d bytes)',
             user_id, page.page_num, page.title, len(raw))
    return aiohttp_web.json_response(
        {'ok': True, 'header': stored,
         'notes': notes,
         'describe': header_frame.describe_header_frame(raw)})


async def api_delete_directory_header(request):
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        body = {}

    resolved, err = _api_resolve_target(
        request, body.get('user') or request.query.get('user'))
    if err:
        return err
    page, directory, user_id = resolved

    json_path = _api_directory_json_path(directory, page)
    data = _api_load_dir_json(json_path)
    if 'header' in data:
        del data['header']
        _api_write_dir_json(json_path, data)
    path, _ = _api_header_paths(directory, page)
    if path and os.path.exists(path):
        os.remove(path)

    audit_log('header_removed', user=user_id, page=page.page_num,
              title=page.title)
    return aiohttp_web.json_response({'ok': True})


async def api_directory_header_png(request):
    """A rendition of the header currently on this directory, as a PNG.

    Rendered from the same palette and font the real clients use (§A.3, §A.5 via
    assets.json) so the preview cannot disagree with them about what the header
    looks like. Only the directory's OWN header — an inherited one belongs to an
    ancestor the user may not own, and offering to preview it here would imply
    they can change it.
    """
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)

    resolved, err = _api_resolve_target(request, request.query.get('user'))
    if err:
        return err
    page, directory, _user_id = resolved

    json_path = _api_directory_json_path(directory, page)
    header_file = _api_load_dir_json(json_path).get('header')
    if not header_file:
        return aiohttp_web.json_response({'error': 'no header'}, status=404)

    assets = header_preview.load_assets(SERVER_DIR, WEB_CLIENT_DIR)
    if not assets:
        # The font ships in assets.json; without it there is nothing to draw
        # with, and guessing a substitute font would misrepresent the header.
        log.warning('HEADER: assets.json not found — no preview available')
        return aiohttp_web.json_response(
            {'error': 'preview unavailable'}, status=503)

    # ⚠ Imported here, not at module scope. api_binding is deliberately a lazy
    # import (see main()): importing it eagerly once took the whole framed
    # protocol down with it when a dependency was missing, putting every vintage
    # client offline. A preview is the last thing that should be able to do that.
    try:
        import api_binding
    except ImportError:
        return aiohttp_web.json_response(
            {'error': 'preview unavailable'}, status=503)

    frame = api_binding.render_header_file(header_file)
    if not frame:
        return aiohttp_web.json_response({'error': 'no header'}, status=404)

    png = header_preview.cells_to_png(frame['cells'], assets)
    return aiohttp_web.Response(
        body=png, content_type='image/png',
        # The file can be replaced at any moment by an upload, and it is small.
        headers={'Cache-Control': 'no-cache, must-revalidate'})


async def api_set_directory_settings(request):
    """`owner_only` — whether others may upload here, and so whether they can
    create directories beneath it (a sub-directory is created by descending
    into an uploaded page, which _can_upload_here gates).
    """
    if not _api_check_auth(request):
        return aiohttp_web.json_response({'error': 'unauthorized'}, status=401)
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return aiohttp_web.json_response({'error': 'invalid JSON'}, status=400)

    resolved, err = _api_resolve_target(request, body.get('user'))
    if err:
        return err
    page, directory, user_id = resolved

    json_path = _api_directory_json_path(directory, page)
    data = _api_load_dir_json(json_path)
    if body.get('owner_only'):
        # An explicit `false` STOPS the inherited flag for this directory and
        # everything beneath it. Absent would merely defer to the ancestor,
        # which in an open area means "open" — the opposite of what was asked.
        data['open_upload'] = False
    else:
        data.pop('open_upload', None)
    _api_write_dir_json(json_path, data)

    audit_log('directory_settings_changed', user=user_id, page=page.page_num,
              owner_only=bool(body.get('owner_only')))
    return aiohttp_web.json_response(
        {'ok': True, 'owner_only': data.get('open_upload') is False})


# ============================================================
# Main
# ============================================================

async def main():
    tcp_server = await asyncio.start_server(tcp_handler, '0.0.0.0', TCP_PORT)
    log.info('TCP server on port %d', TCP_PORT)

    term_server = await asyncio.start_server(terminal.terminal_handler, '0.0.0.0', TERM_PORT)
    log.info('PETSCII terminal on port %d', TERM_PORT)

    if aiohttp_web:
        app = aiohttp_web.Application()
        app.router.add_get('/api/health', api_health)
        app.router.add_post('/api/auth', api_auth)
        app.router.add_get('/api/users', api_list_users)
        app.router.add_get('/api/users/{user_id}', api_get_user)
        app.router.add_post('/api/users', api_create_user)
        app.router.add_put('/api/users/{user_id}', api_update_user)
        app.router.add_delete('/api/users/{user_id}', api_delete_user)
        app.router.add_get('/api/pending', api_list_pending)
        app.router.add_post('/api/pending', api_create_pending)
        app.router.add_get('/api/pending/{token}', api_get_pending)
        app.router.add_delete('/api/pending/{token}', api_consume_pending)
        app.router.add_post('/api/broadcast', api_broadcast)
        app.router.add_get('/api/audit', api_get_audit)
        app.router.add_post('/api/audit', api_post_audit)
        app.router.add_get('/api/tree', api_get_tree)
        app.router.add_post('/api/pages/{page_num}/rename', api_rename_page)
        app.router.add_post('/api/pages/{page_num}/move', api_move_page)
        app.router.add_delete('/api/pages/{page_num}', api_delete_page)
        app.router.add_post('/api/pages/{page_num}/reorder', api_reorder_page)
        app.router.add_get('/api/pages/{page_num}/frame/{index}.png',
                           api_page_frame_png)
        app.router.add_get('/api/directories', api_list_directories)
        app.router.add_post('/api/directories/{page_num}/header',
                            api_set_directory_header)
        app.router.add_delete('/api/directories/{page_num}/header',
                              api_delete_directory_header)
        app.router.add_get('/api/directories/{page_num}/header.png',
                           api_directory_header_png)
        app.router.add_put('/api/directories/{page_num}/settings',
                           api_set_directory_settings)
        app.router.add_get('/ws/partyline', api_ws_partyline)
        runner = aiohttp_web.AppRunner(app)
        await runner.setup()
        site = aiohttp_web.TCPSite(runner, '0.0.0.0', API_PORT)
        await site.start()
        log.info('REST API on port %d', API_PORT)

        # Binding B — modern JSON client API, its own isolated app + port (6404).
        #
        # ⚠ A failure here MUST NOT take the server down. Binding B is a second
        # binding over the same core (§1.8), not a dependency of the first: the
        # C64 and Amiga clients on 6400 do not touch a line of it. An unguarded
        # import meant a deployment that shipped compunet_server.py without
        # api_binding.py died at startup and took the framed protocol with it —
        # every vintage client offline because a JSON module was absent. The
        # REST API above already degrades this way when aiohttp is missing;
        # this now matches it.
        try:
            import sys as _sys
            import api_binding
            # ⚠ Serve the web client from the SAME origin as the API when it is
            # present. That is what lets a tunnel publish ONE hostname
            # (connect.compunet.live -> compunet-server:6404): the client needs
            # no address typed, there is no CORS, and mixed content cannot
            # arise. Absent the directory the API runs alone, exactly as before.
            client_api = api_binding.make_app(_sys.modules[__name__],
                                              web_client_dir=WEB_CLIENT_DIR)
            client_runner = aiohttp_web.AppRunner(client_api)
            await client_runner.setup()
            client_site = aiohttp_web.TCPSite(client_runner, '0.0.0.0', CLIENT_API_PORT)
            await client_site.start()
            log.info('Client API (Binding B) on port %d', CLIENT_API_PORT)
        except Exception:
            log.exception('Client API (Binding B) failed to start on port %d — '
                          'continuing without it; the framed protocol is unaffected',
                          CLIENT_API_PORT)
    else:
        log.warning('aiohttp not installed — REST API disabled')

    for _vp in [os.path.join(SERVER_DIR, 'VERSION'), os.path.join(SERVER_DIR, '..', 'VERSION')]:
        if os.path.exists(_vp):
            _version = open(_vp).read().strip()
            break
    else:
        _version = 'unknown'
    log.info('Compunet server v%s ready.', _version)

    async with tcp_server, term_server:
        await asyncio.gather(
            tcp_server.serve_forever(),
            term_server.serve_forever(),
        )


if __name__ == '__main__':
    asyncio.run(main())
