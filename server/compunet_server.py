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

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
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
    
    def __init__(self, page_num, title, page_type='T', size=0, author='SYSTEM'):
        self.page_num = page_num
        self.title = title
        self.page_type = page_type
        self.size = size
        self.author = author
        self.vote = 0
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
    """The content tree."""
    
    def __init__(self):
        self.pages = {}
        self.root = None
        self._build_tree()
    
    def _build_tree(self):
        root = CompunetPage(1, 'COMPUNET', 'D')
        self.root = root
        self.pages[1] = root
        
        entries = [
            (100, 'WELCOME', 'T', 8),
            (107, 'COMPUNET NEWS', 'T', 0),
            (120, 'FULL GUIDE', 'T', 12),
            (140, 'COURIER GUIDE', 'T', 6),
            (150, 'INDEX', 'D', 0),
            (202, 'NEWS', 'T', 0),
            (210, 'COMMODORE NEWS', 'T', 0),
            (231, 'TELESOFTWARE', 'D', 0),
            (310, 'TELESHOPPING', 'D', 0),
            (600, 'GENERAL JUNGLE', 'D', 0),
            (2020, 'COMMS SOFTWARE', 'P', 6),
        ]
        
        for page_num, title, ptype, size in entries:
            page = CompunetPage(page_num, title, ptype, size)
            page.parent = root
            root.children.append(page)
            self.pages[page_num] = page
        
        self._load_content()
    
    def _load_content(self):
        """Load SEQ files from content/pages/ as servable frames."""
        pages_dir = os.path.join(CONTENT_DIR, 'pages')
        if not os.path.exists(pages_dir):
            return
        
        page_num = 10001
        for seq_file in sorted(glob.glob(os.path.join(pages_dir, '*.seq'))):
            name = Path(seq_file).stem
            with open(seq_file, 'rb') as f:
                frame_data = f.read()
            
            page = CompunetPage(page_num, name.upper()[:20], 'T', 1)
            page.frames = [frame_data]
            page.parent = self.root
            self.root.children.append(page)
            self.pages[page_num] = page
            page_num += 1


class CompunetSession:
    """A client session - same logic for WebSocket and TCP clients."""
    
    def __init__(self, directory):
        self.directory = directory
        self.user_id = None
        self.authenticated = False
        self.current_page = directory.root
        self.selected_entry = 0
        self.credit = 0.0
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
            return self._make_frame_response(page.frames[0])
        else:
            return self._make_error(ascii_to_petscii('NO CONTENT'))
    
    def handle_select(self, index):
        """Handle selection of a directory entry by index."""
        if 0 <= index < len(self.current_page.children):
            self.selected_entry = index
        return b''  # No response needed for selection change
    
    def _cmd_dir(self, params):
        """DIR command - enter sub-directory of selected entry."""
        if self.selected_entry < len(self.current_page.children):
            child = self.current_page.children[self.selected_entry]
            if child.has_subdir():
                self.current_page = child
                self.selected_entry = 0
        return self._make_dir_response()
    
    def _cmd_show(self, params):
        """SHOW command - display frames of selected entry."""
        if self.selected_entry < len(self.current_page.children):
            child = self.current_page.children[self.selected_entry]
            if child.frames:
                return self._make_frame_response(child.frames[0])
        return self._make_error(ascii_to_petscii('NO TEXT'))
    
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
        
        return bytes([RESP_FRAME]) + bytes(frame)
    
    def _cmd_back(self):
        """BACK command - go to parent directory."""
        if self.current_page.parent:
            self.current_page = self.current_page.parent
            self.selected_entry = 0
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
        
        return bytes([RESP_FRAME]) + bytes(frame)
    
    def _cmd_buy(self, params):
        """BUY command."""
        return self._make_error(ascii_to_petscii('NOTHING TO BUY'))
    
    def _make_dir_response(self):
        """Build a directory listing response in protocol format."""
        page = self.current_page
        
        # Directory response: RESP_DIR + PETSCII-encoded listing
        # Each entry: page_num(5 ascii digits) + space + title + space + type + $0D
        # Terminated by $00
        data = bytearray()
        data.append(RESP_DIR)
        
        # Header: page number and routing
        data.append(PETSCII_RETURN)
        data.append(PETSCII_RED)
        data.extend(b'\x06\x02')  # 2 spaces
        data.extend(ascii_to_petscii(page.title))
        data.append(PETSCII_RETURN)
        data.append(PETSCII_RETURN)
        
        # Entries
        for child in page.children:
            data.append(PETSCII_BLUE)
            # Page number (right-aligned in 5 chars)
            num_str = str(child.page_num).rjust(5)
            data.extend(ascii_to_petscii(num_str))
            data.append(0x20)  # space
            
            # Title
            data.append(PETSCII_WHITE)
            title = child.title[:20].ljust(20)
            data.extend(ascii_to_petscii(title))
            
            # Type
            data.append(PETSCII_GREEN)
            data.extend(ascii_to_petscii(child.type_string()))
            
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
            return bytes([RESP_FRAME]) + frame_data
        
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
        return bytes([RESP_FRAME]) + bytes(frame)
    
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
        # Send login prompt (simplified - real protocol would use packet framing)
        # For now just close - full implementation needed
        writer.write(b'\x00')  # placeholder
        await writer.drain()
        
        # Read login
        data = await reader.read(256)
        if not data:
            return
        
        parts = data.split(b'\x00')
        user_id = parts[0].decode('latin-1', errors='replace') if parts else 'GUEST'
        password = parts[1].decode('latin-1', errors='replace') if len(parts) > 1 else ''
        
        response = session.handle_login(user_id, password)
        writer.write(response)
        await writer.drain()
        
        # Command loop
        while True:
            data = await reader.read(256)
            if not data:
                break
            
            response = session.handle_command(data)
            if response:
                writer.write(response)
                await writer.drain()
    
    except (ConnectionResetError, BrokenPipeError):
        pass
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
