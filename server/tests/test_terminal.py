#!/usr/bin/env python3
"""Regression tests for the PETSCII terminal (server/terminal.py).

Run:  python server/tests/test_terminal.py            (or -v)

⚠ NOTHING COVERED terminal.py BEFORE THIS FILE, and that is not a small gap: it
is a third surface onto the same content tree, reached by a real user with a real
terminal program, and for a long time it did its own writing. Three of the four
defects these tests pin were found by reading it rather than by running anything,
because there was nothing to run.

The rule they hold is the one the project already applies to auditing, extended
to the thing being audited: **an action is performed by ONE shared function, and
every surface calls it.** A surface that reimplements an action does not merely
risk drifting — it had already drifted, in four separate ways (see
`compunet_server.complete_content_upload`). So each test below asserts the
terminal produces the SHARED behaviour, not merely a plausible one.

The suite writes, so it works on a temp copy of the fixture tree and redirects
the audit log; it never touches the tracked fixtures or the real log.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.dirname(_HERE)
sys.path.insert(0, _SERVER)

os.environ.setdefault('COMPUNET_CONTENT_DIR',
                      os.path.join(_SERVER, 'data', 'content.test'))

import compunet_server as srv     # noqa: E402
import terminal as term           # noqa: E402

USER = 'TEST'
JUNGLE, GRAPHICS = 600, 601


class _Writer:
    """Just enough of an asyncio StreamWriter to be constructed with."""

    def __init__(self):
        self.data = bytearray()

    def write(self, data):
        self.data.extend(data)

    async def drain(self):
        pass


class FakeTerminal(term.TerminalSession):
    """A TerminalSession with the screen and the keyboard stubbed out.

    Everything below the rendering is the real class — in particular the real
    `_can_upload_here`, the real adapters, and the real calls into the shared
    writer. Stubbing more than the I/O would test the stub.
    """

    def __init__(self, directory, user_id=USER):
        super().__init__(None, _Writer(), directory)
        self.user_id = user_id
        self.authenticated = True
        self.client_ip = 'test'
        self.screen = []          # every send_text, stripped
        self.xmodem_payload = b''

    # --- I/O stubs ---
    async def send(self, data):
        pass

    async def send_text(self, text):
        self.screen.append(text.strip())

    async def cursor_to(self, row, col):
        pass

    async def read_key(self):
        return 0x0D

    async def render_directory(self):
        pass

    async def render_duckshoot(self):
        pass

    async def _xmodem_receive(self):
        return self.xmodem_payload

    # --- assertions helper ---
    def said(self, text):
        return any(text in line for line in self.screen)


class TerminalTestCase(unittest.TestCase):
    """Temp copy of the tree + a temp audit log, so a write test cannot leave a
    diff in the tracked fixtures or an entry in the real audit log."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix='compunet-term-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        self._saved_audit = srv.AUDIT_LOG_PATH
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')
        srv.AUDIT_LOG_PATH = os.path.join(self._tmp, 'audit.jsonl')
        self.directory = srv.CompunetDirectory()

    def tearDown(self):
        srv.ROOT_DIR = self._saved_root
        srv.AUDIT_LOG_PATH = self._saved_audit
        shutil.rmtree(self._tmp, ignore_errors=True)

    # --- helpers ---

    def terminal(self, page=GRAPHICS, user_id=USER):
        t = FakeTerminal(self.directory, user_id=user_id)
        t.current_page = self.directory.pages[page]
        return t

    @staticmethod
    def drive(coro):
        """Run one terminal coroutine to completion. NOT named `run` — that is
        unittest.TestCase's own method, and shadowing it makes the whole suite
        collapse into one confusing error."""
        return asyncio.run(coro)

    def graphics_json(self):
        with open(os.path.join(srv.ROOT_DIR, 'jungle', 'graphics',
                               'directory.json')) as f:
            return json.load(f)['pages']

    def entry(self, title):
        return next((p for p in self.graphics_json() if p['title'] == title), None)

    def events(self):
        if not os.path.exists(srv.AUDIT_LOG_PATH):
            return []
        with open(srv.AUDIT_LOG_PATH) as f:
            return [json.loads(line) for line in f if line.strip()]

    @staticmethod
    def text_upload(title, frames=None, page_type='T', price=0.0, life=30):
        return {'mode': 'upload', 'title': title, 'type': page_type,
                'price': price, 'lifetime': life,
                'frames': frames if frames is not None else [b'\x00\x06\x0f\x8e\x0dHI\x00']}


class TextUpload(TerminalTestCase):
    """UPLD of a text page, completed with SEND."""

    def test_a_text_upload_lands_in_the_directory(self):
        t = self.terminal()
        t._upload_pending = self.text_upload('TERMPAGE')
        self.drive(t._complete_text_upload())
        entry = self.entry('TERMPAGE')
        self.assertIsNotNone(entry, 'the terminal wrote nothing: %r' % (t.screen,))
        self.assertEqual(entry['author'], USER)
        self.assertEqual(entry['type'], 'T')
        self.assertEqual(entry['life'], 30)
        self.assertTrue(t.said('UPLOAD COMPLETE'))

    def test_the_frames_are_written_as_seq_files(self):
        t = self.terminal()
        t._upload_pending = self.text_upload('TWOFRAMES',
                                             frames=[b'ONE\x00', b'TWO\x00'])
        self.drive(t._complete_text_upload())
        page_dir = os.path.join(srv.ROOT_DIR, 'jungle', 'graphics', 'twoframes')
        self.assertTrue(os.path.exists(os.path.join(page_dir, 'frame-1.seq')))
        self.assertTrue(os.path.exists(os.path.join(page_dir, 'frame-2.seq')))
        with open(os.path.join(page_dir, 'frame-2.seq'), 'rb') as f:
            self.assertEqual(f.read(), b'TWO\x00')

    def test_a_text_upload_is_audited_as_coming_from_the_terminal(self):
        t = self.terminal()
        t._upload_pending = self.text_upload('AUDITED')
        self.drive(t._complete_text_upload())
        ev = next((e for e in self.events() if e['event'] == 'page_uploaded'), None)
        self.assertIsNotNone(ev, 'the upload was not audited')
        self.assertEqual(ev['via'], 'terminal')
        self.assertEqual(ev['user'], USER)

    def test_a_replacement_says_so_on_screen_and_in_the_audit(self):
        """`action` distinguishes a new page from one that overwrote someone's
        work. It was recorded ONLY by the terminal's own copy of the writer; now
        it comes from the shared one, so every surface has it."""
        t = self.terminal()
        t._upload_pending = self.text_upload('REPLACEME')
        self.drive(t._complete_text_upload())

        t2 = self.terminal()
        t2._upload_pending = self.text_upload('REPLACEME', frames=[b'NEW\x00'])
        self.drive(t2._complete_text_upload())

        self.assertTrue(t2.said('UPLOAD REPLACED'))
        actions = [e.get('action') for e in self.events()
                   if e['event'] == 'page_uploaded']
        self.assertEqual(actions, ['uploaded', 'replaced'])


class ProgramUpload(TerminalTestCase):
    """UPLD of a program, delivered over XMODEM.

    ⚠ The terminal receives a PRG exactly as it sits on disk — load address then
    program — while the shared writer takes the wire format, [8-byte header][body],
    and rebuilds the file as `header[4:6] + body`. The terminal re-wraps to bridge
    that, and this is where a mistake would be invisible: a wrong wrap still
    produces a plausible .prg of nearly the right length, which then loads at the
    wrong address or is short by two bytes. So assert the bytes, not the shape.
    """

    PRG = bytes([0x01, 0x08]) + bytes(range(240))     # $0801, the usual BASIC start

    def _upload(self, title, prg=None):
        t = self.terminal()
        t._upload_pending = {'mode': 'upload', 'title': title, 'type': 'P',
                             'price': 1.5, 'lifetime': 60, 'frames': []}
        t.xmodem_payload = self.PRG if prg is None else prg
        self.drive(t._cmd_upload_send())
        return t

    def test_the_prg_round_trips_byte_for_byte(self):
        t = self._upload('TERMPROG')
        self.assertTrue(t.said('UPLOAD COMPLETE'), repr(t.screen))
        path = os.path.join(srv.ROOT_DIR, 'jungle', 'graphics',
                            'termprog', 'termprog.prg')
        with open(path, 'rb') as f:
            stored = f.read()
        self.assertEqual(stored, self.PRG,
                         'the XMODEM re-wrap must reproduce the uploaded file exactly')

    def test_the_load_address_survives(self):
        """The specific failure a bad wrap produces: $0801 becomes $0000 and the
        program will not run. Worth its own assertion because the file length
        alone would not show it."""
        self._upload('LOADADDR')
        path = os.path.join(srv.ROOT_DIR, 'jungle', 'graphics',
                            'loadaddr', 'loadaddr.prg')
        with open(path, 'rb') as f:
            self.assertEqual(f.read(2), bytes([0x01, 0x08]))

    def test_a_c64_program_records_no_machine_type(self):
        """Absent means C64 (§7). The terminal is a C64 surface, so it must write
        no key — writing `c64` explicitly would be noise, and writing `amiga`
        would corrupt the download descriptor for whoever fetched it."""
        self._upload('NOMACHINE')
        self.assertIsNone(self.entry('NOMACHINE').get('machine_type'))

    def test_the_price_and_life_from_the_prompt_are_stored(self):
        self._upload('PRICED')
        entry = self.entry('PRICED')
        self.assertEqual(entry['price'], 1.5)
        self.assertEqual(entry['life'], 60)


class TerminalRefusals(TerminalTestCase):
    """Every refusal the shared writer can return must reach the terminal's
    screen. They used to be a mixture of hand-written duplicates (not-owner) and
    conditions the terminal simply did not have (type gate, owner-only)."""

    def test_replacing_another_users_page_is_refused(self):
        t = self.terminal()
        t._upload_pending = self.text_upload('OWNED')
        self.drive(t._complete_text_upload())
        # Re-home the page on someone else, then try again as TEST.
        page = next(c for c in self.directory.pages[GRAPHICS].children
                    if c.title == 'OWNED')
        page.author = 'SOMEONE'
        t2 = self.terminal()
        t2._upload_pending = self.text_upload('OWNED', frames=[b'MINE\x00'])
        self.drive(t2._complete_text_upload())
        self.assertTrue(t2.said('CANNOT REPLACE (NOT OWNER)'), repr(t2.screen))

    def test_an_owner_only_directory_is_respected(self):
        """⚠ THE DIVERGENCE. `open_upload: false` on a directory inside an open
        parent means "closed, stop inheriting" — it is exactly what a user sets to
        keep their own space private inside the open Jungle. The terminal's own
        permission walk only ever looked for a TRUE and kept going past a FALSE,
        so it found the Jungle's TRUE above and allowed the write that the C64 and
        the web client both refused."""
        self.directory.pages[GRAPHICS].open_upload = False
        t = self.terminal()
        t._upload_pending = self.text_upload('SNEAKY')
        self.drive(t._complete_text_upload())
        self.assertTrue(t.said('UPLOAD NOT PERMITTED'), repr(t.screen))
        self.assertIsNone(self.entry('SNEAKY'), 'a closed directory was written to')

    def test_the_owner_may_still_write_to_their_own_closed_directory(self):
        """The other half of the same rule — a user must not be locked out of
        their own space. Without this the test above would pass for a gate that
        simply refuses everyone."""
        page = self.directory.pages[GRAPHICS]
        page.open_upload = False
        page.author = USER
        t = self.terminal()
        t._upload_pending = self.text_upload('MYOWN')
        self.drive(t._complete_text_upload())
        self.assertIsNotNone(self.entry('MYOWN'), repr(t.screen))

    def test_an_action_type_is_refused_by_the_writer(self):
        """An 'A' is native code the client executes on arrival (§7.4.1). The
        terminal refuses it at the PAGE TYPE prompt as well; this asserts the
        floor beneath that, so removing the prompt check could not silently
        reopen it."""
        t = self.terminal()
        t._upload_pending = self.text_upload('EVIL', page_type='A')
        self.drive(t._complete_text_upload())
        self.assertTrue(t.said('INVALID PAGE TYPE'), repr(t.screen))
        self.assertIsNone(self.entry('EVIL'), 'an executable reached the tree')

    def test_a_full_directory_is_refused(self):
        """11 entries is the limit the client can render (§7.2). The terminal
        checks at the UPLD prompt, but the writer is what actually holds it —
        between the prompt and the SEND, another session can fill the last slot."""
        page = self.directory.pages[GRAPHICS]
        while len(page.children) < 11:
            p = srv.CompunetPage(page_num=self.directory.next_page_num(),
                                 title='FILLER%d' % len(page.children),
                                 page_type='T', size=1, author=USER,
                                 price=0, life=1)
            p.parent = page
            page.children.append(p)
        t = self.terminal()
        t._upload_pending = self.text_upload('TOOMANY')
        self.drive(t._complete_text_upload())
        self.assertTrue(t.said('DIRECTORY FULL'), repr(t.screen))
        self.assertIsNone(self.entry('TOOMANY'))


class SharedWriterIsActuallyShared(TerminalTestCase):
    """The point of the merge, asserted directly: the terminal and the protocol
    bindings must produce the SAME page from the same upload. A test that only
    checked the terminal looked reasonable for years while the two copies drifted
    apart in four ways."""

    def test_the_terminal_and_binding_a_write_the_same_page(self):
        t = self.terminal()
        t._upload_pending = self.text_upload('SAMEPAGE')
        self.drive(t._complete_text_upload())
        from_terminal = dict(self.entry('SAMEPAGE'))

        s = srv.CompunetSession(self.directory)
        s.user_id = USER
        s.client_ip = 'test'
        s.current_page = self.directory.pages[GRAPHICS]
        s._complete_content_upload(self.text_upload('SAMEPAGE'))
        from_binding = dict(self.entry('SAMEPAGE'))

        # The upload time and the page number legitimately differ between the two
        # writes; nothing else may.
        for key in ('uploaded', 'page_num'):
            from_terminal.pop(key, None)
            from_binding.pop(key, None)
        self.assertEqual(from_terminal, from_binding)


if __name__ == '__main__':
    unittest.main(verbosity=2)
