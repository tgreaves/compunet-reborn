"""
Partyline module — multi-user chat for Compunet Reborn.

After a C64 client downloads and executes the partyline program, the server
switches from X.25 framed protocol to a raw line-based protocol
(CR-terminated text lines, $0D = line terminator).

Web clients connect via WebSocket and use a queue-based adapter.
"""

import asyncio
import datetime
import json
import logging
import os
import random

logger = logging.getLogger(__name__)

# Partyline log
PARTYLINE_LOG_PATH = os.path.join(os.path.dirname(__file__), 'data', 'partyline.jsonl')


def partyline_log(event, user=None, **details):
    """Append an event to the partyline log (JSON-lines format).

    ⚠ A `join` is ALSO an audit event, recorded here rather than by the callers.
    All three surfaces reach this line — Binding A through handle_session, the
    terminal and Binding B by registering themselves — but only the first two
    audited it, so entering Partyline from the web client left no trace (#127).
    This is the one point they share.
    """
    if event == 'join' and user:
        try:
            from compunet_server import audit_log
            audit_log('partyline_entered', user=user, via=details.get('via'))
        except ImportError:      # partyline used standalone
            pass
    entry = {
        'ts': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'event': event,
    }
    if user:
        entry['user'] = user
    entry.update(details)
    try:
        os.makedirs(os.path.dirname(PARTYLINE_LOG_PATH), exist_ok=True)
        with open(PARTYLINE_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except OSError:
        logger.warning('Failed to write partyline log entry: %s', entry)


# Ban list
CFG_DIR = os.path.join(os.path.dirname(__file__), 'cfg')
BANS_FILE = os.path.join(CFG_DIR, 'partyline-bans.json')


def _load_bans():
    if os.path.exists(BANS_FILE):
        with open(BANS_FILE, 'r') as f:
            return json.load(f)
    return []


def _save_bans(bans):
    os.makedirs(os.path.dirname(BANS_FILE), exist_ok=True)
    with open(BANS_FILE, 'w') as f:
        json.dump(bans, f, indent=2)


def _is_banned(user_id):
    return user_id.upper() in [b.upper() for b in _load_bans()]


def _is_privileged(user_id):
    """Check if user has admin or editor flag."""
    users_file = os.path.join(CFG_DIR, 'users.json')
    if not os.path.exists(users_file):
        return False
    with open(users_file, 'r') as f:
        users = json.load(f)
    user = users.get(user_id, {})
    return user.get('admin', False) or user.get('editor', False)

# Global state: connected partyline users
# {user_id: {"writer": writer, "alias": None, "room": "Lobby"}}
_users = {}

CR = b'\x0d'


class WebWriter:
    """Adapter to make a WebSocket + asyncio.Queue look like a StreamWriter."""

    def __init__(self, queue):
        self._queue = queue

    def write(self, data):
        # Decode CR-terminated line and put on queue
        text = data.rstrip(b'\x0d').decode('ascii', errors='replace')
        if text:
            self._queue.put_nowait(text)

    async def drain(self):
        pass


class WebReader:
    """Adapter to make an asyncio.Queue look like a StreamReader."""

    def __init__(self, queue):
        self._queue = queue

    async def read(self, n):
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=60.0)
        except asyncio.TimeoutError:
            return b''

HELP_TEXT = """\
Partyline help:-

Press RETURN twice to send commands
or messages.

Sample Partyline commands:-

*alias (name, max 8 chars)
*who  (tells who's in pline)
*where (user) to find someone
*enter (room, max 8 chars,
 no spaces)
*dice (number) to roll
*call (user) to call someone
*save to save chat log
*quit to leave partyline"""


def display_name(user_id):
    """Return the user's alias if set, otherwise their user_id."""
    entry = _users.get(user_id)
    if entry and entry["alias"]:
        return entry["alias"]
    return user_id


def petscii_to_ascii(buf):
    """Convert PETSCII bytes to ASCII string (shifted/lowercase mode).

    Shared conversion used by both protocol and terminal partyline handlers.
    """
    result = []
    for b in (buf if isinstance(buf, (bytes, bytearray)) else buf.encode('latin-1')):
        if 0xC1 <= b <= 0xDA:
            result.append(chr(b - 0x80))  # uppercase A-Z
        elif 0x41 <= b <= 0x5A:
            result.append(chr(b + 0x20))  # lowercase a-z
        elif 0x20 <= b <= 0x3F:
            result.append(chr(b))         # digits, punctuation, space
        else:
            result.append(chr(b & 0x7F) if 0x20 <= (b & 0x7F) <= 0x7E else '?')
    return ''.join(result)


async def process_input(user_id, line, writer):
    """Process a partyline input line (command or message).

    Shared handler for both protocol and terminal clients.
    writer: the user's writer (or TermWriter proxy for terminal clients).
    Returns True if the user should exit partyline, False otherwise.
    """
    line = line.strip()
    if not line:
        return False

    if line.startswith('*'):
        parts = line[1:].split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        logger.info("Partyline cmd from %s: *%s %s", user_id, cmd, args)
        room = _users[user_id]["room"] if user_id in _users else "?"
        partyline_log('command', user=user_id, room=room, cmd=cmd, args=args)

        if cmd == "help":
            await _cmd_help(writer, user_id)
        elif cmd == "alias":
            await _cmd_alias(writer, user_id, args)
        elif cmd == "who":
            await _cmd_who(writer, user_id)
        elif cmd == "where":
            await _cmd_where(writer, user_id, args)
        elif cmd == "enter":
            await _cmd_enter(writer, user_id, args)
        elif cmd == "dice":
            await _cmd_dice(writer, user_id, args)
        elif cmd == "call":
            await _cmd_call(writer, user_id, args)
        elif cmd == "kick":
            await _cmd_kick(writer, user_id, args)
        elif cmd == "ban":
            await _cmd_ban(writer, user_id, args)
        elif cmd == "unban":
            await _cmd_unban(writer, user_id, args)
        elif cmd == "save":
            # Handled by the client (C64 saves locally, terminal uses XMODEM)
            # Return special marker so caller knows to handle save
            return 'save'
        elif cmd == "quit" or cmd == "exit":
            await _cmd_quit(writer, user_id)
            return True
        else:
            await send_line(writer, f"Unknown command: *{cmd}")
            await send_line(writer, "")
    else:
        # Chat message — format and broadcast
        name = display_name(user_id)
        room = _users[user_id]["room"]
        partyline_log('message', user=user_id, room=room, text=line)
        chunks = [line[i:i+35] for i in range(0, len(line), 35)]
        # Send to self
        await send_line(writer, f"{name}:")
        for chunk in chunks:
            await send_line(writer, chunk)
        await send_line(writer, "")
        # Broadcast to room
        await broadcast_room(room, f"{name}:", exclude=user_id)
        for chunk in chunks:
            await broadcast_room(room, chunk, exclude=user_id)
        await broadcast_room(room, "", exclude=user_id)
        logger.info("Partyline msg from %s [%s]: %s", user_id, room, line)

    return False


def _ascii_to_petscii(text):
    """Convert ASCII text to PETSCII for C64 display (lowercase mode)."""
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


class _AmigaQuit(Exception):
    """Raised when the Amiga CnetTty viewer tears its link down (Done gadget / 0x02)."""


async def _drain_raw(reader, n, timeout):
    """Best-effort: read and discard up to n raw bytes (handshake replies). Never raises."""
    got = 0
    while got < n:
        try:
            data = await asyncio.wait_for(reader.read(n - got), timeout=timeout)
        except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError, OSError):
            return
        if not data:
            return
        got += len(data)


async def send_line(writer, text):
    """Send one CR-terminated line to a client."""
    if getattr(writer, '_amiga', False):
        # The Amiga CnetTty viewer is a plain ASCII terminal (renders 0x20-0x7e via the
        # system font, drops everything else). Protocol sentinels (*EXIT/*PING) mean nothing
        # to it — its link is torn down out-of-band with 0x02 bytes — so drop those lines.
        if text.startswith('*'):
            return
        writer.write(text.encode('ascii', errors='replace') + CR)
        await writer.drain()
        return
    if text.startswith('*'):
        # Protocol sentinels (*EXIT, *PING) sent as raw ASCII
        writer.write(text.encode('ascii', errors='replace') + CR)
    else:
        writer.write(_ascii_to_petscii(text) + CR)
    await writer.drain()


async def broadcast_room(room, text, exclude=None):
    """Send a message to all users in the specified room, except excluded user."""
    for uid, entry in _users.items():
        if entry["room"] == room and uid != exclude:
            try:
                await send_line(entry["writer"], text)
            except (ConnectionResetError, BrokenPipeError, OSError):
                logger.debug("Failed to send broadcast to %s (disconnected)", uid)


async def read_line(reader, amiga=False):
    """Read bytes from reader until CR ($0D). Returns the line as a string.

    Raises asyncio.TimeoutError if no data within 60 seconds.
    Raises ConnectionResetError if the connection is closed.
    In amiga mode: input is raw ASCII (not PETSCII), and a 0x02 byte signals the CnetTty
    viewer tearing the link down (Done gadget / link_end) -> _AmigaQuit.
    """
    buf = bytearray()
    while True:
        data = await asyncio.wait_for(reader.read(1), timeout=60.0)
        if not data:
            raise ConnectionResetError("Client disconnected")
        if amiga:
            b = data[0]
            if b == 0x02:            # CnetTty link teardown (Done / link_end)
                raise _AmigaQuit()
            if b == 0x0d:            # CnetTty sends 0x0d 0x0d on RETURN-twice; break on each
                break
            if b < 0x20:             # ignore other control bytes (stray LF etc.)
                continue
            buf.append(b)
            continue
        if data == CR:
            break
        buf.extend(data)
    if amiga:
        return buf.decode('ascii', errors='replace')
    return petscii_to_ascii(buf)


async def _cmd_help(writer, user_id):
    """Send help text to user."""
    for line in HELP_TEXT.split('\n'):
        await send_line(writer, line)
    await send_line(writer, "")


async def _cmd_alias(writer, user_id, args):
    """Set user alias (max 8 characters, mixed case and spaces allowed)."""
    name = args.strip()
    if not name:
        await send_line(writer, "Usage: *alias <name>")
        await send_line(writer, "")
        return
    if len(name) > 8:
        await send_line(writer, "Alias max 8 characters")
        await send_line(writer, "")
        return
    old_name = display_name(user_id)
    _users[user_id]["alias"] = name
    await send_line(writer, f"Alias set to {name}")
    await send_line(writer, "")
    await broadcast_room(
        _users[user_id]["room"],
        f"{old_name} is now known as {name}",
        exclude=user_id
    )
    await broadcast_room(_users[user_id]["room"], "", exclude=user_id)
    logger.info("User %s set alias to %s", user_id, name)


async def _cmd_who(writer, user_id):
    """List all partyline users."""
    await send_line(writer, "Users in partyline:-")
    for uid, entry in _users.items():
        alias = entry["alias"] or uid
        room = entry["room"]
        await send_line(writer, f" {alias:<10} ({uid:<8}) {room}")
    await send_line(writer, "")


async def _cmd_where(writer, user_id, args):
    """Show which room a user is in."""
    target = args.strip().upper()
    if not target:
        await send_line(writer, "Usage: *where <user>")
        await send_line(writer, "")
        return
    if target in _users:
        room = _users[target]["room"]
        await send_line(writer, f"{target} is in {room}.")
    else:
        await send_line(writer, f"{target} is not on Partyline.")
    await send_line(writer, "")


async def _cmd_enter(writer, user_id, args):
    """Move user to a different room (max 8 chars, no spaces)."""
    new_room = args.strip().split()[0] if args.strip() else ''
    if not new_room:
        await send_line(writer, "Usage: *enter <room>")
        await send_line(writer, "")
        return
    if len(new_room) > 8:
        await send_line(writer, "Room name max 8 characters")
        await send_line(writer, "")
        return
    old_room = _users[user_id]["room"]
    # Case-insensitive room match — find existing room with same name
    existing_room = None
    for uid, entry in _users.items():
        if entry["room"].lower() == new_room.lower():
            existing_room = entry["room"]
            break
    if existing_room:
        new_room = existing_room
    if new_room == old_room:
        await send_line(writer, f"You are already in {old_room}")
        await send_line(writer, "")
        return
    name = display_name(user_id)
    # Notify old room
    await broadcast_room(old_room, f"{name} has left to {new_room}", exclude=user_id)
    await broadcast_room(old_room, "", exclude=user_id)
    # Switch room
    _users[user_id]["room"] = new_room
    # Notify new room
    await broadcast_room(new_room, f"{name} has entered {new_room}", exclude=user_id)
    await broadcast_room(new_room, "", exclude=user_id)
    await send_line(writer, f"You are now in {new_room}")
    await send_line(writer, "")
    logger.info("User %s moved from %s to %s", user_id, old_room, new_room)


async def _cmd_dice(writer, user_id, args):
    """Roll a random number."""
    try:
        n = int(args.strip())
        if n < 1:
            raise ValueError
    except (ValueError, TypeError):
        await send_line(writer, "Usage: *dice <number>")
        await send_line(writer, "")
        return
    result = random.randint(1, n)
    name = display_name(user_id)
    await send_line(writer, f"You have thrown {result}/{n}")
    await send_line(writer, "")
    await broadcast_room(_users[user_id]["room"], f"{name} has thrown {result}/{n}", exclude=user_id)
    await broadcast_room(_users[user_id]["room"], "", exclude=user_id)


async def _cmd_call(writer, user_id, args):
    """Call another user."""
    target = args.strip()
    if not target:
        await send_line(writer, "Usage: *call <username>")
        await send_line(writer, "")
        return
    # Find target by user_id or alias
    target_uid = None
    for uid, entry in _users.items():
        if uid == target or (entry["alias"] and entry["alias"].lower() == target.lower()):
            target_uid = uid
            break
    if target_uid is None:
        await send_line(writer, f"{target} is not in partyline")
        await send_line(writer, "")
        return
    if target_uid == user_id:
        await send_line(writer, "You cannot call yourself")
        await send_line(writer, "")
        return
    caller_name = display_name(user_id)
    caller_room = _users[user_id]["room"]
    try:
        await send_line(_users[target_uid]["writer"], f"{caller_name} calls you from {caller_room}")
        await send_line(_users[target_uid]["writer"], "")
    except (ConnectionResetError, BrokenPipeError, OSError):
        await send_line(writer, f"Could not reach {target}")
        await send_line(writer, "")
        return
    await send_line(writer, f"You called {display_name(target_uid)}")
    await send_line(writer, "")


async def _cmd_kick(writer, user_id, args):
    """Kick a user from partyline (ADMIN/EDITOR only)."""
    if not _is_privileged(user_id):
        await send_line(writer, "Permission denied.")
        await send_line(writer, "")
        return
    target = args.strip().upper()
    if not target:
        await send_line(writer, "Usage: *kick USER")
        await send_line(writer, "")
        return
    if target == user_id:
        await send_line(writer, "You can't kick yourself.")
        await send_line(writer, "")
        return
    if target == 'ADMIN':
        await send_line(writer, "ADMIN cannot be kicked.")
        await send_line(writer, "")
        return
    if target not in _users:
        await send_line(writer, f"{target} is not in partyline.")
        await send_line(writer, "")
        return
    target_room = _users[target]["room"]
    target_writer = _users[target]["writer"]
    del _users[target]
    await send_line(target_writer, "You have been kicked from partyline.")
    await send_line(target_writer, "*EXIT")
    await broadcast_room(target_room, f"{target} was kicked from partyline")
    await broadcast_room(target_room, "")
    await send_line(writer, f"Kicked {target}.")
    await send_line(writer, "")
    from compunet_server import audit_log
    audit_log('partyline_kicked', user=user_id, target=target)
    partyline_log('kick', user=user_id, target=target, room=target_room)
    logger.info("User %s kicked %s from partyline", user_id, target)


async def _cmd_ban(writer, user_id, args):
    """Ban a user from partyline (ADMIN/EDITOR only)."""
    if not _is_privileged(user_id):
        await send_line(writer, "Permission denied.")
        await send_line(writer, "")
        return
    target = args.strip().upper()
    if not target:
        await send_line(writer, "Usage: *ban USER")
        await send_line(writer, "")
        return
    if target == user_id:
        await send_line(writer, "You can't ban yourself.")
        await send_line(writer, "")
        return
    if target == 'ADMIN':
        await send_line(writer, "ADMIN cannot be banned.")
        await send_line(writer, "")
        return
    bans = _load_bans()
    if target.upper() not in [b.upper() for b in bans]:
        bans.append(target)
        _save_bans(bans)
    # Kick if currently online
    if target in _users:
        target_room = _users[target]["room"]
        target_writer = _users[target]["writer"]
        del _users[target]
        await send_line(target_writer, "You have been banned from partyline.")
        await send_line(target_writer, "*EXIT")
        await broadcast_room(target_room, f"{target} has been banned from partyline")
        await broadcast_room(target_room, "")
    await send_line(writer, f"Banned {target}.")
    await send_line(writer, "")
    from compunet_server import audit_log
    audit_log('partyline_banned', user=user_id, target=target)
    partyline_log('ban', user=user_id, target=target)
    logger.info("User %s banned %s from partyline", user_id, target)


async def _cmd_unban(writer, user_id, args):
    """Unban a user from partyline (ADMIN/EDITOR only)."""
    if not _is_privileged(user_id):
        await send_line(writer, "Permission denied.")
        await send_line(writer, "")
        return
    target = args.strip().upper()
    if not target:
        await send_line(writer, "Usage: *unban USER")
        await send_line(writer, "")
        return
    bans = _load_bans()
    bans = [b for b in bans if b.upper() != target.upper()]
    _save_bans(bans)
    await send_line(writer, f"Unbanned {target}.")
    await send_line(writer, "")
    from compunet_server import audit_log
    audit_log('partyline_unbanned', user=user_id, target=target)
    logger.info("User %s unbanned %s from partyline", user_id, target)


async def _cmd_quit(writer, user_id):
    """Handle user quitting partyline."""
    if user_id not in _users:
        return
    name = display_name(user_id)
    room = _users[user_id]["room"]
    # Remove user from state before broadcasting
    del _users[user_id]
    await broadcast_room(room, f"{name} has left partyline")
    await broadcast_room(room, "")
    # Send exit sentinel to client
    try:
        await send_line(writer, "*EXIT")
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    logger.info("User %s quit partyline", user_id)
    partyline_log('leave', user=user_id, room=room)


async def handle_session(reader, writer, user_id, amiga=False):
    """Handle a partyline session. Returns when user quits."""
    logger.info("User %s entering partyline", user_id)
    partyline_log('join', user=user_id)

    # Check ban list
    if _is_banned(user_id):
        logger.info("User %s is banned from partyline", user_id)
        await send_line(writer, "You are banned from partyline.")
        await send_line(writer, "*EXIT")
        return

    # Register user
    _users[user_id] = {"writer": writer, "alias": None, "room": "Lobby"}

    try:
        # Announce entry
        await send_line(writer, f"{user_id} has entered partyline")
        await send_line(writer, "")
        await broadcast_room("Lobby", f"{user_id} has entered partyline", exclude=user_id)
        await broadcast_room("Lobby", "", exclude=user_id)

        # Show who's online
        await _cmd_who(writer, user_id)

        # Main loop
        idle_pings = 0
        while user_id in _users:
            try:
                line = await read_line(reader, amiga=amiga)
                idle_pings = 0  # Reset on any received data
            except asyncio.TimeoutError:
                # Send keepalive to prevent NAT/firewall dropping the connection
                idle_pings += 1
                if idle_pings > 20:
                    logger.info("User %s exceeded max idle pings, disconnecting", user_id)
                    break
                logger.debug("Partyline PING keepalive sent to %s", user_id)
                try:
                    await send_line(_users[user_id]["writer"], "*PING")
                except (ConnectionResetError, BrokenPipeError, OSError):
                    break
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                logger.info("User %s disconnected", user_id)
                break

            line = line.strip()
            if not line:
                continue

            result = await process_input(user_id, line, writer)
            if result == 'save':
                # C64 client handles save locally from its own buffer
                await send_line(writer, "Saving...")
                await send_line(writer, "")
            elif result:
                return

    except (ConnectionResetError, BrokenPipeError, OSError):
        logger.info("User %s connection lost", user_id)
    finally:
        # Clean up if user is still registered (abnormal disconnect)
        if user_id in _users:
            room = _users[user_id]["room"]
            name = display_name(user_id)
            del _users[user_id]
            partyline_log('disconnect', user=user_id, room=room)
            await broadcast_room(room, f"{name} has left partyline")
            await broadcast_room(room, "")
            logger.info("User %s removed from partyline (cleanup)", user_id)


async def handle_amiga_session(reader, writer, user_id):
    """Partyline for the Amiga CnetTty viewer ("Scrollback v1.0", Zugger '89).

    The 8-byte link header has already been sent (framed) by the caller. This runs the raw
    phase: the link preamble handshake, the ASCII chat session (reusing handle_session), and
    the 0x02-based teardown that returns CnetTty's terminal loop to the client.

    Protocol (verified against the decrunched viewer, tools/re/cnettty-re.md):
      - CnetTty's link_drain_preamble reads raw bytes until it sees three consecutive 0x01,
        then replies with 0x01 x6.
      - the session is raw ASCII, CR-terminated (RETURN-twice sends 0x0d 0x0d).
      - the viewer's loop returns on three consecutive 0x02 from us (server-initiated *quit)
        or on its own "Done" gadget, after which the client sends 0x02 x6 (link_end).
    """
    writer._amiga = True
    client_left = False
    try:
        writer.write(b'\x01\x01\x01')          # arm markers for link_drain_preamble
        await writer.drain()
        await _drain_raw(reader, 6, timeout=2.0)   # its 0x01 x6 reply
        await handle_session(reader, writer, user_id, amiga=True)
    except _AmigaQuit:
        client_left = True                     # user hit "Done"; client already tore down
    except (ConnectionResetError, BrokenPipeError, OSError):
        client_left = True
    finally:
        try:
            if not client_left:
                # Server-initiated (*quit): three 0x02 return CnetTty's loop; it then sends
                # 0x02 x6 (link_end), which we drain before resuming X.25.
                writer.write(b'\x02\x02\x02')
                await writer.drain()
                await _drain_raw(reader, 6, timeout=2.0)
            else:
                await _drain_raw(reader, 6, timeout=0.5)   # drain any residual link_end 0x02s
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        try:
            del writer._amiga
        except AttributeError:
            pass


async def handle_web_session(ws, user_id):
    """Handle a partyline session from a WebSocket client.

    Messages to the client are sent as WS text frames.
    Messages from the client arrive as WS text frames.
    """
    import aiohttp.web as aiohttp_web

    out_queue = asyncio.Queue()
    in_queue = asyncio.Queue()
    writer = WebWriter(out_queue)
    reader = WebReader(in_queue)

    # Task to forward outgoing messages to WebSocket
    async def ws_sender():
        try:
            while True:
                msg = await out_queue.get()
                await ws.send_str(msg)
        except (asyncio.CancelledError, ConnectionResetError):
            pass

    # Task to forward incoming WebSocket messages to reader queue
    async def ws_receiver():
        try:
            async for msg in ws:
                if msg.type == aiohttp_web.WSMsgType.TEXT:
                    # Convert to bytes with CR terminator (one byte at a time for read_line)
                    line_bytes = msg.data.encode('ascii', errors='replace')
                    for b in line_bytes:
                        await in_queue.put(bytes([b]))
                    await in_queue.put(CR)
                elif msg.type in (aiohttp_web.WSMsgType.ERROR,
                                  aiohttp_web.WSMsgType.CLOSE):
                    break
        except (asyncio.CancelledError, ConnectionResetError):
            pass

    sender_task = asyncio.create_task(ws_sender())
    receiver_task = asyncio.create_task(ws_receiver())

    try:
        await handle_session(reader, writer, user_id)
    finally:
        sender_task.cancel()
        receiver_task.cancel()
