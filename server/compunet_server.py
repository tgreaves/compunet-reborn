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
  WebSocket (port 6502): binary frames containing raw protocol bytes
  TCP (port 6400): raw protocol bytes over stream
"""

import asyncio
import hashlib
import json
import os
import re
import glob
import logging
import secrets
from pathlib import Path
import partyline

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    raise

try:
    from aiohttp import web as aiohttp_web
except ImportError:
    aiohttp_web = None

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('compunet')

# Load .env file if present (allows restart without rebuild)
_env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_file):
    with open(_env_file, 'r') as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _key, _val = _line.split('=', 1)
            os.environ.setdefault(_key.strip(), _val.strip())

# Server configuration
WS_PORT = 6502
TCP_PORT = 6400
API_PORT = 6403
SERVER_DIR = os.path.dirname(__file__)
CFG_DIR = os.path.join(SERVER_DIR, 'cfg')
DATA_DIR = os.path.join(SERVER_DIR, 'data')
CONTENT_DIR = os.path.join(DATA_DIR, 'content')
ROOT_DIR = os.path.join(CONTENT_DIR, 'root')
MAIL_DIR = os.path.join(DATA_DIR, 'mail')
VOTES_PATH = os.path.join(DATA_DIR, 'votes.json')

# Protocol constants
RESP_ACK = 0x41       # 'A' - acknowledge/proceed
RESP_LINKING = 0x4C   # 'L' - linking required
RESP_DIR = 0x44       # 'D' - directory data
RESP_FRAME = 0x46     # 'F' - frame data
RESP_ERROR = 0x45     # 'E' - error

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
_online_users = set()

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
        self.children = []
        self.frames = []    # list of bytes objects (raw frame data)
        self.parent = None
    
    def has_subdir(self):
        return len(self.children) > 0
    
    def type_string(self):
        """Generate the type suffix shown in directory listings."""
        s = self.page_type
        if self.page_type != 'L' and self.size > 0:
            s += str(self.size)
        if self.has_subdir():
            s += '+'
        return s


class CompunetDirectory:
    """The content tree, loaded fresh from per-directory JSON files on each access."""

    def __init__(self):
        self.pages = {}
        self.root = None
        self.global_adverts = []
        self.reload()

    def reload(self):
        """Reload the entire tree from disk."""
        self.pages = {}
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

    def _build_flat_page(self, node, parent, base_dir):
        """Build a page from flat JSON node, resolving paths from its folder."""
        page_slug = node['title'].lower().replace(' ', '-')
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
        self.pages[page.page_num] = page

        # Load frames from page folder
        page._frame_files = node.get('frames', [])
        for frame_file in page._frame_files:
            frame_path = os.path.join(page_dir, frame_file)
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    page.frames.append(f.read())

        # For program pages, calculate size in KB from file data
        if page.page_type == 'P' and page.frames:
            page.size = (len(page.frames[0]) - 2 + 1023) // 1024

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


class CompunetSession:
    """A client session - same logic for WebSocket and TCP clients."""
    
    def __init__(self, directory):
        self.directory = directory
        self.user_id = None
        self.authenticated = False
        self.is_admin = False
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
        log.info('Login OK: %s (credit=%.2f, purchased=%s)', user_id, self.credit, self.purchased)
        return self._make_welcome_frame(user)
    
    def handle_command(self, data):
        """
        Process a command packet from the client.
        data[0] = command byte
        data[1:] = parameters
        Returns response bytes to send back.
        """
        self.last_response_type = None  # Reset per-command for WS prefix detection
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
        """Check if current user can upload/create DIRs in the current page."""
        if self.is_admin:
            return True
        author = self.current_page.author
        return author == 'JUNGLE' or author == self.user_id

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
        if not params:
            return self._make_error(ascii_to_petscii('NO DESTINATION'))

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

        return self._make_error(ascii_to_petscii('PAGE NOT FOUND'))

    def _goto_page(self, page_num):
        """Navigate to a page by number."""
        page = self.directory.pages.get(page_num)
        if page is None:
            return self._make_error(ascii_to_petscii('PAGE NOT FOUND'))

        self.current_page = page
        self.selected_entry = 0
        self.dir_page_offset = 0
        if page.has_subdir():
            return self._make_dir_response()
        elif page.frames:
            if page.parent:
                self.current_page = page.parent
            self.show_page = page
            self.show_frame_index = 0
            return self._send_current_frame()
        else:
            return self._make_error(ascii_to_petscii('NO CONTENT'))

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
                # Type L: send MODEM_INIT_DOWNLOAD format for the linked program
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
            if child.frames:
                # Deduct credit for paid, unpurchased pages (allows overdraft)
                if child.price > 0 and child.page_num not in self.purchased:
                    self.credit -= child.price
                    self.purchased.add(child.page_num)
                    self._save_user()
                    log.info('BUY: user=%s page=%d ("%s") price=%.2f credit=%.2f',
                             self.user_id, child.page_num, child.title,
                             child.price, self.credit)
                self.show_page = child
                self.show_frame_index = 0
                return self._send_current_frame()
            elif child.has_subdir():
                self.current_page = child
                self.selected_entry = 0
                self.dir_page_offset = 0
                return self._make_dir_response()
            else:
                return self._make_error(ascii_to_petscii('NO CONTENT'))
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
                    self.current_page = child
                    self.selected_entry = 0
                    self.dir_page_offset = 0
                    self.dir_displayed = False
                    return self._make_dir_response()
        else:
            log.info('P cmd: dir_displayed=%s params=%s (not entering subdir)',
                     self.dir_displayed, params.hex() if params else 'none')
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
            # Program download: send header, wait for proceed token
            if self.show_page.page_type == 'P':
                prg_data = self.show_page.frames[self.show_frame_index]
                load_lo = prg_data[0]
                load_hi = prg_data[1]
                program_bytes = prg_data[2:]
                size = len(program_bytes)
                size_lo = size & 0xFF
                size_hi = (size >> 8) & 0xFF
                header = bytes([0x00, 0x00, 0x00, 0x00, load_lo, load_hi, size_lo, size_hi])
                self._program_download_pending = True
                self._program_download_data = program_bytes
                log.info('PROGRAM: page=%d "%s" load=$%02X%02X size=%d bytes (%dK), header sent',
                         self.show_page.page_num, self.show_page.title,
                         load_hi, load_lo, size, (size + 1023) // 1024)
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
        """
        self.last_response_type = RESP_ACK
        if len(params) < 2:
            return bytes([0x00])

        try:
            entry_idx = int(params[0:2].decode('ascii'))
            extend_by = int(params[2:].decode('ascii').strip()) if len(params) > 2 else 0
        except (ValueError, UnicodeDecodeError):
            return bytes([0x00])

        # Find the page from current directory
        offset = getattr(self, 'dir_page_offset', 0)
        visible_children = self.current_page.children[offset:offset+11]
        if entry_idx >= len(visible_children):
            return bytes([0x00])

        child = visible_children[entry_idx]

        # Type 'L' — link: handled by _cmd_dir, BUY just returns ACK
        if child.page_type == 'L':
            return bytes([0x00])

        # Check ownership (admins can modify any content)
        if child.author != self.user_id and not self.is_admin:
            log.info('EXTEND DENIED: user=%s is not author of page %d (author=%s)',
                     self.user_id, child.page_num, child.author)
            return bytes([0x00])

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
            self._save_directory()
            log.info('EXTEND: user=%s page=%d ("%s") extend_by=%d new_life=%d',
                     self.user_id, child.page_num, child.title, extend_by, child.life)

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

            # If life reaches 0, delete the page
            if child.life <= 0:
                parent = self.current_page
                if child in parent.children:
                    parent.children.remove(child)
                if child.page_num in self.directory.pages:
                    del self.directory.pages[child.page_num]
                log.info('DELETE: page %d ("%s") removed (life=0)', child.page_num, child.title)

            self._save_user()
            self._save_directory()

        self.dir_displayed = False
        return bytes([0x00])

    def _get_quarter_start(self):
        """Return the start date of the current calendar quarter."""
        import datetime
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
        import datetime
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
        """VOTE command. Params: 2-digit entry index + 1-digit score (1-9)."""
        if len(params) < 3:
            log.warning('VOTE: params too short: %s', params.hex())
            self.last_response_type = RESP_ACK
            return bytes([RESP_ACK])

        try:
            index = int(params[:2].decode('ascii'))
            score = int(params[2:3].decode('ascii'))
        except (ValueError, UnicodeDecodeError):
            log.warning('VOTE: invalid params: %s', params.hex())
            self.last_response_type = RESP_ACK
            return bytes([RESP_ACK])

        offset = getattr(self, 'dir_page_offset', 0)
        visible_children = self.current_page.children[offset:offset+11]

        if index >= len(visible_children) or score < 1 or score > 9:
            log.warning('VOTE: out of range index=%d score=%d', index, score)
            self.last_response_type = RESP_ACK
            return bytes([RESP_ACK])

        page = visible_children[index]
        page_key = str(page.page_num)

        votes = self._load_votes()
        if page_key not in votes:
            votes[page_key] = {}
        votes[page_key][self.user_id] = score
        self._save_votes(votes)

        avg = round(sum(votes[page_key].values()) / len(votes[page_key]))
        page.vote = avg
        self._save_directory()

        log.info('VOTE: user=%s page=%d (%s) score=%d avg=%d',
                 self.user_id, page.page_num, page.title, score, avg)

        self.last_response_type = RESP_ACK
        return bytes([RESP_ACK])

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
        """Load mail metadata for the current user."""
        mail_file = os.path.join(MAIL_DIR, self.user_id + '.json')
        if os.path.exists(mail_file):
            with open(mail_file, 'r') as f:
                data = json.load(f)
            return data.get('messages', [])
        return []

    def _make_mail_response(self):
        """Build mailbox listing as 6-part directory response."""
        self.mail_mode = True
        self.last_response_type = RESP_DIR
        self.dir_displayed = True
        data = bytearray()

        # Part 1: no frame header
        data.append(0x00)

        # Part 2: footer (empty)
        data.append(0x0D)
        data.append(0x0D)

        # Part 3: field definitions (stored at $D580+)
        # Format: [field_id_nibble] '=' [value] $0D ... $00
        # Field 3 ($D588) = DATE, Field 4 ($D5A8) = TIME
        import datetime
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
        import datetime
        now = datetime.datetime.now()
        users = self._load_users()
        real_name = users.get(self.user_id, {}).get('name', self.user_id)
        data.extend(ascii_to_petscii(' USER ID : ' + self.user_id))
        data.append(0x0D)
        data.extend(ascii_to_petscii(real_name))
        data.append(0x0D)
        data.append(0x0D)
        data.extend(ascii_to_petscii(now.strftime('%d-%m-%y')))
        data.append(0x0D)
        data.extend(ascii_to_petscii(now.strftime('%H:%M')))
        data.append(0x00)

        # Part 5: column headers
        data.extend(ascii_to_petscii('SENDER'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('DATE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('STATUS'))
        data.append(0x0D)
        data.append(0x00)

        # Part 6: mail entries (max 11 per page)
        offset = getattr(self, 'mail_page_offset', 0)
        visible = self.mail_messages[offset:offset+11]

        if not self.mail_messages:
            data.extend(ascii_to_petscii('      (NO MAIL)'))
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
            # Mark as read
            self.mail_messages[actual_index]['read'] = True
            self._save_mail()
            return self._send_mail_frame()
        else:
            # Beyond visible entries — advance to next page
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
        mail_file = os.path.join(MAIL_DIR, self.user_id + '.json')
        data = {'messages': self.mail_messages}
        with open(mail_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _next_message_number(self):
        """Get and increment the global message sequence number."""
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
        # Second 'U' (no params) = ready to send a frame, just ACK it
        if len(params) == 0:
            log.info('UPLOAD: frame-ready signal, sending ACK')
            self.last_response_type = RESP_ACK
            return bytes([RESP_ACK])

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
        return bytes(data)

    def _cmd_upload_content(self, title, page_type, rest):
        """Handle content UPLOAD — store metadata for frame upload."""
        price_str = rest[0:8].decode('latin-1').strip()
        lifetime_str = rest[8:].decode('latin-1').strip() if len(rest) > 8 else '0'

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
        data.extend(ascii_to_petscii(price_str.ljust(8)[:8]))
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

    def _complete_mail_send(self, send):
        """Deliver mail to recipients."""
        import datetime
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

        log.info('MAIL: delivered from %s to %s subject="%s" frames=%d',
                 self.user_id, send['to'], send['subject'], len(send['frames']))
        return b''

    def _complete_content_upload(self, send):
        """Add uploaded page to the current directory."""
        if not self._can_upload_here():
            log.info('UPLOAD DISCARDED: user=%s cannot upload to page owned by %s',
                     self.user_id, self.current_page.author)
            return

        if len(self.current_page.children) >= 11:
            log.info('UPLOAD DISCARDED: user=%s directory full (%d entries)',
                     self.user_id, len(self.current_page.children))
            return

        all_pages = list(self.directory.pages.keys())
        next_page_num = max(all_pages) + 1 if all_pages else 1000

        # Create page folder
        page_slug = send['title'].lower().replace(' ', '-')
        parent_dir = getattr(self.current_page, '_dir_path', ROOT_DIR)
        page_dir = os.path.join(parent_dir, page_slug)
        os.makedirs(page_dir, exist_ok=True)

        # Save frames into page folder
        frame_files = []
        is_program = send['type'] == 'P'
        for i, frame_data in enumerate(send['frames']):
            if is_program:
                # Client sends: [4 padding] [load_lo] [load_hi] [size_lo] [size_hi] [data...]
                # Store as standard PRG: [load_lo] [load_hi] [data...]
                frame_data = bytes(frame_data[4:6]) + bytes(frame_data[8:])
                frame_file = f'{page_slug}.prg' if i == 0 else f'{page_slug}-{i+1}.prg'
            else:
                frame_file = f'frame-{i+1}.seq'
            frame_path = os.path.join(page_dir, frame_file)
            with open(frame_path, 'wb') as f:
                f.write(frame_data)
            frame_files.append(frame_file)

        if is_program and send['frames']:
            size = (len(send['frames'][0]) - 2 + 1023) // 1024
        else:
            size = len(send['frames'])

        new_page = CompunetPage(
            page_num=next_page_num,
            title=send['title'],
            page_type=send['type'],
            size=size,
            author=self.user_id,
            price=send['price'],
            life=send['lifetime'],
        )
        new_page.parent = self.current_page
        new_page._frame_files = frame_files
        new_page._dir_path = page_dir
        new_page._adverts = []
        for frame_file in frame_files:
            frame_path = os.path.join(page_dir, frame_file)
            with open(frame_path, 'rb') as f:
                new_page.frames.append(f.read())
        self.current_page.children.append(new_page)
        self.directory.pages[next_page_num] = new_page

        self._save_directory()

        log.info('CONTENT: uploaded page %d "%s" by %s (%d frames, price=%.2f, life=%d)',
                 next_page_num, send['title'], self.user_id,
                 len(send['frames']), send['price'], send['lifetime'])
        return b''

    def _save_directory(self):
        """Persist the directory tree to per-directory JSON files."""
        def _page_slug(title):
            return title.lower().replace(' ', '-')

        def _save_dir_json(page, json_path):
            """Write a directory JSON for a page's children."""
            data = {}
            if hasattr(page, 'header') and page.header:
                data['header'] = page.header
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
                frame_files = getattr(child, '_frame_files', [])
                if frame_files:
                    node['frames'] = frame_files
                if child.children:
                    child_slug = _page_slug(child.title)
                    child_dir = getattr(child, '_dir_path', '')
                    dir_json_path = os.path.join(child_dir, 'directory.json')
                    node['directory'] = os.path.relpath(dir_json_path, ROOT_DIR)
                    _save_dir_json(child, dir_json_path)
                pages_list.append(node)
            data['pages'] = pages_list
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)

        root_json_path = os.path.join(ROOT_DIR, 'root.json')
        _save_dir_json(self.directory.root, root_json_path)
        log.info('DIR: saved directory tree')

    def _cmd_ucat(self):
        """UCAT command - list all pages owned by the current user."""
        self.last_response_type = RESP_DIR
        user_pages = [p for p in self.directory.pages.values()
                      if p.author == self.user_id]
        data = bytearray()

        # Part 1: no header frame
        data.append(0x00)

        # Part 2: footer/adverts (empty)
        data.append(0x0D)
        data.append(0x0D)

        # Part 3: field definitions (none)
        data.append(0x00)

        # Part 4: breadcrumb
        data.extend(ascii_to_petscii('    1 *** COMPUNET ***'))
        data.append(0x0D)
        data.extend(ascii_to_petscii('  YOUR UPLOADS'))
        data.append(0x00)

        # Part 5: column headers
        data.extend(ascii_to_petscii('LIFE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('PRICE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('VOTE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('PAGE'))
        data.append(0x0D)
        data.append(0x00)

        # Part 6: entries
        if not user_pages:
            data.extend(ascii_to_petscii('      (NO UPLOADS)'))
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x0D)
        else:
            for page in user_pages:
                page_str = str(page.page_num).ljust(6)
                type_str = page.type_string().ljust(3)
                title_field = page.title[:18].ljust(18) + type_str
                data.extend(ascii_to_petscii(page_str + title_field))
                data.append(0x2C)
                # Column 1: LIFE
                data.extend(ascii_to_petscii(str(page.life)))
                data.append(0x2C)
                # Column 2: PRICE
                price_str = '{:.2f}'.format(page.price) if page.price > 0 else ''
                data.extend(ascii_to_petscii(price_str))
                data.append(0x2C)
                # Column 3: VOTE
                vote_str = str(page.vote) if page.vote > 0 else ''
                data.extend(ascii_to_petscii(vote_str))
                data.append(0x2C)
                # Column 4: PAGE
                data.extend(ascii_to_petscii(str(page.page_num)))
                data.append(0x0D)

        log.info('UCAT: user=%s pages=%d', self.user_id, len(user_pages))
        return bytes(data)
    
    def _make_dir_response(self):
        """Build directory response in the 6-part format for 'P' command."""
        # Reload content tree from disk (picks up changes without restart)
        current_page_num = self.current_page.page_num
        self.directory.reload()
        self.current_page = self.directory.pages.get(current_page_num, self.directory.root)

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
        data.extend(ascii_to_petscii('    1 *** COMPUNET ***'))
        data.append(0x0D)
        path_line2 = '  ' + str(page.page_num) + ' ' + (page.title or '')
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
        data.extend(ascii_to_petscii('PRICE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('LIFE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('AUTHOR'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('VOTE'))
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
            data.extend(ascii_to_petscii('0     (EMPTY)'))
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x0D)
        else:
            for child in visible:
                # Combined field: [page_num padded to 6] + [title...type right-aligned]
                # First 6 chars = page number (hidden in bg colour)
                # Chars 7-26 = title left-aligned, type right-aligned (20 chars total)
                # Type suffix must start at screen column 25 (SHOW reads $19)
                page_str = str(child.page_num).ljust(6)
                type_str = child.type_string().ljust(3)
                title = child.title[:18]
                title_field = title.ljust(18) + type_str
                data.extend(ascii_to_petscii(page_str + title_field))
                data.append(0x2C)
                # Column 1: PRICE (0 if already purchased)
                effective_price = 0 if child.page_num in self.purchased else child.price
                if effective_price > 0:
                    data.extend(ascii_to_petscii('{:.2f}'.format(effective_price)[:8]))
                data.append(0x2C)
                # Column 2: LIFE
                if child.life > 0:
                    data.extend(ascii_to_petscii(str(child.life)[:8]))
                data.append(0x2C)
                # Column 3: AUTHOR
                data.extend(ascii_to_petscii(child.author[:8]))
                data.append(0x2C)
                # Column 4: VOTE — "avg (count)" format
                if child.vote > 0:
                    vote_count = self._get_vote_count(child.page_num)
                    vote_str = f'{child.vote} ({vote_count})'
                    data.extend(ascii_to_petscii(vote_str[:8]))
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
        import datetime
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
        data.extend(ascii_to_petscii('    1 *** COMPUNET ***'))
        data.append(0x0D)
        data.extend(ascii_to_petscii('  WHO'))
        data.append(0x00)

        # Part 5: column header
        data.extend(ascii_to_petscii('WHO'))
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
        import datetime
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
            mail_waiting = any(not m.get('read', True) for m in inbox.get('messages', []))

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
# WebSocket interface - binary protocol over WebSocket frames
# ============================================================

async def ws_handler(websocket):
    """Handle a WebSocket connection. Same protocol as TCP but over WebSocket binary frames.

    Unlike the TCP/C64 path where the client knows what response to expect based
    on the command it sent, WebSocket responses are prefixed with a type byte so
    the web client can demultiplex them:
      $41 = ACK, $44 = Directory, $46 = Frame, $45 = Error
    """
    directory = CompunetDirectory()
    session = CompunetSession(directory)

    log.info('WebSocket client connected: %s', websocket.remote_address)

    def _ws_wrap(response):
        """Add response type prefix byte for WebSocket clients.

        The session sets last_response_type before building each response.
        Methods that already embed their own prefix byte (_make_error, _cmd_mail,
        _cmd_vote) are detected by checking if first byte equals the tracked type.
        """
        if not response:
            return response
        prefix = session.last_response_type
        if not prefix:
            # No type tracked - check if response self-identifies
            first = response[0]
            if first in (RESP_ACK, RESP_ERROR, RESP_FRAME, RESP_DIR, RESP_LINKING):
                return response
            return bytes([RESP_DIR]) + response
        # If the response already starts with its own prefix, pass through
        if response[0] == prefix:
            return response
        return bytes([prefix]) + response

    try:
        # Login loop - keep prompting until successful
        while True:
            login_data = await websocket.recv()
            if isinstance(login_data, str):
                login_data = login_data.encode('latin-1')

            parts = login_data.split(b'\x00')
            user_id = parts[0].decode('latin-1') if len(parts) > 0 else 'GUEST'
            password = parts[1].decode('latin-1') if len(parts) > 1 else ''

            async with _lock_users:
                response = session.handle_login(user_id, password)
            await websocket.send(_ws_wrap(response))

            if session.authenticated:
                break

        # Command loop (only reached after successful login)
        async for message in websocket:
            if isinstance(message, str):
                message = message.encode('latin-1')

            if len(message) == 0:
                continue

            # Check for GOTO (special: starts with 'G' + page number as ASCII)
            if message[0] == ord('G') and len(message) > 1:
                try:
                    page_num = int(message[1:].decode('latin-1'))
                    response = session.handle_goto(page_num)
                except ValueError:
                    response = session._make_error(ascii_to_petscii('INVALID PAGE'))
            # Check for SELECT (highlight change: 'S' + index byte)
            elif message[0] == ord('S') and len(message) > 1:
                session.handle_select(message[1])
                continue  # no response
            else:
                # Standard command (lock prevents interleaved writes)
                async with _lock_content:
                    response = session.handle_command(message)

            if response:
                await websocket.send(_ws_wrap(response))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        log.info('WebSocket client disconnected')


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
    
    directory = CompunetDirectory()
    session = CompunetSession(directory)
    x25 = X25Connection()
    
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
                
                ident_received = True
                rx_buffer.clear()
                
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
                            line = line.replace('{VERSION}', _ver.center(9))
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
                data = await asyncio.wait_for(reader.read(256), timeout=600.0)
            except asyncio.TimeoutError:
                log.info('TCP: idle timeout (10 minutes)')
                break
            if not data:
                log.info('TCP: connection closed by client')
                break
            
            log.debug('TCP RX: %d bytes: %s', len(data), data.hex())
            packets = x25.feed_data(data)
            
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
                        cnload_1 = cmd_payload[25] if len(cmd_payload) > 25 else 0
                        cnload_2 = cmd_payload[26] if len(cmd_payload) > 26 else 0
                        skip_linking = (cnload_1 == 0x30 and cnload_2 == 0x30)
                        
                        log.info('TCP: *** LOGIN ***')
                        log.info('TCP:   user=%r cnload_bytes=$%02X/$%02X (skip=%s)',
                                 user_id, cnload_1, cnload_2, skip_linking)
                        
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
                            await asyncio.sleep(0.5)
                            MAX_PAYLOAD = 100
                            offset = 0
                            while offset < len(error_frame):
                                chunk = error_frame[offset:offset + MAX_PAYLOAD]
                                pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                                writer.write(pkt)
                                await writer.drain()
                                await asyncio.sleep(0.05)
                                offset += MAX_PAYLOAD
                            eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                            writer.write(eos_pkt)
                            await writer.drain()
                            await asyncio.sleep(2.0)
                            writer.close()
                            await writer.wait_closed()
                            return
                        
                        authenticated = True
                        _online_users.add(session.user_id)
                        log.info('TCP: login OK! Skipping LINKING (terminal pre-loaded)')

                        # Send welcome frame — L89D0 reads this after login
                        if response:
                            MAX_PAYLOAD = 100
                            offset = 0
                            while offset < len(response):
                                chunk = response[offset:offset + MAX_PAYLOAD]
                                pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                                writer.write(pkt)
                                await writer.drain()
                                await asyncio.sleep(0.25)
                                offset += MAX_PAYLOAD
                            eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                            writer.write(eos_pkt)
                            await writer.drain()
                            log.info('TCP: sent welcome frame (%d bytes + EOS)', len(response))
                    
                    elif cmd_byte == 0x5A and authenticated:
                        # Retransmitted login packet — ignore it
                        log.debug('TCP: ignoring retransmitted login packet')
                    
                    elif authenticated:
                        # Post-login commands (lock prevents interleaved writes)
                        log.info('TCP: dispatching command (authenticated=True)')
                        async with _lock_content:
                            cmd_response = session.handle_command(cmd_payload)
                        if cmd_response:
                            log.info('CMD: pre-response delay 500ms starting')
                            await asyncio.sleep(0.5)
                            log.info('CMD: sending %d bytes in %d-byte chunks', len(cmd_response), 100)
                            MAX_PAYLOAD = 100
                            offset = 0
                            pkt_num = 0
                            while offset < len(cmd_response):
                                chunk = cmd_response[offset:offset + MAX_PAYLOAD]
                                pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                                writer.write(pkt)
                                await writer.drain()
                                pkt_num += 1
                                log.info('CMD: sent pkt %d (%d payload, %d wire), sleeping 500ms', pkt_num, len(chunk), len(pkt))
                                await asyncio.sleep(0.5)
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
                                log.info('TCP: entering partyline mode for user=%s', session.user_id)
                                await asyncio.sleep(1.0)
                                await partyline.handle_session(reader, writer, session.user_id)
                                log.info('TCP: exited partyline mode, resuming X.25 for user=%s', session.user_id)
                                continue

                elif token == 0x40 and session._program_download_pending:
                    # Client confirms download proceed — send program data
                    program_data = session._program_download_data
                    session._program_download_pending = False
                    session._program_download_data = None
                    log.info('DOWNLOAD: proceed received, sending %d bytes of program data', len(program_data))
                    await asyncio.sleep(0.5)
                    MAX_PAYLOAD = 100
                    offset = 0
                    pkt_num = 0
                    while offset < len(program_data):
                        chunk = program_data[offset:offset + MAX_PAYLOAD]
                        pkt = x25.make_data_packet(chunk, TOKEN_DAT)
                        writer.write(pkt)
                        await writer.drain()
                        pkt_num += 1
                        await asyncio.sleep(0.05)
                        offset += MAX_PAYLOAD
                    eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                    writer.write(eos_pkt)
                    await writer.drain()
                    log.info('DOWNLOAD: sent %d packets + EOS (%d bytes total)', pkt_num, len(program_data))

                elif token == 0x41 and session._program_download_pending:
                    # Client aborted download (no room in RAM)
                    session._program_download_pending = False
                    session._program_download_data = None
                    session.show_page = None
                    log.info('DOWNLOAD: client aborted (no room in RAM)')

                elif token == TOKEN_ACK:
                    log.debug('TCP: received ACK seq=$%02X', seq)

                elif session.pending_send is not None and token != 0x43:
                    # Any non-COM packet during upload = frame data chunk
                    log.info('TCP: upload chunk token=$%02X seq=$%02X payload=%d bytes',
                             token, seq, len(payload))
                    # Accumulate chunks into current frame buffer
                    if '_current_frame' not in session.pending_send:
                        session.pending_send['_current_frame'] = bytearray()
                    session.pending_send['_current_frame'].extend(payload)
                    # Final chunk (< 100 bytes) = end of this frame
                    if len(payload) < 100:
                        frame_data = bytes(session.pending_send['_current_frame'])
                        session.pending_send['frames'].append(frame_data)
                        session.pending_send['_current_frame'] = bytearray()
                        log.info('UPLOAD: frame %d complete (%d bytes)',
                                 len(session.pending_send['frames']), len(frame_data))
                        await asyncio.sleep(0.5)
                        ack_data = bytes([RESP_ACK]) + b'\x00' * 10
                        ack_pkt = x25.make_data_packet(ack_data, TOKEN_DAT)
                        writer.write(ack_pkt)
                        await writer.drain()
                        log.info('UPLOAD: sent frame ACK (%d wire)', len(ack_pkt))

                else:
                    log.debug('TCP: other token=$%02X seq=$%02X', token, seq)
    
    except (ConnectionResetError, BrokenPipeError) as e:
        log.info('TCP: connection error: %s', e)
    finally:
        if session.user_id:
            _online_users.discard(session.user_id)
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

    user = users.get(user_id)
    if user is None:
        return aiohttp_web.json_response({'error': 'invalid credentials'}, status=401)

    password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    if user['password'] != password_hash:
        return aiohttp_web.json_response({'error': 'invalid credentials'}, status=401)

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

        _api_save_users(users)

    log.info('API: updated user %s', user_id)
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

    return aiohttp_web.json_response(entry)


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


# ============================================================
# Main
# ============================================================

async def main():
    ws_server = await websockets.serve(ws_handler, '0.0.0.0', WS_PORT)
    log.info('WebSocket server on port %d', WS_PORT)

    tcp_server = await asyncio.start_server(tcp_handler, '0.0.0.0', TCP_PORT)
    log.info('TCP server on port %d', TCP_PORT)

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
        app.router.add_get('/ws/partyline', api_ws_partyline)
        runner = aiohttp_web.AppRunner(app)
        await runner.setup()
        site = aiohttp_web.TCPSite(runner, '0.0.0.0', API_PORT)
        await site.start()
        log.info('REST API on port %d', API_PORT)
    else:
        log.warning('aiohttp not installed — REST API disabled')

    for _vp in [os.path.join(SERVER_DIR, 'VERSION'), os.path.join(SERVER_DIR, '..', 'VERSION')]:
        if os.path.exists(_vp):
            _version = open(_vp).read().strip()
            break
    else:
        _version = 'unknown'
    log.info('Compunet server v%s ready.', _version)

    async with ws_server, tcp_server:
        await asyncio.gather(
            ws_server.serve_forever(),
            tcp_server.serve_forever(),
        )


if __name__ == '__main__':
    asyncio.run(main())
