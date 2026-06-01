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
    """Append an event to the partyline log (JSON-lines format)."""
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
# {user_id: {"writer": writer, "alias": None, "room": "lobby"}}
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

*alias (followed by a name)
*who  (tells who's in pline)
*enter (any room name) to enter
 a different room
*dice (number) to roll
*call (user) to call someone
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


async def send_line(writer, text):
    """Send one CR-terminated line to a client."""
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


async def read_line(reader):
    """Read bytes from reader until CR ($0D). Returns the line as a string.

    Raises asyncio.TimeoutError if no data within 60 seconds.
    Raises ConnectionResetError if the connection is closed.
    """
    buf = bytearray()
    while True:
        data = await asyncio.wait_for(reader.read(1), timeout=60.0)
        if not data:
            raise ConnectionResetError("Client disconnected")
        if data == CR:
            break
        buf.extend(data)
    return petscii_to_ascii(buf)


async def _cmd_help(writer, user_id):
    """Send help text to user."""
    for line in HELP_TEXT.split('\n'):
        await send_line(writer, line)
    await send_line(writer, "")


async def _cmd_alias(writer, user_id, args):
    """Set user alias (max 8 characters)."""
    name = args.strip()[:8]
    if not name:
        await send_line(writer, "Usage: *alias <name>")
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


async def _cmd_enter(writer, user_id, args):
    """Move user to a different room."""
    new_room = args.strip().lower()
    if not new_room:
        await send_line(writer, "Usage: *enter <room>")
        await send_line(writer, "")
        return
    old_room = _users[user_id]["room"]
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
    audit_log('partyline_kick', user=user_id, target=target)
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
    audit_log('partyline_ban', user=user_id, target=target)
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
    audit_log('partyline_unban', user=user_id, target=target)
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


async def handle_session(reader, writer, user_id):
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
    _users[user_id] = {"writer": writer, "alias": None, "room": "lobby"}

    try:
        # Announce entry
        await send_line(writer, f"{user_id} has entered partyline")
        await send_line(writer, "")
        await broadcast_room("lobby", f"{user_id} has entered partyline", exclude=user_id)
        await broadcast_room("lobby", "", exclude=user_id)

        # Main loop
        idle_pings = 0
        while user_id in _users:
            try:
                line = await read_line(reader)
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

            should_exit = await process_input(user_id, line, writer)
            if should_exit:
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
