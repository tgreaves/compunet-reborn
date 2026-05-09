"""
Compunet Server - Recreated from reverse-engineered protocol.

Provides two interfaces:
  - WebSocket (port 6502) for the web client
  - TCP (port 6400) for real C64 clients via WiFi modem

Protocol:
  Client sends COM packets: single ASCII letter + parameters
  Server responds with frames (DAT) or status codes

Application-layer commands:
  'A' = ACCNT (account info)
  'B' = BUY (download program/show paid text)
  'C' = BACK (parent directory)
  'D' = DIR (directory listing)
  'E' = EDITR (enter editor online)
  'I' = ID (check user ID)
  'M' = MAIL (Courier mailbox)
  'P' = SHOW (read text frames)
  'U' = UPLD (upload content)
  'V' = VOTE (vote on content)
"""

import asyncio
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


class CompunetPage:
    """A single page/frame in the Compunet directory tree."""
    
    def __init__(self, page_num, title, page_type='T', size=0, price=0, author='SYSTEM'):
        self.page_num = page_num
        self.title = title
        self.page_type = page_type  # T=text, P=program, PP=protected, D=directory, L=link
        self.size = size
        self.price = price
        self.author = author
        self.vote = 0
        self.vote_count = 0
        self.children = []  # sub-directory entries
        self.frames = []    # list of frame data (bytes) for text pages
        self.parent = None
    
    def has_subdir(self):
        return len(self.children) > 0


class CompunetDirectory:
    """The Compunet content tree."""
    
    def __init__(self):
        self.pages = {}  # page_num -> CompunetPage
        self.root = None
        self._build_default_tree()
    
    def _build_default_tree(self):
        """Build a default directory structure."""
        # Root directory
        root = CompunetPage(1, 'COMPUNET', 'D')
        self.root = root
        self.pages[1] = root
        
        # Main directory entries (from the manual)
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
        
        # Load any SEQ files as content
        self._load_seq_content()
    
    def _load_seq_content(self):
        """Load SEQ files from the content directory as page frames."""
        seq_dir = os.path.join(CONTENT_DIR, 'pages')
        if not os.path.exists(seq_dir):
            return
        
        for seq_file in sorted(glob.glob(os.path.join(seq_dir, '*.seq'))):
            name = Path(seq_file).stem
            with open(seq_file, 'rb') as f:
                frame_data = f.read()
            
            # Find or create a page for this file
            # Use hash of filename as page number (above 10000)
            page_num = 10000 + (hash(name) % 90000)
            if page_num in self.pages:
                page_num += 1
            
            page = CompunetPage(page_num, name.upper(), 'T', 1)
            page.frames = [frame_data]
            page.parent = self.root
            self.root.children.append(page)
            self.pages[page_num] = page
    
    def get_page(self, page_num):
        return self.pages.get(page_num)
    
    def get_directory_listing(self, page):
        """Generate directory listing data for a page."""
        if not page.children:
            return None
        
        entries = []
        for child in page.children:
            type_str = child.page_type
            if child.size > 0:
                type_str += str(child.size)
            if child.has_subdir():
                type_str += '+'
            entries.append({
                'page_num': child.page_num,
                'title': child.title,
                'type': type_str,
                'author': child.author,
                'vote': child.vote,
            })
        return entries


class CompunetSession:
    """A single client session."""
    
    def __init__(self, directory):
        self.directory = directory
        self.user_id = None
        self.authenticated = False
        self.current_page = directory.root
        self.credit = 0.0
    
    def login(self, user_id, password):
        """Authenticate a user. For now, accept anything."""
        self.user_id = user_id
        self.authenticated = True
        log.info('User logged in: %s', user_id)
        return True
    
    def handle_command(self, cmd_byte, params):
        """
        Handle an application-layer command.
        Returns a response dict with type and data.
        """
        cmd = chr(cmd_byte) if isinstance(cmd_byte, int) else cmd_byte
        
        log.info('Command: %s params=%s', cmd, params.hex() if params else '')
        
        if cmd == 'D':
            return self._cmd_dir(params)
        elif cmd == 'P':
            return self._cmd_show(params)
        elif cmd == 'A':
            return self._cmd_accnt()
        elif cmd == 'V':
            return self._cmd_vote(params)
        elif cmd == 'C':
            return self._cmd_back()
        elif cmd == 'M':
            return self._cmd_mail()
        else:
            log.warning('Unknown command: %s', cmd)
            return {'type': 'error', 'message': 'UNKNOWN COMMAND'}
    
    def _cmd_dir(self, params):
        """DIR - return directory listing."""
        listing = self.directory.get_directory_listing(self.current_page)
        if listing is None:
            return {'type': 'error', 'message': 'NO DIRECTORY'}
        return {'type': 'directory', 'entries': listing, 'page': self.current_page.page_num}
    
    def _cmd_show(self, params):
        """SHOW - return page frames."""
        # For now, show the first frame of the current highlighted entry
        # In a full implementation, params would contain the page number
        return {'type': 'frame', 'data': None, 'message': 'NO CONTENT'}
    
    def _cmd_accnt(self):
        """ACCNT - return account info."""
        return {
            'type': 'account',
            'user_id': self.user_id,
            'credit': self.credit,
        }
    
    def _cmd_vote(self, params):
        """VOTE - register a vote."""
        return {'type': 'ok', 'message': 'VOTE REGISTERED'}
    
    def _cmd_back(self):
        """BACK - go to parent directory."""
        if self.current_page.parent:
            self.current_page = self.current_page.parent
        return self._cmd_dir(b'')
    
    def _cmd_mail(self):
        """MAIL - access Courier."""
        return {'type': 'mail', 'messages': [], 'message': 'NO MAIL'}


# ============================================================
# WebSocket interface (for web client)
# ============================================================

async def ws_handler(websocket):
    """Handle a WebSocket connection from the web client."""
    directory = CompunetDirectory()
    session = CompunetSession(directory)
    
    log.info('WebSocket client connected: %s', websocket.remote_address)
    
    try:
        # Send welcome/login prompt
        await websocket.send(json.dumps({
            'type': 'login_prompt',
        }))
        
        async for message in websocket:
            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                continue
            
            msg_type = msg.get('type', '')
            
            if msg_type == 'login':
                user_id = msg.get('user_id', 'GUEST')
                password = msg.get('password', '')
                if session.login(user_id, password):
                    # Send initial directory
                    listing = directory.get_directory_listing(directory.root)
                    await websocket.send(json.dumps({
                        'type': 'login_ok',
                        'user_id': user_id,
                        'directory': listing,
                    }))
                else:
                    await websocket.send(json.dumps({
                        'type': 'login_fail',
                        'message': 'INVALID ID OR PASSWORD',
                    }))
            
            elif msg_type == 'command':
                cmd = msg.get('cmd', '')
                params = bytes.fromhex(msg.get('params', ''))
                response = session.handle_command(cmd, params)
                await websocket.send(json.dumps(response))
            
            elif msg_type == 'goto':
                page_num = msg.get('page', 0)
                page = directory.get_page(page_num)
                if page:
                    session.current_page = page
                    if page.frames:
                        # Send frame data as base64
                        import base64
                        await websocket.send(json.dumps({
                            'type': 'frame',
                            'data': base64.b64encode(page.frames[0]).decode('ascii'),
                            'title': page.title,
                        }))
                    elif page.has_subdir():
                        listing = directory.get_directory_listing(page)
                        await websocket.send(json.dumps({
                            'type': 'directory',
                            'entries': listing,
                            'page': page.page_num,
                        }))
                    else:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': 'NO CONTENT',
                        }))
                else:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'PAGE NOT FOUND',
                    }))
    
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        log.info('WebSocket client disconnected')


# ============================================================
# TCP interface (for real C64 clients)
# ============================================================

async def tcp_handler(reader, writer):
    """Handle a TCP connection from a real C64 client."""
    addr = writer.get_extra_info('peername')
    log.info('TCP client connected: %s', addr)
    
    # TODO: Implement the raw Compunet protocol
    # This would handle:
    # 1. Login sequence (receive user ID + password)
    # 2. Send linking payload (cnet.prg binary)
    # 3. Enter command/response loop using the X.25 packet protocol
    
    writer.write(b'COMPUNET SERVER - NOT YET IMPLEMENTED\r\n')
    await writer.drain()
    writer.close()
    await writer.wait_closed()
    log.info('TCP client disconnected: %s', addr)


# ============================================================
# Main
# ============================================================

async def main():
    # Create content directory if it doesn't exist
    os.makedirs(os.path.join(CONTENT_DIR, 'pages'), exist_ok=True)
    
    # Start WebSocket server
    ws_server = await websockets.serve(ws_handler, '0.0.0.0', WS_PORT)
    log.info('WebSocket server listening on port %d', WS_PORT)
    
    # Start TCP server
    tcp_server = await asyncio.start_server(tcp_handler, '0.0.0.0', TCP_PORT)
    log.info('TCP server listening on port %d', TCP_PORT)
    
    log.info('Compunet server ready.')
    log.info('  Web client: ws://localhost:%d', WS_PORT)
    log.info('  C64 client: tcp://localhost:%d', TCP_PORT)
    
    # Run forever
    async with ws_server, tcp_server:
        await asyncio.gather(
            ws_server.serve_forever(),
            tcp_server.serve_forever(),
        )


if __name__ == '__main__':
    asyncio.run(main())
