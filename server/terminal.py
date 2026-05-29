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
DUCK_MAIL = ['SHOW', 'SEND', 'BACK', 'DONE']

# Import server components (deferred to avoid circular imports)
_server_module = None


def _get_server():
    global _server_module
    if _server_module is None:
        import compunet_server as cs
        _server_module = cs
    return _server_module


def ascii_to_petscii(text):
    """Convert ASCII text to PETSCII (shifted charset / lowercase+uppercase mode).

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
        self.duck_pos = 0
        self.mode = 'login'         # login, directory, frame, mail
        self.show_page = None
        self.show_frame_idx = 0
        self.client_ip = ''
        self.telnet = False
        self.entries_row = 8  # screen row where directory entries start

    # --- I/O helpers ---

    async def send(self, data):
        """Send raw bytes to terminal. Escapes $FF for Telnet."""
        if self.telnet:
            data = data.replace(b'\xff', b'\xff\xff')
        self.writer.write(data)
        await self.writer.drain()

    async def send_text(self, text):
        """Send ASCII text converted to PETSCII."""
        await self.send(ascii_to_petscii(text))

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
        await self.send(COL_BLUE)
        await self.send(CR)
        await self.send_text('    COMPUNET REBORN\r\r')
        await self.send_text('    PETSCII TERMINAL ACCESS\r\r')
        await self.send(COL_CYAN)
        await self.send_text('  Visit compunet.live for registration.\r\r')
        await self.send(COL_WHITE)
        await self.send_text('  PETSCII OK if you see a block: ')
        await self.send(RVS_ON + b'\x20' + RVS_OFF)
        await self.send(CR + CR)

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
            await self.send_text('  UNKNOWN USER ID\r')
            await asyncio.sleep(2)
            return False

        pw_hash = hashlib.sha256(password.upper().encode('utf-8')).hexdigest()
        if user.get('password') != pw_hash:
            await self.send_text('  INCORRECT PASSWORD\r')
            await asyncio.sleep(2)
            return False

        self.user_id = user_id
        self.authenticated = True
        self.client_ip = self.writer.get_extra_info('peername', ('', 0))[0]

        cs._online_users.add(user_id)
        cs.audit_log('connect', user=user_id, ip=self.client_ip)

        # Build welcome frame using same logic as protocol server
        await self.send(CLR)
        await self.send(UPPERCASE)

        welcome_frame = self._make_welcome_frame(user)
        await self.send(expand_frame(welcome_frame))

        await self.send(LOWERCASE)
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
        """Draw the full directory screen with borders matching C64 client."""
        await self.send(CLR)

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
                await self.send(UPPERCASE)
                with open(header_path, 'rb') as f:
                    frame_data = b'\x00\x00\x00\x00' + f.read()
                await self.send(expand_frame(frame_data))

        # Row 6: frame top border
        await self.cursor_to(6, 0)
        await self.send(UPPERCASE)
        await self.send(COL_WHITE)
        await self.send(self.B_TEE_L + self.B_THICK_H * 28 + self.B_THIN_H +
                        self.B_TEE_DOWN + self.B_THIN_H * 8 + self.B_CORNER_TR)

        # Row 7: status line
        await self.send(LOWERCASE)
        await self.send(COL_WHITE)
        await self.send(UPPERCASE)
        await self.send(self.B_THICK_V)
        await self.send(LOWERCASE)
        await self.send(COL_WHITE)
        await self.send_text('    1 ')
        await self.send(COL_BLUE)
        await self.send_text('*** COMPUNET ***')
        await self.send(COL_WHITE)
        spaces = 29 - 6 - 16  # 7 spaces to fill remaining width
        await self.send(b'\x20' * spaces)
        await self.send(UPPERCASE)
        await self.send(self.B_THICK_V)
        await self.send(b'\x20' * 8)
        await self.send(self.B_THICK_V)

        # Row 8: breadcrumb + column header
        await self.send(LOWERCASE)
        await self.send(UPPERCASE)
        await self.send(self.B_THICK_V)
        await self.send(LOWERCASE)
        await self.send(COL_WHITE)
        breadcrumb = f'  {page.page_num} {page.title}'
        await self.send_text(breadcrumb[:29].ljust(29))
        await self.send(UPPERCASE)
        await self.send(self.B_THIN_V)
        await self.send(LOWERCASE)
        cols = ['PRICE', 'LIFE', 'AUTHOR', 'VOTE']
        await self.send_text(cols[self.dir_column].ljust(8)[:8])
        await self.send(UPPERCASE)
        await self.send(self.B_THIN_V)

        # Row 9: entry area top border
        await self.send(self.B_TEE_R + self.B_THICK_H * 29 + self.B_CROSS +
                        self.B_THICK_H * 8 + self.B_TEE_ENTRY_R)

        # Rows 10-20: entries (11 rows)
        await self.send(LOWERCASE)
        visible = page.children[self.dir_offset:self.dir_offset + 11]
        self.entries_row = 10
        for i in range(11):
            if i < len(visible):
                child = visible[i]
                # Page number + title
                page_num_str = str(child.page_num)
                title = child.title[:18].ljust(18)
                type_str = child.type_string()[:5].ljust(5)
                content = f'{page_num_str:3s}   {title}{type_str}'[:29]

                # Column value
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
                    await self.send(UPPERCASE)
                    await self.send(self.B_THICK_V)
                    await self.send(LOWERCASE)
                    await self.send(RVS_ON)
                    await self.send_text(content.ljust(29))
                    await self.send(RVS_OFF)
                    await self.send(UPPERCASE)
                    await self.send(self.B_THIN_V)
                    await self.send(LOWERCASE)
                    await self.send(RVS_ON)
                    await self.send_text(col_val)
                    await self.send(RVS_OFF)
                    await self.send(UPPERCASE)
                    await self.send(self.B_THIN_V)
                else:
                    await self.send(COL_WHITE)
                    await self.send(UPPERCASE)
                    await self.send(self.B_THICK_V)
                    await self.send(LOWERCASE)
                    await self.send(COL_BLUE)
                    await self.send_text(content.ljust(29))
                    await self.send(COL_WHITE)
                    await self.send(UPPERCASE)
                    await self.send(self.B_THIN_V)
                    await self.send(LOWERCASE)
                    await self.send(COL_BLUE)
                    await self.send_text(col_val)
                    await self.send(COL_WHITE)
                    await self.send(UPPERCASE)
                    await self.send(self.B_THICK_V)
            else:
                # Empty row
                await self.send(COL_WHITE)
                await self.send(UPPERCASE)
                await self.send(self.B_THICK_V)
                await self.send(LOWERCASE)
                await self.send(b'\x20' * 29)
                await self.send(UPPERCASE)
                await self.send(self.B_THIN_V)
                await self.send(b'\x20' * 8)
                await self.send(self.B_THICK_V)

        # Row 21: bottom border
        await self.send(UPPERCASE)
        await self.send(COL_WHITE)
        await self.send(self.B_CORNER_BL + self.B_THIN_H * 29 + self.B_TEE_UP)
        await self.send(LOWERCASE)
        await self.send_text('<F7)(F8>')
        await self.send(UPPERCASE)
        await self.send(b'\xab')  # corner

        # Rows 22-23: adverts
        await self.send(LOWERCASE)
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
        await self.send(LOWERCASE)
        await self.send(COL_WHITE)

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
            out.extend(ascii_to_petscii(ch))
        if currently_reversed:
            out.extend(RVS_OFF)
        await self.send(bytes(out))

    async def redraw_column(self):
        """Redraw just the column header and column values (F7/F8 toggle)."""
        # Column header at row 8, col 31
        await self.cursor_to(8, 31)
        await self.send(LOWERCASE)
        await self.send(COL_WHITE)
        cols = ['PRICE', 'LIFE', 'AUTHOR', 'VOTE']
        await self.send_text(cols[self.dir_column].ljust(8)[:8])

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
        content = f'{page_num_str:3s}   {title}{type_str}'[:29]

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
            await self.send(UPPERCASE)
            await self.send(self.B_THICK_V)
            await self.send(LOWERCASE)
            await self.send(RVS_ON)
            await self.send_text(content.ljust(29))
            await self.send(RVS_OFF)
            await self.send(UPPERCASE)
            await self.send(self.B_THIN_V)
            await self.send(LOWERCASE)
            await self.send(RVS_ON)
            await self.send_text(col_val)
            await self.send(RVS_OFF)
            await self.send(UPPERCASE)
            await self.send(self.B_THIN_V)
        else:
            await self.send(COL_WHITE)
            await self.send(UPPERCASE)
            await self.send(self.B_THICK_V)
            await self.send(LOWERCASE)
            await self.send(COL_BLUE)
            await self.send_text(content.ljust(29))
            await self.send(COL_WHITE)
            await self.send(UPPERCASE)
            await self.send(self.B_THIN_V)
            await self.send(LOWERCASE)
            await self.send(COL_BLUE)
            await self.send_text(col_val)
            await self.send(COL_WHITE)
            await self.send(UPPERCASE)
            await self.send(self.B_THICK_V)

    def _get_duckshoot(self):
        if self.mode == 'frame':
            return DUCK_FRAME
        elif self.mode == 'mail':
            return DUCK_MAIL
        return DUCK_DIR

    # --- Frame display ---

    async def render_frame(self):
        """Display a text frame."""
        if not self.show_page or not self.show_page.frames:
            return
        await self.send(CLR)
        await self.send(UPPERCASE)
        frame_data = self.show_page.frames[self.show_frame_idx]
        await self.send(expand_frame(frame_data))

        # Switch back to shifted charset for duckshoot text
        await self.send(LOWERCASE)

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
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                child = visible[self.dir_cursor]
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
                if child.has_subdir():
                    self.current_page = child
                    self.dir_cursor = 0
                    self.dir_offset = 0
            await self.render_directory()

        elif cmd == 'BACK':
            if self.current_page.parent:
                self.current_page = self.current_page.parent
                self.dir_cursor = 0
                self.dir_offset = 0
            await self.render_directory()

        elif cmd == 'GOTO':
            await self.cursor_to(23, 0)
            await self.send(COL_WHITE)
            await self.send_text('PAGE? ')
            page_str = await self.read_line(max_len=6)
            try:
                page_num = int(page_str)
                if page_num in self.directory.pages:
                    target = self.directory.pages[page_num]
                    if target.parent:
                        self.current_page = target.parent
                    self.dir_cursor = 0
                    self.dir_offset = 0
            except ValueError:
                pass
            await self.render_directory()

        elif cmd == 'WHO':
            cs._regenerate_who_frame()
            frame_path = os.path.join(cs.WHO_PAGE_DIR, 'frame-1.seq')
            if os.path.exists(frame_path):
                with open(frame_path, 'rb') as f:
                    frame_data = f.read()
                await self.send(CLR)
                await self.send(UPPERCASE)
                await self.send(expand_frame(frame_data))
                await self.read_key()  # Wait for any key
            await self.render_directory()

        elif cmd == 'LEAVE':
            await self.send(CLR)
            await self.send(COL_BLUE)
            await self.send_text('\r\r  GOODBYE!\r')
            await asyncio.sleep(1)
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
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                await self.cursor_to(23, 0)
                await self.send(COL_WHITE)
                await self.send_text('VOTE (1-9)? ')
                score_str = await self.read_line(max_len=1)
                try:
                    score = int(score_str)
                    if 1 <= score <= 9:
                        child = visible[self.dir_cursor]
                        # Use server vote logic
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
            await self.render_directory()

        elif cmd == 'MAIL':
            # Simple mail listing for now
            await self.send(CLR)
            await self.send(COL_BLUE)
            await self.send_text('  COURIER - MAIL\r\r')
            mail_dir = os.path.join(cs.MAIL_DIR, self.user_id)
            if os.path.exists(mail_dir):
                import json
                meta_files = sorted([f for f in os.listdir(mail_dir) if f.endswith('.json')])
                for mf in meta_files[:11]:
                    with open(os.path.join(mail_dir, mf)) as f:
                        msg = json.load(f)
                    if not msg.get('read'):
                        await self.send(COL_WHITE)
                    else:
                        await self.send(COL_BLUE)
                    await self.send_text(f"  {msg.get('from','?')}: {msg.get('subject','')[:25]}\r")
            else:
                await self.send_text('  NO MAIL\r')
            await self.send(CR)
            await self.send(COL_WHITE)
            await self.send_text('  PRESS ANY KEY')
            await self.read_key()
            await self.render_directory()

        elif cmd == 'LIFE':
            page = self.current_page
            visible = page.children[self.dir_offset:self.dir_offset + 11]
            if self.dir_cursor < len(visible):
                child = visible[self.dir_cursor]
                await self.cursor_to(23, 0)
                await self.send(COL_WHITE)
                await self.send_text(f'LIFE: {child.life} DAYS  ')
            await self.read_key()
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
                    self.mode = 'directory'
                    if cmd == 'DIR':
                        # From welcome: show root directory (don't enter a child)
                        await self.render_directory()
                    else:
                        await self.execute_command(cmd)

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
