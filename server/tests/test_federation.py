#!/usr/bin/env python3
"""Tests for the Federation link (server/federation.py).

Run:  python server/tests/test_federation.py            (or -v)

The federation server is not ours, so what is worth testing is the bridge: that
we identify the user exactly once, that lines cross intact and in the right
character set, that no command of the far end's is answered here, that an idle
session is left alone, and that entering is audited — from whichever surface the
user came through.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.dirname(_HERE)
sys.path.insert(0, _SERVER)

os.environ.setdefault('COMPUNET_CONTENT_DIR',
                      os.path.join(_SERVER, 'data', 'content.test'))

import compunet_server as srv     # noqa: E402
import federation as fed          # noqa: E402
import partyline as pl            # noqa: E402


class FakeReader:
    """The client side of a Binding-A session: a fixed script, then EOF."""

    def __init__(self, data=b''):
        self._data = bytearray(data)

    async def read(self, n):
        if not self._data:
            return b''               # read_line turns this into a disconnect
        out = bytes(self._data[:n])
        del self._data[:n]
        return out


class FakeWriter:
    def __init__(self):
        self.data = bytearray()

    def write(self, chunk):
        self.data += chunk

    async def drain(self):
        pass

    def lines(self):
        """What the client would have seen, decoded back out of PETSCII."""
        return [pl.petscii_to_ascii(part)
                for part in bytes(self.data).split(b'\x0d')[:-1]]


class StubFederationServer:
    """A federation server that records what it is told and can talk back.

    In memory, standing in for `asyncio.open_connection`: the harness has no
    right to listen on a port, and a real socket would test the kernel rather
    than the bridge.
    """

    def __init__(self):
        self.received = []               # complete lines we were sent
        self.connected = asyncio.Event()
        self._to_client = asyncio.Queue()
        self._partial = b''

    # --- the halves federation.Link is handed --------------------------------

    async def open_connection(self, host, port):
        self.connected.set()
        return self, self

    async def readline(self):
        return await self._to_client.get()

    def write(self, chunk):
        self._partial += chunk
        while b'\n' in self._partial:
            line, _, self._partial = self._partial.partition(b'\n')
            self.received.append(line.decode('ascii'))

    async def drain(self):
        pass

    def close(self):
        pass

    async def wait_closed(self):
        pass

    # --- what the test drives it with ----------------------------------------

    async def say(self, text):
        await self._to_client.put(text.encode('ascii') + b'\n')

    async def hang_up(self):
        await self._to_client.put(b'')


class FederationTestCase(unittest.IsolatedAsyncioTestCase):
    """Redirects the audit log to a temp file and runs a stub upstream server."""

    async def asyncSetUp(self):
        self._tmp = tempfile.mkdtemp(prefix='compunet-fed-')
        self._saved_path = srv.AUDIT_LOG_PATH
        self._saved_addr = os.environ.get(fed.ADDR_ENV)
        srv.AUDIT_LOG_PATH = os.path.join(self._tmp, 'audit.jsonl')
        os.environ[fed.ADDR_ENV] = 'fed.test:30003'
        self.upstream = StubFederationServer()
        self._patch = unittest.mock.patch('asyncio.open_connection',
                                          self.upstream.open_connection)
        self._patch.start()

    async def asyncTearDown(self):
        self._patch.stop()
        srv.AUDIT_LOG_PATH = self._saved_path
        if self._saved_addr is None:
            os.environ.pop(fed.ADDR_ENV, None)
        else:
            os.environ[fed.ADDR_ENV] = self._saved_addr
        shutil.rmtree(self._tmp, ignore_errors=True)

    def events(self, name=None):
        if not os.path.exists(srv.AUDIT_LOG_PATH):
            return []
        out = []
        with open(srv.AUDIT_LOG_PATH) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if name is None or entry.get('event') == name:
                        out.append(entry)
        return out


class TheAddressComesFromTheEnvironment(unittest.TestCase):

    def setUp(self):
        self._saved = os.environ.get(fed.ADDR_ENV)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop(fed.ADDR_ENV, None)
        else:
            os.environ[fed.ADDR_ENV] = self._saved

    def test_unset_means_the_feature_is_off(self):
        os.environ.pop(fed.ADDR_ENV, None)
        self.assertIsNone(fed.address())
        self.assertFalse(fed.is_enabled())

    def test_host_and_port_are_split(self):
        os.environ[fed.ADDR_ENV] = 'fed.example.com:30003'
        self.assertEqual(fed.address(), ('fed.example.com', 30003))

    def test_an_ipv6_address_keeps_its_brackets(self):
        os.environ[fed.ADDR_ENV] = '[::1]:30003'
        self.assertEqual(fed.address(), ('[::1]', 30003))

    def test_a_malformed_value_is_refused_rather_than_guessed(self):
        for bad in ('fed.example.com', 'fed.example.com:chat', ':30003'):
            os.environ[fed.ADDR_ENV] = bad
            self.assertIsNone(fed.address(), bad)


class TheUserIsIdentifiedOnce(FederationTestCase):

    async def test_the_login_line_names_the_user_surface_and_ip(self):
        link = await fed.Link.open('ZARD', via='c64', ip='203.0.113.9')
        await link.close()
        self.assertEqual(self.upstream.received, ['JOIN ZARD c64 203.0.113.9'])

    async def test_an_unknown_surface_still_produces_a_valid_line(self):
        link = await fed.Link.open('ZARD')
        await link.close()
        self.assertEqual(self.upstream.received, ['JOIN ZARD unknown unknown'])

    async def test_entering_is_audited_where_the_link_is_opened(self):
        link = await fed.Link.open('ZARD', via='web', ip='203.0.113.9')
        await link.close()
        entered = self.events('federation_entered')
        self.assertEqual(len(entered), 1)
        self.assertEqual(entered[0]['user'], 'ZARD')
        self.assertEqual(entered[0]['via'], 'web')
        self.assertEqual(entered[0]['ip'], '203.0.113.9')
        self.assertEqual(entered[0]['kind'], 'federation')

    async def test_a_refused_connection_becomes_federation_unavailable(self):
        with unittest.mock.patch('asyncio.open_connection',
                                 side_effect=ConnectionRefusedError):
            with self.assertRaises(fed.FederationUnavailable):
                await fed.Link.open('ZARD', via='c64')


class LinesCrossIntact(FederationTestCase):

    async def test_what_the_client_types_reaches_the_far_end_as_ascii(self):
        # PETSCII lowercase 'hello' ($48 $45 $4c $4c $4f), CR-terminated.
        reader = FakeReader(b'\x48\x45\x4c\x4c\x4f\x0d')
        writer = FakeWriter()
        await fed.handle_session(reader, writer, 'ZARD', via='c64')
        self.assertEqual(self.upstream.received, ['JOIN ZARD c64 unknown', 'hello'])

    async def test_what_the_far_end_says_arrives_as_petscii(self):
        reader = FakeReader()
        writer = FakeWriter()
        task = asyncio.create_task(fed.handle_session(reader, writer, 'ZARD'))
        await asyncio.wait_for(self.upstream.connected.wait(), timeout=2.0)
        await self.upstream.say('Hello ZARD')
        await asyncio.sleep(0.05)
        await self.upstream.hang_up()
        await asyncio.wait_for(task, timeout=2.0)
        self.assertIn('Hello ZARD', writer.lines())

    async def test_a_long_line_is_wrapped_to_the_chat_window(self):
        reader = FakeReader()
        writer = FakeWriter()
        task = asyncio.create_task(fed.handle_session(reader, writer, 'ZARD'))
        await asyncio.wait_for(self.upstream.connected.wait(), timeout=2.0)
        await self.upstream.say('x' * 80)
        await asyncio.sleep(0.05)
        await self.upstream.hang_up()
        await asyncio.wait_for(task, timeout=2.0)
        for line in writer.lines():
            self.assertLessEqual(len(line), fed.CHAT_WIDTH)

    async def test_remote_text_starting_with_a_star_is_text_not_a_sentinel(self):
        # ⚠ The C64 program exits on a literal "*EXIT" line. If remote text were
        # passed through pl.send_line it would be sent raw, and a federation
        # server saying "*EXIT" — or any "*** notice ***" — would end the
        # session on the client while the server carried on proxying.
        reader = FakeReader()
        writer = FakeWriter()
        task = asyncio.create_task(fed.handle_session(reader, writer, 'ZARD'))
        await asyncio.wait_for(self.upstream.connected.wait(), timeout=2.0)
        await self.upstream.say('*EXIT')
        await asyncio.sleep(0.05)
        await self.upstream.hang_up()
        await asyncio.wait_for(task, timeout=2.0)
        self.assertNotIn(b'*EXIT\x0d', bytes(writer.data)[:6])


class NoCommandIsOurs(FederationTestCase):
    """The remote server owns its command set; the bridge answers none of it."""

    async def test_quit_is_forwarded_like_any_other_line(self):
        reader = FakeReader(b'*quit\x0d')
        writer = FakeWriter()
        await fed.handle_session(reader, writer, 'ZARD', via='c64')
        self.assertEqual(self.upstream.received, ['JOIN ZARD c64 unknown', '*quit'])

    async def test_a_command_the_bridge_has_never_heard_of_goes_through(self):
        reader = FakeReader(b'*warp 7\x0d')
        writer = FakeWriter()
        await fed.handle_session(reader, writer, 'ZARD', via='c64')
        self.assertIn('*warp 7', self.upstream.received)

    async def test_the_client_is_told_to_exit_when_the_session_ends(self):
        reader = FakeReader(b'*quit\x0d')
        writer = FakeWriter()
        await fed.handle_session(reader, writer, 'ZARD', via='c64')
        self.assertTrue(bytes(writer.data).endswith(b'*EXIT\x0d'))

    async def test_the_far_end_hanging_up_says_so_and_exits(self):
        reader = FakeReader()
        writer = FakeWriter()
        task = asyncio.create_task(fed.handle_session(reader, writer, 'ZARD'))
        await asyncio.wait_for(self.upstream.connected.wait(), timeout=2.0)
        await self.upstream.hang_up()
        await asyncio.wait_for(task, timeout=2.0)
        self.assertIn(fed._CLOSED, writer.lines())
        self.assertTrue(bytes(writer.data).endswith(b'*EXIT\x0d'))


class NothingIsSentToAnIdleClient(FederationTestCase):
    """Federation has no keepalive — not on the wire, and not in either client."""

    async def test_a_silent_client_is_left_alone(self):
        # ⚠ pl.read_line gives up on silence after 60s; a Partyline session
        # answers that with *PING. This one must answer it with nothing at all,
        # or every client would need teaching to ignore a line that, on this
        # link, has never existed.
        calls = []

        async def read_line(reader, amiga=False):
            calls.append(1)
            if len(calls) == 1:
                raise asyncio.TimeoutError()
            raise ConnectionResetError()

        reader = FakeReader()
        writer = FakeWriter()
        with unittest.mock.patch.object(pl, 'read_line', read_line):
            await fed.handle_session(reader, writer, 'ZARD', via='c64')

        self.assertEqual(len(calls), 2)             # it waited again, silently
        self.assertNotIn('*PING', writer.lines())
        self.assertEqual(bytes(writer.data), b'*EXIT\x0d')


class WithNoServerConfigured(FederationTestCase):

    async def test_the_user_is_told_and_returned_to_the_directory(self):
        os.environ.pop(fed.ADDR_ENV, None)
        reader = FakeReader()
        writer = FakeWriter()
        await fed.handle_session(reader, writer, 'ZARD', via='c64')
        self.assertIn(fed._UNAVAILABLE, writer.lines())
        self.assertTrue(bytes(writer.data).endswith(b'*EXIT\x0d'))
        self.assertEqual(self.events('federation_entered'), [])


class TheDirectoryEntryChoosesTheService(unittest.TestCase):
    """`L` entries are Partyline unless they name Federation (§7.4)."""

    def test_a_link_entry_without_the_field_is_partyline(self):
        page = srv.CompunetPage(page_num=1, title='JOIN PARTYLINE', page_type='L')
        self.assertIsNone(getattr(page, 'link', None))

    def test_the_field_round_trips_through_the_directory_json(self):
        tree = srv.CompunetDirectory.__new__(srv.CompunetDirectory)
        tree.pages = {}
        tree.duplicate_page_nums = set()
        node = {'page_num': 501, 'title': 'PLAY FEDERATION', 'type': 'L',
                'link': 'federation'}
        page = tree._build_flat_page(node, None, os.path.join(_SERVER, 'data'))
        self.assertEqual(page.link, 'federation')


if __name__ == '__main__':
    unittest.main()
