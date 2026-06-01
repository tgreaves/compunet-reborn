"""
PETSCII Terminal Mode — server-rendered BBS interface for Compunet Reborn.

Allows any standard PETSCII terminal program (CCGMS, StrikeTerm, etc.) to
connect on port 6401 without needing the custom protocol client.

The server renders all screens (directories, frames, duckshoot) as PETSCII
control codes and sends them to the terminal. Navigation via cursor keys.
"""

import asyncio
import datetime
import logging
import os
import hashlib

logger = logging.getLogger(__name__)

# PETSCII control codes
CLR = b'\x93'           # Clear screen
HOME = b'\x13'          # Cursor home
CR = b'\x0d'            # Carriage return
CRSR_DOWN = b'\x11'     # Cursor down
CRSR_UP = b'\x91'       # Cursor up
CRSR_RIGHT = b'\x1d'    # Cursor right
CRSR_LEFT = b'\x9d'     # Cursor left
RVS_ON = b'\x12'        # Reverse video on
RVS_OFF = b'\x92'       # Reverse video off
COL_WHITE = b'\x05'
COL_RED = b'\x1c'
COL_BLUE = b'\x1f'
COL_GREEN = b'\x1e'
COL_PURPLE = b'\x9c'
COL_CYAN = b'\x9f'
COL_YELLOW = b'\x9e'
UPPERCASE = b'\x8e'     # Switch to uppercase/graphics mode
LOWERCASE = b'\x0e'     # Switch to lowercase/uppercase mode

# Key codes received from terminal
KEY_RETURN = 0x0D
KEY_DEL = 0x14
KEY_CRSR_DOWN = 0x11
KEY_CRSR_UP = 0x91
KEY_CRSR_RIGHT = 0x1D
KEY_CRSR_LEFT = 0x9D
KEY_F7 = 0x88
KEY_F8 = 0x8C
KEY_RUNSTOP = 0x03

# Duckshoot commands by mode (from C64 ROM at $A176/$A21E)
DUCK_DIR = ['HELP', 'DIR', 'SHOW', 'BACK', 'GOTO', 'UCAT', 'MAIL', 'ACCNT',
            'SAVE', 'EDITR', 'LEAVE', 'PRINT', 'LIFE', 'BUY', 'LOAD', 'UPLD', 'VOTE']
DUCK_FRAME = ['MORE', 'FINISH']
DUCK_MAIL = ['ID', 'EDITR', 'DONE', 'SEND', 'SHOW', 'MORE']
DUCK_UPLOAD = ['SEND', 'ABORT']
DUCK_UPLOAD_TEXT = ['SEND', 'FINSH', 'LAST', 'NEXT', 'EDITR']
DUCK_EDITOR = ['RETURN', 'HELP', 'EDIT', 'LAST', 'NEXT', 'NEW',
               'COPY', 'ERASE', 'GET', 'PUT', 'STORE', 'PRINT', 'FREE']

# Import server components (deferred to avoid circular imports)
_server_module = None


def _get_server():
    global _server_module
    if _server_module is None:
        import compunet_server as cs
        _server_module = cs
    return _server_module


def ascii_to_petscii_shifted(text):
    """Convert ASCII text to PETSCII for shifted (lowercase+uppercase) mode.

    $41-$5A = lowercase a-z, $C1-$DA = uppercase A-Z.
    """
    result = bytearray()
    for ch in text:
        b = ord(ch)
        if 0x41 <= b <= 0x5A:       # ASCII uppercase → PETSCII uppercase ($C1-$DA)
            result.append(b + 0x80)
        elif 0x61 <= b <= 0x7A:     # ASCII lowercase → PETSCII lowercase ($41-$5A)
            result.append(b - 0x20)
        else:
            result.append(b)
    return bytes(result)


def ascii_to_petscii_unshifted(text):
    """Convert ASCII text to PETSCII for unshifted (uppercase/graphics) mode.

    $41-$5A = uppercase A-Z. No lowercase available.
    """
    result = bytearray()
    for ch in text:
        b = ord(ch)
        if 0x61 <= b <= 0x7A:       # ASCII lowercase → uppercase ($41-$5A)
            result.append(b - 0x20)
        else:
            result.append(b)
    return bytes(result)


# Default alias for backward compat (template replacements in welcome frame use this)
ascii_to_petscii = ascii_to_petscii_shifted


def expand_frame(frame_data):
    """Expand Compunet .seq frame data to raw PETSCII for terminal display.

    Handles Compunet-specific extensions:
      $00 = end of frame
      $06 <N> = repeat space (1 + N) times
      $07 <char> <count> = RLE (repeat char (1 + count) times)
    The count byte is additional repeats after the initial emission.
    All other bytes pass through unchanged for the terminal to interpret.

    Tracks column position to suppress CR after a full 40-char line
    (the terminal auto-wraps, so CR would create a blank line).
    """
    result = bytearray()
    col = 0
    i = 4  # Skip bytes 0-3: flags, duckshoot colour, border colour, background colour
    while i < len(frame_data):
        b = frame_data[i]
        if b == 0x00:
            break
        elif b == 0x06:
            i += 1
            if i < len(frame_data):
                count = frame_data[i] + 1
                result.extend(b'\x20' * count)
                col += count
        elif b == 0x07:
            i += 1
            if i + 1 < len(frame_data):
                char = frame_data[i]
                i += 1
                count = frame_data[i] + 1
                result.extend(bytes([char]) * count)
                col += count
        elif b == 0x0D:
            if col >= 40:
                # Terminal already wrapped — CR would skip a line, so just reset col
                col = 0
            else:
                result.append(b)
                col = 0
        elif b < 0x20 or (0x80 <= b <= 0x9F):
            result.append(b)
        else:
            result.append(b)
            col += 1
        i += 1
    return bytes(result)


class TerminalSession:
    """A PETSCII terminal session — renders Compunet server-side."""

    def __init__(self, reader, writer, directory):
        self.reader = reader
        self.writer = writer
        self.directory = directory
        self.user_id = None
        self.authenticated = False
        self.current_page = directory.root
        self.dir_cursor = 0
        self.dir_offset = 0
        self.dir_column = 0         # 0=PRICE, 1=LIFE, 2=AUTHOR, 3=VOTE
        self.mail_column = 0        # 0=SENDER, 1=DATE, 2=STATUS
        self.duck_pos = 0
        self.mode = 'login'         # login, directory, frame, mail
        self.show_page = None
        self.show_frame_idx = 0
        self.client_ip = ''
        self.telnet = False
        self.charset = 'upper'  # 'upper' = unshifted (default), 'lower' = shifted
        self.terminal_type = 'c64'  # 'c64' or 'pc'
        self._upload_pending = None
        self._ucat_active = False
        self._ucat_saved_page = None
        self._ucat_saved_cursor = 0
        self._ucat_saved_offset = 0
        self._frame_memory = []    # Last 20 frames viewed (raw frame data)
        self._editor_idx = 0       # Current position in frame memory
        self.entries_row = 8  # screen row where directory entries start

    # --- I/O helpers ---

    async def send(self, data):
        """Send raw bytes to terminal. Escapes $FF for Telnet."""
        if self.telnet:
            data = data.replace(b'\xff', b'\xff\xff')
        self.writer.write(data)
        await self.writer.drain()

    async def send_text(self, text):
        """Send ASCII text converted to PETSCII based on current charset mode."""
        if self.charset == 'upper':
            await self.send(ascii_to_petscii_unshifted(text))
        else:
            await self.send(ascii_to_petscii_shifted(text))

    async def set_charset(self, mode):
        """Switch charset mode: 'upper' (unshifted) or 'lower' (shifted).

        For PC terminals, charset switching is suppressed (they use a fixed font).
        The tracking is still updated so send_text uses the correct conversion.
        """
        if mode == 'upper' and self.charset != 'upper':
            if self.terminal_type == 'c64':
                await self.send(UPPERCASE)
            self.charset = 'upper'
        elif mode == 'lower' and self.charset != 'lower':
            if self.terminal_type == 'c64':
                await self.send(LOWERCASE)
            self.charset = 'lower'

    async def cursor_to(self, row, col):
        """Position cursor using HOME + cursor-down/right."""
        out = bytearray(HOME)
        out.extend(CRSR_DOWN * row)
        out.extend(CRSR_RIGHT * col)
        await self.send(bytes(out))

    async def read_key(self):
        """Read a single byte from the terminal, skipping Telnet IAC sequences."""
        if hasattr(self, '_first_byte') and self._first_byte is not None:
            b = self._first_byte
            self._first_byte = None
            return b
        while True:
            data = await asyncio.wait_for(self.reader.read(1), timeout=300.0)
            if not data:
                raise ConnectionResetError("Client disconnected")
            b = data[0]
            if b == 0xFF and self.telnet:
                # IAC — read command byte
                cmd_data = await asyncio.wait_for(self.reader.read(1), timeout=5.0)
                if not cmd_data:
                    raise ConnectionResetError("Client disconnected")
                cmd = cmd_data[0]
                if cmd in (0xFB, 0xFC, 0xFD, 0xFE):
                    # WILL/WONT/DO/DONT — skip the option byte
                    await asyncio.wait_for(self.reader.read(1), timeout=5.0)
                elif cmd == 0xFA:
                    # Subnegotiation — read until IAC SE (FF F0)
                    while True:
                        sb = await asyncio.wait_for(self.reader.read(1), timeout=5.0)
                        if sb and sb[0] == 0xFF:
                            se = await asyncio.wait_for(self.reader.read(1), timeout=5.0)
                            if se and se[0] == 0xF0:
                                break
                elif cmd == 0xFF:
                    return 0xFF  # Escaped $FF = literal $FF
                continue
            return b

    async def read_line(self, max_len=20, echo=True, password=False):
        """Read a line of input until CR."""
        buf = bytearray()
        while True:
            key = await self.read_key()
            if key == KEY_RETURN:
                break
            elif key == KEY_DEL and buf:
                buf = buf[:-1]
                if echo:
                    await self.send(b'\x9d\x20\x9d')  # left, space, left
            elif 0x20 <= key <= 0x7E and len(buf) < max_len:
                buf.append(key)
                if echo:
                    if password:
                        await self.send(b'*')
                    else:
                        await self.send(bytes([key]))
        return buf.decode('ascii', errors='replace').upper()

    # --- Login ---

    async def do_login(self):
        """Display login screen and authenticate."""
        cs = _get_server()

        await self.send(CLR)
        await self.send(UPPERCASE)
        self.charset = 'upper'
        await self.send(COL_BLUE)
        await self.send(CR)
        version = ''
        for vp in [os.path.join(os.path.dirname(__file__), 'VERSION'),
                   os.path.join(os.path.dirname(__file__), '..', 'VERSION')]:
            if os.path.exists(vp):
                with open(vp) as f:
                    version = ' v' + f.read().strip()
                break
        await self.send_text(f'    COMPUNET REBORN{version}\r\r')
        await self.send_text('    PETSCII TERMINAL ACCESS\r\r')
        await self.send(COL_CYAN)
        await self.send_text('  Visit compunet.live for registration.\r\r')
        await self.send(COL_WHITE)
        await self.send_text('  Terminal type:\r')
        await self.send_text('    1) C64 / C64 Ultimate\r')
        await self.send_text('    2) SyncTerm / PC (C64 LOWER font)\r\r')
        await self.send_text('  Select (1/2): ')
        # Read terminal type selection
        while True:
            key = await self.read_key()
            if key == 0x31:  # '1'
                self.terminal_type = 'c64'
                await self.send(b'\x31')  # echo '1'
                break
            elif key == 0x32:  # '2'
                self.terminal_type = 'pc'
                await self.send(b'\x32')  # echo '2'
                break
        await self.send(CR + CR)
        await self.send(CR)
        await self.send_text('  Ensure terminal at 40 x 25.\r\r')

        # User ID
        await self.send(COL_WHITE)
        await self.send_text('  User ID: ')
        user_id = await self.read_line(max_len=8)
        await self.send(CR)

        # Password
        await self.send_text('  Password: ')
        password = await self.read_line(max_len=6, password=True)
        await self.send(CR + CR)

        # Authenticate
        users = cs._api_load_users()
        user = users.get(user_id)
        if not user:
            await self.send_text('  INVALID USERNAME / PASSWORD\r')
            await asyncio.sleep(2)
            return False

        pw_hash = hashlib.sha256(password.upper().encode('utf-8')).hexdigest()
        if user.get('password') != pw_hash:
            await self.send_text('  INVALID USERNAME / PASSWORD\r')
            await asyncio.sleep(2)
            return False

        self.user_id = user_id
        self.authenticated = True
        self.client_ip = self.writer.get_extra_info('peername', ('', 0))[0]

        cs._online_users.add(user_id)
        cs.audit_log('connect', user=user_id, ip=self.client_ip)

        # Build welcome frame using same logic as protocol server
        await self.send(CLR)
        await self.set_charset('upper')

        welcome_frame = self._make_welcome_frame(user)
        await self.send(expand_frame(welcome_frame))

        # Stay in uppercase mode for the duckshoot
        self.mode = 'welcome'
        await self.render_duckshoot()
        return True

    def _make_welcome_frame(self, user):
        """Build the welcome frame from template, filling placeholders."""
        import json
        cs = _get_server()

        now = datetime.datetime.now()
        MONTHS = ['JAN','FEB','MAR','APR','MAY','JUN',
                  'JUL','AUG','SEP','OCT','NOV','DEC']

        prev_date = user.get('last_login_date', '')
        prev_time = user.get('last_login_time', '')
        if not prev_date:
            prev_date = 'NEVER'
            prev_time = ''

        # Check for unread mail
        mail_file = os.path.join(cs.MAIL_DIR, self.user_id + '.json')
        mail_waiting = False
        if os.path.exists(mail_file):
            with open(mail_file, 'r') as f:
                inbox = json.load(f)
            mail_waiting = any(not m.get('read', True) for m in inbox.get('messages', []))

        # Pillarbox indicator
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

        # Pages/storage
        user_pages = [p for p in self.directory.pages.values() if p.author == self.user_id]
        pages_count = len(user_pages)
        near_death = len([p for p in user_pages if 0 < p.life < 5])
        pages_stats = f'{pages_count}/{near_death}'
        free_storage = str(user.get('free_storage', 2000))

        # Next quarter
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
        template_path = os.path.join(os.path.dirname(cs.ROOT_DIR), 'templates', 'welcome.seq')
        if os.path.exists(template_path):
            with open(template_path, 'rb') as f:
                frame = f.read()
        else:
            frame = b'\x00\x03\x0F\x8E\x0D\x1F WELCOME\x0D\x00'

        # Replace placeholders (same formula as protocol server)
        # Protocol server emits $06 <N> which C64 ROM renders as N+1 spaces.
        # We emit literal spaces, so we need N+1 to match.
        def replace_padded(frame, placeholder, value, orig_len):
            val = value.encode('ascii') if isinstance(value, str) else value
            pos = frame.find(placeholder)
            if pos < 0:
                return frame
            after = pos + len(placeholder)
            if after + 1 < len(frame) and frame[after] == 0x06:
                orig_pad = frame[after + 1]
                total_width = orig_len + orig_pad + 1
                new_pad = max(0, total_width - len(val))
                frame = frame[:pos] + val + (b'\x20' * new_pad) + frame[after + 2:]
            else:
                frame = frame[:pos] + val + frame[after:]
            return frame

        user_name = user.get('name', self.user_id).upper()
        frame = replace_padded(frame, b'{USER_NAME}', user_name, 14)
        frame = replace_padded(frame, b'{LAST_TIME}', prev_time or '', 5)
        frame = replace_padded(frame, b'{PAGES_STATS}', pages_stats, 3)
        frame = replace_padded(frame, b'{FREE_STORAGE}', free_storage, 3)
        frame = replace_padded(frame, b'{NEXT_QUARTER}', next_quarter_str, 6)
        frame = frame.replace(b'{LAST_DATE}', prev_date.ljust(9).encode('ascii'))
        frame = frame.replace(b'{PB1}', pb1)
        frame = frame.replace(b'{PB2}', pb2)
        frame = frame.replace(b'{PB3}', pb3)
        frame = frame.replace(b'{PB4}', pb4)
        frame = frame.replace(b'{PB5}', pb5)
        frame = frame.replace(b'{PB6}', pb6)

        return frame

    # --- Directory rendering ---

    # Border PETSCII bytes (unshifted charset)
    B_THICK_V = b'\x7d'    # ┃ thick vertical
    B_THIN_V = b'\x62'     # │ thin vertical
    B_THICK_H = b'\x63'    # ━ thick horizontal
    B_THIN_H = b'\x60'     # ─ thin horizontal
    B_TEE_L = b'\x75'      # ╠ T-junction (frame top left)
    B_TEE_R = b'\xab'      # ├ T-right (entry top left)
    B_CROSS = b'\x7b'      # ┼ cross (entry top col 30)
    B_CORNER_TR = b'\x69'  # ╮ top-right corner
    B_CORNER_BL = b'\x6a'  # ╰ bottom-left corner
    B_CORNER_BR = b'\xab'  # ╮ bottom-right corner
    B_TEE_DOWN = b'\xb2'   # ┬ T-down (frame top col 30)
    B_TEE_UP = b'\xb1'     # ┴ T-up (bottom col 30)
    B_TEE_ENTRY_R = b'\xb3'  # ┤ (entry top right)

    async def render_directory(self):
        """Draw the full directory screen with borders matching C64 client.

        Entire screen rendered in uppercase (unshifted) mode — no charset switching.
        """
        await self.send(CLR)
        # Force uppercase (raw frame/file data may have silently changed charset)
        if self.terminal_type == 'c64':
            await self.send(UPPERCASE)
        self.charset = 'upper'

        # Header (rows 0-4)
        page = self.current_page
        header_file = getattr(page, 'header', None)
        ancestor = page
        while ancestor and not header_file:
            header_file = getattr(ancestor, 'header', None)
            ancestor = getattr(ancestor, 'parent', None)

        if header_file:
            cs = _get_server()
            header_path = os.path.join(cs.ROOT_DIR, header_file)
            if os.path.exists(header_path):
                with open(header_path, 'rb') as f:
                    frame_data = b'\x00\x00\x00\x00' + f.read()
                await self.send(expand_frame(frame_data))

        # Row 6: frame top border
        await self.cursor_to(6, 0)
        await self.send(COL_WHITE)
        await self.send(self.B_TEE_L + self.B_THICK_H * 28 + self.B_THIN_H +
                        self.B_TEE_DOWN + self.B_THIN_H * 8 + self.B_CORNER_TR)

        # Row 7: status line
        await self.send(self.B_THICK_V)
        await self.send(COL_WHITE)
        await self.send_text('    1 ')
        await self.send(COL_BLUE)
        await self.send_text('*** COMPUNET ***')
        await self.send(COL_WHITE)
        spaces = 29 - 6 - 16
        await self.send(b'\x20' * spaces)
        await self.send(self.B_THICK_V)
        await self.send(b'\x20' * 8)
        await self.send(self.B_THICK_V)

        # Row 8: breadcrumb + column header
        await self.send(self.B_THICK_V)
        await self.send(COL_WHITE)
        breadcrumb = f'  {page.page_num} {page.title}'
        await self.send_text(breadcrumb[:29].ljust(29))
        await self.send(self.B_THIN_V)
        cols = ['PRICE', 'LIFE', 'AUTHOR', 'VOTE']
        await self.send_text((' ' + cols[self.dir_column]).ljust(8)[:8])
        await self.send(self.B_THIN_V)

        # Row 9: entry area top border
        await self.send(self.B_TEE_R + self.B_THICK_H * 29 + self.B_CROSS +
                        self.B_THICK_H * 8 + self.B_TEE_ENTRY_R)

        # Rows 10-20: entries (11 rows)
        visible = page.children[self.dir_offset:self.dir_offset + 11]
        self.entries_row = 10
        for i in range(11):
            if i < len(visible):
                child = visible[i]
                page_num_str = str(child.page_num)
                title = child.title[:18].ljust(18)
                type_str = child.type_string()[:5].ljust(5)
                content = f'{page_num_str:>5s} {title}{type_str}'[:29]

                if self.dir_column == 0:
                    col_val = '{:.2f}'.format(child.price) if child.price > 0 else ''
                elif self.dir_column == 1:
                    col_val = str(child.life) if child.life > 0 else ''
                elif self.dir_column == 2:
                    col_val = child.author[:8]
                else:
                    col_val = str(child.vote) if child.vote > 0 else ''
                col_val = col_val[:8].ljust(8)

                if i == self.dir_cursor:
                    await self.send(COL_WHITE)
                    await self.send(self.B_THICK_V)
                    await self.send(RVS_ON)
                    await self.send_text(content.ljust(29))
                    await self.send(RVS_OFF)
                    await self.send(self.B_THIN_V)
                    await self.send(RVS_ON)
                    await self.send_text(col_val)
                    await self.send(RVS_OFF)
                    await self.send(self.B_THIN_V)
                else:
                    await self.send(COL_WHITE)
                    await self.send(self.B_THICK_V)
                    await self.send(COL_BLUE)
                    await self.send_text(content.ljust(29))
                    await self.send(COL_WHITE)
                    await self.send(self.B_THIN_V)
                    await self.send(COL_BLUE)
                    await self.send_text(col_val)
                    await self.send(COL_WHITE)
                    await self.send(self.B_THICK_V)
            else:
                await self.send(COL_WHITE)
                await self.send(self.B_THICK_V)
                await self.send(b'\x20' * 29)
                await self.send(self.B_THIN_V)
                await self.send(b'\x20' * 8)
                await self.send(self.B_THICK_V)

        # Row 21: bottom border
        await self.send(COL_WHITE)
        await self.send(self.B_CORNER_BL + self.B_THIN_H * 29 + self.B_TEE_UP)
        await self.send_text('<F7)(F8>')
        await self.send(b'\xab')  # corner

        # Rows 22-23: adverts
        await self.cursor_to(22, 0)
        await self.send(COL_YELLOW)
        advert = ''
        if self.directory.global_adverts:
            import random
            advert = random.choice(self.directory.global_adverts)
        if advert:
            lines = advert.split('\n')
            for i, line in enumerate(lines[:2]):
                text = line[:40]
                await self.send_text(text)
                if len(text) < 40:
                    await self.send(CR)
        else:
            await self.send(CR + CR)

        # Row 24: duckshoot
        await self.cursor_to(24, 0)
        await self.render_duckshoot()

    async def render_duckshoot(self):
        """Draw the duckshoot command bar — selected item in centre, others revolve.

        Fills all 40 screen positions. Each command occupies 6 chars (padded).
        Selected item at position 18-23 (chars 3*6). Non-selected in reverse video.
        Commands wrap circularly to fill the entire row.
        """
        commands = self._get_duckshoot()
        n = len(commands)
        if n == 0:
            return
        await self.send(COL_WHITE)

        # Pick the right conversion for current charset
        convert = ascii_to_petscii_unshifted if self.charset == 'upper' else ascii_to_petscii_shifted

        # Build 39 chars from commands wrapping circularly
        # Selected item starts at char position 18 (slot 3 × 6)
        chars = []  # list of (char, is_reversed) for exactly 39 positions
        offset = -3
        while len(chars) < 39:
            idx = (self.duck_pos + offset) % n
            cmd = commands[idx]
            padded = cmd.center(6)[:6]
            is_selected = (offset == 0)
            for ch in padded:
                if len(chars) >= 39:
                    break
                chars.append((ch, not is_selected))
            offset += 1

        # Emit with minimal reverse toggling
        out = bytearray()
        currently_reversed = False
        for ch, rev in chars:
            if rev and not currently_reversed:
                out.extend(RVS_ON)
                currently_reversed = True
            elif not rev and currently_reversed:
                out.extend(RVS_OFF)
                currently_reversed = False
            out.extend(convert(ch))
        if currently_reversed:
            out.extend(RVS_OFF)
        await self.send(bytes(out))

    async def redraw_column(self):
        """Redraw just the column header and column values (F7/F8 toggle)."""
        # Column header at row 8, col 31
        await self.cursor_to(8, 31)
        await self.send(COL_WHITE)
        cols = ['PRICE', 'LIFE', 'AUTHOR', 'VOTE']
        await self.send_text((' ' + cols[self.dir_column]).ljust(8)[:8])

        # Column values for each visible entry
        page = self.current_page
        visible = page.children[self.dir_offset:self.dir_offset + 11]
        for i in range(11):
            await self.cursor_to(self.entries_row + i, 31)
            if i < len(visible):
                child = visible[i]
                if self.dir_column == 0:
                    col_val = '{:.2f}'.format(child.price) if child.price > 0 else ''
                elif self.dir_column == 1:
                    col_val = str(child.life) if child.life > 0 else ''
                elif self.dir_column == 2:
                    col_val = child.author[:8]
                else:
                    col_val = str(child.vote) if child.vote > 0 else ''
                col_val = col_val[:8].ljust(8)
                if i == self.dir_cursor:
                    await self.send(COL_WHITE)
                    await self.send(RVS_ON)
                    await self.send_text(col_val)
                    await self.send(RVS_OFF)
                else:
                    await self.send(COL_BLUE)
                    await self.send_text(col_val)
            else:
                await self.send(b'\x20' * 8)

    async def redraw_entry(self, idx):
        """Redraw a single directory entry line at the given index."""
        page = self.current_page
        visible = page.children[self.dir_offset:self.dir_offset + 11]
        if idx >= len(visible):
            return
        row = self.entries_row + idx
        await self.cursor_to(row, 0)

        child = visible[idx]
        page_num_str = str(child.page_num)
        title = child.title[:18].ljust(18)
        type_str = child.type_string()[:5].ljust(5)
        content = f'{page_num_str:>5s} {title}{type_str}'[:29]

        if self.dir_column == 0:
            col_val = '{:.2f}'.format(child.price) if child.price > 0 else ''
        elif self.dir_column == 1:
            col_val = str(child.life) if child.life > 0 else ''
        elif self.dir_column == 2:
            col_val = child.author[:8]
        else:
            col_val = str(child.vote) if child.vote > 0 else ''
        col_val = col_val[:8].ljust(8)

        if idx == self.dir_cursor:
            await self.send(COL_WHITE)
            await self.send(self.B_THICK_V)
            await self.send(RVS_ON)
            await self.send_text(content.ljust(29))
            await self.send(RVS_OFF)
            await self.send(self.B_THIN_V)
            await self.send(RVS_ON)
            await self.send_text(col_val)
            await self.send(RVS_OFF)
            await self.send(self.B_THIN_V)
        else:
            await self.send(COL_WHITE)
            await self.send(self.B_THICK_V)
            await self.send(COL_BLUE)
            await self.send_text(content.ljust(29))
            await self.send(COL_WHITE)
            await self.send(self.B_THIN_V)
            await self.send(COL_BLUE)
            await self.send_text(col_val)
            await self.send(COL_WHITE)
            await self.send(self.B_THICK_V)

    async def redraw_mail_entry(self, idx):
        """Redraw a single mail entry line."""
        visible = self.mail_messages[self.mail_offset:self.mail_offset + 11]
        if idx >= len(visible):
            return
        row = self.entries_row + idx
        await self.cursor_to(row, 0)

        msg = visible[idx]
        msg_id = str(msg.get('id', ''))[:5].rjust(5)
        subject = msg.get('subject', '')[:18].ljust(18)
        msg_type = 'T' + str(len(msg.get('frames', [])))
        type_str = msg_type[:5].ljust(5)
        content = f'{msg_id} {subject}{type_str}'[:29]
        col_val = self._mail_col_value(msg)

        if idx == self.mail_cursor:
            await self.send(COL_WHITE)
            await self.send(self.B_THICK_V)
            await self.send(RVS_ON)
            await self.send_text(content)
            await self.send(RVS_OFF)
            await self.send(self.B_THIN_V)
            await self.send(RVS_ON)
            await self.send_text(col_val)
            await self.send(RVS_OFF)
            await self.send(self.B_THIN_V)
        else:
            unread = not msg.get('read')
            await self.send(COL_WHITE)
            await self.send(self.B_THICK_V)
            await self.send(COL_WHITE if unread else COL_BLUE)
            await self.send_text(content)
            await self.send(COL_WHITE)
            await self.send(self.B_THIN_V)
            await self.send(COL_WHITE if unread else COL_BLUE)
            await self.send_text(col_val)
            await self.send(COL_WHITE)
            await self.send(self.B_THICK_V)

    async def redraw_mail_column(self):
        """Redraw the mail column header and values (F7/F8 toggle)."""
        mail_cols = ['SENDER', 'DATE', 'STATUS']
        # Column header at row 8, col 31
        await self.cursor_to(8, 31)
        await self.send(COL_WHITE)
        await self.send_text((' ' + mail_cols[self.mail_column]).ljust(8)[:8])

        # Column values for each visible entry
        visible = self.mail_messages[self.mail_offset:self.mail_offset + 11]
        for i in range(11):
            await self.cursor_to(self.entries_row + i, 31)
            if i < len(visible):
                msg = visible[i]
                col_val = self._mail_col_value(msg)
                if i == self.mail_cursor:
                    await self.send(COL_WHITE)
                    await self.send(RVS_ON)
                    await self.send_text(col_val)
                    await self.send(RVS_OFF)
                else:
                    unread = not msg.get('read')
                    await self.send(COL_WHITE if unread else COL_BLUE)
                    await self.send_text(col_val)
            else:
                await self.send(b'\x20' * 8)

    # --- Mail ---

    def _load_mail(self):
        """Load mail messages for the current user."""
        import json
        cs = _get_server()
        mail_file = os.path.join(cs.MAIL_DIR, self.user_id + '.json')
        if os.path.exists(mail_file):
            with open(mail_file, 'r') as f:
                data = json.load(f)
            messages = data.get('messages', [])
            # Filter expired (read > 2 days ago)
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
        return []

    def _mail_col_value(self, msg):
        """Get the column value for a mail entry based on current mail_column."""
        if self.mail_column == 0:
            return msg.get('from', '?')[:8].ljust(8)
        elif self.mail_column == 1:
            date_raw = msg.get('date', '')
            if len(date_raw) >= 10:
                return f'{date_raw[8:10]}-{date_raw[5:7]}-{date_raw[2:4]}'.ljust(8)
            return date_raw[:8].ljust(8)
        else:
            if msg.get('read'):
                return 'READ    '
            return 'NEW     '

    async def render_mail(self):
        """Draw the mail screen with borders matching the C64 client.

        Entire screen rendered in uppercase (unshifted) mode.
        """
        cs = _get_server()
        users = cs._api_load_users()
        user = users.get(self.user_id, {})
        real_name = user.get('name', self.user_id)

        await self.send(CLR)
        # Force uppercase (raw frame/file data may have silently changed charset)
        if self.terminal_type == 'c64':
            await self.send(UPPERCASE)
        self.charset = 'upper'

        # Header (same as DIR — rows 0-5)
        page = self.current_page
        header_file = getattr(page, 'header', None)
        ancestor = page
        while ancestor and not header_file:
            header_file = getattr(ancestor, 'header', None)
            ancestor = getattr(ancestor, 'parent', None)

        if header_file:
            header_path = os.path.join(cs.ROOT_DIR, header_file)
            if os.path.exists(header_path):
                with open(header_path, 'rb') as f:
                    frame_data = b'\x00\x00\x00\x00' + f.read()
                await self.send(expand_frame(frame_data))

        # Row 6: frame top border
        await self.cursor_to(6, 0)
        await self.send(COL_WHITE)
        await self.send(self.B_TEE_L + self.B_THICK_H * 28 + self.B_THIN_H +
                        self.B_TEE_DOWN + self.B_THIN_H * 8 + self.B_CORNER_TR)

        # Row 7: user id line
        await self.send(self.B_THICK_V)
        await self.send(COL_WHITE)
        user_line = f' USER ID : {self.user_id}'
        await self.send_text(user_line[:29].ljust(29))
        await self.send(self.B_THICK_V)
        await self.send(b'\x20' * 8)
        await self.send(self.B_THICK_V)

        # Row 8: real name + column header (SENDER)
        await self.send(self.B_THICK_V)
        await self.send(COL_WHITE)
        await self.send_text(real_name[:29].ljust(29))
        await self.send(self.B_THIN_V)
        mail_cols = ['SENDER', 'DATE', 'STATUS']
        await self.send_text((' ' + mail_cols[self.mail_column]).ljust(8)[:8])
        await self.send(self.B_THIN_V)

        # Row 9: entry area top border
        await self.send(self.B_TEE_R + self.B_THICK_H * 29 + self.B_CROSS +
                        self.B_THICK_H * 8 + self.B_TEE_ENTRY_R)

        # Rows 10-20: mail entries (11 rows)
        visible = self.mail_messages[self.mail_offset:self.mail_offset + 11]
        self.entries_row = 10
        for i in range(11):
            if i < len(visible):
                msg = visible[i]
                msg_id = str(msg.get('id', ''))[:5].rjust(5)
                subject = msg.get('subject', '')[:18].ljust(18)
                msg_type = 'T' + str(len(msg.get('frames', [])))
                type_str = msg_type[:5].ljust(5)
                content = f'{msg_id} {subject}{type_str}'[:29]
                col_val = self._mail_col_value(msg)

                if i == self.mail_cursor:
                    await self.send(COL_WHITE)
                    await self.send(self.B_THICK_V)
                    await self.send(RVS_ON)
                    await self.send_text(content)
                    await self.send(RVS_OFF)
                    await self.send(self.B_THIN_V)
                    await self.send(RVS_ON)
                    await self.send_text(col_val)
                    await self.send(RVS_OFF)
                    await self.send(self.B_THIN_V)
                else:
                    unread = not msg.get('read')
                    await self.send(COL_WHITE)
                    await self.send(self.B_THICK_V)
                    await self.send(COL_WHITE if unread else COL_BLUE)
                    await self.send_text(content)
                    await self.send(COL_WHITE)
                    await self.send(self.B_THIN_V)
                    await self.send(COL_WHITE if unread else COL_BLUE)
                    await self.send_text(col_val)
                    await self.send(COL_WHITE)
                    await self.send(self.B_THICK_V)
            else:
                await self.send(COL_WHITE)
                await self.send(self.B_THICK_V)
                await self.send(b'\x20' * 29)
                await self.send(self.B_THIN_V)
                await self.send(b'\x20' * 8)
                await self.send(self.B_THICK_V)

        # Row 21: bottom border
        await self.send(COL_WHITE)
        await self.send(self.B_CORNER_BL + self.B_THIN_H * 29 + self.B_TEE_UP)
        await self.send_text('<F7)(F8>')
        await self.send(b'\xab')

        # Rows 22-23: empty
        await self.cursor_to(22, 0)
        await self.send(CR + CR)

        # Row 24: duckshoot
        await self.cursor_to(24, 0)
        await self.render_duckshoot()

    async def _xmodem_send_data(self, data, use_crc):
        """Send raw data via XMODEM. Returns True on success, False on failure."""
        SOH = 0x01
        EOT = 0x04
        ACK = 0x06
        NAK = 0x15
        block_num = 1
        offset = 0

        while offset < len(data):
            block = data[offset:offset + 128]
            if len(block) < 128:
                block = block + bytes([0x1A] * (128 - len(block)))

            pkt = bytearray([SOH, block_num & 0xFF, (255 - block_num) & 0xFF])
            pkt.extend(block)

            if use_crc:
                crc = self._xmodem_crc16(block)
                pkt.append((crc >> 8) & 0xFF)
                pkt.append(crc & 0xFF)
            else:
                checksum = sum(block) & 0xFF
                pkt.append(checksum)

            retries = 10
            while retries > 0:
                self.writer.write(bytes(pkt))
                await self.writer.drain()
                try:
                    resp = await asyncio.wait_for(self.reader.read(1), timeout=10.0)
                    if resp and resp[0] == ACK:
                        break
                    elif resp and resp[0] == NAK:
                        retries -= 1
                    else:
                        retries -= 1
                except asyncio.TimeoutError:
                    retries -= 1

            if retries == 0:
                return False

            block_num += 1
            offset += 128

        # EOT with retry
        for _ in range(5):
            self.writer.write(bytes([EOT]))
            await self.writer.drain()
            try:
                resp = await asyncio.wait_for(self.reader.read(1), timeout=10.0)
                if resp and resp[0] == ACK:
                    break
            except asyncio.TimeoutError:
                break
        return True

    async def _xmodem_send(self, page):
        """Send a program page via XMODEM-CRC protocol."""
        cs = _get_server()
        prg_data = page.frames[0]

        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        filename = page.title[:16].strip().replace(' ', '-').lower()
        await self.send_text(f'XMODEM: {filename} ({len(prg_data)}b)'.ljust(39))

        try:
            start_byte = await asyncio.wait_for(self._wait_xmodem_start(), timeout=60.0)
        except asyncio.TimeoutError:
            await self.cursor_to(24, 0)
            await self.send_text('TRANSFER TIMEOUT'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        success = await self._xmodem_send_data(prg_data, start_byte == 0x43)
        if not success:
            await self.cursor_to(24, 0)
            await self.send_text('TRANSFER FAILED'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        cs.audit_log('download', user=self.user_id, ip=self.client_ip,
                     page=page.page_num, title=page.title)

        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('TRANSFER COMPLETE'.ljust(39))
        await self.read_key()
        await self.cursor_to(24, 0)
        await self.render_duckshoot()

    async def _wait_xmodem_start(self):
        """Wait for XMODEM receiver to send 'C' (CRC) or NAK (checksum)."""
        while True:
            data = await asyncio.wait_for(self.reader.read(1), timeout=60.0)
            if not data:
                raise ConnectionResetError("Client disconnected")
            if data[0] == 0x43 or data[0] == 0x15:  # 'C' or NAK
                return data[0]

    @staticmethod
    def _xmodem_crc16(data):
        """Calculate XMODEM CRC-16."""
        crc = 0
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

    async def _enter_partyline(self):
        """Enter partyline with a custom terminal UI."""
        import partyline as pl
        cs = _get_server()

        cs.audit_log('partyline', user=self.user_id, ip=self.client_ip)

        # Check ban
        if pl._is_banned(self.user_id):
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('YOU ARE BANNED FROM PARTYLINE'.ljust(39))
            await self.read_key()
            await self.render_directory()
            return

        # Draw partyline UI (shifted mode for mixed case chat)
        await self.send(CLR)
        # Draw borders in uppercase mode (one switch), then switch to shifted for text
        await self.set_charset('upper')

        # Row 1: chat top border
        await self.cursor_to(1, 2)
        await self.send(b'\xb0')  # ┌
        await self.send(b'\x60' * 35)  # ─
        await self.send(b'\xae')  # ┐

        # Rows 2-16: pipes at col 2 and col 38
        for r in range(2, 17):
            await self.cursor_to(r, 2)
            await self.send(b'\x7d')  # │
            await self.cursor_to(r, 38)
            await self.send(b'\x7d')

        # Row 17: chat bottom border
        await self.cursor_to(17, 2)
        await self.send(b'\xad')  # └
        await self.send(b'\x60' * 35)
        await self.send(b'\xbd')  # ┘

        # Row 18: input area top (pipes)
        await self.cursor_to(18, 3)
        await self.send(b'\x7d')
        await self.cursor_to(18, 39)
        await self.send(b'\x7d')

        # Rows 19-22: input pipes
        for r in range(19, 23):
            await self.cursor_to(r, 3)
            await self.send(b'\x7d')
            await self.cursor_to(r, 39)
            await self.send(b'\x7d')

        # Row 23: input bottom border
        await self.cursor_to(23, 3)
        await self.send(b'\xad')
        await self.send(b'\x60' * 35)
        await self.send(b'\xbd')

        # Switch to shifted mode for text (partyline uses mixed case)
        await self.set_charset('lower')

        # Row 0: title
        await self.cursor_to(0, 0)
        await self.send(COL_BLUE)
        await self.send_text('  PARTYLINE')
        await self.send(CR)

        # Row 24: status
        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('*HELP for commands  ESC to quit'.ljust(39))

        # Register with partyline
        pl._users[self.user_id] = {"writer": None, "alias": None, "room": "lobby"}
        pl.partyline_log('join', user=self.user_id)

        # Chat history buffer (server-side, scrollable)
        chat_lines = []  # full history (up to 500 lines)
        scroll_offset = 0  # 0 = showing latest, >0 = scrolled back

        async def redraw_chat():
            """Redraw the 15-line chat area from the buffer at current scroll offset."""
            total = len(chat_lines)
            # Window shows lines ending at (total - scroll_offset)
            end = total - scroll_offset
            start = max(0, end - 15)
            for i in range(15):
                await self.cursor_to(2 + i, 3)
                line_idx = start + i
                if line_idx < end and line_idx < total:
                    await self.send(COL_BLUE)
                    await self.send_text(chat_lines[line_idx][:35].ljust(35))
                else:
                    await self.send_text(' ' * 35)

        async def add_chat_line(text):
            nonlocal scroll_offset
            # Wrap long lines
            while len(text) > 35:
                chat_lines.append(text[:35])
                text = text[35:]
            chat_lines.append(text)
            # Trim to 500 lines max
            while len(chat_lines) > 500:
                chat_lines.pop(0)
            # If at bottom, redraw; otherwise just leave scroll position
            if scroll_offset == 0:
                await redraw_chat()

        await add_chat_line(f'{self.user_id} has entered partyline')
        await add_chat_line('')
        await pl.broadcast_room("lobby", f"{self.user_id} has entered partyline", exclude=self.user_id)
        await pl.broadcast_room("lobby", "", exclude=self.user_id)

        # Input state
        input_buf = ''
        input_col = 0
        input_row = 0
        await self.cursor_to(19, 4)

        # Create an asyncio queue for incoming messages
        msg_queue = asyncio.Queue()

        class _QueueMsg:
            """Wrapper to distinguish queue messages from reader bytes."""
            def __init__(self, data):
                self.data = data

        # Override the writer in pl._users so broadcasts/send_line reach us
        class TermWriter:
            def __init__(self, queue):
                self.queue = queue
            def write(self, data):
                self.queue.put_nowait(_QueueMsg(data))
            async def drain(self):
                pass

        term_writer = TermWriter(msg_queue)
        pl._users[self.user_id]["writer"] = term_writer

        # Main loop
        try:
            while True:
                # Check for incoming messages or keyboard input
                done, pending = await asyncio.wait(
                    [asyncio.ensure_future(self.reader.read(1)),
                     asyncio.ensure_future(msg_queue.get())],
                    return_when=asyncio.FIRST_COMPLETED)

                for task in pending:
                    task.cancel()

                for task in done:
                    result = task.result()

                    if isinstance(result, _QueueMsg):
                        # Message from partyline (via queue)
                        raw = result.data
                        if isinstance(raw, bytes):
                            raw = raw.rstrip(b'\r\n')
                        else:
                            raw = raw.encode('latin-1').rstrip(b'\r\n')
                        raw_str = raw.decode('ascii', errors='replace')
                        if raw_str == '*EXIT':
                            raise StopIteration()
                        if raw_str == '*PING':
                            continue
                        line = pl.petscii_to_ascii(raw)
                        await add_chat_line(line)
                        await self.cursor_to(19 + input_row, 4 + input_col)
                    elif isinstance(result, bytes):
                        # Keyboard input
                        if not result:
                            raise ConnectionResetError()
                        key = result[0]

                        if key == 0x1B or key == KEY_RUNSTOP:
                            # Quit
                            raise StopIteration()
                        elif key == KEY_CRSR_UP:
                            # Scroll chat up (show older)
                            max_scroll = max(0, len(chat_lines) - 15)
                            if scroll_offset < max_scroll:
                                scroll_offset += 1
                                await redraw_chat()
                                await self.cursor_to(19 + input_row, 4 + input_col)
                        elif key == KEY_CRSR_DOWN:
                            # Scroll chat down (show newer)
                            if scroll_offset > 0:
                                scroll_offset -= 1
                                await redraw_chat()
                                await self.cursor_to(19 + input_row, 4 + input_col)
                        elif key == KEY_RETURN:
                            if input_buf.strip():
                                # Convert PETSCII input to ASCII
                                ascii_line = pl.petscii_to_ascii(
                                    bytes([ord(c) for c in input_buf.strip()]))
                                # Process through shared handler
                                result = await pl.process_input(
                                    self.user_id, ascii_line, term_writer)
                                if result == 'save':
                                    await self._partyline_save(chat_lines)
                                elif result:
                                    raise StopIteration()
                            # Clear input
                            input_buf = ''
                            input_col = 0
                            input_row = 0
                            for r in range(19, 23):
                                await self.cursor_to(r, 4)
                                await self.send_text(' ' * 35)
                            await self.cursor_to(19, 4)
                        elif key == KEY_DEL:
                            if input_buf:
                                input_buf = input_buf[:-1]
                                if input_col > 0:
                                    input_col -= 1
                                else:
                                    input_row = max(0, input_row - 1)
                                    input_col = 34
                                await self.cursor_to(19 + input_row, 4 + input_col)
                                await self.send(b'\x20')
                                await self.cursor_to(19 + input_row, 4 + input_col)
                        elif key >= 0x20 and len(input_buf) < 140:
                            input_buf += chr(key)
                            await self.send(bytes([key]))
                            input_col += 1
                            if input_col >= 35:
                                input_col = 0
                                input_row += 1
                                if input_row >= 4:
                                    input_row = 3
                                await self.cursor_to(19 + input_row, 4 + input_col)


        except (StopIteration, asyncio.CancelledError):
            pass
        finally:
            # Leave partyline
            room = pl._users.get(self.user_id, {}).get('room', 'lobby')
            if self.user_id in pl._users:
                del pl._users[self.user_id]
                pl.partyline_log('leave', user=self.user_id, room=room)
            await pl.broadcast_room(room, f'{self.user_id} has left partyline')
            await pl.broadcast_room(room, "")

    async def _partyline_save(self, chat_lines):
        """Save partyline scrollback via XMODEM (terminal client)."""
        # Build raw PETSCII data from chat_lines (matching historical format)
        data = bytearray()
        for line in chat_lines:
            data.extend(ascii_to_petscii_shifted(line))
            data.append(0x0D)

        # Prompt user to start XMODEM receive
        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text(f'XMODEM SAVE ({len(data)} bytes)...'.ljust(39))

        try:
            start_byte = await asyncio.wait_for(self._wait_xmodem_start(), timeout=60.0)
        except asyncio.TimeoutError:
            await self.cursor_to(24, 0)
            await self.send_text('SAVE TIMEOUT'.ljust(39))
            await self.read_key()
            return

        success = await self._xmodem_send_data(bytes(data), start_byte == 0x43)
        await self.cursor_to(24, 0)
        if success:
            await self.send_text('SAVE COMPLETE'.ljust(39))
        else:
            await self.send_text('SAVE FAILED'.ljust(39))
        await self.read_key()

        # Return to directory
        await self.render_directory()

    async def _render_editor_frame(self):
        """Display the current frame from editor memory with editor duckshoot."""
        await self.send(CLR)
        await self.set_charset('upper')
        if self._frame_memory and 0 <= self._editor_idx < len(self._frame_memory):
            frame_data = self._frame_memory[self._editor_idx]
            await self.send(expand_frame(frame_data))
        await self.cursor_to(24, 0)
        await self.render_duckshoot()

    async def _render_upload_text_frame(self):
        """Display current frame in upload-text mode with upload duckshoot."""
        await self.send(CLR)
        await self.set_charset('upper')
        if self._frame_memory and 0 <= self._editor_idx < len(self._frame_memory):
            frame_data = self._frame_memory[self._editor_idx]
            await self.send(expand_frame(frame_data))
        await self.cursor_to(24, 0)
        await self.render_duckshoot()

    async def _cmd_edit(self):
        """Enter free-cursor editing mode on the current editor frame."""
        if not self._frame_memory or self._editor_idx >= len(self._frame_memory):
            return

        # Initialize 40x24 screen buffer (row 24 reserved for duckshoot)
        buf = [[0x20] * 40 for _ in range(24)]
        colour = [[0x06] * 40 for _ in range(24)]  # default blue

        # Expand current frame into the buffer
        frame_data = self._frame_memory[self._editor_idx]
        row, col = 0, 0
        cur_colour = 0x06
        i = 4  # skip 4-byte header
        while i < len(frame_data):
            b = frame_data[i]
            if b == 0x00:
                break
            elif b == 0x06:
                i += 1
                if i < len(frame_data):
                    count = frame_data[i] + 1
                    for _ in range(count):
                        if row < 24 and col < 40:
                            buf[row][col] = 0x20
                            colour[row][col] = cur_colour
                            col += 1
                            if col >= 40:
                                col = 0
                                row += 1
            elif b == 0x07:
                i += 1
                if i + 1 < len(frame_data):
                    char = frame_data[i]
                    i += 1
                    count = frame_data[i] + 1
                    for _ in range(count):
                        if row < 24 and col < 40:
                            buf[row][col] = char
                            colour[row][col] = cur_colour
                            col += 1
                            if col >= 40:
                                col = 0
                                row += 1
            elif b == 0x0D:
                if col >= 40:
                    pass  # suppress CR after full line
                else:
                    row += 1
                    col = 0
            elif b < 0x20 or (0x80 <= b <= 0x9F):
                # Colour codes
                if b in (0x05, 0x1C, 0x1E, 0x1F, 0x81, 0x90, 0x95, 0x96,
                         0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F):
                    cur_colour = b
            else:
                if row < 24 and col < 40:
                    buf[row][col] = b
                    colour[row][col] = cur_colour
                    col += 1
                    if col >= 40:
                        col = 0
                        row += 1
            i += 1

        # Display frame and position cursor at 0,0
        await self.send(CLR)
        await self.set_charset("upper")
        await self.send(expand_frame(frame_data))
        await self.cursor_to(0, 0)

        # Edit loop — free cursor mode
        edit_row, edit_col = 0, 0
        cur_colour = 0x05  # white default for typing

        while True:
            key = await self.read_key()

            if key == KEY_RUNSTOP or key == 0x1B:  # RUN/STOP or ESC
                break
            elif key == KEY_CRSR_DOWN:
                if edit_row < 23:
                    edit_row += 1
                    await self.send(CRSR_DOWN)
            elif key == KEY_CRSR_UP:
                if edit_row > 0:
                    edit_row -= 1
                    await self.send(CRSR_UP)
            elif key == KEY_CRSR_RIGHT:
                if edit_col < 39:
                    edit_col += 1
                    await self.send(CRSR_RIGHT)
            elif key == KEY_CRSR_LEFT:
                if edit_col > 0:
                    edit_col -= 1
                    await self.send(CRSR_LEFT)
            elif key == 0x13:  # HOME
                edit_row, edit_col = 0, 0
                await self.send(HOME)
            elif key == KEY_RETURN:
                if edit_row < 23:
                    edit_row += 1
                    edit_col = 0
                    await self.send(CR)
            elif key == KEY_DEL:
                if edit_col > 0:
                    edit_col -= 1
                    buf[edit_row][edit_col] = 0x20
                    colour[edit_row][edit_col] = cur_colour
                    await self.send(b'\x9d\x20\x9d')  # left, space, left
            elif key in (0x05, 0x1C, 0x1E, 0x1F, 0x81, 0x90, 0x95, 0x96,
                         0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9E, 0x9F):
                # Colour change
                cur_colour = key
                await self.send(bytes([key]))
            elif key == 0x12:  # RVS ON
                await self.send(RVS_ON)
            elif key == 0x92:  # RVS OFF
                await self.send(RVS_OFF)
            elif key >= 0x20:
                # Printable character
                if edit_row < 24 and edit_col < 40:
                    buf[edit_row][edit_col] = key
                    colour[edit_row][edit_col] = cur_colour
                    await self.send(bytes([key]))
                    edit_col += 1
                    if edit_col >= 40:
                        edit_col = 0
                        edit_row += 1
                        if edit_row >= 24:
                            edit_row = 23

        # Convert buffer back to frame data
        frame = bytearray()
        frame.extend(b'\x00\x06\x0F\x8E')  # standard header
        prev_colour = 0x06
        for r in range(24):
            # Find last non-space on this row
            last_col = 39
            while last_col >= 0 and buf[r][last_col] == 0x20:
                last_col -= 1
            if last_col < 0 and r < 23:
                frame.append(0x0D)
                continue
            for c in range(last_col + 1):
                if colour[r][c] != prev_colour:
                    frame.append(colour[r][c])
                    prev_colour = colour[r][c]
                frame.append(buf[r][c])
            if r < 23:
                frame.append(0x0D)
        frame.append(0x00)  # end of frame

        # Save back to frame memory
        self._frame_memory[self._editor_idx] = bytes(frame)

        # Return to editor duckshoot
        await self._render_editor_frame()

    def _generate_mail_envelope(self, msg_seq, sender_id, subject, dest_ids, timestamp, users, cs):
        """Generate COURIER envelope header frame (same as protocol server)."""
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
                line = b'\x20\x20\x1F' + did.ljust(8)[:8].encode('ascii') + b'\x1C: \x1F' + dest_name.encode('ascii')
            else:
                line = b'\x20\x20\x06\x08\x1C:'
            dest_lines.append(line)

        # Load template
        template_path = os.path.join(cs.CONTENT_DIR, 'templates', 'courier-envelope.seq')
        if os.path.exists(template_path):
            with open(template_path, 'rb') as f:
                frame = f.read()
        else:
            # Fallback minimal envelope
            frame = b'\x00\x06\x0F\x8E\x0D\x1F COURIER\x0D\x00'
            return frame

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

    async def _deliver_mail(self):
        """Deliver composed mail to recipients."""
        import json
        cs = _get_server()
        send = self._upload_pending
        now = datetime.datetime.now()
        users = cs._api_load_users()

        # Generate message sequence number
        seq_file = os.path.join(cs.MAIL_DIR, 'sequence.json')
        if os.path.exists(seq_file):
            with open(seq_file, 'r') as f:
                seq_data = json.load(f)
            msg_seq = seq_data.get('next', 100000)
        else:
            msg_seq = 100000
        with open(seq_file, 'w') as f:
            json.dump({'next': msg_seq + 1}, f)

        msg_id = str(msg_seq)

        # Generate envelope header frame
        envelope = self._generate_mail_envelope(
            msg_seq, self.user_id, send['subject'], send['to'], now, users, cs)

        # Deliver to each recipient
        for dest_id in send['to']:
            if dest_id not in users:
                continue
            dest_dir = os.path.join(cs.MAIL_DIR, dest_id)
            os.makedirs(dest_dir, exist_ok=True)

            # Load or create inbox
            dest_mail_file = os.path.join(cs.MAIL_DIR, dest_id + '.json')
            if os.path.exists(dest_mail_file):
                with open(dest_mail_file, 'r') as f:
                    dest_inbox = json.load(f)
            else:
                dest_inbox = {'messages': []}

            # Save frame files (envelope as frame 0, then user frames)
            frame_files = []
            # Frame 0: envelope
            env_file = f'{msg_id}-0.seq'
            env_path = os.path.join(dest_dir, env_file)
            with open(env_path, 'wb') as f:
                f.write(envelope)
            frame_files.append(env_file)
            # Frame 1+: user content
            for i, frame_data in enumerate(send['frames']):
                frame_file = f'{msg_id}-{i+1}.seq'
                frame_path = os.path.join(dest_dir, frame_file)
                with open(frame_path, 'wb') as f:
                    f.write(frame_data)
                frame_files.append(frame_file)

            # Add to inbox
            dest_inbox['messages'].append({
                'id': msg_id,
                'from': self.user_id,
                'subject': send['subject'],
                'date': now.date().isoformat(),
                'read': False,
                'frames': frame_files,
            })
            with open(dest_mail_file, 'w') as f:
                json.dump(dest_inbox, f, indent=2)

        cs.audit_log('mail_send', user=self.user_id, ip=self.client_ip,
                     subject=send['subject'], to=send['to'])

        # Email notification for each recipient
        for dest_id in send['to']:
            if dest_id in users:
                asyncio.get_event_loop().create_task(
                    cs._send_mail_notification(dest_id, self.user_id, send['subject'], users))

        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('MAIL SENT'.ljust(39))
        await self.read_key()

        self._upload_pending = None
        self._mail_send_pending = None
        self.mode = 'mail'
        self.mail_messages = self._load_mail()
        self.mail_cursor = 0
        self.duck_pos = 3  # SEND
        await self.render_mail()

    async def _cmd_upload(self):
        """UPLD command — prompt for page details then switch to upload mode."""
        cs = _get_server()
        page = self.current_page

        # Check if directory has space
        if len(page.children) >= 11:
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('DIRECTORY FULL'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        # Check upload permission
        can_upload = (self.user_id == page.author or
                      cs._api_load_users().get(self.user_id, {}).get('admin') or
                      cs._api_load_users().get(self.user_id, {}).get('editor'))
        if not can_upload:
            ancestor = page
            while ancestor:
                if getattr(ancestor, 'open_upload', False):
                    can_upload = True
                    break
                ancestor = getattr(ancestor, 'parent', None)
        if not can_upload:
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('UPLOAD NOT PERMITTED'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        # The new entry will appear in the next blank directory slot
        new_idx = len(page.children)
        entry_row = self.entries_row + new_idx

        # Helper to update the preview entry in the directory
        async def _update_preview(title='', page_type='', price=0.0, lifetime=0):
            if new_idx >= 11:
                return
            await self.cursor_to(entry_row, 0)
            await self.send(COL_CYAN)
            await self.set_charset("upper")
            await self.send(self.B_THICK_V)
            type_str = (page_type + str(lifetime) if page_type else '')[:5].ljust(5)
            content = f'      {title[:18]:<18s}{type_str}'[:29]
            await self.send_text(content)
            await self.set_charset("upper")
            await self.send(self.B_THIN_V)
            price_str = f'{price:.2f}' if price > 0 else ''
            await self.send_text(price_str[:8].ljust(8))
            await self.set_charset("upper")
            await self.send(self.B_THICK_V)

        # Prompt for page details on duckshoot line
        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('UPLOAD PAGE TITLE? '.ljust(39))
        await self.cursor_to(24, 19)
        title = await self.read_line(max_len=16)
        if not title.strip():
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return
        await _update_preview(title=title.strip())

        await self.cursor_to(24, 0)
        await self.send_text('PAGE TYPE (P)? '.ljust(39))
        await self.cursor_to(24, 15)
        page_type = await self.read_line(max_len=1)
        if not page_type.strip():
            page_type = 'P'
        await _update_preview(title=title.strip(), page_type=page_type.strip())

        await self.cursor_to(24, 0)
        await self.send_text('PRICE? '.ljust(39))
        await self.cursor_to(24, 7)
        price_str = await self.read_line(max_len=6)
        try:
            price = round(float(price_str), 2) if price_str.strip() else 0.0
        except ValueError:
            price = 0.0
        await _update_preview(title=title.strip(), page_type=page_type.strip(), price=price)

        await self.cursor_to(24, 0)
        await self.send_text('LIFETIME? '.ljust(39))
        await self.cursor_to(24, 10)
        life_str = await self.read_line(max_len=3)
        try:
            lifetime = int(life_str) if life_str.strip() else 0
        except ValueError:
            lifetime = 0
        await _update_preview(title=title.strip(), page_type=page_type.strip(), price=price, lifetime=lifetime)

        await self.cursor_to(24, 0)
        await self.send_text('NEW ENTRY OK? (Y/N) '.ljust(39))
        await self.cursor_to(24, 20)
        confirm = await self.read_line(max_len=1)
        if confirm != 'Y':
            # Clear the preview
            if new_idx < 11:
                await self.cursor_to(entry_row, 0)
                await self.send(COL_WHITE)
                await self.set_charset("upper")
                await self.send(self.B_THICK_V)
                await self.send(b'\x20' * 29)
                await self.set_charset("upper")
                await self.send(self.B_THIN_V)
                await self.send(b'\x20' * 8)
                await self.send(self.B_THICK_V)
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        # Store upload metadata and switch to upload mode
        self._upload_pending = {
            'title': title.strip(),
            'type': page_type.strip(),
            'price': price,
            'lifetime': lifetime,
            'frames': [],  # collected frames for T-type uploads
        }

        self._saved_duck_pos = self.duck_pos

        if page_type.strip() == 'T':
            # Text upload: enter editor to compose/select frames
            self.mode = 'upload_text'
            self.duck_pos = 0  # SEND selected
            # Show last frame from memory (or blank)
            if not self._frame_memory:
                blank_frame = b'\x00\x06\x0F\x8E\x0D\x00'
                self._frame_memory.append(blank_frame)
            self._editor_idx = len(self._frame_memory) - 1
            await self._render_upload_text_frame()
        else:
            # Program upload: XMODEM transfer
            self.mode = 'upload'
            self.duck_pos = 0  # SEND selected
            await self.cursor_to(24, 0)
            await self.render_duckshoot()

    async def _complete_text_upload(self):
        """Complete a text-type upload — save frames to directory or deliver mail."""
        import json
        cs = _get_server()

        if not self._upload_pending or not self._upload_pending.get('frames'):
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('NO FRAMES TO UPLOAD'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        # Mail delivery
        if self._upload_pending.get('_is_mail'):
            await self._deliver_mail()
            return

        page = self.current_page
        send = self._upload_pending

        # Create page folder
        page_slug = cs.CompunetDirectory._make_slug(send['title'])
        parent_dir = getattr(page, '_dir_path', cs.ROOT_DIR)
        page_dir = os.path.join(parent_dir, page_slug)
        os.makedirs(page_dir, exist_ok=True)

        # Save frames as .seq files
        frame_files = []
        for i, frame_data in enumerate(send['frames']):
            frame_file = f'frame-{i+1}.seq'
            frame_path = os.path.join(page_dir, frame_file)
            with open(frame_path, 'wb') as f:
                f.write(frame_data)
            frame_files.append(frame_file)

        # Allocate page number
        all_pages = list(self.directory.pages.keys())
        next_page_num = max(all_pages) + 1 if all_pages else 1000

        size = len(send['frames'])

        # Create page object
        new_page = cs.CompunetPage(
            page_num=next_page_num,
            title=send['title'],
            page_type='T',
            size=size,
            author=self.user_id,
            price=send['price'],
            life=send['lifetime'],
        )
        new_page.uploaded = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        new_page.parent = page
        new_page._frame_files = frame_files
        new_page._dir_path = page_dir
        new_page._adverts = []
        for frame_file in frame_files:
            frame_path = os.path.join(page_dir, frame_file)
            with open(frame_path, 'rb') as f:
                new_page.frames.append(f.read())
        page.children.append(new_page)
        self.directory.pages[next_page_num] = new_page

        # Save directory
        self._save_directory_tree(cs)

        cs.audit_log('upload', user=self.user_id, ip=self.client_ip,
                     title=send['title'], page=next_page_num, type='T')

        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('UPLOAD COMPLETE'.ljust(39))
        await self.read_key()

        self._upload_pending = None
        self.mode = 'directory'
        self.duck_pos = getattr(self, '_saved_duck_pos', 0)
        await self.render_directory()

    async def _cmd_upload_send(self):
        """SEND in upload mode — receive file via XMODEM then save."""
        import json
        cs = _get_server()

        if not self._upload_pending:
            self.mode = 'directory'
            await self.render_directory()
            return

        # Prompt for XMODEM transfer
        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('START XMODEM UPLOAD NOW...'.ljust(39))

        # XMODEM receive
        try:
            prg_data = await self._xmodem_receive()
        except (asyncio.TimeoutError, ConnectionResetError):
            await self.cursor_to(24, 0)
            await self.send_text('TRANSFER FAILED'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        if not prg_data:
            await self.cursor_to(24, 0)
            await self.send_text('NO DATA RECEIVED'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        # Save the upload using the server's content upload logic
        send = {
            'mode': 'upload',
            'title': self._upload_pending['title'],
            'type': self._upload_pending['type'],
            'price': self._upload_pending['price'],
            'lifetime': self._upload_pending['lifetime'],
            'frames': [prg_data],  # Raw PRG data (load_lo, load_hi, program bytes)
        }

        # Use the server's _complete_content_upload logic directly
        page = self.current_page
        page_slug = cs.CompunetDirectory._make_slug(send['title'])
        parent_dir = getattr(page, '_dir_path', cs.ROOT_DIR)
        page_dir = os.path.join(parent_dir, page_slug)
        os.makedirs(page_dir, exist_ok=True)

        # Save PRG file
        frame_file = f'{page_slug}.prg'
        frame_path = os.path.join(page_dir, frame_file)
        with open(frame_path, 'wb') as f:
            f.write(prg_data)

        # Allocate page number
        all_pages = list(self.directory.pages.keys())
        next_page_num = max(all_pages) + 1 if all_pages else 1000

        # Calculate size in K
        size = (len(prg_data) - 2 + 1023) // 1024 if len(prg_data) > 2 else 1

        # Create page object
        new_page = cs.CompunetPage(
            page_num=next_page_num,
            title=send['title'],
            page_type=send['type'],
            size=size,
            author=self.user_id,
            price=send['price'],
            life=send['lifetime'],
        )
        new_page.uploaded = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        new_page.parent = page
        new_page._frame_files = [frame_file]
        new_page._dir_path = page_dir
        new_page._adverts = []
        new_page.frames = [prg_data]
        page.children.append(new_page)
        self.directory.pages[next_page_num] = new_page

        # Save directory JSON (reuse server's save logic)
        import json as json_mod
        self._save_directory_tree(cs)

        cs.audit_log('upload', user=self.user_id, ip=self.client_ip,
                     title=send['title'], page=next_page_num, type=send['type'])

        await self.cursor_to(24, 0)
        await self.send_text('UPLOAD COMPLETE'.ljust(39))
        await self.read_key()

        self._upload_pending = None
        self.mode = 'directory'
        self.duck_pos = getattr(self, '_saved_duck_pos', 0)
        await self.render_directory()

    def _save_directory_tree(self, cs):
        """Save directory tree to JSON files (same logic as CompunetSession._save_directory)."""
        import json

        def _save_dir_json(page, json_path):
            data = {}
            if hasattr(page, 'header') and page.header:
                data['header'] = page.header
            if hasattr(page, '_adverts') and page._adverts:
                data['adverts'] = page._adverts
            if hasattr(page, 'shortcuts') and page.shortcuts:
                data['shortcuts'] = page.shortcuts
            if hasattr(page, 'open_upload') and page.open_upload:
                data['open_upload'] = True
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
                frame_files = getattr(child, '_frame_files', [])
                if frame_files:
                    node['frames'] = frame_files
                if child.children:
                    child_dir = getattr(child, '_dir_path', '')
                    dir_json_path = os.path.join(child_dir, 'directory.json')
                    node['directory'] = os.path.relpath(dir_json_path, cs.ROOT_DIR)
                    _save_dir_json(child, dir_json_path)
                pages_list.append(node)
            data['pages'] = pages_list
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)

        root_json_path = os.path.join(cs.ROOT_DIR, 'root.json')
        _save_dir_json(self.directory.root, root_json_path)

    async def _xmodem_receive(self):
        """Receive a file via XMODEM-CRC (supports both 128-byte and 1K blocks)."""
        SOH = 0x01  # 128-byte block
        STX = 0x02  # 1024-byte block
        EOT = 0x04
        ACK = 0x06
        NAK = 0x15
        CAN = 0x18

        # Send 'C' to request CRC mode until sender responds
        first = None
        for _ in range(10):
            self.writer.write(b'C')
            await self.writer.drain()
            try:
                first = await asyncio.wait_for(self.reader.read(1), timeout=3.0)
                if first and first[0] in (SOH, STX):
                    break
                elif first and first[0] == EOT:
                    self.writer.write(bytes([ACK]))
                    await self.writer.drain()
                    return b''
                first = None
            except asyncio.TimeoutError:
                continue
        else:
            raise asyncio.TimeoutError("No response from sender")

        # Receive blocks
        data = bytearray()
        expected_block = 1

        while True:
            if first:
                hdr = first[0]
                first = None
            else:
                hdr_data = await asyncio.wait_for(self.reader.read(1), timeout=10.0)
                if not hdr_data:
                    raise ConnectionResetError()
                hdr = hdr_data[0]

            if hdr == EOT:
                self.writer.write(bytes([ACK]))
                await self.writer.drain()
                break
            elif hdr == CAN:
                break
            elif hdr == SOH:
                block_size = 128
            elif hdr == STX:
                block_size = 1024
            else:
                self.writer.write(bytes([NAK]))
                await self.writer.drain()
                continue

            # Read: block_num(1) + complement(1) + data(block_size) + CRC(2)
            pkt_len = 2 + block_size + 2
            pkt = bytearray()
            while len(pkt) < pkt_len:
                chunk = await asyncio.wait_for(
                    self.reader.read(pkt_len - len(pkt)), timeout=10.0)
                if not chunk:
                    raise ConnectionResetError()
                pkt.extend(chunk)

            block_num = pkt[0]
            block_comp = pkt[1]
            block_data = pkt[2:2 + block_size]
            crc_hi = pkt[2 + block_size]
            crc_lo = pkt[2 + block_size + 1]

            # Validate block number
            if (block_num + block_comp) & 0xFF != 0xFF:
                self.writer.write(bytes([NAK]))
                await self.writer.drain()
                continue

            # Validate CRC
            crc_received = (crc_hi << 8) | crc_lo
            crc_calc = self._xmodem_crc16(block_data)
            if crc_received != crc_calc:
                self.writer.write(bytes([NAK]))
                await self.writer.drain()
                continue

            if block_num == expected_block & 0xFF:
                data.extend(block_data)
                expected_block += 1

            self.writer.write(bytes([ACK]))
            await self.writer.drain()

        # Strip trailing SUB ($1A) padding from last block
        while data and data[-1] == 0x1A:
            data = data[:-1]

        return bytes(data)

    async def _mail_show(self):
        """Show the selected mail message."""
        import json
        cs = _get_server()
        visible = self.mail_messages[self.mail_offset:self.mail_offset + 11]
        if self.mail_cursor >= len(visible):
            return
        msg = visible[self.mail_cursor]
        msg_id = msg.get('id')

        # Load message frames
        mail_dir = os.path.join(cs.MAIL_DIR, self.user_id)
        frames = []
        frame_idx = 0
        while True:
            frame_path = os.path.join(mail_dir, f'{msg_id}-{frame_idx}.seq')
            if not os.path.exists(frame_path):
                break
            with open(frame_path, 'rb') as f:
                frames.append(f.read())
            frame_idx += 1

        if not frames:
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('NO MESSAGE DATA'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()
            return

        # Mark as read
        msg['read'] = True
        msg['read_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
        mail_file = os.path.join(cs.MAIL_DIR, self.user_id + '.json')
        with open(mail_file, 'r') as f:
            mail_data = json.load(f)
        for m in mail_data.get('messages', []):
            if m.get('id') == msg_id:
                m['read'] = True
                m['read_date'] = msg['read_date']
                break
        with open(mail_file, 'w') as f:
            json.dump(mail_data, f)
        cs.audit_log('mail_read', user=self.user_id, ip=self.client_ip, msg_id=msg_id)

        # Display frames
        for i, frame_data in enumerate(frames):
            await self.send(CLR)
            await self.set_charset('upper')
            await self.send(expand_frame(frame_data))
            # Store in editor frame memory
            self._frame_memory.append(frame_data)
            if len(self._frame_memory) > 20:
                self._frame_memory.pop(0)
            self._editor_idx = len(self._frame_memory) - 1
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            if i < len(frames) - 1:
                await self.send_text('MORE...')
            else:
                await self.send_text('PRESS ANY KEY')
            await self.read_key()

        # Return to mail listing
        await self.render_mail()

    async def _cmd_mail_send(self):
        """SEND command in mail mode — compose and send a new message."""
        import json
        cs = _get_server()
        users = cs._api_load_users()
        user = users.get(self.user_id, {})
        real_name = user.get('name', self.user_id)
        now = datetime.datetime.now()

        # Draw the mail compose screen (uppercase mode)
        await self.send(CLR)
        await self.set_charset('upper')
        await self.send(COL_RED)

        # Row 3: COURIER header
        await self.cursor_to(3, 3)
        await self.send_text('COURIER')

        # Row 4: divider
        await self.cursor_to(4, 3)
        await self.send(b'\x60' * 7)  # horizontal line

        # Row 6: from
        await self.cursor_to(6, 3)
        await self.send_text('FROM : ')
        await self.send(COL_BLUE)
        await self.send_text(self.user_id)

        # Row 7: real name (aligned under user ID value)
        await self.cursor_to(7, 10)
        await self.send(COL_BLUE)
        await self.send_text(real_name)

        # Row 9: date
        await self.cursor_to(9, 3)
        await self.send(COL_RED)
        await self.send_text('DATE : ')
        await self.send(COL_BLUE)
        await self.send_text(now.strftime('%d-%m-%y'))

        # Row 10: time
        await self.cursor_to(10, 3)
        await self.send(COL_RED)
        await self.send_text('TIME : ')
        await self.send(COL_BLUE)
        await self.send_text(now.strftime('%H:%M'))

        # Row 12: subject label
        await self.cursor_to(12, 3)
        await self.send(COL_RED)
        await self.send_text('SUBJECT : ')

        # Row 14: to label + colon lines for destinations
        await self.cursor_to(14, 3)
        await self.send_text('TO : ')
        for i in range(5):
            await self.cursor_to(16 + i, 12)
            await self.send_text(':')

        # Prompt for subject on duckshoot line
        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('SUBJECT? '.ljust(39))
        await self.cursor_to(24, 9)
        subject = await self.read_line(max_len=20)
        if not subject.strip():
            await self.render_mail()
            return

        # Show subject on screen
        await self.cursor_to(12, 13)
        await self.send(COL_BLUE)
        await self.send_text(subject[:20])

        # Prompt for destination IDs (up to 5)
        destinations = []
        for i in range(5):
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('DESTINATION ID? '.ljust(39))
            await self.cursor_to(24, 16)
            dest_id = await self.read_line(max_len=8)

            if not dest_id.strip():
                if i == 0:
                    # First empty = abort
                    await self.render_mail()
                    return
                break

            destinations.append(dest_id.strip())
            # Show on screen (first dest at row 16, blank line after TO :)
            row = 16 + i
            await self.cursor_to(row, 3)
            await self.send(COL_BLUE)
            await self.send_text(dest_id.strip())

        # Validate all destination IDs and show real names
        all_valid = True
        for i, dest_id in enumerate(destinations):
            dest_user = users.get(dest_id)
            row = 16 + i
            if dest_user:
                name = dest_user.get('name', dest_id)
                await self.cursor_to(row, 14)
                await self.send(COL_BLUE)
                await self.send_text(name[:20])
            else:
                await self.cursor_to(row, 14)
                await self.send(COL_RED)
                await self.send_text('*** NO SUCH USER ***')
                all_valid = False

        if not all_valid:
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('PRESS ANY KEY'.ljust(39))
            await self.read_key()
            await self.render_mail()
            return

        # Confirm
        await self.cursor_to(24, 0)
        await self.send(COL_WHITE)
        await self.send_text('OKAY? (Y/N) '.ljust(39))
        await self.cursor_to(24, 12)
        confirm = await self.read_line(max_len=1)
        if confirm != 'Y':
            await self.render_mail()
            return

        # Enter editor for composing mail frames
        self._mail_send_pending = {
            'subject': subject.strip(),
            'to': destinations,
            'frames': [],
        }

        # Switch to upload_text mode for composing
        self.mode = 'upload_text'
        self.duck_pos = 0  # SEND selected
        if not self._frame_memory:
            blank_frame = b'\x00\x06\x0F\x8E\x0D\x00'
            self._frame_memory.append(blank_frame)
        # Start with a new blank frame
        blank_frame = b'\x00\x06\x0F\x8E\x0D\x00'
        self._frame_memory.append(blank_frame)
        if len(self._frame_memory) > 20:
            self._frame_memory.pop(0)
        self._editor_idx = len(self._frame_memory) - 1
        self._upload_pending = self._mail_send_pending  # reuse upload_text SEND/FINSH
        self._upload_pending['_is_mail'] = True
        await self._render_upload_text_frame()

    def _get_duckshoot(self):
        if self.mode == 'frame':
            return DUCK_FRAME
        elif self.mode == 'mail':
            return DUCK_MAIL
        elif self.mode == 'upload':
            return DUCK_UPLOAD
        elif self.mode == 'upload_text':
            return DUCK_UPLOAD_TEXT
        elif self.mode == 'editor':
            return DUCK_EDITOR
        return DUCK_DIR

    # --- Frame display ---

    async def render_frame(self):
        """Display a text frame."""
        if not self.show_page or not self.show_page.frames:
            return
        await self.send(CLR)
        await self.set_charset("upper")
        self.charset = 'upper'
        frame_data = self.show_page.frames[self.show_frame_idx]
        await self.send(expand_frame(frame_data))

        # Store in editor frame memory (last 20)
        self._frame_memory.append(frame_data)
        if len(self._frame_memory) > 20:
            self._frame_memory.pop(0)
        self._editor_idx = len(self._frame_memory) - 1

        # Determine final charset state by parsing the frame content properly
        # (can't just scan for $0E — it may appear as an RLE count)
        i = 4
        while i < len(frame_data):
            b = frame_data[i]
            if b == 0x00:
                break
            elif b == 0x06:
                i += 2  # skip count byte
                continue
            elif b == 0x07:
                i += 3  # skip char + count bytes
                continue
            elif b == 0x0E:
                self.charset = 'lower'
            elif b == 0x8E:
                self.charset = 'upper'
            i += 1

        has_more = self.show_frame_idx < len(self.show_page.frames) - 1
        self._saved_duck_pos = self.duck_pos
        await self.cursor_to(24, 0)

        if len(self.show_page.frames) == 1:
            # Single frame — just wait for any key then return to directory
            await self.send(COL_WHITE)
            await self.send_text('PRESS ANY KEY')
            await self.read_key()
            self.mode = 'directory'
            self.show_page = None
            self.duck_pos = self._saved_duck_pos
            await self.render_directory()
        else:
            # Multi-frame — show MORE/FINISH duckshoot
            self.mode = 'frame'
            self.duck_pos = 0
            await self.render_duckshoot()

    # --- Command execution ---

    async def execute_command(self, cmd):
        """Execute a duckshoot command."""
        cs = _get_server()

        if cmd == 'SHOW':
            if self.mode == 'mail':
                await self._mail_show()
                return
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                child = visible[self.dir_cursor]
                if child.page_type == 'L':
                    await self.cursor_to(24, 0)
                    await self.send(COL_WHITE)
                    await self.send_text('PLEASE USE BUY'.ljust(39))
                    await self.read_key()
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                    return
                if child.frames:
                    # Dynamic page check
                    if getattr(child, 'dynamic', None) == 'who':
                        cs._regenerate_who_frame()
                        frame_path = os.path.join(cs.WHO_PAGE_DIR, 'frame-1.seq')
                        if os.path.exists(frame_path):
                            with open(frame_path, 'rb') as f:
                                child.frames = [f.read()]
                    self.show_page = child
                    self.show_frame_idx = 0
                    await self.render_frame()
                    return
            await self.render_directory()

        elif cmd == 'DIR':
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                child = visible[self.dir_cursor]
                # Dynamic directory: populate on each view
                if getattr(child, 'dynamic', None) == 'new':
                    cs._populate_whats_new(child, self.directory)
                if child.has_subdir():
                    self.current_page = child
                    self.dir_cursor = 0
                    self.dir_offset = 0
                else:
                    # Create empty sub-directory (only if user can upload here)
                    users = cs._api_load_users()
                    user_data = users.get(self.user_id, {})
                    can_upload = (self.user_id == page.author or
                                  user_data.get('admin') or
                                  user_data.get('editor'))
                    if not can_upload:
                        ancestor = page
                        while ancestor:
                            if getattr(ancestor, 'open_upload', False):
                                can_upload = True
                                break
                            ancestor = getattr(ancestor, 'parent', None)
                    if can_upload:
                        # Enter the page as an empty directory
                        child.parent = page
                        if not hasattr(child, '_dir_path') or not child._dir_path:
                            parent_dir = getattr(page, '_dir_path', cs.ROOT_DIR)
                            child._dir_path = os.path.join(
                                parent_dir, cs.CompunetDirectory._make_slug(child.title))
                        self.current_page = child
                        self.dir_cursor = 0
                        self.dir_offset = 0
            await self.render_directory()

        elif cmd == 'BACK':
            if self._ucat_active and not self.current_page.parent:
                # Exit UCAT — restore previous location
                self._ucat_active = False
                self.current_page = self._ucat_saved_page
                self.dir_cursor = self._ucat_saved_cursor
                self.dir_offset = self._ucat_saved_offset
            elif self.current_page.parent:
                self.current_page = self.current_page.parent
                self.dir_cursor = 0
                self.dir_offset = 0
            await self.render_directory()

        elif cmd == 'GOTO':
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('GOTO? '.ljust(39))
            await self.cursor_to(24, 6)
            target_str = await self.read_line(max_len=8)
            target_str = target_str.strip()

            if target_str:
                # Built-in: WHO
                if target_str.upper() == 'WHO':
                    cs._regenerate_who_frame()
                    frame_path = os.path.join(cs.WHO_PAGE_DIR, 'frame-1.seq')
                    if os.path.exists(frame_path):
                        with open(frame_path, 'rb') as f:
                            frame_data = f.read()
                        await self.send(CLR)
                        await self.set_charset("upper")
                        await self.send(expand_frame(frame_data))
                        await self.cursor_to(24, 0)
                        await self.send(COL_WHITE)
                        await self.send_text('PRESS ANY KEY')
                        await self.read_key()
                    await self.render_directory()
                    return

                # Try numeric page number
                target_page = None
                try:
                    page_num = int(target_str)
                    target_page = self.directory.pages.get(page_num)
                except ValueError:
                    # Try keyword lookup
                    for pg in self.directory.pages.values():
                        if pg.keyword and pg.keyword.upper() == target_str.upper():
                            target_page = pg
                            break

                if target_page:
                    if target_page.parent:
                        self.current_page = target_page.parent
                        # Find target in parent's children to highlight it
                        for i, child in enumerate(self.current_page.children):
                            if child.page_num == target_page.page_num:
                                self.dir_cursor = i
                                self.dir_offset = max(0, i - 5)
                                break
                        else:
                            self.dir_cursor = 0
                            self.dir_offset = 0
                    else:
                        self.dir_cursor = 0
                        self.dir_offset = 0

            await self.render_directory()

        elif cmd == 'WHO':
            cs._regenerate_who_frame()
            frame_path = os.path.join(cs.WHO_PAGE_DIR, 'frame-1.seq')
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    frame_data = f.read()
                await self.send(CLR)
                await self.set_charset("upper")
                await self.send(expand_frame(frame_data))
                await self.read_key()  # Wait for any key
            await self.render_directory()

        elif cmd == 'LEAVE':
            cs = _get_server()
            goodbye_path = os.path.join(cs.CONTENT_DIR, 'templates', 'goodbye.seq')
            await self.send(CLR)
            await self.set_charset("upper")
            if os.path.exists(goodbye_path):
                with open(goodbye_path, 'rb') as f:
                    await self.send(expand_frame(f.read()))
            else:
                await self.send(COL_BLUE)
                await self.send_text('\r\r  GOODBYE!\r')
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('PRESS ANY KEY')
            await self.read_key()
            raise ConnectionResetError("User left")

        elif cmd == 'MORE':
            if self.show_page and self.show_frame_idx < len(self.show_page.frames) - 1:
                self.show_frame_idx += 1
                await self.render_frame()
            else:
                self.mode = 'directory'
                self.show_page = None
                self.duck_pos = getattr(self, '_saved_duck_pos', 0)
                await self.render_directory()

        elif cmd == 'FINISH':
            self.mode = 'directory'
            self.show_page = None
            self.duck_pos = getattr(self, '_saved_duck_pos', 0)
            await self.render_directory()

        elif cmd == 'VOTE':
            if self.mode != 'directory':
                return
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                await self.cursor_to(24, 0)
                await self.send(COL_WHITE)
                await self.send_text('VOTE (1-9)? '.ljust(39))
                await self.cursor_to(24, 12)
                score_str = await self.read_line(max_len=1)
                try:
                    score = int(score_str)
                    if 1 <= score <= 9:
                        child = visible[self.dir_cursor]
                        votes_path = cs.VOTES_PATH
                        import json
                        votes = {}
                        if os.path.exists(votes_path):
                            with open(votes_path, 'r') as f:
                                votes = json.load(f)
                        page_key = str(child.page_num)
                        if page_key not in votes:
                            votes[page_key] = {}
                        votes[page_key][self.user_id] = score
                        with open(votes_path, 'w') as f:
                            json.dump(votes, f)
                        cs.audit_log('vote', user=self.user_id, ip=self.client_ip,
                                     page=child.page_num, title=child.title, score=score)
                except (ValueError, TypeError):
                    pass
            await self.cursor_to(24, 0)
            await self.render_duckshoot()

        elif cmd == 'MAIL':
            self.mail_messages = self._load_mail()
            self.mail_cursor = 0
            self.mail_offset = 0
            self._saved_duck_pos = self.duck_pos
            self.mode = 'mail'
            self.duck_pos = 3  # SEND is default selected
            await self.render_mail()

        elif cmd == 'DONE':
            self.mode = 'directory'
            self.duck_pos = getattr(self, '_saved_duck_pos', 0)
            await self.render_directory()

        elif cmd == 'ID':
            cs = _get_server()
            users = cs._api_load_users()

            # Draw ID screen
            await self.send(CLR)
            if self.terminal_type == 'c64':
                await self.send(UPPERCASE)
            self.charset = 'upper'
            await self.send(COL_BLUE)

            # Row 3: COURIER header
            await self.cursor_to(3, 3)
            await self.send_text('COURIER')

            # Row 4: divider
            await self.cursor_to(4, 3)
            await self.send(self.B_THICK_H * 7)

            # Draw colon placeholders for 5 slots
            for i in range(5):
                await self.cursor_to(6 + i, 12)
                await self.send_text(':')

            # Prompt for IDs
            ids_entered = []
            for i in range(5):
                await self.cursor_to(24, 0)
                await self.send(COL_WHITE)
                await self.send_text('ID TO CHECK? '.ljust(39))
                await self.cursor_to(24, 13)
                user_id = await self.read_line(max_len=8)

                if not user_id.strip():
                    if i == 0:
                        await self.render_mail()
                        return
                    break

                ids_entered.append(user_id.strip())
                # Show ID on screen
                await self.cursor_to(6 + i, 3)
                await self.send(COL_BLUE)
                await self.send_text(user_id.strip()[:8])

            # Show real names / errors
            for i, uid in enumerate(ids_entered):
                user = users.get(uid)
                await self.cursor_to(6 + i, 14)
                if user:
                    name = user.get('name', uid)
                    await self.send(COL_BLUE)
                    await self.send_text(name[:20])
                else:
                    await self.send(COL_RED)
                    await self.send_text('*** NO SUCH USER ***')

            # Press any key
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('PRESS ANY KEY'.ljust(39))
            await self.read_key()
            await self.render_mail()

        elif cmd == 'LIFE':
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                child = visible[self.dir_cursor]
                await self.cursor_to(24, 0)
                await self.send(COL_WHITE)
                await self.send_text('EXTEND BY? '.ljust(39))
                await self.cursor_to(24, 11)
                ext_str = await self.read_line(max_len=4)
                try:
                    extend_by = int(ext_str) if ext_str.strip() else 0
                except ValueError:
                    extend_by = 0
                if extend_by != 0:
                    # Permission check for negative extend
                    if extend_by < 0:
                        users = cs._api_load_users()
                        user_data = users.get(self.user_id, {})
                        if (child.author != self.user_id and
                                not user_data.get('admin') and
                                not user_data.get('editor')):
                            await self.cursor_to(24, 0)
                            await self.send_text('NOT PERMITTED'.ljust(39))
                            await self.read_key()
                            await self.cursor_to(24, 0)
                            await self.render_duckshoot()
                            return
                    num_frames = len(child.frames) if child.frames else 1
                    if extend_by > 0:
                        # Deduct from free storage, overflow to credit
                        import json
                        users = cs._api_load_users()
                        user = users.get(self.user_id, {})
                        storage_cost = num_frames * extend_by
                        free_used = user.get('free_storage_used', 0)
                        free_remaining = max(0, 2000 - free_used)
                        if storage_cost <= free_remaining:
                            user['free_storage_used'] = free_used + storage_cost
                        else:
                            from_free = free_remaining
                            user['free_storage_used'] = free_used + from_free
                            user['credit'] = user.get('credit', 0.0) - (storage_cost - from_free)
                        child.life += extend_by
                        users_path = os.path.join(os.path.dirname(__file__), 'cfg', 'users.json')
                        with open(users_path, 'w') as f:
                            json.dump(users, f)
                    else:
                        # Negative: reduce life, refund storage
                        actual_reduction = min(abs(extend_by), child.life)
                        refund = num_frames * actual_reduction
                        import json
                        users = cs._api_load_users()
                        user = users.get(self.user_id, {})
                        user['free_storage_used'] = max(0, user.get('free_storage_used', 0) - refund)
                        child.life -= actual_reduction
                        users_path = os.path.join(os.path.dirname(__file__), 'cfg', 'users.json')
                        with open(users_path, 'w') as f:
                            json.dump(users, f)
                    # Save directory and audit
                    self._save_directory_tree(cs)
                    cs.audit_log('extend', user=self.user_id, ip=self.client_ip,
                                 page=child.page_num, title=child.title,
                                 extend_by=extend_by, new_life=child.life)
            await self.render_directory()

        elif cmd == 'ACCNT':
            cs = _get_server()
            users = cs._api_load_users()
            user = users.get(self.user_id, {})
            credit = user.get('credit', 0.0)
            if credit >= 0:
                msg = f'YOU ARE {credit:.2f} IN CREDIT'
            else:
                msg = f'YOU ARE {abs(credit):.2f} IN DEBIT'
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text(msg.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()

        elif cmd == 'BUY':
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                child = visible[self.dir_cursor]
                # Deduct credit for paid pages
                if child.price > 0:
                    users = cs._api_load_users()
                    user = users.get(self.user_id, {})
                    user['credit'] = user.get('credit', 0.0) - child.price
                    import json
                    users_path = os.path.join(os.path.dirname(__file__), 'cfg', 'users.json')
                    with open(users_path, 'w') as f:
                        json.dump(users, f)
                    cs.audit_log('buy', user=self.user_id, ip=self.client_ip,
                                 page=child.page_num, title=child.title, price=child.price)
                # Type L (link): enter partyline
                if child.page_type == 'L':
                    await self._enter_partyline()
                # Program page: trigger XMODEM download
                elif child.page_type == 'P' and child.frames:
                    await self._xmodem_send(child)
                else:
                    # Non-program: just show the page (same as SHOW)
                    if child.frames:
                        self.show_page = child
                        self.show_frame_idx = 0
                        await self.render_frame()
                    else:
                        await self.render_directory()
            else:
                await self.render_directory()

        elif cmd == 'UCAT':
            # Save current location
            self._ucat_saved_page = self.current_page
            self._ucat_saved_cursor = self.dir_cursor
            self._ucat_saved_offset = self.dir_offset
            self._ucat_active = True
            # Build virtual page with user's uploads
            cs = _get_server()
            ucat_page = cs.CompunetPage(
                page_num=0, title='YOUR UPLOADS', page_type='D', author=self.user_id)
            ucat_page.parent = None
            user_pages = [p for p in self.directory.pages.values()
                          if p.author == self.user_id]
            ucat_page.children = sorted(user_pages, key=lambda p: p.page_num)
            self.current_page = ucat_page
            self.dir_cursor = 0
            self.dir_offset = 0
            await self.render_directory()

        elif cmd == 'UPLD':
            await self._cmd_upload()

        elif cmd == 'EDITR':
            if not self._frame_memory:
                blank_frame = b'\x00\x06\x0F\x8E\x0D\x00'
                self._frame_memory.append(blank_frame)
            self._saved_duck_pos = self.duck_pos
            self.mode = 'editor'
            self.duck_pos = 1  # HELP default
            self._editor_idx = len(self._frame_memory) - 1
            await self._render_editor_frame()

        elif cmd == 'RETURN':
            self.mode = 'directory'
            self.duck_pos = getattr(self, '_saved_duck_pos', 0)
            await self.render_directory()

        elif cmd == 'LAST':
            if self._frame_memory and self._editor_idx > 0:
                self._editor_idx -= 1
                await self._render_editor_frame()

        elif cmd == 'NEXT':
            if self._frame_memory and self._editor_idx < len(self._frame_memory) - 1:
                self._editor_idx += 1
                await self._render_editor_frame()

        elif cmd == 'EDIT':
            await self._cmd_edit()

        elif cmd == 'NEW':
            # Create a blank frame and add to memory
            blank_frame = b'\x00\x06\x0F\x8E\x0D\x00'  # minimal frame: flags, space, bg, uppercase, CR, end
            self._frame_memory.append(blank_frame)
            if len(self._frame_memory) > 20:
                self._frame_memory.pop(0)
            self._editor_idx = len(self._frame_memory) - 1
            await self._render_editor_frame()

        elif cmd == 'COPY':
            # Duplicate the current frame in memory
            if self._frame_memory and 0 <= self._editor_idx < len(self._frame_memory):
                copy = self._frame_memory[self._editor_idx]
                self._frame_memory.append(copy)
                if len(self._frame_memory) > 20:
                    self._frame_memory.pop(0)
                self._editor_idx = len(self._frame_memory) - 1
                await self._render_editor_frame()

        elif cmd == 'ERASE':
            # Erase the current frame (replace with blank)
            if self._frame_memory and 0 <= self._editor_idx < len(self._frame_memory):
                blank_frame = b'\x00\x06\x0F\x8E\x0D\x00'
                self._frame_memory[self._editor_idx] = blank_frame
                await self._render_editor_frame()

        elif cmd == 'PUT':
            # Download current frame via XMODEM
            if self._frame_memory and 0 <= self._editor_idx < len(self._frame_memory):
                frame_data = self._frame_memory[self._editor_idx]
                await self.cursor_to(24, 0)
                await self.send(COL_WHITE)
                await self.send_text(f'XMODEM: frame ({len(frame_data)}b)'.ljust(39))
                try:
                    start_byte = await asyncio.wait_for(self._wait_xmodem_start(), timeout=60.0)
                except asyncio.TimeoutError:
                    await self.cursor_to(24, 0)
                    await self.send_text('TRANSFER TIMEOUT'.ljust(39))
                    await self.read_key()
                    await self._render_editor_frame()
                    return
                # Send frame data via XMODEM
                await self._xmodem_send_data(frame_data, start_byte == 0x43)
                await self.cursor_to(24, 0)
                await self.send_text('TRANSFER COMPLETE'.ljust(39))
                await self.read_key()
            await self._render_editor_frame()

        elif cmd == 'GET':
            # Upload frame(s) via XMODEM into editor memory
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('START XMODEM UPLOAD NOW...'.ljust(39))
            try:
                raw_data = await self._xmodem_receive()
            except (asyncio.TimeoutError, ConnectionResetError):
                await self.cursor_to(24, 0)
                await self.send_text('TRANSFER FAILED'.ljust(39))
                await self.read_key()
                await self._render_editor_frame()
                return
            if raw_data:
                # Split on $00 terminators into individual frames
                frames = []
                start = 0
                for i in range(len(raw_data)):
                    if raw_data[i] == 0x00 and i > start:
                        frames.append(raw_data[start:i + 1])  # include the $00
                        start = i + 1
                if start < len(raw_data):
                    # Remaining data without terminator — add $00
                    frames.append(raw_data[start:] + b'\x00')
                # Load frames into memory
                for frame in frames:
                    self._frame_memory.append(frame)
                    if len(self._frame_memory) > 20:
                        self._frame_memory.pop(0)
                self._editor_idx = len(self._frame_memory) - 1
                await self.cursor_to(24, 0)
                await self.send_text(f'{len(frames)} FRAME(S) LOADED'.ljust(39))
            else:
                await self.cursor_to(24, 0)
                await self.send_text('NO DATA RECEIVED'.ljust(39))
            await self.read_key()
            await self._render_editor_frame()

        elif cmd == 'STORE':
            # Download ALL frames in memory via XMODEM
            if not self._frame_memory:
                await self.cursor_to(24, 0)
                await self.send(COL_WHITE)
                await self.send_text('NO FRAMES IN MEMORY'.ljust(39))
                await self.read_key()
                await self._render_editor_frame()
                return
            # Concatenate all frames (each already $00-terminated)
            all_data = bytearray()
            for frame in self._frame_memory:
                all_data.extend(frame)
                if not frame.endswith(b'\x00'):
                    all_data.append(0x00)
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text(f'XMODEM: {len(self._frame_memory)} frames ({len(all_data)}b)'.ljust(39))
            try:
                start_byte = await asyncio.wait_for(self._wait_xmodem_start(), timeout=60.0)
            except asyncio.TimeoutError:
                await self.cursor_to(24, 0)
                await self.send_text('TRANSFER TIMEOUT'.ljust(39))
                await self.read_key()
                await self._render_editor_frame()
                return
            await self._xmodem_send_data(bytes(all_data), start_byte == 0x43)
            await self.cursor_to(24, 0)
            await self.send_text('TRANSFER COMPLETE'.ljust(39))
            await self.read_key()
            await self._render_editor_frame()

        elif cmd == 'FREE':
            free_frames = 20 - len(self._frame_memory)
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text(f'{free_frames} FRAMES FREE'.ljust(39))
            await self.read_key()
            await self.cursor_to(24, 0)
            await self.render_duckshoot()

        elif cmd == 'SEND':
            if self.mode == 'mail':
                await self._cmd_mail_send()
            else:
                await self._cmd_upload_send()

        elif cmd == 'ABORT':
            self._upload_pending = None
            await self.render_directory()

        elif cmd == 'HELP':
            cs = _get_server()
            if self.mode == 'editor':
                help_path = os.path.join(os.path.dirname(__file__), 'cfg', 'editor-help.pet')
            else:
                help_path = os.path.join(os.path.dirname(__file__), 'cfg', 'help.pet')
            if os.path.exists(help_path):
                with open(help_path, 'rb') as f:
                    await self.send(f.read())
            else:
                await self.send(CLR)
                await self.send_text('HELP not available\r')
            await self.cursor_to(24, 0)
            await self.send(COL_WHITE)
            await self.send_text('PRESS ANY KEY')
            await self.read_key()
            if self.mode == 'editor':
                await self._render_editor_frame()
            else:
                await self.render_directory()

    # --- Main input loop ---

    async def run(self):
        """Main session loop — handle input and dispatch."""
        while True:
            key = await self.read_key()

            if self.mode == 'directory':
                if key == KEY_CRSR_DOWN:
                    visible = self.current_page.children[self.dir_offset:self.dir_offset + 11]
                    if self.dir_cursor < len(visible) - 1:
                        old = self.dir_cursor
                        self.dir_cursor += 1
                        await self.redraw_entry(old)
                        await self.redraw_entry(self.dir_cursor)
                elif key == KEY_CRSR_UP:
                    if self.dir_cursor > 0:
                        old = self.dir_cursor
                        self.dir_cursor -= 1
                        await self.redraw_entry(old)
                        await self.redraw_entry(self.dir_cursor)
                elif key == KEY_CRSR_RIGHT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos + 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_CRSR_LEFT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos - 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_RETURN:
                    commands = self._get_duckshoot()
                    await self.execute_command(commands[self.duck_pos])
                elif key == KEY_F7 or key == KEY_F8:
                    self.dir_column = (self.dir_column + (1 if key == KEY_F8 else -1)) % 4
                    await self.redraw_column()

            elif self.mode == 'welcome':
                if key == KEY_CRSR_RIGHT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos + 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_CRSR_LEFT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos - 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_RETURN:
                    commands = self._get_duckshoot()
                    cmd = commands[self.duck_pos]
                    # Only certain commands are valid from welcome screen
                    if cmd in ('DIR', 'GOTO', 'MAIL', 'HELP', 'ACCNT', 'LEAVE',
                               'WHO', 'EDITR', 'UCAT'):
                        self.mode = 'directory'
                        if cmd == 'DIR':
                            await self.render_directory()
                        else:
                            await self.execute_command(cmd)

            elif self.mode == 'mail':
                if key == KEY_CRSR_DOWN:
                    visible = self.mail_messages[self.mail_offset:self.mail_offset + 11]
                    if self.mail_cursor < len(visible) - 1:
                        old = self.mail_cursor
                        self.mail_cursor += 1
                        await self.redraw_mail_entry(old)
                        await self.redraw_mail_entry(self.mail_cursor)
                elif key == KEY_CRSR_UP:
                    if self.mail_cursor > 0:
                        old = self.mail_cursor
                        self.mail_cursor -= 1
                        await self.redraw_mail_entry(old)
                        await self.redraw_mail_entry(self.mail_cursor)
                elif key == KEY_CRSR_RIGHT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos + 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_CRSR_LEFT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos - 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_RETURN:
                    commands = self._get_duckshoot()
                    await self.execute_command(commands[self.duck_pos])
                elif key == KEY_F7 or key == KEY_F8:
                    self.mail_column = (self.mail_column + (1 if key == KEY_F8 else -1)) % 3
                    await self.redraw_mail_column()

            elif self.mode == 'upload':
                if key == KEY_CRSR_RIGHT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos + 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_CRSR_LEFT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos - 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_RETURN:
                    commands = self._get_duckshoot()
                    await self.execute_command(commands[self.duck_pos])

            elif self.mode == 'upload_text':
                if key == KEY_CRSR_RIGHT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos + 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_CRSR_LEFT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos - 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_RETURN:
                    commands = self._get_duckshoot()
                    cmd = commands[self.duck_pos]
                    if cmd == 'SEND':
                        # Add current frame to upload
                        if self._frame_memory and 0 <= self._editor_idx < len(self._frame_memory):
                            self._upload_pending['frames'].append(
                                self._frame_memory[self._editor_idx])
                        await self.cursor_to(24, 0)
                        await self.send(COL_WHITE)
                        n = len(self._upload_pending['frames'])
                        await self.send_text(f'FRAME {n} ADDED. NEXT OR FINISH'.ljust(39))
                        await self.read_key()
                        await self.cursor_to(24, 0)
                        await self.render_duckshoot()
                    elif cmd == 'FINSH':
                        await self._complete_text_upload()
                    elif cmd == 'LAST':
                        if self._frame_memory and self._editor_idx > 0:
                            self._editor_idx -= 1
                            await self._render_upload_text_frame()
                    elif cmd == 'NEXT':
                        if self._frame_memory and self._editor_idx < len(self._frame_memory) - 1:
                            self._editor_idx += 1
                            await self._render_upload_text_frame()
                    elif cmd == 'EDITR':
                        await self._cmd_edit()
                        await self._render_upload_text_frame()

            elif self.mode == 'editor':
                if key == KEY_CRSR_RIGHT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos + 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_CRSR_LEFT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos - 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_RETURN:
                    commands = self._get_duckshoot()
                    await self.execute_command(commands[self.duck_pos])

            elif self.mode == 'frame':
                if key == KEY_CRSR_RIGHT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos + 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_CRSR_LEFT:
                    commands = self._get_duckshoot()
                    self.duck_pos = (self.duck_pos - 1) % len(commands)
                    await self.cursor_to(24, 0)
                    await self.render_duckshoot()
                elif key == KEY_RETURN:
                    commands = self._get_duckshoot()
                    await self.execute_command(commands[self.duck_pos])
                elif key == KEY_RUNSTOP:
                    await self.execute_command('FINISH')


async def terminal_handler(reader, writer):
    """Handle a PETSCII terminal connection on port 6401."""
    cs = _get_server()
    addr = writer.get_extra_info('peername')
    logger.info('Terminal client connected: %s', addr)

    # Enable TCP keepalives to prevent NAT/firewall timeout
    import socket
    sock = writer.get_extra_info('socket')
    if sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'TCP_KEEPIDLE'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 15)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 4)

    directory = cs.CompunetDirectory()
    session = TerminalSession(reader, writer, directory)
    session.client_ip = addr[0] if addr else ''

    # Auto-detect Telnet vs Raw: wait briefly for client IAC
    try:
        first = await asyncio.wait_for(reader.read(1), timeout=0.5)
        if first and first[0] == 0xFF:
            # Telnet client — negotiate
            session.telnet = True
            logger.info('Telnet client detected: %s', addr)
            # Consume rest of initial negotiation
            try:
                while True:
                    more = await asyncio.wait_for(reader.read(64), timeout=0.2)
                    if not more:
                        break
            except asyncio.TimeoutError:
                pass
            # Send WILL ECHO, WILL SGA
            writer.write(b'\xff\xfb\x01\xff\xfb\x03')
            await writer.drain()
        else:
            # Raw client — push byte back by prepending to buffer
            session.telnet = False
            if first:
                session._first_byte = first[0]
            logger.info('Raw client detected: %s', addr)
    except asyncio.TimeoutError:
        session.telnet = False
        session._first_byte = None

    try:
        # Login loop (allow 3 attempts)
        for _ in range(3):
            if await session.do_login():
                break
        else:
            await session.send_text('\r  TOO MANY ATTEMPTS\r')
            await asyncio.sleep(2)
            return

        # Main loop (welcome screen already showed duckshoot)
        session.current_page = directory.root
        await session.run()

    except (ConnectionResetError, BrokenPipeError, OSError, asyncio.TimeoutError) as e:
        logger.info('Terminal client disconnected: %s (%s)', addr, e)
    finally:
        if session.user_id:
            cs._online_users.discard(session.user_id)
        try:
            writer.close()
            await writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        logger.info('Terminal session ended: %s', addr)
