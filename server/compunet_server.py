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
import glob
import logging
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    raise

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('compunet')

# Server configuration
WS_PORT = 6502
TCP_PORT = 6400
CONTENT_DIR = os.path.join(os.path.dirname(__file__), 'content')

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
    
    def __init__(self, page_num, title, page_type='T', size=0, author='SYSTEM', price=0.0, life=0, vote=0):
        self.page_num = page_num
        self.title = title
        self.page_type = page_type
        self.size = size
        self.author = author
        self.price = price
        self.life = life
        self.vote = vote
        self.children = []
        self.frames = []    # list of bytes objects (raw frame data)
        self.parent = None
    
    def has_subdir(self):
        return len(self.children) > 0
    
    def type_string(self):
        """Generate the type suffix shown in directory listings."""
        s = self.page_type
        if self.size > 0:
            s += str(self.size)
        if self.has_subdir():
            s += '+'
        return s


class CompunetDirectory:
    """The content tree, loaded from root.json."""
    
    def __init__(self):
        self.pages = {}
        self.root = None
        self._load_tree()
    
    def _load_tree(self):
        """Load directory structure from JSON."""
        json_path = os.path.join(CONTENT_DIR, 'root.json')
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)
            self.root = self._build_page(data['root'], None)
        else:
            # Fallback: minimal default
            self.root = CompunetPage(1, 'COMPUNET', 'D')
            self.pages[1] = self.root
    
    def _build_page(self, node, parent):
        """Recursively build page tree from JSON node."""
        page = CompunetPage(
            page_num=node['page_num'],
            title=node['title'],
            page_type=node.get('type', 'T'),
            size=node.get('size', 0),
            author=node.get('author', 'SYSTEM'),
            price=node.get('price', 0),
            life=node.get('life', 0),
            vote=node.get('vote', 0),
        )
        page.parent = parent
        self.pages[page.page_num] = page
        
        # Load header file (directory frame header)
        page.header = node.get('header', None)
        
        # Load frame files
        page._frame_files = []
        for frame_file in node.get('frames', []):
            frame_path = os.path.join(CONTENT_DIR, 'pages', frame_file)
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    page.frames.append(f.read())
                page._frame_files.append(frame_file)
        
        # Build children
        for child_node in node.get('children', []):
            child = self._build_page(child_node, page)
            page.children.append(child)
        
        return page


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
        self.mail_mode = False
        self.mail_messages = []
        self.mail_show_msg = None
        self.mail_frame_index = 0
        self.pending_send = None
        self.last_response_type = None  # Set by response methods for WS prefix detection
        self._users = self._load_users()
    
    def _load_users(self):
        users_file = os.path.join(os.path.dirname(__file__), 'users.json')
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
        elif cmd == ord('N'):
            return self._cmd_more(params)
        else:
            return self._make_error(ascii_to_petscii('UNKNOWN COMMAND'))
    
    def handle_goto(self, page_num):
        """Handle GOTO to a specific page number."""
        self.last_response_type = None  # Reset per-command for WS prefix detection
        page = self.directory.pages.get(page_num)
        if page is None:
            return self._make_error(ascii_to_petscii('PAGE NOT FOUND'))
        
        self.current_page = page
        if page.has_subdir():
            return self._make_dir_response()
        elif page.frames:
            # Set current_page to parent so BACK/FINISH returns correctly
            if page.parent:
                self.current_page = page.parent
            self.show_page = page
            self.show_frame_index = 0
            return self._send_current_frame()
        else:
            return self._make_error(ascii_to_petscii('NO CONTENT'))
    
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

        # If already viewing a frame, advance to next page
        if hasattr(self, 'show_page') and self.show_page:
            if self.show_frame_index < len(self.show_page.frames) - 1:
                self.show_frame_index += 1
                return self._send_current_frame()
            else:
                # On last frame — clear state. If no params (FINISH/MORE after
                # last page), return directory. If params present (new SHOW from
                # directory), fall through to handle as fresh entry selection.
                self.show_page = None
                if not params:
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
        If we're already viewing the directory and the selected entry has a
        sub-directory, enter it. Otherwise show the current page directory.
        """
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
                    if child.has_subdir():
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
        """
        self.last_response_type = RESP_FRAME
        if self.show_page and self.show_frame_index < len(self.show_page.frames):
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
        goodbye_path = os.path.join(CONTENT_DIR, 'pages', 'goodbye.seq')
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
        """LIFE/EXTEND command ('X') — extend life of owned content.

        Params: entry_index (2 ASCII digits) + extension (up to 4 ASCII digits).
        Server validates ownership and adds extension to page life.
        Returns $00 byte (consumed by C64 client as success indicator).
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

        # Check ownership
        if child.author != self.user_id:
            log.info('EXTEND DENIED: user=%s is not author of page %d (author=%s)',
                     self.user_id, child.page_num, child.author)
            return bytes([0x00])

        # Extend life
        child.life += extend_by
        log.info('EXTEND: user=%s page=%d ("%s") extend_by=%d new_life=%d',
                 self.user_id, child.page_num, child.title, extend_by, child.life)
        return bytes([0x00])

    def _save_user(self):
        """Persist user credit and purchases to users.json."""
        users_file = os.path.join(os.path.dirname(__file__), 'users.json')
        users = self._load_users()
        if self.user_id in users:
            users[self.user_id]['credit'] = self.credit
            users[self.user_id]['purchased'] = sorted(self.purchased)
            with open(users_file, 'w') as f:
                json.dump(users, f, indent=2)

    def _cmd_back(self):
        """BACK command - go to previous page, or parent directory if on first page."""
        if self.mail_mode:
            self.mail_mode = False
            self.mail_show_msg = None
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
        """VOTE command."""
        self.last_response_type = RESP_ACK
        return bytes([RESP_ACK])
    
    def _cmd_mail(self):
        """MAIL command - show mailbox as 6-part directory listing."""
        self.mail_mode = True
        self.mail_messages = self._load_mail()
        self.mail_frame_index = 0
        self.mail_show_msg = None
        return self._make_mail_response()

    def _load_mail(self):
        """Load mail metadata for the current user."""
        mail_file = os.path.join(os.path.dirname(__file__), 'mail', self.user_id + '.json')
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
        data.extend(ascii_to_petscii('           '))  # 11 bytes padding (offset $0B)
        data.extend(ascii_to_petscii(self.user_id))
        data.append(0x0D)
        data.extend(ascii_to_petscii(real_name))
        data.append(0x0D)
        data.append(0x0D)
        data.extend(ascii_to_petscii(now.strftime('%d-%m-%y')))
        data.append(0x0D)
        data.extend(ascii_to_petscii(now.strftime('%H:%M')))
        data.append(0x00)

        # Part 5: column headers
        data.extend(ascii_to_petscii('DATE'))
        data.append(0x2C)
        data.extend(ascii_to_petscii('STATUS'))
        data.append(0x0D)
        data.append(0x00)

        # Part 6: mail entries
        if not self.mail_messages:
            data.extend(ascii_to_petscii('      (NO MAIL)'))
            data.append(0x2C)
            data.append(0x2C)
            data.append(0x0D)
        else:
            for i, msg in enumerate(self.mail_messages):
                from_str = msg.get('from', '?')[:6]
                subject = msg.get('subject', '')[:9]
                num_frames = len(msg.get('frames', []))
                type_str = ('T' + str(num_frames)).ljust(3)
                title = from_str + ': ' + subject
                page_str = str(i + 1).rjust(4) + '  '
                title_field = title[:17].ljust(18) + type_str
                data.extend(ascii_to_petscii(page_str + title_field))
                data.append(0x2C)
                # Date as DD-MM-YY (8 chars max)
                raw_date = msg.get('date', '')
                if len(raw_date) == 10:
                    date_str = raw_date[8:10] + '-' + raw_date[5:7] + '-' + raw_date[2:4]
                else:
                    date_str = raw_date[:8]
                data.extend(ascii_to_petscii(date_str))
                data.append(0x2C)
                status = 'NEW' if not msg.get('read', False) else 'READ'
                data.extend(ascii_to_petscii(status))
                data.append(0x0D)

        log.info('MAIL response: %d messages, %d bytes', len(self.mail_messages), len(data))
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

        if selected < len(self.mail_messages):
            self.mail_show_msg = selected
            self.mail_frame_index = 0
            # Mark as read
            self.mail_messages[selected]['read'] = True
            self._save_mail()
            return self._send_mail_frame()

        return self._make_error(ascii_to_petscii('NO SUCH MESSAGE'))

    def _send_mail_frame(self):
        """Send current mail message frame."""
        self.last_response_type = RESP_FRAME
        msg = self.mail_messages[self.mail_show_msg]
        frames = msg.get('frames', [])
        frame_file = frames[self.mail_frame_index]
        mail_dir = os.path.join(os.path.dirname(__file__), 'mail', self.user_id)
        frame_path = os.path.join(mail_dir, frame_file)

        if os.path.exists(frame_path):
            with open(frame_path, 'rb') as f:
                frame_data = bytearray(f.read())
        else:
            frame_data = bytearray(b'\x00\x06\x0f\x8e\x0d\x0d  MESSAGE NOT FOUND\x0d\x00')

        has_more = self.mail_frame_index < len(frames) - 1
        if has_more:
            frame_data[0] |= 0x80
        log.info('MAIL FRAME: msg=%d frame=%d/%d file=%s (%d bytes, more=%s)',
                 self.mail_show_msg, self.mail_frame_index + 1, len(frames),
                 frame_file, len(frame_data), has_more)
        return bytes(frame_data)

    def _save_mail(self):
        """Persist mail metadata (read status etc)."""
        mail_file = os.path.join(os.path.dirname(__file__), 'mail', self.user_id + '.json')
        data = {'messages': self.mail_messages}
        with open(mail_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _next_message_number(self):
        """Get and increment the global message sequence number."""
        seq_file = os.path.join(os.path.dirname(__file__), 'mail', 'sequence.json')
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
        sender_name = users.get(sender_id, {}).get('name', sender_id)

        # Build destination slot lines
        dest_lines = []
        for i in range(5):
            if i < len(dest_ids):
                did = dest_ids[i]
                dest_name = users.get(did, {}).get('name', '')
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

        # Parse price: strip leading zeros, format as X.XX
        try:
            price = float(price_str)
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
        mail_dir = os.path.join(os.path.dirname(__file__), 'mail')
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

            msg_num = len(dest_inbox['messages']) + 1
            msg_id = f'msg{msg_num:03d}'

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
        # Find next available page number
        all_pages = list(self.directory.pages.keys())
        next_page_num = max(all_pages) + 1 if all_pages else 1000

        # Save frame files
        frame_files = []
        for i, frame_data in enumerate(send['frames']):
            frame_file = f'upload-{next_page_num}-{i+1}.seq'
            frame_path = os.path.join(CONTENT_DIR, 'pages', frame_file)
            with open(frame_path, 'wb') as f:
                f.write(frame_data)
            frame_files.append(frame_file)

        # Create new page in the directory tree
        new_page = CompunetPage(
            page_num=next_page_num,
            title=send['title'],
            page_type=send['type'],
            size=len(send['frames']),
            author=self.user_id,
            price=send['price'],
            life=send['lifetime'],
            vote=0,
        )
        new_page.parent = self.current_page
        new_page._frame_files = frame_files
        for frame_file in frame_files:
            frame_path = os.path.join(CONTENT_DIR, 'pages', frame_file)
            with open(frame_path, 'rb') as f:
                new_page.frames.append(f.read())
        self.current_page.children.append(new_page)
        self.directory.pages[next_page_num] = new_page

        # Persist to root.json
        self._save_directory()

        log.info('CONTENT: uploaded page %d "%s" by %s (%d frames, price=%.2f, life=%d)',
                 next_page_num, send['title'], self.user_id,
                 len(send['frames']), send['price'], send['lifetime'])
        return b''

    def _save_directory(self):
        """Persist the directory tree back to root.json."""
        def _page_to_dict(page):
            node = {
                'page_num': page.page_num,
                'title': page.title,
                'type': page.page_type,
                'size': page.size,
                'author': page.author,
                'price': page.price,
                'life': page.life,
                'vote': page.vote,
            }
            if hasattr(page, 'header') and page.header:
                node['header'] = page.header
            frame_files = getattr(page, '_frame_files', [])
            if frame_files:
                node['frames'] = frame_files
            node['children'] = [_page_to_dict(child) for child in page.children]
            return node

        tree = {'root': _page_to_dict(self.directory.root)}
        json_path = os.path.join(CONTENT_DIR, 'root.json')
        with open(json_path, 'w') as f:
            json.dump(tree, f, indent=2)
        log.info('DIR: saved directory tree to root.json')

    def _cmd_ucat(self):
        """UCAT command - user catalogue listing."""
        return self._make_error(ascii_to_petscii('NO UPLOADS'))
    
    def _make_dir_response(self):
        """Build directory response in the 6-part format for 'P' command."""
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
        # Loaded from the page's "header" SEQ file if defined.
        header_file = getattr(page, 'header', None)
        if header_file:
            header_path = os.path.join(CONTENT_DIR, 'pages', header_file)
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
        
        # --- Part 2: Footer text (2 CR-terminated lines, displayed at row 22) ---
        # Used for adverts or status text below the directory box.
        data.append(0x0D)  # Line 1: empty
        data.append(0x0D)  # Line 2: empty

        # --- Part 3: Field definitions ---
        # $00 = none
        data.append(0x00)

        # --- Part 4: Routing/breadcrumb (stored at $D400, displayed at row 7) ---
        # Shows current directory path inside the box, above entries.
        data.extend(ascii_to_petscii('    1 *** COMPUNET ***'))
        data.append(0x0D)
        path_line2 = '  ' + str(page.page_num) + ' ' + (page.title or '')
        data.extend(ascii_to_petscii(path_line2[:22]))
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
            data.extend(ascii_to_petscii('T'))
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
                page_str = ('  ' + str(child.page_num)).ljust(6)[:6]
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
                # Column 4: VOTE
                if child.vote > 0:
                    data.extend(ascii_to_petscii(str(child.vote)[:8]))
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
        mail_file = os.path.join(os.path.dirname(__file__), 'mail', self.user_id + '.json')
        mail_waiting = False
        if os.path.exists(mail_file):
            with open(mail_file, 'r') as f:
                inbox = json.load(f)
            mail_waiting = any(not m.get('read', True) for m in inbox.get('messages', []))

        # Mail indicator — PETSCII pillarbox graphic or blank
        if mail_waiting:
            mail_ind = b'\x1C\x12 MAIL \x92'  # red reversed "MAIL"
        else:
            mail_ind = b''

        # Credit display
        credit = user.get('credit', 0.0)
        if credit >= 0:
            credit_str = f'{credit:.2f} CREDIT'
        else:
            credit_str = f'{abs(credit):.2f} DEBIT'

        # Load template
        template_path = os.path.join(CONTENT_DIR, 'templates', 'welcome.seq')
        if os.path.exists(template_path):
            with open(template_path, 'rb') as f:
                frame = f.read()
        else:
            frame = b'\x00\x03\x0F\x8E\x0D\x1F WELCOME\x0D\x00'

        # Replace placeholders
        frame = frame.replace(b'{USER_ID}', self.user_id.encode('ascii'))
        frame = frame.replace(b'{ACCOUNT_TYPE}', user.get('account_type', 'BASIC').encode('ascii'))
        frame = frame.replace(b'{LAST_DATE}', prev_date.encode('ascii'))
        frame = frame.replace(b'{LAST_TIME}', prev_time.encode('ascii'))
        frame = frame.replace(b'{PAGES}', b'0')  # TODO: calculate from directory
        frame = frame.replace(b'{NEAR_DEATH}', b'0')  # TODO: calculate pages with life <= 3
        frame = frame.replace(b'{FREE_STORAGE}', b'2000')  # TODO: calculate from account type
        frame = frame.replace(b'{CREDIT}', credit_str.encode('ascii'))
        frame = frame.replace(b'{MAIL_IND}', mail_ind)

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
                # Standard command
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
        # Phase 1: Connection handshake
        # Client sends $20 (space), we respond with $20
        # ============================================================
        log.info('TCP: connected, waiting for break delay...')
        
        # Handshake: minimal delay then send bytes immediately
        await asyncio.sleep(0.05)
        log.info('X25: sending handshake bytes one at a time')
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
                
                # Send "*CON\r" immediately — no delay.
                writer.write(b'\x2a\x43\x4f\x4e\x0d')
                await writer.drain()
                log.info('TCP TX: sent "*CON\\r" connection signal (burst)')
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
                        log.info('TCP:   user=%r pass=%r cnload_bytes=$%02X/$%02X (skip=%s)',
                                 user_id, password, cnload_1, cnload_2, skip_linking)
                        
                        response = session.handle_login(user_id, password)
                        if not session.authenticated:
                            log.info('TCP: login FAILED - closing connection')
                            writer.close()
                            await writer.wait_closed()
                            return
                        
                        authenticated = True
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
                                await asyncio.sleep(0.05)
                                offset += MAX_PAYLOAD
                            eos_pkt = x25.make_data_packet(b'', TOKEN_DAT)
                            writer.write(eos_pkt)
                            await writer.drain()
                            log.info('TCP: sent welcome frame (%d bytes + EOS)', len(response))
                    
                    elif cmd_byte == 0x5A and authenticated:
                        # Retransmitted login packet — ignore it
                        log.debug('TCP: ignoring retransmitted login packet')
                    
                    elif authenticated:
                        # Post-login commands
                        log.info('TCP: dispatching command (authenticated=True)')
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

                elif token == TOKEN_ACK:
                    log.debug('TCP: received ACK seq=$%02X', seq)

                elif session.pending_send is not None and token != 0x43:
                    # Any non-COM packet during upload = frame data chunk
                    log.info('TCP: upload chunk token=$%02X seq=$%02X payload=%d bytes',
                             token, seq, len(payload))
                    session.pending_send['frames'].append(bytes(payload))
                    # ACK only the final chunk (< 100 bytes = partial = last)
                    # Client calls L96D2 once after all bytes sent
                    if len(payload) < 100:
                        log.info('UPLOAD: final chunk received (%d total chunks), sending ACK',
                                 len(session.pending_send['frames']))
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
        writer.close()
        await writer.wait_closed()
        log.info('TCP client disconnected: %s', addr)


# ============================================================
# Main
# ============================================================

async def main():
    os.makedirs(os.path.join(CONTENT_DIR, 'pages'), exist_ok=True)
    
    ws_server = await websockets.serve(ws_handler, '0.0.0.0', WS_PORT)
    log.info('WebSocket server on port %d', WS_PORT)
    
    tcp_server = await asyncio.start_server(tcp_handler, '0.0.0.0', TCP_PORT)
    log.info('TCP server on port %d', TCP_PORT)
    
    log.info('Compunet server ready.')
    
    async with ws_server, tcp_server:
        await asyncio.gather(
            ws_server.serve_forever(),
            tcp_server.serve_forever(),
        )


if __name__ == '__main__':
    asyncio.run(main())
