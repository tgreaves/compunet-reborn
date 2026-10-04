"""
Federation module — bridges a Compunet session to an external federation server.

The federation server does NOT live in this repository. Everything this module
knows about it is three facts: where it listens, that it wants one login line
naming the user, and that it speaks complete LF-terminated ASCII lines after
that. Commands, rooms and moderation are its business, not ours.

    C64 / Amiga / terminal / web        this module          federation server
    -----------------------------------------------------------------------
    PETSCII, CR-terminated        <->   translate, proxy  <->  ASCII, LF

⚠ NO COMMAND IS OURS, AND FEDERATION HAS NONE. Every line the user commits goes
upstream verbatim, `*quit` included. Leaving is the host's business: it ends the
session on an in-game command or event (or by crashing), and we send the client
the *EXIT that returns it to the framed protocol.

The one line we originate is *EXIT, and only to end the session: the client waits
for it before handing control back to the X.25 protocol engine. Nothing else is
ours — there is no keepalive, because Federation has never had one on either
side, and inventing one would put a line on the wire that the client would have
to be taught to ignore.

⚠ No client has a local way out — not RUN/STOP, not ESC — as in the original: a
stray keypress must not drop a player from the game. The Amiga CnetTty "Done"
gadget is the one exception, and it is the original viewer's.

Entry is by activating an `L` directory entry carrying `"link": "federation"`
(§7.4), exactly as Partyline is entered without it.
"""

import asyncio
import logging
import os

import partyline as pl

logger = logging.getLogger(__name__)

ADDR_ENV = 'FEDERATION_ADDR'             # "host:port"; unset = feature off
TOKEN_ENV = 'FEDERATION_TOKEN'           # 32-byte secret
CONNECT_TIMEOUT = 10.0
CHAT_WIDTH = 40                          # pegterm output area, in columns

EXIT = '*EXIT'                           # the only line we originate

_UNAVAILABLE = 'Federation is not available.'
_UNREACHABLE = 'Cannot contact Federation DataSpace.'
_CLOSED = 'Federation link closed.'


class FederationUnavailable(Exception):
    """No federation server is configured, or it refused the connection."""


def address():
    """(host, port) from FEDERATION_ADDR, or None when unset."""
    raw = os.environ.get(ADDR_ENV, '').strip()
    if not raw:
        return None

    host, sep, port = raw.rpartition(':')
    if not sep or not host or not port.isdigit():
        logger.error('%s is not host:port: %r', ADDR_ENV, raw)
        return None

    return host, int(port)


def is_enabled():
    """Whether a federation server is configured at all."""
    return address() is not None


class Link:
    """One connection to the federation server, on behalf of one user."""

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer

    @classmethod
    async def open(cls, user_id, via=None, ip=None):
        """Connect and identify the user. Raises FederationUnavailable.

        ⚠ The entry is audited HERE, in the function that performs it, so every
        surface inherits it — the mistake Partyline had to be fixed for (#127).
        """
        addr = address()
        if addr is None:
            raise FederationUnavailable(_UNAVAILABLE)

        token = os.environ.get(TOKEN_ENV, '').strip()
        if not token:
            raise FederationUnavailable(_UNAVAILABLE)

        host, port = addr
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT)
        except (OSError, asyncio.TimeoutError) as exc:
            logger.warning('Federation connect to %s:%d failed: %s', host, port, exc)
            raise FederationUnavailable(_UNREACHABLE)

        link = cls(reader, writer)
        # One login line names the user and the surface they came through, so the
        # remote server can tell a C64 apart from a browser without asking us.
        await link.send('JOIN %s %s %s %s' % (token, user_id, via or 'unknown', ip or 'unknown'))
        logger.info('Federation: %s connected to %s:%d (via %s)', user_id, host, port, via)

        try:
            from compunet_server import audit_log
            extra = {k: v for k, v in (('via', via), ('ip', ip)) if v}
            audit_log('federation_entered', user=user_id, server='%s:%d' % (host, port), **extra)
        except ImportError:      # federation used standalone
            pass

        return link

    async def send(self, text):
        """Send one LF-terminated ASCII line upstream."""
        self._writer.write(text.encode('ascii', errors='replace') + b'\n')
        await self._writer.drain()

    async def readline(self):
        """Next line from upstream, without its terminator. None at end of stream.

        Tolerant of CR, LF and CRLF, because the remote end is not ours to fix.
        """
        try:
            raw = await self._reader.readline()
        except (asyncio.LimitOverrunError, ValueError):
            return ''                        # over-long line: drop, keep the link
        except (ConnectionResetError, BrokenPipeError, OSError):
            return None

        if not raw:
            return None

        return raw.rstrip(b'\r\n').decode('ascii', errors='replace')

    async def close(self):
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass


async def _send_text(writer, text, amiga=False):
    """Send one line of remote text to the client, wrapped to the chat window.

    ⚠ NOT pl.send_line for text: that treats any line starting with `*` as a raw
    protocol sentinel, so a remote line of "*** welcome ***" would arrive as
    unconverted ASCII — and a remote line of "*EXIT" would end the session on the
    client's side while we carried on proxying. Remote text is always text.
    """
    for start in range(0, max(len(text), 1), CHAT_WIDTH):
        chunk = text[start:start + CHAT_WIDTH]
        if amiga:
            writer.write(chunk.encode('ascii', errors='replace') + pl.CR)
        else:
            writer.write(pl._ascii_to_petscii(chunk) + pl.CR)
        await writer.drain()


async def _pump_up(reader, writer, link, user_id, amiga):
    """Client -> federation, verbatim. Returns when the client goes away."""
    while True:
        try:
            line = await pl.read_line(reader, amiga=amiga)
        except asyncio.TimeoutError:
            # pl.read_line gives up on silence after a minute. Silence is not a
            # fault: the user is reading, or has walked away. Wait again — a
            # session ends when a side closes it, never on a timer here.
            continue
        except (ConnectionResetError, BrokenPipeError, OSError):
            return
        # ⚠ _AmigaQuit is NOT an error and must not be swallowed: it says the
        # CnetTty viewer has already torn the link down itself, and
        # handle_amiga_session sends its 0x02 teardown only when it has not.
        # Caught here, an Amiga user leaving would be answered with a teardown
        # nothing is listening for, and the bytes would surface in X.25.

        line = line.strip()
        if not line:
            continue

        try:
            await link.send(line)
        except (ConnectionResetError, BrokenPipeError, OSError):
            return


async def _pump_down(link, writer, amiga):
    """Federation -> client. Returns when the remote server closes the link."""
    while True:
        line = await link.readline()
        if line is None:
            return
        try:
            await _send_text(writer, line, amiga=amiga)
        except (ConnectionResetError, BrokenPipeError, OSError):
            return


async def handle_session(reader, writer, user_id, amiga=False, via=None, ip=None):
    """Binding A: proxy a raw line session. Returns when either end hangs up."""
    try:
        link = await Link.open(user_id, via=via, ip=ip)
    except FederationUnavailable as exc:
        await _send_text(writer, str(exc), amiga=amiga)
        await pl.send_line(writer, EXIT)
        return

    up = asyncio.create_task(_pump_up(reader, writer, link, user_id, amiga))
    down = asyncio.create_task(_pump_down(link, writer, amiga))
    raised = None
    try:
        done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            raised = raised or task.exception()

        # The remote end dropping is not something the user did — say so, or the
        # screen just stops answering.
        if down in done and raised is None:
            await _send_text(writer, _CLOSED, amiga=amiga)
    finally:
        await link.close()
        logger.info('Federation: %s left', user_id)

    if raised is not None:
        raise raised                     # _AmigaQuit: the client tore down first

    try:
        await pl.send_line(writer, EXIT)
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass


async def handle_amiga_session(reader, writer, user_id, via=None, ip=None):
    """Federation for the Amiga CnetTty viewer.

    Same raw link as Partyline's — the 0x01 preamble handshake, an ASCII session,
    then the 0x02 teardown that returns CnetTty's terminal loop to the client (see
    partyline.handle_amiga_session, which documents the protocol). Only the
    session in the middle differs.
    """
    writer._amiga = True
    client_left = False
    try:
        writer.write(b'\x01\x01\x01')
        await writer.drain()
        await pl._drain_raw(reader, 6, timeout=2.0)
        await handle_session(reader, writer, user_id, amiga=True, via=via, ip=ip)
    except pl._AmigaQuit:
        client_left = True                     # user hit "Done"; already torn down
    except (ConnectionResetError, BrokenPipeError, OSError):
        client_left = True
    finally:
        try:
            if not client_left:
                writer.write(b'\x02\x02\x02')
                await writer.drain()
                await pl._drain_raw(reader, 6, timeout=2.0)
            else:
                await pl._drain_raw(reader, 6, timeout=0.5)
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        try:
            del writer._amiga
        except AttributeError:
            pass


# --- Binding B (gateway) ----------------------------------------------------
#
# The gateway is already message-oriented, so there is no raw phase: lines from
# the federation server are pushed as `partyline` messages and lines from the
# client arrive as `partyline.send`/`partyline.command`. The vocabulary is shared
# with Partyline deliberately — it is the same chat window on screen — and the
# `service` field on entry/exit says which one the user is actually in.


async def web_enter(session, ws, msg_id=None):
    """Join Federation from Binding B. Returns an error message, or None."""
    if getattr(session, '_fed_link', None) is not None:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "already in federation"}

    try:
        link = await Link.open(session.user_id,
                               via=getattr(session, 'audit_via', None),
                               ip=getattr(session, 'client_ip', None))
    except FederationUnavailable as exc:
        return {"type": "error", "id": msg_id, "code": "unavailable",
                "message": str(exc)}

    session._fed_link = link
    await ws.send_json({"type": "partyline.entered", "id": msg_id,
                        "room": "Federation", "service": "federation"})

    async def pump():
        while True:
            line = await link.readline()
            if line is None:
                break
            try:
                await ws.send_json({"type": "partyline", "line": line})
            except Exception:
                break
        # Remote hung up: tell the client the window is over.
        try:
            await ws.send_json({"type": "partyline", "line": _CLOSED})
            await ws.send_json({"type": "partyline.left", "service": "federation"})
        except Exception:
            pass
        session._fed_link = None

    session._fed_task = asyncio.create_task(pump())
    return None


async def web_input(session, line, msg_id=None):
    """Feed one line from Binding B upstream, verbatim.

    `*quit` is a line like any other: Federation has no `*` commands.
    """
    link = getattr(session, '_fed_link', None)
    if link is None:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "not in federation"}

    line = line.strip()
    if line:
        try:
            await link.send(line)
        except (ConnectionResetError, BrokenPipeError, OSError):
            return await web_leave(session, msg_id)

    return None


async def web_leave(session, msg_id=None):
    """Leave Federation and resume normal gateway commands."""
    link = getattr(session, '_fed_link', None)
    if link is None:
        return {"type": "error", "id": msg_id, "code": "invalid",
                "message": "not in federation"}

    session._fed_link = None
    task = getattr(session, '_fed_task', None)
    if task is not None:
        task.cancel()
        session._fed_task = None
    await link.close()
    logger.info('Federation(api): %s left', session.user_id)

    return {"type": "partyline.left", "id": msg_id, "service": "federation"}
