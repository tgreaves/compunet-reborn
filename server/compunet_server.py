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
CMD_BUY = 0x42        # 'B'
CMD_BACK = 0x43       # 'C'
CMD_DIR = 0x44        # 'D'
CMD_EDITR = 0x45      # 'E'
CMD_ID = 0x49         # 'I'
CMD_MAIL = 0x4D       # 'M'
CMD_SHOW = 0x50       # 'P'
CMD_UPLD = 0x55       # 'U'
CMD_VOTE = 0x56       # 'V'

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
    """The content tree, loaded from directory.json."""
    
    def __init__(self):
        self.pages = {}
        self.root = None
        self._load_tree()
    
    def _load_tree(self):
        """Load directory structure from JSON."""
        json_path = os.path.join(CONTENT_DIR, 'directory.json')
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
        
        # Load frame files
        for frame_file in node.get('frames', []):
            frame_path = os.path.join(CONTENT_DIR, 'pages', frame_file)
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    page.frames.append(f.read())
        
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
        self.current_page = directory.root
        self.selected_entry = 0
        self.credit = 0.0
        self.show_page = None
        self.show_frame_index = 0
        self.dir_page_offset = 0
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
        log.info('Login OK: %s', user_id)
        return self._make_welcome_frame(user)
    
    def handle_command(self, data):
        """
        Process a command packet from the client.
        data[0] = command byte
        data[1:] = parameters
        Returns response bytes to send back.
        """
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
        elif cmd == CMD_VOTE:
            return self._cmd_vote(params)
        elif cmd == CMD_MAIL:
            return self._cmd_mail()
        elif cmd == CMD_BUY:
            return self._cmd_buy(params)
        elif cmd == ord('N'):
            return self._cmd_more(params)
        else:
            return self._make_error(ascii_to_petscii('UNKNOWN COMMAND'))
    
    def handle_goto(self, page_num):
        """Handle GOTO to a specific page number."""
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
        """DIR command - enter sub-directory of selected entry, or go up if not a directory."""
        offset = getattr(self, 'dir_page_offset', 0)
        visible_children = self.current_page.children[offset:offset+11]
        
        if self.selected_entry < len(visible_children):
            # Selected a real entry
            child = visible_children[self.selected_entry]
            if child.has_subdir():
                self.current_page = child
                self.selected_entry = 0
                self.dir_page_offset = 0
            elif self.current_page.parent:
                # Not a directory entry - go up to parent
                self.current_page = self.current_page.parent
                self.selected_entry = 0
                self.dir_page_offset = 0
        else:
            # Selected the ***MORE*** entry - show next page
            self.dir_page_offset = offset + 11
            self.selected_entry = 0
        return self._make_dir_response()
    
    def _cmd_show(self, params):
        """SHOW command - display frames of selected entry."""
        if self.selected_entry < len(self.current_page.children):
            child = self.current_page.children[self.selected_entry]
            if child.frames:
                self.show_page = child
                self.show_frame_index = 0
                return self._send_current_frame()
        return self._make_error(ascii_to_petscii('NO TEXT'))
    
    def _cmd_more(self, params):
        """MORE command - show next frame of current page."""
        if hasattr(self, 'show_page') and self.show_page:
            if self.show_frame_index < len(self.show_page.frames) - 1:
                self.show_frame_index += 1
                return self._send_current_frame()
        return bytes([RESP_ACK])
    
    def _send_current_frame(self):
        """Send the current frame being viewed."""
        if self.show_page and self.show_frame_index < len(self.show_page.frames):
            frame_data = self.show_page.frames[self.show_frame_index]
            has_more = self.show_frame_index < len(self.show_page.frames) - 1
            response = bytearray([RESP_FRAME])
            response.append(0x01 if has_more else 0x00)  # more-pages flag
            response.extend(frame_data)
            return bytes(response)
        return bytes([RESP_ACK])
    
    def _cmd_accnt(self):
        """ACCNT command - return account info frame."""
        # Build a simple account info frame
        frame = bytearray()
        frame.append(0x00)  # frame start
        frame.append(0xF6)  # border = blue
        frame.append(0xF1)  # bg = white
        frame.append(PETSCII_UPPER)
        frame.append(PETSCII_RETURN)
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')  # 3 spaces
        frame.append(PETSCII_RED)
        frame.extend(ascii_to_petscii('ACCOUNT INFORMATION'))
        frame.append(PETSCII_RETURN)
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')
        frame.append(PETSCII_BLUE)
        frame.extend(ascii_to_petscii('USER ID : '))
        frame.extend(ascii_to_petscii(self.user_id or 'GUEST'))
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')
        frame.extend(ascii_to_petscii('CREDIT  : '))
        frame.extend(ascii_to_petscii('{:.2f}'.format(self.credit)))
        frame.append(PETSCII_RETURN)
        frame.append(0x00)  # end of frame
        
        return bytes([RESP_FRAME, 0x00]) + bytes(frame)
    
    def _cmd_back(self):
        """BACK command - go to previous page, or parent directory if on first page."""
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
        return bytes([RESP_ACK])
    
    def _cmd_mail(self):
        """MAIL command - no mail for now."""
        frame = bytearray()
        frame.append(0x00)
        frame.append(0xF6)  # border blue
        frame.append(0xF1)  # bg white
        frame.append(PETSCII_UPPER)
        frame.append(PETSCII_RETURN)
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')
        frame.append(PETSCII_RED)
        frame.extend(ascii_to_petscii('COURIER'))
        frame.append(PETSCII_RETURN)
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')
        frame.append(PETSCII_BLUE)
        frame.extend(ascii_to_petscii('NO MAIL WAITING'))
        frame.append(PETSCII_RETURN)
        frame.append(0x00)
        
        return bytes([RESP_FRAME, 0x00]) + bytes(frame)
    
    def _cmd_buy(self, params):
        """BUY command."""
        return self._make_error(ascii_to_petscii('NOTHING TO BUY'))
    
    def _make_dir_response(self):
        """Build a directory listing response.
        
        From the disassembly: the server sends structured data with
        fields separated by $2C (comma), entries by $0D, terminated by $00.
        The client parses this, stores in RAM, and renders locally.
        
        Entry format (comma-separated fields):
          page_number,title,type_string,price,life,author,vote
        """
        page = self.current_page
        
        data = bytearray()
        data.append(RESP_DIR)
        
        # Number of entries (max 11 per page + ***MORE*** if more exist, fitting 12 rows)
        offset = getattr(self, 'dir_page_offset', 0)
        page_children = page.children[offset:]
        has_more = len(page_children) > 11
        visible = page_children[:11] if has_more else page_children
        entry_count = len(visible) + (1 if has_more else 0)
        data.append(entry_count)
        
        # Routing/title of current directory
        data.extend(ascii_to_petscii(page.title))
        data.append(PETSCII_RETURN)
        
        # Directory entries (comma-separated fields, CR-terminated)
        for child in visible:
            # Page number
            data.extend(ascii_to_petscii(str(child.page_num)))
            data.append(0x2C)  # comma
            
            # Title
            data.extend(ascii_to_petscii(child.title))
            data.append(0x2C)
            
            # Type string
            data.extend(ascii_to_petscii(child.type_string()))
            data.append(0x2C)
            
            # Price
            if child.price > 0:
                data.extend(ascii_to_petscii('{:.2f}'.format(child.price)))
            data.append(0x2C)
            
            # Life (days)
            if child.life > 0:
                data.extend(ascii_to_petscii(str(child.life)))
            data.append(0x2C)
            
            # Author
            data.extend(ascii_to_petscii(child.author))
            data.append(0x2C)
            
            # Vote
            if child.vote > 0:
                data.extend(ascii_to_petscii(str(child.vote)))
            
            data.append(PETSCII_RETURN)  # end of entry
        
        # Add ***MORE*** entry if there are more pages
        if has_more:
            data.extend(ascii_to_petscii('0'))       # page number (dummy)
            data.append(0x2C)
            data.extend(ascii_to_petscii('***MORE***'))
            data.append(0x2C)
            data.extend(ascii_to_petscii('D+'))
            data.append(0x2C)  # price
            data.append(0x2C)  # life
            data.append(0x2C)  # author
            data.append(0x2C)  # vote
            data.append(PETSCII_RETURN)
        
        data.append(0x00)  # end of listing
        return bytes(data)
    
    def _make_frame_response(self, frame_data):
        """Wrap frame data in a response packet."""
        return bytes([RESP_FRAME]) + frame_data
    
    def _make_welcome_frame(self, user):
        """Build the personal information welcome screen."""
        welcome_path = os.path.join(CONTENT_DIR, 'pages', 'welcome.seq')
        if os.path.exists(welcome_path):
            with open(welcome_path, 'rb') as f:
                frame_data = f.read()
            return bytes([RESP_FRAME, 0x00]) + frame_data  # 0x00 = no more pages
        
        # Fallback: generate a simple welcome frame
        frame = bytearray()
        frame.append(0x00)  # frame start
        frame.append(0xF6)  # border = blue
        frame.append(0xF1)  # bg = white
        frame.append(0x8E)  # uppercase charset
        frame.append(PETSCII_RETURN)
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')
        frame.append(PETSCII_RED)
        frame.extend(ascii_to_petscii('COMPUNET'))
        frame.append(PETSCII_RETURN)
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')
        frame.append(PETSCII_BLUE)
        frame.extend(ascii_to_petscii('USER : '))
        frame.extend(ascii_to_petscii(user.get('name', self.user_id)))
        frame.append(PETSCII_RETURN)
        frame.append(PETSCII_RETURN)
        frame.extend(b'\x06\x03')
        frame.extend(ascii_to_petscii('WELCOME TO COMPUNET'))
        frame.append(PETSCII_RETURN)
        frame.append(0x00)  # end
        return bytes([RESP_FRAME, 0x00]) + bytes(frame)
    
    def _make_error(self, message_petscii):
        """Build an error response."""
        return bytes([RESP_ERROR]) + message_petscii + b'\x00'


# ============================================================
# WebSocket interface - binary protocol over WebSocket frames
# ============================================================

async def ws_handler(websocket):
    """Handle a WebSocket connection. Same protocol as TCP but over WebSocket binary frames."""
    directory = CompunetDirectory()
    session = CompunetSession(directory)
    
    log.info('WebSocket client connected: %s', websocket.remote_address)
    
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
            await websocket.send(response)
            
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
                await websocket.send(response)
    
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        log.info('WebSocket client disconnected')


# ============================================================
# TCP interface - raw protocol for C64 clients
# ============================================================

async def tcp_handler(reader, writer):
    """Handle a TCP connection from a real C64 via WiFi modem."""
    addr = writer.get_extra_info('peername')
    log.info('TCP client connected: %s', addr)
    
    directory = CompunetDirectory()
    session = CompunetSession(directory)
    
    # TODO: Implement full X.25 packet framing ($01 header $02)
    # For now, use a simplified framing: length byte + data
    
    try:
        # No handshake - wait for login data directly.
        # The ROM sends a CR (break-cancel) then login credentials.
        # We ignore the CR and accumulate until we find the login pattern.
        #
        # Packet format from ROM: sent byte-by-byte via raw ACIA
        # The ROM sends 27 bytes ($1B) from $C100 buffer containing:
        #   Byte 0: command letter 'Z' ($5A) = login/ID check
        #   Bytes 1-8: User ID (padded with spaces to 8 chars)
        #   Bytes 9-14: Password (padded with spaces to 6 chars)  
        #   Remaining: ROM version/system info bytes
        #
        # But the ROM also wraps this in X.25 framing via $94C1:
        #   $01 (start) + header bytes + payload + $02 (end)
        # These are sent repeatedly until ACKed.
        #
        # For now: accumulate bytes, look for the login data pattern.
        # The user ID "TEST" padded = "TEST    " and password "TEST" padded = "TEST  "
        
        # Read until we have enough data to find the login credentials
        # The ROM sends the packet repeatedly (~every 2 seconds) until it gets a response
        buffer = bytearray()
        
        while True:
            try:
                data = await asyncio.wait_for(reader.read(256), timeout=30.0)
            except asyncio.TimeoutError:
                log.info('TCP: timeout waiting for login data')
                return
            if not data:
                log.info('TCP: connection closed by client')
                return
            buffer.extend(data)
            log.debug('TCP RX buffer: %d bytes total', len(buffer))
            log.debug('TCP RX buffer hex: %s', buffer.hex())
            
            # Look for the login data in the buffer
            # From the ROM disassembly:
            #   $C100 = command byte ('Z' = $5A for login)
            #   $C101-$C108 = User ID (8 bytes, space-padded)
            #   $C109-$C10E = Password (6 bytes, space-padded)
            #   $C10F-$C119 = System info (ROM version etc)
            #
            # The packet is sent with X.25 framing prepended by $94C1:
            #   $01 <header bytes> <$C100 payload> $02
            # And repeated every ~2 seconds until ACKed.
            #
            # Strategy: find 'Z' ($5A) byte that's followed by plausible
            # ASCII user ID data (letters/spaces in $20-$5A range)
            
            if len(buffer) < 27:
                continue  # Need at least 27 bytes
            for idx in range(len(buffer) - 26):
                if buffer[idx] == 0x5A:  # 'Z' command
                    # Check if next 8 bytes look like a user ID (printable PETSCII)
                    candidate = buffer[idx+1:idx+9]
                    if all(0x20 <= b <= 0x5A for b in candidate):
                        # Found it - extract user ID and password
                        user_id = candidate.decode('latin-1').strip()
                        password = buffer[idx+9:idx+15].decode('latin-1', errors='replace').strip()
                        
                        log.info('TCP: login found at offset %d', idx)
                        log.info('TCP: user_id=%r password=%r', user_id, password)
                        
                        response = session.handle_login(user_id, password)
                        if session.authenticated:
                            # Send linking data immediately - the ROM is waiting
                            # Any remaining ROM packet bytes will be interleaved
                            # but the ROM won't send more until it gets a response
                            
                            # Now send linking data (terminal software download)
                            cnet_path = os.path.join(os.path.dirname(__file__), '..', 'historical', 'cnet.prg')
                            with open(cnet_path, 'rb') as cf:
                                cnet_data = cf.read()
                            terminal_code = cnet_data[2:]  # strip PRG header
                            
                            linking = bytearray()
                            linking.append(0x00)  # header 1
                            linking.append(0x00)  # header 2
                            linking.append(0x05)  # return addr low ($A005)
                            linking.append(0xA0)  # return addr high
                            linking.append(0xF0)  # dest addr low ($9FF0)
                            linking.append(0x9F)  # dest addr high
                            linking.append(len(terminal_code) & 0xFF)  # length low
                            linking.append((len(terminal_code) >> 8) & 0xFF)  # length high
                            linking.extend(terminal_code)
                            
                            log.info('TCP TX: linking %d bytes (code=%d)', len(linking), len(terminal_code))
                            # Send all at once - NMI mode + tcpser handles flow control
                            writer.write(bytes(linking))
                            await writer.drain()
                            log.info('TCP TX: linking complete')
                        else:
                            # Auth failed - close connection so tcpser signals NO CARRIER
                            # and the ROM returns to BASIC (matches original Compunet
                            # behaviour where failed auth dropped the modem connection)
                            log.info('Login failed for %r - closing connection', user_id)
                            writer.close()
                            await writer.wait_closed()
                            return
                        break
            else:
                # Haven't found login yet, keep reading
                continue
            break  # Found and processed login
        
        log.info('TCP: login complete, entering command loop')
        
        # Command loop
        while True:
            data = await reader.read(256)
            if not data:
                log.info('TCP: connection closed by client')
                break
            
            log.info('TCP RX: %d bytes: %s', len(data), data.hex())
            log.info('TCP RX (printable): %s', ''.join(chr(b) if 32 <= b < 127 else '.' for b in data))
            
            response = session.handle_command(data)
            if response:
                log.info('TCP TX: %d bytes: %s', len(response), response[:32].hex())
                writer.write(response)
                await writer.drain()
    
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
