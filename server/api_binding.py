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

PHASE 1a (this file): token auth + WebSocket gateway + directory browse.
Frame rendering (frame_to_cells) is a marked stub — the cell-grid renderer
lands in its own pass so the §5 control-code interpretation is done against
the spec rather than guessed.
"""

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

# The top directory's Part-5 column set (spec §7.2). Other responses (e.g.
# mail) carry a different set; Phase 1a only serializes content directories.
_DIR_COLUMNS = ["PRICE", "AUTHOR", "VOTE/NUM", "UPLDDATE", "LIFE"]


def _entry_values(session, child):
    """Per-entry Part-5 column values (strings), mirroring §7.3 semantics."""
    price = 0.0 if child.page_num in session.purchased else child.price
    vote = getattr(child, 'vote', 0) or 0
    return {
        "PRICE": ("%.2f" % price) if price > 0 else "",
        "AUTHOR": child.author or "",
        "VOTE/NUM": (str(vote) if vote else "-"),
        "UPLDDATE": (child.uploaded or "")[:11],
        "LIFE": (str(child.life) if child.life else ""),
    }


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
        "breadcrumb": ["1 *** COMPUNET ***", "%d %s" % (page.page_num, page.title or "")],
        "columns": list(_DIR_COLUMNS),
        "advert": advert,
        "header": None,           # Part-1 header frame -> client built-in template for now
        "hasMore": len(children) > 11,
        "entries": entries,
    }


def frame_to_cells(session, msg_id=None):
    """STUB — the 40x24 cell-grid renderer (spec §5/§6) lands in its own pass,
    so the colour/charset/reverse control-code interpretation is done against
    the spec, not guessed. Until then, reading a page reports not-implemented."""
    return {
        "type": "error", "id": msg_id, "code": "invalid",
        "message": "frame rendering not yet implemented (Phase 1a: directory browse only)",
    }


def _find_index(session, page_num):
    """Map a page number to its index within the current visible window."""
    offset = getattr(session, 'dir_page_offset', 0)
    visible = session.current_page.children[offset:offset + 11]
    for i, c in enumerate(visible):
        if c.page_num == page_num:
            return i
    return None


def _serialize_state(session, msg_id=None):
    """After driving a command, decide frame vs directory from session state."""
    if getattr(session, 'show_page', None):
        return frame_to_cells(session, msg_id)
    return directory_to_json(session, msg_id)


def _drive(session, cmd_bytes, msg_id=None):
    """Run authoritative navigation for its side-effects, then serialize."""
    session.handle_command(cmd_bytes)
    return _serialize_state(session, msg_id)


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
        await ws.send_json({
            "type": "ready",
            "account": {"user": session.user_id, "credit": session.credit},
        })
        # Auto-load the root directory so the client has an initial screen.
        await ws.send_json(directory_to_json(session))
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
            reply = handle_message(session, msg)
            await ws.send_json(reply)
    except Exception as e:
        log.info('API gateway loop ended for %s: %s', session.user_id, e)
    finally:
        log.info('API gateway: %s disconnected', session.user_id if session else '?')
    return ws


def make_app(server_module):
    """Build the isolated aiohttp app for the client API (port 6404)."""
    _bind_server(server_module)
    app = web.Application()
    app.router.add_post('/v1/session', http_session)
    app.router.add_get('/v1/gateway', ws_gateway)
    app.router.add_get('/v1/health', lambda r: web.json_response({"ok": True}))
    return app
