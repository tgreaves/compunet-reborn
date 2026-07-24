#!/usr/bin/env python3
"""
Compunet Reborn — Tier 1 test client (pygame).

PURPOSE
    A measuring instrument for the specification, not a product. It is built
    CLEAN-ROOM from docs/spec/ ONLY — deliberately not referencing server/ or
    the C64/Amiga client source. Every point where the spec left a genuine
    question is marked `SPEC-GAP:` in the code and echoed to the console at
    startup, so building it doubles as a suitability audit of the spec.

SCOPE
    Tier 1 "Browse" (spec §1.4): connect, identify, log in, navigate
    directories, and render frames — exercising spec §§2–7.

DATA
    The C64 font, the 16-colour palette, and the built-in directory template
    are loaded at runtime by parsing the spec's Appendix A
    (docs/spec/99-appendices.md), so the client is a direct consumer of the
    spec's own self-contained data.

USAGE
    python compunet_client.py [host:port] [userid] [password]
    defaults: docker.lan:6400

    Keys:  digits + Enter select an entry (D)   ·   B = back   ·   Space = MORE
           P = show current directory           ·   Esc/Q = quit (LEAVE)
"""

import os
import re
import sys
import socket
import time
# pygame is imported lazily in main() so the transport/asset/render logic can
# be exercised headless (no display) for testing.

# ---------------------------------------------------------------------------
# Running list of places the spec left me guessing (printed at startup).
# ---------------------------------------------------------------------------
SPEC_GAPS = []

SPEC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', '..', 'docs', 'spec')
APPENDIX = os.path.join(SPEC_DIR, '99-appendices.md')

# ===========================================================================
# Appendix A loader — font (§A.5), palette (§A.3), directory template (§A.6)
# ===========================================================================

def load_spec_assets():
    text = open(APPENDIX, encoding='utf-8').read()

    # --- §A.5 font: two sets of 128 glyphs, lines like "  $0A: 3C 66 ..." ---
    def parse_set(header):
        # take the fenced block that follows the given "### ... header" line
        idx = text.index(header)
        block = text[idx: text.index('```', text.index('```', idx) + 3)]
        glyphs = {}
        for m in re.finditer(r'\$([0-9A-Fa-f]{2}):\s*((?:[0-9A-Fa-f]{2}\s*){8})', block):
            code = int(m.group(1), 16)
            glyphs[code] = [int(b, 16) for b in m.group(2).split()]
        return glyphs
    font_upper = parse_set('### Set 1')
    font_lower = parse_set('### Set 2')

    # --- §A.3 palette: table cells "| 2 | red | `#DD0000` |" ---
    palette = {}
    for m in re.finditer(r'\|\s*(\d{1,2})\s*\|\s*[a-z ]+\|\s*`?#([0-9A-Fa-f]{6})`?', text):
        idx = int(m.group(1))
        if idx not in palette:
            hexv = m.group(2)
            palette[idx] = (int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16))

    # --- §A.6 directory template: hex block "  $BCE1: 00 F4 ..." ---
    tstart = text.index('## §A.6')
    tpl = []
    for m in re.finditer(r'\$[0-9A-Fa-f]{4}:\s*((?:[0-9A-Fa-f]{2}\s*)+)', text[tstart:]):
        tpl += [int(b, 16) for b in m.group(1).split()]

    assert len(font_upper) == 128 and len(font_lower) == 128, 'font parse failed'
    assert len(palette) == 16, f'palette parse failed ({len(palette)})'
    assert tpl, 'template parse failed'
    return font_upper, font_lower, palette, bytes(tpl)


# ===========================================================================
# §2 Transport — framing, byte-stuffing, CRC, sequence, ACK
# ===========================================================================

PKT_START, PKT_END = 0x01, 0x02
TOK_ACK, TOK_DAT, TOK_COM = 0x20, 0x22, 0x43
SEQ_MIN, SEQ_MAX = 0x20, 0x5F


def crc_ccitt(data, crc=0x0000):                       # §2.6 (reference algo)
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return (crc >> 8) & 0xFF, crc & 0xFF


def byte_stuff(data):                                  # §2.3
    out = bytearray()
    for b in data:
        if 0x01 <= b <= 0x03:
            out += bytes([0x03, b + 0x20])
        else:
            out.append(b)
    return bytes(out)


class Transport:
    def __init__(self, sock):
        self.sock = sock
        self.rx = bytearray()
        # SPEC-GAP: §2.8 gives the server's starting tx seq ($21) but never
        # states what a client's first COM sequence number should be, nor
        # whether the server validates it. Starting at $20.
        self.tx_seq = SEQ_MIN

    def _next_seq(self):
        s = self.tx_seq
        self.tx_seq = SEQ_MIN if s >= SEQ_MAX else s + 1
        return s

    def send_packet(self, token, payload=b''):         # §2.4
        seq = self._next_seq()
        content = bytearray([len(payload) + 5, token, seq]) + payload
        content += bytes(crc_ccitt(content))
        wire = bytes([PKT_START]) + byte_stuff(content) + bytes([PKT_END])
        self.sock.sendall(wire)
        log(f'TX {tok(token)} seq=${seq:02X} payload={len(payload)}b  {wire.hex()}')

    def send_com(self, payload):
        self.send_packet(TOK_COM, payload)

    def send_ack(self, seq):                            # §2.9 / §2.7
        content = bytearray([0x06, TOK_ACK, 0x20, seq])
        content += bytes(crc_ccitt(content))
        self.sock.sendall(bytes([PKT_START]) + byte_stuff(content) + bytes([PKT_END]))
        log(f'TX ACK seq=${seq:02X}')

    def _read_more(self, timeout=10.0):
        self.sock.settimeout(timeout)
        chunk = self.sock.recv(4096)
        if not chunk:
            raise ConnectionError('server closed connection')
        self.rx += chunk

    def read_packet(self, timeout=10.0):
        """Return (token, seq, payload) for the next framed packet, de-stuffed."""
        while True:
            if PKT_START in self.rx:
                s = self.rx.index(PKT_START)
                if PKT_END in self.rx[s:]:
                    e = self.rx.index(PKT_END, s)
                    wire = bytes(self.rx[s + 1:e])
                    del self.rx[:e + 1]
                    content = self._destuff(wire)
                    if len(content) < 5:
                        continue
                    token, seq, payload = content[1], content[2], content[3:-2]
                    log(f'RX {tok(token)} seq=${seq:02X} payload={len(payload)}b')
                    return token, seq, payload
            self._read_more(timeout)

    @staticmethod
    def _destuff(wire):
        out = bytearray()
        i = 0
        while i < len(wire):
            if wire[i] == 0x03 and i + 1 < len(wire) and 0x20 <= wire[i + 1] <= 0x2F:
                out.append(wire[i + 1] - 0x20)
                i += 2
            else:
                out.append(wire[i])
                i += 1
        return bytes(out)

    def read_dat_stream(self, timeout=10.0):
        """§4.2: reassemble a DAT stream, ACKing each non-empty DAT, until the
        zero-length EOS DAT (§2.9). Returns the concatenated payload."""
        buf = bytearray()
        while True:
            token, seq, payload = self.read_packet(timeout)
            if token == TOK_DAT and len(payload) == 0:
                return bytes(buf)                       # EOS — not ACKed
            if token == TOK_DAT:
                buf += payload
                self.send_ack(seq)
            # SPEC-GAP: §4.2 does not say what a client should do with a
            # non-DAT packet arriving mid-stream; ignoring it.

    def read_raw_until(self, marker, timeout=15.0):
        """Read raw (un-framed) bytes until `marker` appears; return all bytes."""
        while marker not in self.rx:
            self._read_more(timeout)
        i = self.rx.index(marker) + len(marker)
        out = bytes(self.rx[:i])
        del self.rx[:i]
        return out


def tok(t):
    return {TOK_ACK: 'ACK', TOK_DAT: 'DAT', TOK_COM: 'COM'}.get(t, f'${t:02X}')


VERBOSE = True
def log(msg):
    if VERBOSE:
        print(msg)


# ===========================================================================
# §3 Session lifecycle — handshake, identification, greeting, login
# ===========================================================================

def connect_and_login(host, port, user, password):
    sock = socket.create_connection((host, port), timeout=15)
    t = Transport(sock)

    # §3.2 handshake. SPEC-GAP: §3.2 says the server sends a 12×$20 burst and
    # the client must tolerate it, but is not explicit that the client must
    # first send a handshake byte. Sending one $20 (the server peeks the first
    # byte); then discard the server's leading $20 run.
    sock.sendall(bytes([0x20]))

    # §3.3 native identification (raw bytes)
    sock.sendall(b'C CNET\r')
    sock.sendall(b'C CNET\r')
    time.sleep(0.2)
    sock.sendall(b'00000000000000\r')
    log('TX identification (native)')

    # §3.4 greeting: raw MOTD then "*CON\r". Read raw until the connection
    # signal. The leading $20 burst is consumed here too (it is raw, no $01).
    greeting = t.read_raw_until(b'*CON\r')
    motd = bytes(b for b in greeting if b not in (0x20,)).rstrip(b'\r')
    log(f'RX greeting ({len(greeting)}b), *CON received')

    # §3.5 login COM packet: 'Z' + user(8) + pass(6) + sysinfo(10, zero) + hash(2, zero)
    payload = (b'Z'
               + user.upper().encode('latin-1')[:8].ljust(8)
               + password.encode('latin-1')[:6].ljust(6)
               + bytes(12))                             # §3.5: native may zero-fill 15–26
    t.send_com(payload)
    log('TX login')

    # §3.5: server replies with the welcome frame as a DAT stream + EOS.
    welcome = t.read_dat_stream(timeout=20)
    log(f'RX welcome frame ({len(welcome)}b)')
    return t, welcome


# ===========================================================================
# §5 Display + §6 Frame + §7 Directory rendering
# ===========================================================================

CTRL_COLOUR = {0x05: 1, 0x1C: 2, 0x1E: 5, 0x1F: 6, 0x81: 8, 0x90: 0,
               0x95: 9, 0x96: 10, 0x97: 11, 0x98: 12, 0x99: 13, 0x9A: 14,
               0x9B: 15, 0x9C: 4, 0x9E: 7, 0x9F: 3}


def petscii_to_screen(b):                              # §5.3
    if 0x20 <= b <= 0x3F: return b
    if 0x40 <= b <= 0x5F: return b & 0x1F
    if 0x60 <= b <= 0x7F: return (b & 0x1F) | 0x40
    if 0xA0 <= b <= 0xBF: return (b & 0x1F) | 0x60
    if 0xC0 <= b <= 0xDF: return b & 0x7F
    if 0xE0 <= b <= 0xFE: return b & 0x7F
    if b == 0xFF: return 0x5E
    return b & 0x7F


class Screen:
    """A 40×24 cell grid: each cell = (screencode, colour_index, reverse, lower_set)."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.cells = [[(0x20, 1, False, False) for _ in range(40)] for _ in range(24)]
        self.row = self.col = 0
        self.colour = 1           # see SPEC-GAP note below
        self.reverse = False
        self.lower = False
        self.border = 0
        self.background = 0
        # §5.6 "just-wrapped" flag: set when printing a char auto-wraps the
        # column; a CR that follows resets the column WITHOUT advancing the row
        # (prevents the double-row-advance / blank-line-per-row bug). Matches
        # the Amiga's P_WRAP guard in carriage_return.
        self.wrap = False

    def put(self, screencode):
        if 0 <= self.row < 24 and 0 <= self.col < 40:
            self.cells[self.row][self.col] = (screencode, self.colour, self.reverse, self.lower)
        self.col += 1
        if self.col == 40:                             # §5.6 column wrap
            self.col = 0
            if self.row < 23:
                self.row += 1
            self.wrap = True
        else:
            self.wrap = False

    def _cr(self):                                     # §5.6 carriage return (guarded)
        if not self.wrap and self.row < 23:
            self.row += 1
        self.col = 0
        self.wrap = False
        self.reverse = False

    def control(self, b):                              # §5.6
        if b in CTRL_COLOUR: self.colour = CTRL_COLOUR[b]
        elif b == 0x0D: self._cr()
        elif b == 0x8D: self._cr()
        elif b == 0x11: self.row = min(23, self.row + 1); self.wrap = False
        elif b == 0x91: self.row = max(0, self.row - 1); self.wrap = False
        elif b == 0x1D: self.col = min(39, self.col + 1); self.wrap = False
        elif b == 0x9D: self.col = max(0, self.col - 1); self.wrap = False
        elif b == 0x13: self.row = self.col = 0; self.wrap = False
        elif b == 0x93: self.reset_grid()
        elif b == 0x12: self.reverse = True
        elif b == 0x92: self.reverse = False
        elif b == 0x0E: self.lower = True
        elif b == 0x8E: self.lower = False
        # others: no-op

    def reset_grid(self):
        self.cells = [[(0x20, self.colour, False, self.lower) for _ in range(40)] for _ in range(24)]
        self.row = self.col = 0


def render_frame_bytes(screen, data, start=0):
    """§6.2/§6.3: parse header + body into `screen`. `start`=0 for a full frame
    (with header); the directory path uses this on body-only fragments."""
    i = start
    if start == 0:                                     # §6.2 4-byte header
        flags = data[0]
        screen.border = data[1] & 0x0F
        screen.background = data[2] & 0x0F
        # byte 3 = charset control
        screen.lower = (data[3] == 0x0E)
        i = 4
    # §6.3 processing algorithm
    # SPEC-GAP: §6.3 says the pre-colour default text colour is undefined.
    # Choosing white (1) so unstyled text is visible.
    while i < len(data):
        b = data[i]; i += 1
        if b == 0x00:
            break
        elif b == 0x06:                                # §6.4 space run
            n = data[i]; i += 1
            for _ in range(1 + n): screen.put(petscii_to_screen(0x20))
        elif b == 0x07:                                # §6.4 char run
            c = data[i]; n = data[i + 1]; i += 2
            if c < 0x20 or 0x80 <= c <= 0x9F:
                for _ in range(1 + n): screen.control(c)
            else:
                for _ in range(1 + n): screen.put(petscii_to_screen(c))
        elif b < 0x20 or 0x80 <= b <= 0x9F:            # control code
            screen.control(b)
        else:                                          # character
            screen.put(petscii_to_screen(b))
    return i


def _emit_text(screen, data):
    for b in data:
        if b < 0x20 or 0x80 <= b <= 0x9F:
            screen.control(b)
        else:
            screen.put(petscii_to_screen(b))


def render_directory(screen, template, parts, sel_col=0, selected=0):
    """§7.7 composition: draw the template, then overlay the parts. Each entry
    shows ONLY its first field + one selected column value (§7.3/§7.7) — never
    the whole comma-separated line (which overflows 40 columns)."""
    screen.reset()
    render_frame_bytes(screen, template, start=0)      # base chrome (§7.5) — 6 blank header rows + box
    # §7.2 Part 1: an optional header frame (e.g. the COMPUNET logo) overlaid on
    # the header region (rows 0–5). A leading-only $8E (empty header) draws nothing.
    if len(parts['part1']) > 1:
        screen.row, screen.col, screen.colour = 0, 0, 1
        render_frame_bytes(screen, parts['part1'] + b'\x00', start=1)
    if parts['part4']:                                 # path @ row 7 col 1
        screen.row, screen.col = 7, 1
        render_frame_bytes(screen, parts['part4'] + b'\x00', start=1)
    row = 10                                           # entries @ rows 10-20
    for i, entry in enumerate(parts['entries'][:11]):
        fields = entry.split(b',')
        first = fields[0][:27]                         # §7.3 fixed first field
        screen.colour = 6 if i == selected else 2      # §7.7 highlight/normal pen
        screen.row, screen.col = row, 1
        _emit_text(screen, first)
        if len(fields) > 1 + sel_col:                  # one selected column value
            val = fields[1 + sel_col].strip()[:8]
            screen.row, screen.col = row, 31
            _emit_text(screen, val)
        row += 1
    if parts['part2']:                                 # footer @ row 22
        screen.row, screen.col = 22, 0
        render_frame_bytes(screen, parts['part2'] + b'\x00', start=1)


def parse_directory(data):                             # §7.2
    """Split the six-part directory stream. Parts end at $00 (1,3,4,5) or are
    CR-lines (2); part 6 entries are $0D-terminated lines."""
    def read_to_zero(buf, i):
        j = buf.index(0, i) if 0 in buf[i:] else len(buf)
        return buf[i:j], j + 1
    i = 0
    part1, i = read_to_zero(data, i)                   # header frame (or empty)
    # part2: two CR-terminated lines
    p2 = bytearray()
    for _ in range(2):
        if i < len(data) and data[i] == 0x00:          # leading $00 = none
            i += 1; break
        j = data.index(0x0D, i) if 0x0D in data[i:] else len(data)
        p2 += data[i:j] + b'\r'; i = j + 1
    part3, i = read_to_zero(data, i)                   # field defs
    part4, i = read_to_zero(data, i)                   # path line
    # part5: one CR-terminated line then a $00 separator
    j = data.index(0x0D, i) if 0x0D in data[i:] else len(data)
    part5 = data[i:j]; i = j + 1
    if i < len(data) and data[i] == 0x00: i += 1
    # part6: entries, each $0D-terminated
    entries = []
    while i < len(data):
        if data[i] == 0x00: break
        j = data.index(0x0D, i) if 0x0D in data[i:] else len(data)
        entries.append(bytes(data[i:j])); i = j + 1
    return {'part1': bytes(part1), 'part2': bytes(p2).rstrip(b'\r'),
            'part4': bytes(part4), 'part5': bytes(part5), 'entries': entries}


# ===========================================================================
# pygame front-end
# ===========================================================================

SCALE = 3
CELL = 8


def build_glyph_surfaces(font_upper, font_lower, palette):
    # pre-render nothing; we blit per-cell with colour at draw time
    return font_upper, font_lower


def draw_screen(surf, screen, fonts, palette):
    font_upper, font_lower = fonts
    bg = palette[screen.background]
    surf.fill(bg)
    for r in range(24):
        for c in range(40):
            sc, colour, reverse, lower = screen.cells[r][c]
            glyph = (font_lower if lower else font_upper).get(sc & 0x7F)
            if glyph is None:
                continue
            fg = palette[colour]
            x0, y0 = c * CELL * SCALE, r * CELL * SCALE
            for gy in range(8):
                rowbits = glyph[gy]
                for gx in range(8):
                    on = (rowbits >> (7 - gx)) & 1
                    if reverse: on = not on
                    if on:
                        surf.fill(fg, (x0 + gx * SCALE, y0 + gy * SCALE, SCALE, SCALE))


def main():
    host_port = sys.argv[1] if len(sys.argv) > 1 else 'docker.lan:6400'
    host, port = host_port.split(':') if ':' in host_port else (host_port, '6400')
    user = sys.argv[2] if len(sys.argv) > 2 else input('User ID: ').strip()
    password = sys.argv[3] if len(sys.argv) > 3 else input('Password: ').strip()

    import pygame                                       # lazy import (see top note)
    globals()['pygame'] = pygame

    font_upper, font_lower, palette, template = load_spec_assets()
    print(f'[assets] font {len(font_upper)}+{len(font_lower)} glyphs, '
          f'palette {len(palette)}, template {len(template)}b (from Appendix A)')

    t, welcome = connect_and_login(host, int(port), user, password)

    pygame.init()
    surf = pygame.display.set_mode((40 * CELL * SCALE, 24 * CELL * SCALE))
    pygame.display.set_caption('Compunet Reborn — pygame test client (Tier 1)')
    fonts = (font_upper, font_lower)
    screen = Screen()

    # show welcome frame
    render_frame_bytes(screen, welcome, start=0)
    draw_screen(surf, screen, fonts, palette); pygame.display.flip()

    mode = 'frame'           # 'frame' or 'dir'
    typed = ''

    def show_directory():
        nonlocal mode
        t.send_com(b'P')                               # §4.4 show current dir
        data = t.read_dat_stream()
        render_directory(screen, template, parse_directory(data))
        draw_screen(surf, screen, fonts, palette); pygame.display.flip()
        mode = 'dir'

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    try: t.send_com(b'E')              # §4.4 LEAVE
                    except Exception: pass
                    running = False
                elif ev.key == pygame.K_p:
                    show_directory()
                elif ev.key == pygame.K_b:
                    t.send_com(b'B'); data = t.read_dat_stream()
                    render_directory(screen, template, parse_directory(data))
                    draw_screen(surf, screen, fonts, palette); pygame.display.flip()
                elif ev.key == pygame.K_SPACE:         # MORE (next frame)
                    t.send_com(b'D');
                    data = t.read_dat_stream()
                    # SPEC-GAP: §4.5 — after 'D' with no arg while viewing a frame
                    # the reply may be the next frame OR (past the last) a directory.
                    # We assume frame here; a real client tracks paging state.
                    screen.reset(); render_frame_bytes(screen, data, start=0)
                    draw_screen(surf, screen, fonts, palette); pygame.display.flip()
                elif ev.unicode.isdigit():
                    typed += ev.unicode
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if typed:
                        t.send_com(b'D' + typed.encode())   # §4.4 select entry
                        data = t.read_dat_stream()
                        # §4.5: parse per the selected entry's type. For this Tier-1
                        # probe we sniff: a 6-part directory tends to start with a
                        # charset byte + CRs; a frame starts with the 4-byte header.
                        # SPEC-GAP: with no in-band marker (§4.3) the client must
                        # know the selected entry's TYPE from the listing (§7.4) to
                        # choose the parser — see findings.
                        typed = ''
                        screen.reset(); render_frame_bytes(screen, data, start=0)
                        draw_screen(surf, screen, fonts, palette); pygame.display.flip()
                        mode = 'frame'
        pygame.time.wait(20)

    pygame.quit()
    print('\n===== SPEC FINDINGS (guesses forced during the build) =====')
    for g in SPEC_GAPS:
        print(' -', g)


if __name__ == '__main__':
    # Collect the SPEC-GAP notes embedded above for the end-of-run report.
    SPEC_GAPS[:] = [
        "[resolved] §6.2 — server's INVALID-ID frame has $0D (not a charset ctrl) at "
        "byte 3; spec softened: byte 3 is consumed as charset, non-$0E = uppercase.",
        "[resolved] §7.7 — entries must render first-field + one selected column, not "
        "the whole comma-separated line (which overflows 40 cols).",
        "[resolved] §5.6.1 — auto-wrap/CR guard (just-wrapped flag) was under-explained; "
        "caused a blank line between every full-width row until implemented.",
        "§2.8 — client's starting transmit sequence number (spec now: any in-range).",
        "§3.2 — initial handshake byte (spec now: client MAY send one $20).",
        "§4.5 — entry TYPE for D-dispatch read from first-field cols 24-26 (spec now "
        "cross-links §7.3).",
        "§6.3 — pre-colour default text colour is explicitly undefined (chose white).",
        "§4.2 — behaviour on a non-DAT packet mid-stream is unspecified (ignored).",
    ]
    try:
        main()
    except Exception as e:
        print(f'\n[error] {e}')
        print('\n===== SPEC FINDINGS so far =====')
        for g in SPEC_GAPS:
            print(' -', g)
        raise
