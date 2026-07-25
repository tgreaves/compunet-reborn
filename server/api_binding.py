"""Binding B — modern JSON client API (see docs/spec/api/README.md).

A thin serializer over the existing content/session core (CompunetDirectory,
CompunetSession in compunet_server.py). It does NOT reimplement navigation:
it drives the authoritative `handle_command` for its side-effects (which
mutate session state — current_page/show_page, latent-dir creation, paging,
permissions) and then serializes the resulting *model state* to JSON,
discarding the X.25 bytes handle_command returns. This keeps Binding A and
Binding B in lock-step by construction.

Runs on its own aiohttp app / port (default 6404), fully isolated from the
admin API (6403) and the X.25 protocol (6400).

Covers Tiers 1-3: token auth, the WebSocket gateway (directory browse, frame
cell-grid rendering, mail, account, vote/life, ID lookup, download, upload and
the editor path, Partyline), plus cacheable REST reads.
"""

import os
import json
import time
import secrets
import logging

from aiohttp import web, WSMsgType

log = logging.getLogger('compunet.api')

# Bound lazily to symbols from compunet_server to avoid an import cycle
# (compunet_server imports this module during startup wiring).
_srv = None


def _bind_server(server_module):
    global _srv
    _srv = server_module


# ---------------------------------------------------------------------------
# Token store (opaque, in-memory, server-side — simple to expire/revoke)
# ---------------------------------------------------------------------------

_TOKEN_TTL = 86400  # seconds
_tokens = {}        # token -> {"user": str, "exp": float}


def _issue_token(user_id):
    tok = secrets.token_urlsafe(24)
    _tokens[tok] = {"user": user_id, "exp": time.time() + _TOKEN_TTL}
    return tok


def _resolve_token(tok):
    rec = _tokens.get(tok)
    if not rec:
        return None
    if rec["exp"] < time.time():
        _tokens.pop(tok, None)
        return None
    return rec["user"]


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _new_session(client_ip="api"):
    directory = _srv.CompunetDirectory()
    session = _srv.CompunetSession(directory)
    session.client_ip = client_ip
    return session


def _adopt_user(session, user_id):
    """Mark a fresh session as authenticated for user_id WITHOUT re-checking
    the password (the bearer token already proved it). Mirrors the post-auth
    field loads in CompunetSession.handle_login."""
    user = session._users.get(user_id)
    if user is None:
        return False
    session.user_id = user_id
    session.authenticated = True
    session.credit = user.get('credit', 0.0)
    session.purchased = set(user.get('purchased', []))
    session.is_admin = user.get('admin', False)
    session.is_editor = user.get('editor', False)
    return True


def _credentials_ok(user_id, password):
    """Validate credentials via the authoritative handle_login path."""
    session = _new_session()
    resp = session.handle_login(user_id, password)
    return session.authenticated, session


# ---------------------------------------------------------------------------
# Serializers (model state -> JSON)
# ---------------------------------------------------------------------------

# The top directory's Part-5 column set (§7.2). The leading spaces are the C64
# server's positioning (§7.3): they indent the header within the right pane.
# Other responses (e.g. mail) carry a different set; Phase 1 serializes content dirs.
_DIR_COLUMNS = [" PRICE", " AUTHOR", "VOTE/NUM", "UPLDDATE", " LIFE"]


def _entry_values(session, child):
    """Per-entry column values, in column order, with the exact per-column
    justification the C64 server applies (§7.3 / _make_page_response Part 6), so
    the client renders them verbatim in the right pane. Empty string = blank."""
    price = 0.0 if child.page_num in session.purchased else child.price
    vote = getattr(child, 'vote', 0) or 0
    # PRICE: leading space + price right-justified in 6
    price_s = (' ' + ('%.2f' % price).rjust(6)) if price > 0 else ''
    # AUTHOR: plain, truncated to 8
    author_s = (child.author or '')[:8]
    # VOTE/NUM: score right-justified(4) + '/' + count, else '    -'
    if vote > 0:
        try:
            count = session._get_vote_count(child.page_num)
        except Exception:
            count = 0
        vote_s = (str(vote).rjust(4) + '/' + str(count))[:8]
    else:
        vote_s = '    -'
    # UPLDDATE: 'D-MMM' right-justified in 7
    date_s = ''
    up = getattr(child, 'uploaded', None)
    if up:
        try:
            import datetime
            dt = datetime.datetime.fromisoformat(up)
            date_s = ('%d-%s' % (dt.day, dt.strftime('%b').upper())).rjust(7)
        except Exception:
            date_s = ''
    # LIFE: 2-space indent + life right-justified in 3
    life_s = ('  ' + str(child.life).rjust(3)) if child.life > 0 else ''
    return [price_s, author_s, vote_s, date_s, life_s]


def _render_header(session):
    """Render the directory's Part-1 header frame (the COMPUNET logo, §7.2/§7.7)
    as a cell grid, or None. The header is inherited from the nearest ancestor
    that defines one (mirrors _make_page_response). Part-1 headers are body-only
    PETSCII, so we render them with a synthetic 4-byte header (charset $8E)."""
    anc = session.current_page
    header_file = None
    while anc is not None:
        header_file = getattr(anc, 'header', None)
        if header_file:
            break
        anc = getattr(anc, 'parent', None)
    if not header_file:
        return None
    path = os.path.join(_srv.ROOT_DIR, header_file)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        body = f.read()
    # [flags=0][border=$F4][bg=$FF][charset=$8E] + body — border/bg are ignored by
    # the client (it uses the template's), only the header cells are overlaid.
    return frame_to_cells(bytes([0x00, 0xF4, 0xFF, 0x8E]) + body)


def directory_to_json(session, msg_id=None):
    """Serialize the session's current directory (spec §7) as Binding-B JSON.

    Reads model state only — the client composes the 40x24 layout locally
    (template + display rules §7.5-§7.7), so selection and column-cycling
    need no round-trip.
    """
    page = session.current_page
    offset = getattr(session, 'dir_page_offset', 0)
    children = page.children[offset:]
    visible = children[:11]

    entries = []
    for i, child in enumerate(visible):
        size = getattr(child, 'size', 0) or 0
        entries.append({
            "index": i,
            "page": child.page_num,
            "title": child.title,
            "type": child.page_type,
            "size": (size if size > 0 else None),
            "hasSubdir": child.has_subdir(),
            "values": _entry_values(session, child),
        })

    advert = []
    try:
        picked = session._pick_advert()
        if picked:
            advert = [ln[:40] for ln in picked.split('\n')[:2]]
    except Exception:
        pass

    session.dir_displayed = True  # a directory is now on screen (enables DIR)
    return {
        "type": "directory",
        "id": msg_id,
        "page": page.page_num,
        "title": page.title,
        # Part 4 (§7.7): page number right-justified in the 6-char page-number field, then
        # the title — so, drawn from base column 2, the breadcrumb page numbers line up with
        # the entry page numbers directly below. Part 4 carries the padding; the client renders
        # each line verbatim from column 2. Line 1 is the fixed system banner (page 1).
        "breadcrumb": ["%6d %s" % (1, "*** COMPUNET ***"),
                       "%6d %s" % (page.page_num, page.title or "")],
        "columns": list(_DIR_COLUMNS),
        "advert": advert,
        "header": _render_header(session),   # Part-1 header frame (COMPUNET logo, §7.7) or null
        "hasMore": len(children) > 11,
        "entries": entries,
    }


# --- Frame cell-grid renderer (spec §5/§6) ---------------------------------

# Colour control code -> palette index (spec §5.6).
_COLOUR = {
    0x05: 1, 0x1C: 2, 0x1E: 5, 0x1F: 6, 0x81: 8, 0x90: 0, 0x9C: 4, 0x9E: 7,
    0x9F: 3, 0x95: 9, 0x96: 10, 0x97: 11, 0x98: 12, 0x99: 13, 0x9A: 14, 0x9B: 15,
}


def _petscii_to_screencode(b):
    """PETSCII byte -> C64 screen code (spec §5.3)."""
    if 0x20 <= b <= 0x3F:
        return b
    if 0x40 <= b <= 0x5F:
        return b & 0x1F
    if 0x60 <= b <= 0x7F:
        return (b & 0x1F) | 0x40
    if 0xA0 <= b <= 0xBF:
        return (b & 0x1F) | 0x60
    if 0xC0 <= b <= 0xDE:
        return b & 0x7F
    if b == 0xFF:
        return 0x5E
    if 0xE0 <= b <= 0xFE:
        return b & 0x7F
    return b & 0x7F


def _is_control(b):
    return b <= 0x1F or 0x80 <= b <= 0x9F


def frame_to_cells(raw, msg_id=None):
    """Render frame bytes [4-byte header][body][$00] into a 40x24 cell grid
    (spec §6.3 processing loop + §5 control codes). Each cell is {g,fg,bg,rv}:
    g = glyph index 0-255 (0-127 uppercase/graphics set, 128-255 lowercase set),
    fg/bg = palette index 0-15, rv = reverse-video flag."""
    COLS, ROWS = 40, 24
    flags = raw[0] if len(raw) > 0 else 0
    border = (raw[1] & 0x0F) if len(raw) > 1 else 0
    background = (raw[2] & 0x0F) if len(raw) > 2 else 0
    charset_byte = raw[3] if len(raw) > 3 else 0x8E
    body = raw[4:]

    lower = (charset_byte == 0x0E)        # else uppercase/graphics (§6.2)
    colour = 1                            # initial text colour undefined (§6.3) — white
    reverse = 0
    row = col = 0
    just_wrapped = False

    # grid initialised to spaces (screencode 0x20) in the header background
    space_g = 0x20
    grid = [{"g": space_g, "fg": colour, "bg": background, "rv": 0}
            for _ in range(ROWS * COLS)]

    def place(b):
        nonlocal row, col, just_wrapped
        sc = _petscii_to_screencode(b)
        g = sc + (128 if lower else 0)
        grid[row * COLS + col] = {"g": g, "fg": colour, "bg": background, "rv": reverse}
        col += 1
        if col >= COLS:
            col = 0
            if row < ROWS - 1:
                row += 1
            just_wrapped = True
        else:
            just_wrapped = False

    def control(b):
        nonlocal row, col, colour, reverse, lower, just_wrapped
        if b in _COLOUR:
            colour = _COLOUR[b]
            return
        if b in (0x0D, 0x8D):            # CR (§5.6.1 auto-wrap guard)
            col = 0
            reverse = 0
            if not just_wrapped and row < ROWS - 1:
                row += 1
            just_wrapped = False
        elif b == 0x11:                  # cursor down
            row = min(row + 1, ROWS - 1); just_wrapped = False
        elif b == 0x91:                  # cursor up
            row = max(row - 1, 0); just_wrapped = False
        elif b == 0x1D:                  # cursor right (wraps)
            col += 1
            if col >= COLS:
                col = 0; row = min(row + 1, ROWS - 1)
            just_wrapped = False
        elif b == 0x9D:                  # cursor left (wraps)
            col -= 1
            if col < 0:
                col = COLS - 1; row = max(row - 1, 0)
            just_wrapped = False
        elif b == 0x13:                  # home
            row = col = 0; just_wrapped = False
        elif b == 0x93:                  # clear + home
            for i in range(ROWS * COLS):
                grid[i] = {"g": space_g, "fg": colour, "bg": background, "rv": 0}
            row = col = 0; just_wrapped = False
        elif b == 0x12:
            reverse = 1
        elif b == 0x92:
            reverse = 0
        elif b == 0x0E:
            lower = True
        elif b == 0x8E:
            lower = False
        # $14/$94 (delete/insert) and unlisted codes: no-op (§5.6)

    def process(b):
        if _is_control(b):
            control(b)
        else:
            place(b)

    i, n = 0, len(body)
    while i < n:
        b = body[i]; i += 1
        if b == 0x00:                    # terminator (§6.3)
            break
        if b == 0x06:                    # space run (§6.4): 1+N spaces
            N = body[i] if i < n else 0; i += 1
            for _ in range(1 + N):
                place(0x20)
        elif b == 0x07:                  # char/control run (§6.4): c, 1+N times
            c = body[i] if i < n else 0
            N = body[i + 1] if i + 1 < n else 0
            i += 2
            for _ in range(1 + N):
                process(c)
        else:
            process(b)

    return {
        "type": "frame", "id": msg_id,
        "border": border, "background": background,
        "morePages": bool(flags & 0x80),
        "rows": ROWS, "cols": COLS,
        "cells": grid,
    }


def _download_json(session, msg_id=None):
    """Program/telesoftware entry (§8.3.1). The server has staged the program
    bytes; we describe them and let the client fetch with `download.fetch`
    (the Binding-B equivalent of the ROM's `$40` proceed token)."""
    data = getattr(session, '_program_download_data', None) or b''
    return {
        "type": "download", "id": msg_id,
        "page": getattr(session, '_download_page_num', None),
        "title": getattr(session, '_download_title', None),
        "size": len(data),
        "machine": getattr(getattr(session, 'show_page', None), 'machine_type', 'c64'),
    }


def _download_fetch(session, msg_id=None):
    """Deliver the staged program bytes as base64 (§8.3.1 proceed)."""
    import base64
    data = getattr(session, '_program_download_data', None)
    if not data:
        return {"type": "error", "id": msg_id, "code": "not_found",
                "message": "no download pending"}
    session._program_download_pending = False
    session._program_download_data = None
    return {
        "type": "download.data", "id": msg_id,
        "title": getattr(session, '_download_title', None),
        "size": len(data),
        "bytes": base64.b64encode(data).decode('ascii'),
    }


def _petscii_to_ascii(b):
    """Decode a plain PETSCII text field back to ASCII (digits/punctuation are
    unchanged; letters arrive unshifted in these fields)."""
    return b.decode('latin-1', 'replace')


# --- Tier 2 serializers ----------------------------------------------------

# Mail listings carry their own Part-5 set (§7.2), with the same leading-space
# positioning the C64 server applies (_cmd_mail Part 5).
_MAIL_COLUMNS = [" SENDER", " DATE", " STATUS"]


def mail_to_json(session, msg_id=None):
    """Serialize the mailbox as a directory-shaped listing (§8.2). Entries come
    from session.mail_messages, not the content tree, and use the mail columns."""
    offset = getattr(session, 'mail_page_offset', 0)
    msgs = session.mail_messages or []
    visible = msgs[offset:offset + 11]
    entries = []
    for i, m in enumerate(visible):
        raw_date = m.get('date', '') or ''
        if len(raw_date) == 10:                       # YYYY-MM-DD -> DD-MM-YY
            date_s = raw_date[8:10] + '-' + raw_date[5:7] + '-' + raw_date[2:4]
        else:
            date_s = raw_date[:8]
        nframes = len(m.get('frames', []) or [])
        entries.append({
            "index": i,
            "page": m.get('id', offset + i + 1),
            "title": (m.get('subject', '') or '')[:16],
            "type": "T",
            "size": nframes or None,
            "hasSubdir": False,
            "values": [(m.get('from', '?') or '?')[:8],
                       date_s,
                       ('NEW' if not m.get('read', False) else 'READ')],
        })
    if not entries:
        entries.append({"index": 0, "page": 0, "title": "(NO MAIL)", "type": "T",
                        "size": None, "hasSubdir": False, "values": ["", "", ""]})
    return {
        "type": "directory", "id": msg_id, "context": "mail",
        "page": 0, "title": "COURIER",
        "breadcrumb": ["%6d %s" % (1, "*** COMPUNET ***"), "%6s %s" % ("", "COURIER")],
        "columns": list(_MAIL_COLUMNS),
        "advert": [],
        "header": None,
        "hasMore": len(msgs) > offset + 11,
        "entries": entries,
    }


def account_to_json(session, raw, msg_id=None):
    """`A` returns a fixed 10-byte ASCII credit string (§4.4); the client formats it."""
    text = _petscii_to_ascii(raw or b'').strip()
    try:
        credit = float(text)
    except ValueError:
        credit = session.credit
    return {"type": "account", "id": msg_id, "creditText": text, "credit": credit}


def idlookup_to_json(raw, msg_id=None):
    """`I` returns per-ID: 8-byte id + real name (if known) + $1E (§4.4)."""
    users = []
    for rec in (raw or b'').split(b'\x1e'):
        if not rec:
            continue
        uid = _petscii_to_ascii(rec[:8]).strip()
        name = _petscii_to_ascii(rec[8:]).strip()
        if uid:
            users.append({"id": uid, "name": name or None})
    return {"type": "idlookup", "id": msg_id, "users": users}


# --- Upload / editor (§8.3.2, §8.4) -----------------------------------------
#
# Binding A uploads in several wire steps (U -> validation -> DAT frames ->
# finish). Binding B does it in ONE message: the client submits the composed
# page and the server performs the same commit through the same core routine.
# The client never encodes PETSCII — it sends text + colours and the server
# builds the §6 frame, consistent with this binding delivering decoded content.

def _encode_frame(spec):
    """Build §6 frame bytes from a structured editor page.

    spec: {lines: [str], colour?: 0-15, border?: 0-15, background?: 0-15}
    Produces [flags][border][bg][charset $8E] + colour control + PETSCII body + $00.
    """
    # colour index -> the §5.6 control code that selects it
    code_for = {v: k for k, v in _COLOUR.items()}
    border = int(spec.get('border', 6)) & 0x0F
    background = int(spec.get('background', 0)) & 0x0F
    colour = int(spec.get('colour', 1)) & 0x0F
    out = bytearray([0x00, border, background, 0x8E])
    out.append(code_for.get(colour, 0x05))            # default white
    for line in (spec.get('lines') or [])[:23]:
        out.extend(_srv.ascii_to_petscii(str(line)[:40].upper()))
        out.append(0x0D)
    out.append(0x00)
    return bytes(out)


def _upload_precheck(session, title):
    """Apply the checks Binding A performs silently (§8.3.2), as typed errors:
    permission to write here, and space (a directory holds at most 11 entries).
    Returns an error dict, or None when the upload may proceed."""
    if not session._can_upload_here():
        return {"code": "permission_denied",
                "message": "you may not upload into this directory"}
    slug = _srv.CompunetDirectory._make_slug(title)
    existing = next((c for c in session.current_page.children
                     if _srv.CompunetDirectory._make_slug(c.title) == slug), None)
    if existing:
        if (existing.author != session.user_id
                and not session.is_admin and not session.is_editor):
            return {"code": "permission_denied",
                    "message": 'you may not replace "%s"' % existing.title}
        return None                                   # replacing: no space needed
    if len(session.current_page.children) >= 11:
        return {"code": "directory_full",
                "message": "this directory is full (11 entries max)"}
    return None


def upload_content(session, msg, msg_id=None):
    """Content upload (§8.3.2) — commits to the client's *current* directory."""
    title = str(msg.get("title", "")).strip()[:16]
    kind = str(msg.get("kind", "")).upper()
    frames = msg.get("frames") or []
    if not title:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "title is required"}
    if kind not in ("T", "P"):
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "kind must be 'T' (text) or 'P' (program)"}
    if not frames:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "no frames to upload"}
    try:
        price = round(float(msg.get("price", 0) or 0), 2)
    except (TypeError, ValueError):
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "price must be a number"}
    try:
        life = int(msg.get("life", 0) or 0)
    except (TypeError, ValueError):
        life = 0

    err = _upload_precheck(session, title)
    if err:
        return {"type": "error", "id": msg_id, **err}

    if kind == "P":
        import base64
        blobs = [base64.b64decode(f) if isinstance(f, str) else bytes(f) for f in frames]
    else:
        blobs = [_encode_frame(f) for f in frames]

    send = {'mode': 'upload', 'title': title, 'type': kind,
            'price': price, 'lifetime': life, 'frames': blobs}
    session._complete_content_upload(send)
    session.directory.reload()                        # pick up the new page
    log.info('API upload: user=%s title="%s" kind=%s price=%.2f life=%d frames=%d',
             session.user_id, title, kind, price, life, len(blobs))
    return None                                       # caller returns the refreshed directory


def mail_send(session, msg, msg_id=None):
    """Mail send (§8.3.2) — composed frames delivered to recipients."""
    to = [str(x).upper().strip() for x in (msg.get("to") or []) if str(x).strip()]
    subject = str(msg.get("subject", "")).strip()[:16]
    frames = msg.get("frames") or []
    if not to:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "at least one recipient is required"}
    if not frames:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "message body is empty"}
    users = session._load_users()
    unknown = [u for u in to if u not in users]
    if unknown:
        return {"type": "error", "id": msg_id, "code": "not_found",
                "message": "no such user: " + ", ".join(unknown)}
    send = {'mode': 'mail', 'subject': subject, 'to': to,
            'frames': [_encode_frame(f) for f in frames]}
    session._complete_mail_send(send)
    log.info('API mail: %s -> %s (%d frames)', session.user_id, to, len(send['frames']))
    return {"type": "ack", "id": msg_id, "of": "mail.send"}


# --- Partyline bridge (§8.5) ------------------------------------------------
#
# Binding A drops out of the framed protocol into a raw, line-based session.
# Binding B does not need to: the gateway is already message-oriented, so
# Partyline is just `partyline` push events + `partyline.*` commands. We reuse
# the server's partyline module wholesale (rooms, commands, broadcast, bans) by
# adapting its writer interface — no chat logic is duplicated.

class _WsPartylineWriter:
    """Adapter making an aiohttp WebSocket look like a StreamWriter to
    partyline.send_line(). Lines are decoded back from PETSCII and pushed as
    `partyline` messages. write() buffers; drain() flushes (send_line always
    calls write-then-drain, and broadcast_room drives it from other tasks)."""

    def __init__(self, ws, partyline):
        self._ws = ws
        self._pl = partyline
        self._buf = []

    def write(self, data):
        self._buf.append(data)

    async def drain(self):
        buf, self._buf = self._buf, []
        for raw in buf:
            text = self._pl.petscii_to_ascii(raw.rstrip(b'\x0d'))
            if text.strip().lower() in ('*ping',):     # keepalive is transport noise
                continue
            try:
                await self._ws.send_json({"type": "partyline", "line": text})
            except Exception:
                pass


async def partyline_enter(session, ws, msg_id=None):
    """Join Partyline: register with the shared module and stream its output.

    Reached only by activating an `L`-type directory entry (§7.4/§8.5) — there is
    deliberately no "join partyline" command, because Binding A has none either."""
    import partyline as pl
    if getattr(session, '_pl_writer', None) is not None:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "already in partyline"}
    if pl._is_banned(session.user_id):
        return {"type": "error", "id": msg_id, "code": "permission_denied",
                "message": "You are banned from partyline."}

    writer = _WsPartylineWriter(ws, pl)
    session._pl_writer = writer
    pl._users[session.user_id] = {"writer": writer, "alias": None, "room": "Lobby"}
    pl.partyline_log('join', user=session.user_id)
    log.info('PARTYLINE(api): %s entering', session.user_id)

    await ws.send_json({"type": "partyline.entered", "id": msg_id, "room": "Lobby"})
    # Same entry sequence as a Binding-A session (§8.5): announce, then who-listing.
    await pl.send_line(writer, "%s has entered partyline" % session.user_id)
    await pl.send_line(writer, "")
    await pl.broadcast_room("Lobby", "%s has entered partyline" % session.user_id,
                            exclude=session.user_id)
    await pl.broadcast_room("Lobby", "", exclude=session.user_id)
    await pl._cmd_who(writer, session.user_id)
    return None


async def partyline_input(session, line, msg_id=None):
    """Feed one line to the shared partyline handler (chat or *command)."""
    import partyline as pl
    writer = getattr(session, '_pl_writer', None)
    if writer is None:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "not in partyline"}
    result = await pl.process_input(session.user_id, line, writer)
    if result == 'save':
        return {"type": "ack", "id": msg_id, "of": "partyline.save"}
    if result or session.user_id not in pl._users:     # quit, or kicked/banned
        await partyline_leave(session)
        return {"type": "partyline.left", "id": msg_id}
    return None


async def partyline_leave(session, msg_id=None):
    """Leave Partyline and resume normal gateway commands."""
    import partyline as pl
    if getattr(session, '_pl_writer', None) is None:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "not in partyline"}
    uid = session.user_id
    if uid in pl._users:
        room = pl._users[uid]["room"]
        del pl._users[uid]
        name = pl.display_name(uid)
        await pl.broadcast_room(room, "%s has left partyline" % name)
        await pl.broadcast_room(room, "")
    pl.partyline_log('leave', user=uid)
    session._pl_writer = None
    log.info('PARTYLINE(api): %s left', uid)
    return {"type": "partyline.left", "id": msg_id}


def _find_index(session, page_num):
    """Map a page number to its index within the current visible window (content
    directory, or the mailbox when in mail mode)."""
    if getattr(session, 'mail_mode', False):
        offset = getattr(session, 'mail_page_offset', 0)
        visible = (session.mail_messages or [])[offset:offset + 11]
        for i, m in enumerate(visible):
            if m.get('id', offset + i + 1) == page_num:
                return i
        return None
    offset = getattr(session, 'dir_page_offset', 0)
    visible = session.current_page.children[offset:offset + 11]
    for i, c in enumerate(visible):
        if c.page_num == page_num:
            return i
    return None


def _serialize_state(session, raw, msg_id=None):
    """After driving a command, decide frame vs directory vs download from state."""
    if getattr(session, '_enter_partyline', False):
        # An `L` entry was selected; the gateway completes the join (§8.5). The
        # link-header/program bytes Binding A sends here are transport-specific
        # and are not carried into Binding B.
        return {"type": "partyline.entering", "id": msg_id}
    if getattr(session, '_program_download_pending', False):
        return _download_json(session, msg_id)
    if getattr(session, 'mail_mode', False):
        # In the mailbox: a selected message renders as a frame, else the listing.
        if getattr(session, 'mail_show_msg', None) is not None:
            return frame_to_cells(raw, msg_id)
        return mail_to_json(session, msg_id)
    if getattr(session, 'show_page', None):
        return frame_to_cells(raw, msg_id)           # raw = frame bytes from handle_command
    return directory_to_json(session, msg_id)


def _drive(session, cmd_bytes, msg_id=None):
    """Run authoritative navigation for its side-effects, then serialize."""
    raw = session.handle_command(cmd_bytes)
    return _serialize_state(session, raw, msg_id)


# ---------------------------------------------------------------------------
# Command dispatch (client message -> reply dict)
# ---------------------------------------------------------------------------

def handle_message(session, msg):
    """Translate one Binding-B command message to a reply dict."""
    t = msg.get("type")
    mid = msg.get("id")

    if t == "dir" or t == "finish":
        return _drive(session, b'P', mid)
    if t == "enter":
        i = _find_index(session, msg.get("page"))
        if i is None:
            return {"type": "error", "id": mid, "code": "not_found", "message": "no such entry"}
        return _drive(session, b'P' + str(i).encode('ascii'), mid)
    if t == "open":
        i = _find_index(session, msg.get("page"))
        if i is None:
            return {"type": "error", "id": mid, "code": "not_found", "message": "no such entry"}
        return _drive(session, b'D' + str(i).encode('ascii'), mid)
    if t == "more":
        return _drive(session, b'D', mid)
    if t == "back":
        return _drive(session, b'B', mid)
    if t == "goto":
        target = str(msg.get("target", "")).encode('ascii', 'ignore')
        return _drive(session, b'L' + target, mid)

    # --- Tier 2 ---------------------------------------------------------
    if t == "account":
        raw = session.handle_command(b'A')
        return account_to_json(session, raw, mid)

    if t == "ucat":
        return _drive(session, b'C', mid)

    if t == "mail.list":
        session.handle_command(b'M')
        return mail_to_json(session, mid)

    if t == "mail.read":
        i = _find_index(session, msg.get("id_"))
        if i is None:
            i = msg.get("index")
        if i is None:
            return {"type": "error", "id": mid, "code": "not_found",
                    "message": "no such message"}
        return _drive(session, b'D' + ('%02d' % int(i)).encode('ascii'), mid)

    if t == "idlookup":
        ids = msg.get("ids") or []
        payload = b''.join(str(u).upper().ljust(8)[:8].encode('ascii', 'ignore') for u in ids)
        raw = session.handle_command(b'I' + payload)
        return idlookup_to_json(raw, mid)

    if t == "vote":
        i = _find_index(session, msg.get("page"))
        score = int(msg.get("score", 0) or 0)
        if i is None:
            return {"type": "error", "id": mid, "code": "not_found", "message": "no such entry"}
        if not (1 <= score <= 9):
            return {"type": "error", "id": mid, "code": "invalid",
                    "message": "score must be 1-9"}
        session.handle_command(b'V' + ('%02d%d' % (i, score)).encode('ascii'))
        return {"type": "ack", "id": mid, "of": "vote"}

    if t == "life":
        i = _find_index(session, msg.get("page"))
        days = int(msg.get("days", 0) or 0)
        if i is None:
            return {"type": "error", "id": mid, "code": "not_found", "message": "no such entry"}
        session.handle_command(b'X' + ('%02d%d' % (i, days)).encode('ascii'))
        return {"type": "ack", "id": mid, "of": "life"}

    if t == "download.fetch":
        return _download_fetch(session, mid)

    # --- Tier 3 ---------------------------------------------------------
    if t == "upload":
        err = upload_content(session, msg, mid)
        if err:
            return err
        return directory_to_json(session, mid)        # refreshed listing (the finishing `P`)

    if t == "mail.send":
        return mail_send(session, msg, mid)

    if t == "leave":
        # §3.8: LEAVE returns a goodbye frame that the client MUST render before
        # the connection closes. Serialize it rather than discarding it.
        raw = session.handle_command(b'E')
        reply = frame_to_cells(raw, mid)
        reply["goodbye"] = True
        return reply

    return {"type": "error", "id": mid, "code": "invalid",
            "message": "unknown or not-yet-implemented command: %r" % t}


# ---------------------------------------------------------------------------
# HTTP + WebSocket handlers
# ---------------------------------------------------------------------------

async def http_session(request):
    """POST /v1/session {user, pass} -> {token, expiresInSec, account}."""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": {"code": "invalid"}}, status=400)
    user = str(body.get("user", ""))
    password = str(body.get("pass", ""))
    ok, session = _credentials_ok(user, password)
    if not ok:
        return web.json_response({"error": {"code": "unauthorized"}}, status=401)
    token = _issue_token(session.user_id)
    return web.json_response({
        "token": token,
        "expiresInSec": _TOKEN_TTL,
        "account": {"user": session.user_id, "credit": session.credit},
    })


def _bearer(request):
    """Resolve `Authorization: Bearer <token>` to a user id, or None."""
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return _resolve_token(auth[7:].strip())
    return None


def _rest_session(request):
    """A fresh, authenticated session for one REST read.

    REST reads are stateless (that is what makes them cacheable): each request
    gets its own session, navigates to the requested page, and is discarded.
    Interactive state — current directory, paging, pending uploads — belongs to
    the gateway, not here.
    """
    user_id = _bearer(request)
    if not user_id:
        return None
    session = _new_session(request.remote or 'api')
    return session if _adopt_user(session, user_id) else None


async def http_dir(request):
    """GET /v1/dir/{page} — a directory as JSON (§7)."""
    session = _rest_session(request)
    if session is None:
        return web.json_response({"error": {"code": "unauthorized"}}, status=401)
    target = request.match_info.get('page', '')
    session.handle_command(b'L' + str(target).encode('ascii', 'ignore'))
    if getattr(session, 'show_page', None):
        return web.json_response({"error": {"code": "not_found",
                                            "message": "not a directory"}}, status=404)
    return web.json_response(directory_to_json(session))


async def http_frame(request):
    """GET /v1/frame/{page}[?index=N] — a page's frame as a cell grid (§6)."""
    session = _rest_session(request)
    if session is None:
        return web.json_response({"error": {"code": "unauthorized"}}, status=401)
    try:
        page_num = int(request.match_info.get('page', ''))
    except ValueError:
        return web.json_response({"error": {"code": "invalid"}}, status=400)
    page = session.directory.pages.get(page_num)
    if page is None or not page.frames:
        return web.json_response({"error": {"code": "not_found"}}, status=404)
    try:
        index = int(request.query.get('index', '0'))
    except ValueError:
        index = 0
    if index < 0 or index >= len(page.frames):
        return web.json_response({"error": {"code": "not_found",
                                            "message": "no such frame"}}, status=404)
    session.show_page = page
    session.show_frame_index = index
    raw = session._send_current_frame()
    if getattr(session, '_program_download_pending', False):
        return web.json_response(_download_json(session))
    return web.json_response(frame_to_cells(raw))


async def ws_gateway(request):
    """GET /v1/gateway — the interactive session (WebSocket)."""
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    peer = request.remote or "api"

    # First message must authenticate.
    session = None
    try:
        first = await ws.receive(timeout=15)
        if first.type != WSMsgType.TEXT:
            await ws.send_json({"type": "error", "code": "unauthorized"})
            await ws.close()
            return ws
        msg = json.loads(first.data)
        user_id = _resolve_token(msg.get("token", "")) if msg.get("type") == "auth" else None
        if not user_id:
            await ws.send_json({"type": "error", "code": "unauthorized"})
            await ws.close()
            return ws
        session = _new_session(peer)
        if not _adopt_user(session, user_id):
            await ws.send_json({"type": "error", "code": "unauthorized"})
            await ws.close()
            return ws
        log.info('API gateway: %s connected from %s', user_id, peer)
        # Render the welcome frame (spec §3.5/§6) as a cell grid for the client.
        welcome = None
        try:
            user = session._users.get(session.user_id) or {}
            welcome = frame_to_cells(session._make_welcome_frame(user))
        except Exception as e:
            log.warning('welcome frame render failed: %s', e)
        # The welcome frame is the post-login screen (spec §3.5); the client shows
        # it and reaches the root directory when the user issues DIR (§4.7). Do NOT
        # auto-send the directory here — that would clobber the welcome page.
        await ws.send_json({
            "type": "ready",
            "account": {"user": session.user_id, "credit": session.credit},
            "welcome": welcome,
        })
    except Exception as e:
        log.warning('API gateway auth error: %s', e)
        await ws.close()
        return ws

    # Command loop.
    try:
        async for raw in ws:
            if raw.type != WSMsgType.TEXT:
                continue
            try:
                msg = json.loads(raw.data)
            except Exception:
                await ws.send_json({"type": "error", "code": "invalid", "message": "bad JSON"})
                continue

            t, mid = msg.get("type"), msg.get("id")

            # Partyline is async (it pushes) so it is handled here, not in the
            # sync dispatcher.
            if t in ("partyline.send", "partyline.command"):
                reply = await partyline_input(session, str(msg.get("text", "")), mid)
                if reply:
                    await ws.send_json(reply)
                continue
            if t == "partyline.leave":
                await ws.send_json(await partyline_leave(session, mid))
                continue

            reply = handle_message(session, msg)
            await ws.send_json(reply)

            # Selecting an `L` (link) entry activates Partyline (§7.4/§8.5).
            if getattr(session, '_enter_partyline', False):
                session._enter_partyline = False
                err = await partyline_enter(session, ws)
                if err:
                    await ws.send_json(err)
    except Exception as e:
        log.info('API gateway loop ended for %s: %s', session.user_id, e)
    finally:
        # Never leave a ghost in the partyline roster (§8.5).
        if session is not None and getattr(session, '_pl_writer', None) is not None:
            try:
                await partyline_leave(session)
            except Exception:
                pass
        log.info('API gateway: %s disconnected', session.user_id if session else '?')
    return ws


# --- CORS -------------------------------------------------------------------
#
# This API exists to be called by clients served from a DIFFERENT origin: a web
# client on its own host, and the Electron shell, which serves the page from an
# ephemeral 127.0.0.1 port. Without these headers the browser blocks the very
# first call (POST /v1/session) and the client cannot log in at all.
#
# `*` is safe here because authentication is a bearer token in a header, not a
# cookie — nothing is sent automatically by the browser, so there is no CSRF
# surface to protect. Set CLIENT_API_CORS_ORIGIN to pin it to one origin.
_CORS_ORIGIN = os.environ.get('CLIENT_API_CORS_ORIGIN', '*')

_CORS_HEADERS = {
    'Access-Control-Allow-Origin': _CORS_ORIGIN,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
}


@web.middleware
async def _cors_middleware(request, handler):
    if request.method == 'OPTIONS':                   # preflight
        return web.Response(status=204, headers=_CORS_HEADERS)
    try:
        response = await handler(request)
    except web.HTTPException as exc:                  # keep CORS on error replies
        exc.headers.update(_CORS_HEADERS)
        raise
    response.headers.update(_CORS_HEADERS)
    return response


def make_app(server_module):
    """Build the isolated aiohttp app for the client API (port 6404)."""
    _bind_server(server_module)
    app = web.Application(middlewares=[_cors_middleware])
    app.router.add_post('/v1/session', http_session)
    app.router.add_get('/v1/gateway', ws_gateway)
    # Hybrid: cacheable REST reads carrying the same JSON shapes as the gateway.
    app.router.add_get('/v1/dir/{page}', http_dir)
    app.router.add_get('/v1/frame/{page}', http_frame)
    app.router.add_get('/v1/health', lambda r: web.json_response({"ok": True}))
    return app
