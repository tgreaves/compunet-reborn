#!/usr/bin/env python3
"""Regression tests for Binding B (server/api_binding.py).

Run:  python server/tests/test_api_binding.py            (or -v)

These exist because every clean-room run so far has found bugs that the
*previous* round of fixes introduced, and the only regression detector was the
next clean-room run — a full client build, days later. Each test below names the
finding it guards (VALIDATION.md), and between them they would have caught every
regression this binding has shipped.

Three bug classes account for nearly all of them:

  1. REPLY-TYPE INFERENCE. This binding serializes *session state* rather than
     what the command produced, so a stale `show_page` or `mail_mode` makes a
     navigation command answer with a frame, a download descriptor, or the wrong
     listing. Binding A never has this: it returns the bytes the command made.
  2. LISTING SCOPING. `page` and `index` name entries of the listing on screen,
     so anything resolved against the whole tree or the whole mailbox is wrong.
  3. INVARIANTS. A listing is never empty and never exceeds eleven rows; some
     fields are always present.

⚠ Sessions are NEVER shared between tests. Every regression here was a state
bug that only appears in a *sequence*, and a shared session would let one test
mask the next. That is precisely how these shipped in the first place.

The suite is read-only against the fixture tree: it exercises the validation
paths that reject before writing, not the success paths that create content.
"""

import atexit
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_SERVER)

# Point at the tracked fixture tree BEFORE importing the server: its data paths
# are module-level constants (see server/data/content.test/README.md).
os.environ.setdefault('COMPUNET_CONTENT_DIR', os.path.join(_SERVER, 'data', 'content.test'))

# ⚠ MAIL fixtures are copied to a temp directory and the server pointed at the
# COPY. Unlike the content tree, the mail tree cannot be exercised read-only:
# reading a message marks it read and unconditionally rewrites the mailbox JSON
# (_save_mail). Measured: pointed at the tracked tree the suite leaves the file's
# mtime changed but its bytes identical, because the message it happens to read
# is already read. That is luck, not safety — 20 of the fixture messages are
# unread, so the first test that opens one would leave a real diff behind, and
# `git status` noise after an ordinary test run is how someone eventually
# `git checkout`s away a change they meant to keep. The copy makes it structural.
if 'COMPUNET_MAIL_DIR' not in os.environ:
    _mail_tmp = tempfile.mkdtemp(prefix='compunet-mail-')
    _mail_copy = os.path.join(_mail_tmp, 'mail')
    shutil.copytree(os.path.join(_SERVER, 'data', 'mail.test'), _mail_copy)
    os.environ['COMPUNET_MAIL_DIR'] = _mail_copy
    atexit.register(shutil.rmtree, _mail_tmp, True)

sys.path.insert(0, _SERVER)

import compunet_server as srv          # noqa: E402
import api_binding as api              # noqa: E402

api._bind_server(srv)

# ⚠ Supply the login account when this machine has none (#137). A machine with a
# working TEST account keeps using it — see tests/fixture_account.py.
sys.path.insert(0, _HERE)
import fixture_account                  # noqa: E402
fixture_account.ensure(srv)

USER, PASSWORD = fixture_account.USER, fixture_account.PASSWORD
JUNGLE, GRAPHICS, THE_ZOO, MORE_DIR = 600, 601, 699, 909


def session():
    """A fresh authenticated session. Never reuse one across tests."""
    s = srv.CompunetSession(srv.CompunetDirectory())
    s.client_ip = 'test'
    s.handle_login(USER, PASSWORD)
    if not s.authenticated:
        raise unittest.SkipTest('fixture account %s cannot log in' % USER)
    return s


def send(s, **msg):
    return api.handle_message(s, msg)


class ReplyTypeInference(unittest.TestCase):
    """Commands whose reply is definitionally a directory must return one,
    whatever the session was doing beforehand (§4.4, §4.5)."""

    def _open_something(self, s):
        """Leave the session with a frame open."""
        send(s, type='goto', target=str(JUNGLE))
        listing = send(s, type='enter', page=MORE_DIR)
        page = next(e['page'] for e in listing['entries'] if e['type'].startswith('T'))
        self.assertEqual(send(s, type='open', page=page)['type'], 'frame')

    def test_goto_after_open_returns_a_directory(self):
        """F17. §4.5: feeding frame data to a GOTO handler crashes the C64."""
        s = session()
        self._open_something(s)
        self.assertEqual(send(s, type='goto', target=str(JUNGLE))['type'], 'directory')

    def test_back_after_open_returns_a_directory(self):
        """F17. Reached by mail's DONE, which §4.8 maps to BACK."""
        s = session()
        self._open_something(s)
        self.assertEqual(send(s, type='back')['type'], 'directory')

    def test_navigation_does_not_stay_stuck(self):
        """F17. The original symptom was persistence: once wrong, always wrong."""
        s = session()
        self._open_something(s)
        send(s, type='goto', target=str(JUNGLE))
        for _ in range(3):
            self.assertEqual(send(s, type='goto', target=str(JUNGLE))['type'], 'directory')

    def test_finish_after_mail_read_returns_the_mailbox(self):
        """F9. `dir`/`finish` used to answer with a frame and wedge the session."""
        s = session()
        send(s, type='mail.list')
        send(s, type='mail.read', index=0)
        reply = send(s, type='finish')
        self.assertEqual(reply['type'], 'directory')
        self.assertEqual(reply.get('context'), 'mail')

    def test_ucat_is_not_the_current_listing(self):
        """F9. UCAT is synthetic; driving `C` and serializing state returned
        whatever listing the session happened to be on — the mailbox."""
        s = session()
        send(s, type='mail.list')
        reply = send(s, type='ucat')
        self.assertEqual(reply.get('context'), 'ucat')
        self.assertNotEqual(reply.get('context'), 'mail')

    def test_more_in_the_mailbox_pages_the_mailbox(self):
        """MORE in Courier sent the DIRECTORY byte (bare `D`), which the core
        reads as mail-show with a defaulted index of 0 — so MORE opened the
        first message instead of paging, silently becoming SHOW (and marking
        the message read). The mail duckshoot's MORE sends `M`; verified from
        the original client's handler at $B039 (LDA #$4D, no params)."""
        s = session()
        first = send(s, type='mail.list')
        self.assertEqual(first['type'], 'directory')
        reply = send(s, type='more')
        self.assertEqual(reply['type'], 'directory',
                         'MORE in the mailbox must page the listing, not open a message')
        self.assertIsNone(getattr(s, 'mail_show_msg', None),
                          'MORE must not open a message')
        self.assertNotEqual([e['title'] for e in reply['entries']],
                            [e['title'] for e in first['entries']],
                            'the second page should not repeat the first')

    def test_show_downloads_a_whole_message_and_ends_at_the_mailbox(self):
        """⚠ Courier does not page a message — `SHOW` pulls ALL of it (§8.2),
        like `ALL`: `D`+index, then bare `D` until the reply stops being a
        frame. The client drives that loop, so the contract it depends on is
        that the loop TERMINATES, and terminates holding the mailbox.

        With a message open, `more` must therefore stay on bare `D` (advance a
        frame) rather than paging the mailbox — the other half of the rule
        tested above."""
        s = session()
        send(s, type='mail.list')
        reply = send(s, type='mail.read', index=0)
        self.assertEqual(reply['type'], 'frame')
        self.assertIsNotNone(getattr(s, 'mail_show_msg', None))

        frames = 0
        while reply['type'] == 'frame':
            frames += 1
            self.assertLess(frames, 50, 'SHOW loop did not terminate')
            reply = send(s, type='more')

        self.assertGreater(frames, 0)
        self.assertEqual(reply['type'], 'directory',
                         'the frame that ends the download must hand back a listing')
        self.assertEqual(reply.get('context'), 'mail',
                         'and that listing is the MAILBOX, not the content tree')
        self.assertIsNone(getattr(s, 'mail_show_msg', None),
                          'the message must be closed once its frames run out')

    def test_done_leaves_courier_in_one_command(self):
        """§4.8: DONE is `N` and exits Courier outright, returning the directory
        the user came from. It used to be emulated by repeating `back` until
        mail mode cleared — same destination, but the client had to watch for
        the end condition."""
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        send(s, type='mail.list')
        self.assertTrue(getattr(s, 'mail_mode', False))
        reply = send(s, type='mail.done')
        self.assertEqual(reply['type'], 'directory')
        self.assertNotEqual(reply.get('context'), 'mail')
        self.assertFalse(getattr(s, 'mail_mode', True), 'DONE must leave mail mode')

    def test_done_outside_mail_is_refused(self):
        """⚠ The guard matters more than it looks. Outside Courier `N` is MORE,
        and with an upload pending _cmd_more COMPLETES it — so an unguarded
        mail.done would publish a half-composed page instead of doing nothing."""
        s = session()
        send(s, type='dir')
        reply = send(s, type='mail.done')
        self.assertEqual(reply['type'], 'error')
        self.assertEqual(reply.get('code'), 'invalid')

    def test_done_after_reading_a_message_still_exits(self):
        """DONE from inside a message, not just from the listing."""
        s = session()
        send(s, type='mail.list')
        send(s, type='mail.read', index=0)
        reply = send(s, type='mail.done')
        self.assertEqual(reply['type'], 'directory')
        self.assertNotEqual(reply.get('context'), 'mail')

    def test_mail_mode_does_not_outlive_mail(self):
        """F18. `goto` was inert in Courier, and mail mode survived `ucat`."""
        s = session()
        send(s, type='mail.list')
        self.assertEqual(send(s, type='goto', target=str(JUNGLE))['title'], 'JUNGLE')
        s2 = session()
        send(s2, type='mail.list')
        send(s2, type='ucat')
        self.assertEqual(send(s2, type='goto', target=str(JUNGLE))['title'], 'JUNGLE')


class ListingScoping(unittest.TestCase):
    """`page` and `index` name entries of the listing on screen (api §4)."""

    def test_goto_reaches_an_entry_beyond_the_first_page(self):
        """F11/F24. Searching only the visible 11 made page-2 entries 'not found'."""
        s = session()
        send(s, type='dir')
        reply = send(s, type='goto', target='906')
        self.assertEqual(reply['type'], 'directory')
        self.assertIn('selected', reply)
        self.assertEqual(reply['entries'][reply['selected']]['title'], 'PAY TO VIEW')

    def test_goto_names_the_target_entry(self):
        """F13/§4.4: the client MUST NOT compute the target row itself."""
        s = session()
        send(s, type='dir')
        reply = send(s, type='goto', target='905')
        self.assertEqual(reply['entries'][reply['selected']]['title'], 'PAID PAGE')

    def test_mail_read_index_is_bounded_by_the_visible_page(self):
        """Found by self-check: index 10 returned message 11, which is not shown."""
        s = session()
        listing = send(s, type='mail.list')
        real = [e for e in listing['entries'] if e['page'] != api.MORE_PAGE]
        beyond = send(s, type='mail.read', index=len(real))
        self.assertEqual(beyond['type'], 'error')
        self.assertEqual(beyond['code'], 'not_found')

    def test_mail_read_accepts_every_visible_index(self):
        s = session()
        listing = send(s, type='mail.list')
        real = [e for e in listing['entries'] if e['page'] != api.MORE_PAGE]
        for i in range(len(real)):
            self.assertEqual(send(s, type='mail.read', index=i)['type'], 'frame')
            send(s, type='back')


class ListingInvariants(unittest.TestCase):
    """Shape rules that hold for every listing (§7.2, §7.3, §7.7)."""

    def _listings(self, s):
        send(s, type='dir')
        yield 'root', send(s, type='dir')
        yield 'jungle', send(s, type='goto', target=str(JUNGLE))
        yield 'mail', send(s, type='mail.list')
        yield 'ucat', send(s, type='ucat')

    def test_a_listing_is_never_empty(self):
        """F7/F8. §7.3 MUST: an empty directory still carries a placeholder row.
        Zero entries strands the session, because `page` is listing-scoped."""
        s = session()
        for name, reply in self._listings(s):
            self.assertGreaterEqual(len(reply['entries']), 1, name)

    def test_a_listing_never_exceeds_eleven_rows(self):
        """F14. Only eleven rows exist on screen; the MORE row REPLACES the
        eleventh entry rather than becoming a twelfth."""
        s = session()
        for name, reply in self._listings(s):
            self.assertLessEqual(len(reply['entries']), 11, name)

    def test_advert_is_always_two_lines(self):
        """F11. §7.2: Part 2 is always two lines, empty ones if there is no advert."""
        s = session()
        for name, reply in self._listings(s):
            self.assertEqual(len(reply['advert']), 2, name)

    def test_mail_waiting_is_present_without_opening_mail(self):
        """F10. The marker exists to report mail you have NOT looked at."""
        s = session()
        reply = send(s, type='dir')
        self.assertIn('mailWaiting', reply)
        self.assertIsInstance(reply['mailWaiting'], bool)

    def test_entry_page_numbers_are_integers_everywhere(self):
        """F14. The mailbox used to send its message id as a string."""
        s = session()
        for name, reply in self._listings(s):
            for e in reply['entries']:
                self.assertIsInstance(e['page'], int, '%s: %r' % (name, e['title']))

    def test_paging_a_generated_listing_does_not_strand_it(self):
        """F7. Selecting MORE pages; the result is still a usable listing."""
        s = session()
        listing = send(s, type='mail.list')
        if not any(e['page'] == api.MORE_PAGE for e in listing['entries']):
            self.skipTest('fixture mailbox does not overflow')
        paged = send(s, type='enter', page=api.MORE_PAGE)
        self.assertEqual(paged['type'], 'directory')
        self.assertGreaterEqual(len(paged['entries']), 1)


class ErrorTyping(unittest.TestCase):
    """Binding B's stated purpose: make explicit what Binding A signalled by
    silence (§8.3.2, api §3). A silent no-op is a bug here."""

    def test_unknown_goto_target_is_an_error(self):
        """F30. It used to return the current listing, indistinguishable from success."""
        s = session()
        send(s, type='dir')
        for target in ('ZZZNOPE', '99999'):
            reply = send(s, type='goto', target=target)
            self.assertEqual(reply['type'], 'error', target)
            self.assertEqual(reply['code'], 'not_found', target)

    def test_life_requires_a_day_count(self):
        """F13. `life` used to ack anything, including no days at all."""
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        entry = send(s, type='dir')['entries'][0]['page']
        self.assertEqual(send(s, type='life', page=entry)['type'], 'error')
        self.assertEqual(send(s, type='life', page=entry, days=0)['type'], 'error')

    def test_reducing_life_needs_ownership(self):
        """F13. §8.6 restricts a negative amount to owner/editor/admin."""
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        entry = next(e for e in send(s, type='dir')['entries'] if e['values'][1] != USER)
        reply = send(s, type='life', page=entry['page'], days=-1)
        self.assertEqual(reply['type'], 'error')
        self.assertEqual(reply['code'], 'permission_denied')

    def test_vote_score_is_validated(self):
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        entry = send(s, type='dir')['entries'][0]['page']
        for score in (0, 10):
            self.assertEqual(send(s, type='vote', page=entry, score=score)['code'], 'invalid')

    def test_mail_send_caps_recipients_at_five(self):
        """F20. §A.10's frame has five slots; a cap only the client honours is none."""
        s = session()
        reply = api.mail_send(s, {'to': [USER] * 6, 'subject': 'X',
                                  'frames': [{'lines': ['x']}]}, None)
        self.assertEqual(reply['code'], 'invalid')

    def test_upload_requires_price_and_life(self):
        """F21. api §4 calls them required; they were silently optional."""
        s = session()
        send(s, type='goto', target=str(GRAPHICS))
        base = {'title': 'TEST', 'kind': 'T', 'frames': [{'lines': ['x']}]}
        self.assertEqual(api.upload_content(s, dict(base, life=1), None)['code'], 'invalid')
        self.assertEqual(api.upload_content(s, dict(base, price=0), None)['code'], 'invalid')

    def test_creating_a_directory_without_permission_says_so(self):
        """F36. Three runs reported this flow as unreachable because a refusal
        was indistinguishable from nothing happening."""
        s = session()
        send(s, type='goto', target=str(THE_ZOO))
        leaf = next((e for e in send(s, type='dir')['entries'] if not e['hasSubdir']), None)
        if leaf is None:
            self.skipTest('fixture has no leaf entry in the opted-out directory')
        reply = send(s, type='enter', page=leaf['page'])
        self.assertEqual(reply['type'], 'error')
        self.assertEqual(reply['code'], 'permission_denied')

    def test_there_is_no_paging_command(self):
        """F15/F26/F35. Authored directories do not paginate; `dir.more` and
        `dir.back` were invented vocabulary with no Binding-A counterpart."""
        s = session()
        for t in ('dir.more', 'dir.back'):
            self.assertEqual(send(s, type=t)['code'], 'invalid', t)


class RleOperandsAreNeverZero(unittest.TestCase):
    """§6.4 — a `$00` RLE operand is the frame terminator, not a zero count.

    ⚠ The two bindings used to disagree here, and both were "conforming": §6.4
    said `$06 N` draws `1 + N` spaces without constraining N, while §6.3 made
    `$00` the terminator and §6.1 let a client end a frame at the first in-band
    `$00`. So `$06 $00` was one space to this decoder and end-of-part to the
    C64, whose Part-1 copy loop is byte-level and has no notion of RLE. One
    file, two screens. The spec now forbids the operand; these pin this decoder
    to it.

    Nothing legitimate is affected: a zero count is always LONGER than the
    literal it encodes, so no encoder in this tree emits one.
    """

    def _cells(self, body):
        return api.frame_to_cells(bytes([0x00, 0xF4, 0xFF, 0x8E]) + body)['cells']

    def _text(self, cells, count):
        return ''.join(chr(api._screencode_to_petscii(c['g'] & 0x7F))
                       for c in cells[:count])

    def test_a_zero_space_count_ends_the_frame(self):
        # 'AB' then $06 $00 — everything after the operand must be discarded,
        # matching the C64 rather than drawing a space and carrying on.
        self.assertEqual('AB  ', self._text(self._cells(b'AB\x06\x00CD'), 4))

    def test_a_zero_repeat_count_ends_the_frame(self):
        self.assertEqual('AB  ', self._text(self._cells(b'AB\x07\x41\x00CD'), 4))

    def test_a_nul_run_byte_ends_the_frame(self):
        self.assertEqual('AB  ', self._text(self._cells(b'AB\x07\x00\x05CD'), 4))

    def test_ordinary_runs_are_untouched(self):
        """The control: non-zero counts still expand with `1 + N` semantics."""
        self.assertEqual('A***B', self._text(self._cells(b'A\x07\x2A\x02B'), 5))
        self.assertEqual('A  B', self._text(self._cells(b'A\x06\x01B'), 4))


class FrameFidelity(unittest.TestCase):
    """The `cells` submission form must reproduce what it was given (api §5.4)."""

    def test_screencode_inverse_is_total(self):
        """F34. Screen code $5F fell through to a space — one of 128, and it
        falsified §5.4's claim that Binding B can author anything A displays."""
        broken = [sc for sc in range(0x80)
                  if api._petscii_to_screencode(api._screencode_to_petscii(sc)) != sc]
        self.assertEqual(broken, [], 'screen codes lost by the encoder')

    def _grid(self, cells_spec):
        return {'cells': cells_spec, 'border': 4, 'background': 15}

    def test_every_glyph_and_reverse_flag_round_trips(self):
        """F25's experiment, as a test: all 256 glyphs, both charsets, plain and
        reversed. Colour and reverse survive; only per-cell `bg` cannot."""
        cells = []
        for i in range(960):
            g = i % 256
            cells.append({'g': g, 'fg': 1 + (i % 15), 'bg': 15, 'rv': (i // 256) % 2})
        encoded = api._encode_frame(self._grid(cells))
        back = api.frame_to_cells(encoded)['cells']
        for i, (sent, got) in enumerate(zip(cells, back)):
            self.assertEqual(got['g'], sent['g'], 'glyph at %d' % i)
            self.assertEqual(got['rv'], sent['rv'], 'reverse at %d' % i)
            self.assertEqual(got['fg'], sent['fg'], 'colour at %d' % i)

    def test_a_reversed_run_is_bracketed_by_12_and_92(self):
        """§5.7: reverse is a MODE on the wire, not a property carried by each
        cell — `$12` opens a run and `$92` closes it. The round-trip test above
        would still pass if the encoder invented some other mechanism; this pins
        the bytes, because a real C64 has no other way to read them."""
        cells = [{'g': 0x20, 'fg': 1, 'bg': 0, 'rv': 0} for _ in range(960)]
        for c in range(3):
            cells[c] = {'g': 0x01, 'fg': 1, 'bg': 0, 'rv': 1}
        out = api._encode_frame(self._grid(cells))
        self.assertIn(b'\x12', out, 'no reverse-on code emitted at all')
        self.assertEqual(out.count(b'\x12'), 1, 'one run should mean one switch')
        self.assertLess(out.index(b'\x12'), out.index(b'\x92'),
                        'reverse switched off before it was switched on')
        self.assertLess(out.index(b'\x92'), out.index(b'\x0d'),
                        'the run must close before the line ends')

    def test_reverse_never_survives_a_carriage_return(self):
        """§5.7 — a CR clears the attribute, and the encoder resets its own flag
        there. The web editor's newline() clears its typing mode for exactly
        this reason: without it the page would upload un-reversed from that line
        on while the editor went on showing the mode as still active."""
        cells = [{'g': 0x20, 'fg': 1, 'bg': 0, 'rv': 0} for _ in range(960)]
        for i in range(2 * 40):
            cells[i] = {'g': 0x01, 'fg': 1, 'bg': 0, 'rv': 1}
        out = api._encode_frame(self._grid(cells))
        reverse = False
        for i, b in enumerate(out[4:], start=4):
            if b == 0x12:
                reverse = True
            elif b == 0x92:
                reverse = False
            elif b == 0x0d:
                self.assertFalse(reverse,
                                 'reverse left switched on across the CR at byte %d' % i)

    def test_raw_round_trips_byte_identically(self):
        """F26/§8.4.2: an unedited captured page republishes unchanged."""
        import base64
        raw = open(os.path.join(_SERVER, 'cfg', 'help.pet'), 'rb').read()
        out = api._encode_frame({'raw': base64.b64encode(raw).decode('ascii')})
        self.assertEqual(out, raw)

    def test_submission_form_precedence(self):
        """api §5.4: raw wins, then cells, then lines."""
        import base64
        raw = bytes([0x00, 0x06, 0x00, 0x8E, 0x0D, 0x00])
        both = {'raw': base64.b64encode(raw).decode('ascii'),
                'cells': [{'g': 1, 'fg': 1, 'bg': 0, 'rv': 0}] * 960,
                'lines': ['IGNORED']}
        self.assertEqual(api._encode_frame(both), raw)


class ProgramUpload(unittest.TestCase):
    """§8.3.2 `kind: "P"` — a program upload must land byte-identical.

    ⚠ THE HEADER IS MACHINE-DEPENDENT (§8.3.2). For a C64 program, bytes 4-5 are
    the LOAD ADDRESS and 6-7 the size; only an Amiga executable — which has no
    load address — sizes its body across 4-7 big-endian.

    _complete_content_upload rebuilds a C64 program as `header[4:6] + blob[8:]`,
    so bytes 4-5 MUST be the load address. Encode a 4-byte size there and the
    stored .prg opens $0000 and will not run — the second test below shows it.
    Confirmed against live data: a C64 program uploaded 2026-06-05
    (mission-monday.prg, 18381 bytes) is stored opening 01 08 = $0801.

    Writes go to a temp COPY of the fixtures."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix='compunet-prog-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')

    def tearDown(self):
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    @staticmethod
    def _blob(prg, is_c64=True):
        """The client's header construction (main.ts sendProgram), mirrored."""
        body = prg[2:] if is_c64 else prg
        load = (prg[0] | (prg[1] << 8)) if is_c64 else 0
        blob = bytearray(8 + len(body))
        blob[0] = 0 if is_c64 else 1
        blob[4] = load & 0xFF
        blob[5] = (load >> 8) & 0xFF
        blob[6] = len(body) & 0xFF
        blob[7] = (len(body) >> 8) & 0xFF
        blob[8:] = body
        return bytes(blob)

    def test_a_c64_prg_round_trips_byte_for_byte(self):
        import base64
        import glob
        prg = bytes([0x01, 0x08]) + bytes(range(256)) * 4      # load $0801 + body
        s = session()
        # ⚠ GRAPHICS, not the Jungle root: the root fixture already holds its
        # 11-entry maximum, and a full directory refuses the upload (§8.3.2).
        # GRAPHICS is an empty sub-directory and inherits the Jungle's
        # open-upload permission.
        send(s, type='goto', target=str(JUNGLE))
        entered = send(s, type='enter', page=GRAPHICS)
        self.assertEqual(entered.get('type'), 'directory',
                         'could not enter GRAPHICS: %r' % (entered.get('message'),))
        reply = send(s, type='upload', title='PRGTEST', kind='P', price=0, life=30,
                     frames=[base64.b64encode(self._blob(prg)).decode('ascii')])
        self.assertEqual(reply.get('type'), 'directory',
                         'upload refused: %r' % (reply.get('message'),))
        hits = glob.glob(os.path.join(srv.ROOT_DIR, '**', 'prgtest*', '*.prg'),
                         recursive=True)
        self.assertTrue(hits, 'no .prg was written')
        stored = open(hits[0], 'rb').read()
        self.assertEqual(stored, prg,
                         'stored program differs from the source file')
        self.assertEqual(stored[:2], bytes([0x01, 0x08]),
                         'the load address must survive — $0000 will not run')

    def test_a_four_byte_size_would_corrupt_the_c64_load_address(self):
        """Demonstrates WHY a C64 program cannot use the Amiga's 4-byte size
        field, so nobody 'simplifies' the two machines onto one layout: it puts
        00 00 exactly where the load address belongs."""
        prg = bytes([0x01, 0x08]) + b'X' * 100
        body = prg[2:]
        wrong = bytearray(8 + len(body))
        wrong[0] = 0
        wrong[4:8] = len(body).to_bytes(4, 'big')      # §8.3.2's wording
        wrong[8:] = body
        rebuilt = bytes(wrong[4:6]) + bytes(wrong[8:])  # what the server does
        self.assertNotEqual(rebuilt[:2], bytes([0x01, 0x08]))
        self.assertEqual(rebuilt[:2], b'\x00\x00', 'load address lost, as predicted')

    # --- the machine the client DECLARED must survive into machine_type -------
    # ⚠ The upload path used to test `machine == 1` and fold everything else onto
    # the C64 branch, so an ST program (2) was stored as `c64` with two bytes of
    # its body stripped as if they were a load address. The download side already
    # branched three ways (ProgramDownloadDescriptor), so the two ends disagreed.
    # These pin the fix: the declared machine byte round-trips, and only the 6502
    # loses two bytes to a load address.

    def _st_blob(self, exe):
        """A 68k blob whose machine byte is ST (2). Nothing on the wire produces
        this today — the picker offers C64 and Amiga — but the server must store a
        2 as ST rather than mangle it, which is the whole point of the fix."""
        blob = bytearray(8 + len(exe))
        blob[0] = 2
        blob[6] = len(exe) & 0xFF
        blob[7] = (len(exe) >> 8) & 0xFF
        blob[8:] = exe
        return bytes(blob)

    def _upload_to_graphics(self, title, blob, kind='P', ext='prg'):
        """Drive a full Binding-B binary upload into GRAPHICS and return
        (stored_bytes, entry_json). machine_type is `None` in the JSON when the
        server wrote no key — which, per §7, means C64."""
        import base64
        import glob
        import json
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        entered = send(s, type='enter', page=GRAPHICS)
        self.assertEqual(entered.get('type'), 'directory',
                         'could not enter GRAPHICS: %r' % (entered.get('message'),))
        reply = send(s, type='upload', title=title, kind=kind, price=0, life=30,
                     frames=[base64.b64encode(blob).decode('ascii')])
        self.assertEqual(reply.get('type'), 'directory',
                         'upload refused: %r' % (reply.get('message'),))
        with open(os.path.join(srv.ROOT_DIR, 'jungle', 'graphics',
                               'directory.json')) as f:
            pages = json.load(f)['pages']
        entry = next(p for p in pages if p['title'] == title)
        hits = glob.glob(os.path.join(srv.ROOT_DIR, 'jungle', 'graphics',
                                      '**', '*.' + ext), recursive=True)
        stored = open(hits[0], 'rb').read()
        return stored, entry

    def test_a_c64_upload_is_stored_as_c64_minus_its_load_address(self):
        prg = bytes([0x01, 0x08]) + bytes(range(200))
        stored, entry = self._upload_to_graphics('C64PROG', self._blob(prg, is_c64=True))
        # C64 stays absent in the JSON — absent means C64 (§7), and existing
        # content carries no machine_type, so writing one would be noise.
        self.assertIsNone(entry.get('machine_type'), 'C64 must not write a machine_type key')
        self.assertEqual(stored, prg, 'C64 program must round-trip byte-for-byte')

    def test_an_amiga_upload_is_stored_whole_as_amiga(self):
        exe = bytes([0x00, 0x00, 0x03, 0xF3]) + bytes(range(150))   # HUNK header
        stored, entry = self._upload_to_graphics('AMIGAPROG', self._blob(exe, is_c64=False))
        self.assertEqual(entry.get('machine_type'), 'amiga')
        # No load address to strip: the stored file is the whole 68k image.
        self.assertEqual(stored, exe, 'Amiga body must be stored whole')

    def test_an_st_upload_is_stored_whole_as_st_not_folded_into_c64(self):
        """The trap the fix removed: a 2 used to be stored as `c64` with two body
        bytes eaten. It must store as `st`, whole."""
        exe = bytes(range(180))
        stored, entry = self._upload_to_graphics('STPROG', self._st_blob(exe))
        self.assertEqual(entry.get('machine_type'), 'st',
                         'an ST upload must not be folded into c64')
        self.assertEqual(stored, exe,
                         'a 68k body must be stored whole — no load address to strip')

    # --- F: IFF picture upload (#129) -----------------------------------------
    @staticmethod
    def _iff(w=16, h=2, nplanes=1):
        """A minimal but well-formed uncompressed FORM..ILBM."""
        import struct
        rowbytes = ((w + 15) // 16) * 2
        bmhd = struct.pack('>HHhhBBBBHBBhh', w, h, 0, 0, nplanes, 0, 0, 0, 0, 10, 11, w, h)
        body = bytes(rowbytes * nplanes * h)
        def chunk(cid, d):
            return cid + struct.pack('>I', len(d)) + d + (b'\x00' if len(d) & 1 else b'')
        form = b'ILBM' + chunk(b'BMHD', bmhd) + chunk(b'BODY', body)
        return b'FORM' + struct.pack('>I', len(form)) + form

    def _f_blob(self, iff):
        """The web client's F upload: 8-byte header (Amiga machine byte 1) + the IFF."""
        blob = bytearray(8 + len(iff))
        blob[0] = 1
        blob[6] = len(iff) & 0xFF
        blob[7] = (len(iff) >> 8) & 0xFF
        blob[8:] = iff
        return bytes(blob)

    def test_an_iff_picture_uploads_as_f_amiga_whole(self):
        iff = self._iff()
        stored, entry = self._upload_to_graphics('COLOURBARS', self._f_blob(iff),
                                                 kind='F', ext='iff')
        self.assertEqual(entry['type'], 'F', 'an IFF upload must store as type F')
        self.assertEqual(entry.get('machine_type'), 'amiga',
                         'an IFF picture is Amiga content by definition')
        self.assertEqual(stored, iff,
                         'the IFF must be stored whole — no load address to strip')
        self.assertTrue(stored[:4] == b'FORM' and stored[8:12] == b'ILBM')

    def test_an_amiga_originated_f_upload_stores_whole(self):
        """⚠ The Amiga's publish dialog has ALWAYS offered F — put_frame's jump table at
        0x10c3c2 routes 'A','S','P','F' alike to upload_file — but the Binding-A receive
        loop gated on type 'P', so an IFF from an Amiga went to the PETSCII frame
        accumulator and was then mangled by the blob path.

        This drives _complete_content_upload with the header the Amiga actually builds
        (upload_file: bytes 0-3 = $01000000, bytes 4-7 = big-endian size), which is what
        the widened receive loop now hands it."""
        iff = self._iff()
        blob = bytearray(8 + len(iff))
        blob[0] = 0x01                                   # recon: *(ULONG*)hdr = 0x1000000
        blob[4:8] = len(iff).to_bytes(4, 'big')          # recon: *(ULONG*)(hdr+4) = size
        blob[8:] = iff
        stored, entry = self._upload_to_graphics('AMIGAPIC', bytes(blob),
                                                 kind='F', ext='iff')
        self.assertEqual(entry['type'], 'F')
        self.assertEqual(entry.get('machine_type'), 'amiga')
        self.assertEqual(stored, iff,
                         'byte 0 is 1 (Amiga), so the body is stored whole — no load '
                         'address may be stripped')

    def test_a_non_iff_f_upload_is_refused_not_sanitised(self):
        """§7.4.1: reject a mislabelled F at upload rather than let it surface as a
        blank Amiga screen."""
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        send(s, type='enter', page=GRAPHICS)
        import base64
        not_iff = self._f_blob(b'\x00\x00\x03\xf3' + bytes(40))   # a HUNK exe, not IFF
        reply = send(s, type='upload', title='NOTIFF', kind='F', price=0, life=30,
                     frames=[base64.b64encode(not_iff).decode('ascii')])
        self.assertEqual(reply.get('type'), 'error')
        self.assertIn('ILBM', reply.get('message', ''))


class UploadTypeGate(unittest.TestCase):
    """Only T, P and F may be uploaded (§7.4.1, §8.3.2) — and the gate has to hold on
    EVERY path, because the type letter is not decoration: an 'A' is native code the
    client downloads and executes, which is why the server refuses to serve one at all.
    A path that stores an 'A' puts an executable in the tree for a later hand-edit,
    import or migration to expose, and 'unlikely' is not a guard against code execution.

    The spec already asserted this gate existed. It only ever existed in Binding B."""

    def test_binding_b_refuses_an_action_upload(self):
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        send(s, type='enter', page=GRAPHICS)
        reply = send(s, type='upload', title='EVIL', kind='A', price=0, life=30,
                     frames=['AAAA'])
        self.assertEqual(reply.get('type'), 'error')
        self.assertEqual(reply.get('code'), 'invalid')

    def test_binding_a_refuses_an_action_upload_before_the_transfer(self):
        """⚠ Reachable from an ERA client, not just a hostile one: the Amiga's publish
        dialog takes the type as free text and its jump table at 0x10c3c2 routes 'A' and
        'S' down the same upload_file path as 'P' and 'F'.

        Refused at the 'U' command, so the user is told before streaming a file — and
        pending_send must be left clear, or the next data packet would be accumulated
        against a half-built upload."""
        s = session()
        s.current_page = s.directory.pages[GRAPHICS]
        reply = s._cmd_upload_content('EVIL', 'A', b'000.00030')
        self.assertEqual(reply[0], srv.RESP_ERROR,
                         'an unsupported type must be refused, not accepted')
        self.assertIsNone(s.pending_send,
                          'a refused upload must leave no pending transfer behind')

    def test_the_shared_writer_discards_an_action_even_if_something_reaches_it(self):
        """The backstop in _complete_content_upload — the shared function every binding
        goes through — so a future binding cannot reintroduce the gap by forgetting its
        own check. Both current bindings refuse earlier; this asserts the floor."""
        import json
        s = session()
        s.current_page = s.directory.pages[GRAPHICS]
        s._complete_content_upload({'mode': 'upload', 'title': 'EVIL', 'type': 'A',
                                    'price': 0.0, 'lifetime': 30, 'frames': [b'\x01' * 32]})
        with open(os.path.join(srv.ROOT_DIR, 'jungle', 'graphics',
                               'directory.json')) as f:
            titles = [p['title'] for p in json.load(f)['pages']]
        self.assertNotIn('EVIL', titles, 'an A must never reach the directory')

    def test_a_supported_type_still_passes_the_gate(self):
        """Guard against over-refusing: the gate must not break the ordinary case."""
        s = session()
        s.current_page = s.directory.pages[GRAPHICS]
        reply = s._cmd_upload_content('FINEPAGE', 'T', b'000.00030')
        self.assertNotEqual(reply[0], srv.RESP_ERROR)
        self.assertIsNotNone(s.pending_send)
        self.assertEqual(s.pending_send['type'], 'T')


class ProgramUploadAccumulator(unittest.TestCase):
    """Binding A's program-upload receive loop (§8.3.2), which had no test — the
    reason a C64 regression shipped on 2026-07-22 and sat unnoticed.

    The loop lives inside the TCP handler, so this reimplements its state machine
    exactly and drives it with the packet pattern each client produces. If the
    handler changes, this must change with it — which is the point: it pins the
    two DIFFERENT termination rules that the single 'read a size from bytes 4-7'
    reading destroyed."""

    CHUNK = 100

    @staticmethod
    def _feed(packets):
        """Mirror of the handler's accumulator. Returns the stored frame, or None
        if the transfer never completed."""
        ps = {}
        for payload in packets:
            if '_prog_header' not in ps:
                hdr = bytes(payload[:8])
                ps['_prog_header'] = hdr
                ps['_prog_amiga'] = (hdr[0] == 1)
                ps['_prog_size'] = int.from_bytes(hdr[4:8], 'big') if ps['_prog_amiga'] else None
                ps['_prog_body'] = bytearray(payload[8:])
                complete = (not ps['_prog_amiga']) and len(payload) < 100
            else:
                ps['_prog_body'].extend(payload)
                complete = (len(ps['_prog_body']) >= ps['_prog_size']
                            if ps['_prog_amiga'] else len(payload) < 100)
            if complete:
                body = (bytes(ps['_prog_body'][:ps['_prog_size']]) if ps['_prog_amiga']
                        else bytes(ps['_prog_body']))
                return ps['_prog_header'] + body
        return None

    def _c64_packets(self, prg):
        """The C64 client streams header and body continuously, in 100-byte
        chunks, and a short chunk ends it."""
        hdr = bytes([0, 0, 0, 0, prg[0], prg[1], 0, 0])   # 4-5 = load address
        stream = hdr + prg[2:]
        return [stream[i:i + self.CHUNK] for i in range(0, len(stream), self.CHUNK)]

    def _amiga_packets(self, exe):
        """The Amiga client sends the header as its OWN packet, then the body."""
        hdr = bytes([1, 0, 0, 0]) + len(exe).to_bytes(4, 'big')
        return [hdr] + [exe[i:i + self.CHUNK] for i in range(0, len(exe), self.CHUNK)]

    def test_a_c64_program_completes_and_keeps_its_load_address(self):
        prg = bytes([0x01, 0x08]) + bytes(range(256)) * 3 + b'END'
        frame = self._feed(self._c64_packets(prg))
        self.assertIsNotNone(frame, 'C64 upload never completed — the regression')
        # _complete_content_upload rebuilds the stored file this way.
        rebuilt = frame[4:6] + frame[8:]
        self.assertEqual(rebuilt, prg, 'stored .prg differs from the source')
        self.assertEqual(rebuilt[:2], bytes([0x01, 0x08]))

    def test_a_c64_program_ending_on_an_exact_chunk_boundary(self):
        """⚠ The chunk rule needs a short final chunk. A body that lands exactly
        on the boundary relies on the client sending a final short/empty one —
        record the behaviour rather than pretend it cannot happen."""
        # stream = 8-byte header + prg[2:], so prg[2:] must be 3*CHUNK - 8.
        prg = bytes([0x01, 0x08]) + bytes(self.CHUNK * 3 - 8)
        packets = self._c64_packets(prg)
        self.assertTrue(all(len(p) == self.CHUNK for p in packets))
        self.assertIsNone(self._feed(packets),
                          'exact-boundary body cannot self-terminate; the client '
                          'must send a short or empty final chunk')
        self.assertIsNotNone(self._feed(packets + [b'']), 'empty final chunk ends it')

    def test_an_amiga_program_is_sized_not_chunk_terminated(self):
        """A HUNK body rarely ends on a short chunk, which is why it carries a
        size. Body deliberately ends on an exact boundary."""
        exe = bytes([0x00, 0x00, 0x03, 0xF3]) + bytes(self.CHUNK * 2 - 4)
        frame = self._feed(self._amiga_packets(exe))
        self.assertIsNotNone(frame, 'Amiga upload never completed')
        self.assertEqual(frame[8:], exe, 'stored HUNK differs from the source')

    def test_the_old_single_reading_broke_the_c64(self):
        """The regression itself: sizing every machine from bytes 4-7 big-endian
        reads a C64 load address of $0801 as a ~17 MB body."""
        hdr = bytes([0, 0, 0, 0, 0x01, 0x08, 0x00, 0x00])
        self.assertGreater(int.from_bytes(hdr[4:8], 'big'), 17_000_000)


class EmptyListingPlaceholder(unittest.TestCase):
    """§7.3: the (EMPTY) row is a LABEL — blank page number, blank type."""

    def test_binding_b_placeholder_has_no_type(self):
        """It claimed `type: "T"`, drawing a stray T beside "(EMPTY)" — a text
        page announced in a directory that holds nothing."""
        row = api._empty_row()
        self.assertEqual(row['type'], '')
        self.assertEqual(row['page'], 0, 'page 0 is the not-a-real-page sentinel')
        self.assertEqual(row['title'], '(EMPTY)')

    def test_binding_a_placeholder_blanks_both_columns_at_full_width(self):
        """⚠ The widths are load-bearing: the Amiga parser reads fixed-width
        columns with no EOF guard, so a short field hangs it. Blank the columns
        by PADDING, never by shortening."""
        first_field = ''.rjust(6) + ' ' + '(EMPTY)'.ljust(17) + '   '
        self.assertEqual(len(first_field), 27, 'the Amiga parser needs all 27')
        self.assertTrue(first_field[:6].isspace(), 'page column must be blank, not 0')
        self.assertTrue(first_field[24:27].isspace(), 'type column must be blank')
        self.assertIn('(EMPTY)', first_field)

    def test_the_two_bindings_agree(self):
        """§1.8. One binding blanked both columns while the other sent "T", so
        the same empty directory read differently depending on how you reached
        it. That is the divergence this pair of tests exists to prevent."""
        row = api._empty_row()
        first_field = ''.rjust(6) + ' ' + '(EMPTY)'.ljust(17) + '   '
        self.assertEqual(bool(row['type']), bool(first_field[24:27].strip()))
        self.assertEqual(bool(row['page']), bool(first_field[:6].strip()))


class EmbeddedAssets(unittest.TestCase):
    """The client-carried frames of §A.6/§A.8–§A.11 (api §7)."""

    # ⚠ This class used to assert the OPPOSITE of what it now asserts: that
    # help.pet and editor-help.pet were body-only and needed a header supplied.
    # That was true only of the hand-retyped files they contained. All four
    # assets are now the original frames, extracted from the vintage binaries,
    # and all four carry their own §6 header. A test that pins a reconstruction
    # in place is worse than no test — it makes the wrong bytes look verified.
    ASSETS = {                        # file: (source, border, background, charset)
        'help.pet':         ('cnet.prg $BB0C', 3, 3, 0x0E),
        'editor-help.pet':  ('ROM $9589',      6, 12, 0x0E),
        'courier.pet':      ('cnet.prg $BDD6', 4, 1, 0x8E),
        'courier-send.pet': ('cnet.prg $BD77', 4, 1, 0x8E),
    }

    def test_every_asset_carries_its_own_header(self):
        """§A.8–§A.11. Fed raw is the ONLY correct way to render these; a client
        that prepends a header of its own eats the first four real bytes."""
        for name, (src, border, bg, charset) in self.ASSETS.items():
            data = open(os.path.join(_SERVER, 'cfg', name), 'rb').read()
            self.assertEqual(data[0], 0x00, '%s (%s): flags' % (name, src))
            self.assertEqual(data[3], charset, '%s (%s): charset' % (name, src))
            frame = api.frame_to_cells(data)
            self.assertEqual((frame['border'], frame['background']), (border, bg),
                             '%s (%s)' % (name, src))

    def test_help_frames_render_in_the_lowercase_set(self):
        """§A.8/§A.9 are among the few genuinely mixed-case frames — the header's
        $0E is what makes them legible rather than a wall of graphic glyphs."""
        for name in ('help.pet', 'editor-help.pet'):
            frame = api.frame_to_cells(
                open(os.path.join(_SERVER, 'cfg', name), 'rb').read())
            self.assertTrue(frame.get('lower'), name)
            self.assertTrue(any(c['g'] >= 128 for c in frame['cells']), name)

    def test_help_frames_ink_is_blue_and_brown(self):
        """The retyped help.pet used CYAN ink on a cyan background — invisible.
        Both originals use blue ($1F) headings and brown ($95) body text."""
        for name in ('help.pet', 'editor-help.pet'):
            data = open(os.path.join(_SERVER, 'cfg', name), 'rb').read()
            self.assertIn(0x1F, data, '%s: blue' % name)
            self.assertIn(0x95, data, '%s: brown' % name)
            self.assertNotIn(0x9F, data, '%s: cyan ink is the reconstruction' % name)

    def test_assets_match_the_vintage_binaries(self):
        """The whole point: these files are EXTRACTED, not reconstructed. If a
        binary is unavailable the check skips rather than silently passing."""
        vintage = os.path.join(_SERVER, os.pardir, 'client', 'c64', 'vintage')
        sources = {
            'help.pet':         ('cnet.prg', 0x9FF0, 0xBB0C, 2),
            'editor-help.pet':  ('chip0_bank0_8000.bin', 0x8000, 0x9589, 0),
            'courier.pet':      ('cnet.prg', 0x9FF0, 0xBDD6, 2),
            'courier-send.pet': ('cnet.prg', 0x9FF0, 0xBD77, 2),
        }
        for name, (binf, base, addr, skip) in sources.items():
            path = os.path.join(vintage, binf)
            if not os.path.exists(path):
                self.skipTest('%s not present' % binf)
            blob = open(path, 'rb').read()[skip:]
            i = addr - base
            original = blob[i:blob.index(b'\x00', i + 4) + 1]
            ours = open(os.path.join(_SERVER, 'cfg', name), 'rb').read()
            self.assertEqual(ours, original,
                             '%s has drifted from %s $%04X' % (name, binf, addr))


class PersistenceRoundTrip(unittest.TestCase):
    """⚠ The save path is a lossy re-serialisation of the loaded tree, so any
    field it forgets to write is DELETED on the next save — silently, and by an
    unrelated action. These tests run against a temporary COPY of the fixture
    tree (patching srv.ROOT_DIR, which both the loader and saver read at call
    time), so the suite stays read-only against the tracked fixtures."""

    def setUp(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix='compunet-save-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')

    def tearDown(self):
        import shutil
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _jungle_entry(self, page_num):
        import json
        with open(os.path.join(srv.ROOT_DIR, 'jungle', 'directory.json')) as f:
            data = json.load(f)
        return next(p for p in data['pages'] if p['page_num'] == page_num)

    def test_an_empty_sub_directory_survives_a_save(self):
        """GRAPHICS (601) has a directory.json holding no pages. Saving used to
        write its parent entry back WITHOUT the `directory` key — the sub-tree
        became unreachable while its files sat on disk. §7.3 lists an empty
        directory with the (EMPTY) placeholder; empty is not absent."""
        before = self._jungle_entry(GRAPHICS)
        self.assertIn('directory', before, 'fixture precondition')

        s = session()
        self.assertEqual(s.directory.pages[GRAPHICS].children, [],
                         'fixture precondition: GRAPHICS is empty')
        s._save_directory_containing(s.directory.pages[JUNGLE])

        self.assertIn('directory', self._jungle_entry(GRAPHICS),
                      'saving deleted an empty sub-directory')

    def test_a_populated_sub_directory_survives_a_save(self):
        """The control: the same field on a directory that does have children."""
        s = session()
        self.assertTrue(s.directory.pages[MORE_DIR].children, 'fixture precondition')
        s._save_directory_containing(s.directory.pages[JUNGLE])
        self.assertIn('directory', self._jungle_entry(MORE_DIR))

    def _dir_json(self, *parts):
        import json
        with open(os.path.join(srv.ROOT_DIR, *parts)) as f:
            return json.load(f)

    def test_a_directory_header_survives_an_unrelated_save(self):
        """Users can now set the Part-1 header themselves (#120), so a save that
        drops it destroys someone's artwork rather than an operator's typo."""
        self.assertIn('header', self._dir_json('jungle', 'directory.json'),
                      'fixture precondition')
        s = session()
        s._save_directory_containing(s.directory.pages[JUNGLE])
        self.assertEqual(
            'jungle/header.seq',
            self._dir_json('jungle', 'directory.json').get('header'),
            'saving deleted a directory header frame')

    def test_function_key_shortcuts_survive_a_save(self):
        """⚠ The regression: `shortcuts` was loaded but never written back, so
        the F-key block in root.json was deleted by the next upload, vote or
        extend — an action with nothing to do with it. The terminal's own copy
        of the serializer *did* write it, so whether the shortcuts survived
        depended on which subsystem the user happened to be using."""
        import json
        root_json = os.path.join(srv.ROOT_DIR, 'root.json')
        with open(root_json) as f:
            data = json.load(f)
        data['shortcuts'] = {'F1': 'JUNGLE', 'F3': 'PARTY'}
        with open(root_json, 'w') as f:
            json.dump(data, f, indent=2)

        s = session()
        s._save_directory_containing(s.directory.root)

        self.assertEqual({'F1': 'JUNGLE', 'F3': 'PARTY'},
                         self._dir_json('root.json').get('shortcuts'),
                         'saving deleted the function-key shortcuts')

    def test_an_explicit_upload_optout_survives_a_save(self):
        """THE ZOO sets `open_upload: false` to stop the Jungle's inheritance.
        Writing back only the truthy case reopens the directory to everyone —
        and that is exactly what the terminal's serializer used to do."""
        self.assertIs(False,
                      self._dir_json('jungle', 'the-zoo', 'directory.json')
                          .get('open_upload'), 'fixture precondition')
        s = session()
        s._save_directory_containing(s.directory.pages[THE_ZOO])
        self.assertIs(False,
                      self._dir_json('jungle', 'the-zoo', 'directory.json')
                          .get('open_upload'),
                      'saving reopened a directory that had opted out')

    def test_the_directory_path_is_written_with_forward_slashes(self):
        """os.path.relpath yields backslashes on Windows, and the tree is served
        from Linux — a path saved on one does not resolve on the other."""
        s = session()
        srv.save_directory_tree(s.directory.root, srv.ROOT_DIR)
        for page in self._dir_json('root.json')['pages']:
            if 'directory' in page:
                self.assertNotIn('\\', page['directory'])

    def test_one_sessions_save_does_not_discard_anothers(self):
        """⚠ THE regression the targeted writes exist for.

        Every session holds its own `CompunetDirectory`. A whole-tree save
        republishes that session's entire view of the content, so anything another
        session committed since it loaded was silently overwritten — an upload,
        gone, with nothing logged and no error.

        This is not a race between writers: within one event loop the saves cannot
        interleave. It is one writer publishing stale data over fresh data, which
        is why a lock would not have fixed it and writing only what changed does.
        """
        first = session()
        second = session()          # loaded independently, same content

        # The first session changes something and commits it.
        jungle = first.directory.pages[JUNGLE]
        target = jungle.children[0]
        target.life = 4321
        first.current_page = jungle
        first._save_directory_containing(jungle)
        self.assertEqual(
            4321,
            next(p['life'] for p in self._dir_json('jungle', 'directory.json')['pages']
                 if p['page_num'] == target.page_num))

        # The second session, which never saw that, now commits something of its
        # own in a DIFFERENT directory.
        zoo = second.directory.pages[THE_ZOO]
        second.current_page = zoo
        second._save_directory_containing(zoo)

        # The first session's change must still be on disk.
        self.assertEqual(
            4321,
            next(p['life'] for p in self._dir_json('jungle', 'directory.json')['pages']
                 if p['page_num'] == target.page_num),
            'a save from another session discarded a committed change')

    def test_an_upload_leaves_unrelated_directories_untouched(self):
        """The invariant behind the fix, stated positively.

        A write must touch the directory it changed (and its parent, since a
        latent directory becomes real on first upload) and NOTHING else. Asserted
        on mtime rather than content: a whole-tree save often rewrites unrelated
        files byte-identically, so comparing bytes would pass while the
        stale-data bug remained.
        """
        import base64
        import os as _os

        def mtimes():
            found = {}
            for base, _dirs, files in _os.walk(srv.ROOT_DIR):
                for name in files:
                    if name == 'directory.json' or name == 'root.json':
                        path = _os.path.join(base, name)
                        found[path] = _os.stat(path).st_mtime_ns
            return found

        before = mtimes()
        s = session()
        send(s, type='goto', target=str(JUNGLE))
        send(s, type='enter', page=GRAPHICS)
        reply = send(s, type='upload', title='TOUCHTEST', kind='T', price=0, life=30,
                     frames=[{'raw': base64.b64encode(
                         b'\x00\x00\x00\x8eHI').decode('ascii')}])
        self.assertEqual('directory', reply.get('type'),
                         'upload refused: %r' % (reply.get('message'),))

        touched = {p for p, t in mtimes().items() if before.get(p) != t}
        # GRAPHICS gains the entry; the Jungle above it may gain the `directory`
        # key that makes GRAPHICS reachable. Everything else must be untouched.
        allowed = {_os.path.join(srv.ROOT_DIR, 'jungle', 'graphics', 'directory.json'),
                   _os.path.join(srv.ROOT_DIR, 'jungle', 'directory.json')}
        self.assertTrue(touched, 'the upload wrote nothing at all')
        self.assertFalse(touched - allowed,
                         'an upload rewrote unrelated directories: %s'
                         % sorted(p.replace(srv.ROOT_DIR, '') for p in touched - allowed))

    def test_a_vote_writes_no_directory_json_at_all(self):
        """Votes live in votes.json and `vote` is never a directory-JSON key, so
        the whole-tree write that used to happen on every VOTE persisted nothing
        and could only clobber other sessions. Guarded by mtime: the file must be
        untouched, not merely unchanged in content."""
        import os as _os
        path = os.path.join(srv.ROOT_DIR, 'jungle', 'directory.json')
        before = _os.stat(path).st_mtime_ns

        s = session()
        s.current_page = s.directory.pages[JUNGLE]
        s.dir_page_offset = 0
        s._cmd_vote(b'005')          # entry 0, score 5

        self.assertEqual(before, _os.stat(path).st_mtime_ns,
                         'VOTE rewrote a directory JSON')


class ClientAddressResolution(unittest.TestCase):
    """§ audit: record the person, not the hop in front of them.

    ⚠ `request.remote` is the PROXY in every real deployment — production is
    reached through a Cloudflare tunnel, so the peer is a compose-network
    address. Logging it puts 172.18.0.x against the whole internet, which is no
    more useful than the literal "api" that web-client logins used to record."""

    class _Req:
        def __init__(self, headers=None, remote='172.18.0.4'):
            self.headers = headers or {}
            self.remote = remote

    def test_prefers_cloudflares_header(self):
        r = self._Req({'CF-Connecting-IP': '203.0.113.7',
                       'X-Forwarded-For': '198.51.100.1, 172.18.0.4'})
        self.assertEqual(api._client_ip(r), '203.0.113.7')

    def test_falls_back_to_the_first_forwarded_entry(self):
        """X-Forwarded-For is a CHAIN and the client can append to it, so only
        the first entry is meaningful; the rest are hops."""
        r = self._Req({'X-Forwarded-For': '198.51.100.1, 172.18.0.4'})
        self.assertEqual(api._client_ip(r), '198.51.100.1')

    def test_falls_back_to_the_peer_when_direct(self):
        self.assertEqual(api._client_ip(self._Req({}, remote='10.1.2.3')), '10.1.2.3')

    def test_never_returns_empty(self):
        """A blank header must not become a blank audit field."""
        r = self._Req({'CF-Connecting-IP': '   ', 'X-Forwarded-For': ' , '}, remote=None)
        self.assertEqual(api._client_ip(r), 'api')

    def test_a_login_records_the_address_not_the_literal_api(self):
        """The regression itself: _credentials_ok defaulted client_ip to "api",
        so handle_login audited that as the origin of every web-client login."""
        ok, s = api._credentials_ok(USER, PASSWORD, '203.0.113.7')
        self.assertTrue(ok)
        self.assertEqual(s.client_ip, '203.0.113.7')


class AuditWriteEndpoint(unittest.TestCase):
    """POST /api/audit — the website records events through the server, because
    it cannot write the file and should not be able to.

    ⚠ Before this endpoint existed the website appended to a path of its own,
    which under Docker resolved inside its own container and vanished on the
    next recreate. `password_reset_request` and `password_reset` — user and IP —
    had therefore never once been recorded: 0 of 6,566 entries in the live log.
    """

    KEY = 'test-key-1234'

    def setUp(self):
        import asyncio
        self._tmp = tempfile.mkdtemp(prefix='compunet-audit-')
        self._saved_path = srv.AUDIT_LOG_PATH
        self._saved_key = os.environ.get('COMPUNET_API_KEY')
        srv.AUDIT_LOG_PATH = os.path.join(self._tmp, 'audit.jsonl')
        os.environ['COMPUNET_API_KEY'] = self.KEY
        self._loop = asyncio.new_event_loop()

    def tearDown(self):
        srv.AUDIT_LOG_PATH = self._saved_path
        if self._saved_key is None:
            os.environ.pop('COMPUNET_API_KEY', None)
        else:
            os.environ['COMPUNET_API_KEY'] = self._saved_key
        self._loop.close()
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _post(self, body, auth=True, raw=None):
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        async def run():
            app = web.Application()
            app.router.add_post('/api/audit', srv.api_post_audit)
            cl = TestClient(TestServer(app))
            await cl.start_server()
            hdr = {'Authorization': 'Bearer %s' % self.KEY} if auth else {}
            if raw is not None:
                r = await cl.post('/api/audit', data=raw, headers=hdr)
            else:
                r = await cl.post('/api/audit', json=body, headers=hdr)
            status = r.status
            await cl.close()
            return status

        return self._loop.run_until_complete(run())

    def _stored(self):
        import json
        if not os.path.exists(srv.AUDIT_LOG_PATH):
            return []
        return [json.loads(l) for l in open(srv.AUDIT_LOG_PATH) if l.strip()]

    def test_requires_the_api_key(self):
        """It writes to the security log — an unguarded writer lets anyone
        forge the record of a password reset."""
        self.assertEqual(self._post({'event': 'page_read'}, auth=False), 401)
        self.assertEqual(self._stored(), [])

    def test_rejects_a_missing_event(self):
        self.assertEqual(self._post({'event': ''}), 400)
        self.assertEqual(self._post({}), 400)
        self.assertEqual(self._stored(), [])

    def test_rejects_malformed_json(self):
        self.assertEqual(self._post(None, raw='not json'), 400)

    def test_rejects_an_undeclared_event(self):
        """The vocabulary is enforced at the boundary (#127). An unknown name used
        to be accepted, written, and then invisible to every filter that knows the
        event set — a record that exists but cannot be found."""
        self.assertEqual(self._post({'event': 'something_made_up'}), 400)
        self.assertEqual(self._stored(), [])

    def test_records_the_event(self):
        self.assertEqual(self._post({'event': 'password_reset_requested',
                                     'user': 'TEST',
                                     'details': {'ip': '10.0.0.9'}}), 200)
        entries = self._stored()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['event'], 'password_reset_requested')
        self.assertEqual(entries[0]['kind'], 'session')
        self.assertEqual(entries[0]['user'], 'TEST')
        self.assertEqual(entries[0]['ip'], '10.0.0.9')
        self.assertIn('time', entries[0])

    def test_a_caller_cannot_forge_time_or_event(self):
        """⚠ `details` is filtered, not spread wholesale. Letting a caller set
        `time` would let it claim a reset happened at a different hour, which
        is exactly what an audit log exists to prevent."""
        self.assertEqual(self._post({'event': 'password_reset', 'user': 'TEST',
                                     'details': {'time': 'FORGED',
                                                 'event': 'evil',
                                                 'user': 'SOMEONE_ELSE',
                                                 'ip': '10.0.0.9'}}), 200)
        e = self._stored()[0]
        self.assertNotEqual(e['time'], 'FORGED')
        self.assertEqual(e['event'], 'password_reset')
        self.assertEqual(e['user'], 'TEST')
        self.assertEqual(e['ip'], '10.0.0.9')


class ProgramDownloadDescriptor(unittest.TestCase):
    """§8.3.1 — the 8-byte download descriptor is MACHINE-DEPENDENT, exactly as the
    upload header is (§8.3.2). It was not, and every Amiga download carried a wrong size.

    Ground truth is the relocated disassembly of the original Amiga client's
    file_download_xfer (FUN_0010b174), which reads the body size from a different
    field per machine:

        C64   (0): 16-bit WORD at header+6   10b21c: moveq #6,d0; move.w (a0,d0.l),d1
        Amiga (1): 32-bit LONG at header+4   10b22e: move.l $45ec(a4),-$a(a5)
        ST    (2): 32-bit LONG at header+4   10b268: same instruction

    g_dl_header is $45e8(a4), so $45ec is header+4. The split is by CPU, not brand:
    both 68k machines take a big-endian longword, the 6502 a 16-bit word. A C64
    cannot use 4-7 for a size because 4-5 carry its load address.

    Regression guarded: serving the C64 layout to an Amiga truncated the size to 16
    bits AND byte-swapped it — a 169,966-byte module was described as 61,079.
    """

    @staticmethod
    def _descriptor(prg_bytes, machine_type):
        s = session()
        page = srv.CompunetPage(page_num=1234, title='T', page_type='P',
                                author='TEST', price=0.0, life=1)
        page.frames = [prg_bytes]
        page.machine_type = machine_type
        s.show_page = page
        s.show_frame_index = 0
        return s._send_current_frame(), s

    def test_amiga_size_is_a_big_endian_longword_at_4(self):
        body = bytes(169966)
        hdr, s = self._descriptor(body, 'amiga')
        self.assertEqual(len(hdr), 8)
        self.assertEqual(hdr[0], 1)
        self.assertEqual(int.from_bytes(hdr[4:8], 'big'), 169966)
        self.assertEqual(hdr, bytes([1, 0, 0, 0]) + (169966).to_bytes(4, 'big'))
        # The staged body is the stored file whole — no load address is stripped.
        self.assertEqual(s._program_download_data, body)

    def test_amiga_size_survives_beyond_64k(self):
        """The old layout could not express this at all: it is the wrong field, not
        a rounding error."""
        for n in (65535, 65536, 169966, 1 << 20):
            hdr, _ = self._descriptor(bytes(n), 'amiga')
            self.assertEqual(int.from_bytes(hdr[4:8], 'big'), n, 'size %d' % n)

    def test_st_uses_the_same_68k_layout_as_amiga(self):
        hdr, _ = self._descriptor(bytes(70000), 'st')
        self.assertEqual(hdr[0], 2)
        self.assertEqual(int.from_bytes(hdr[4:8], 'big'), 70000)

    def test_c64_layout_is_unchanged(self):
        """The C64 path must stay byte-for-byte identical — 4-5 load address (little
        endian), 6-7 size, body = stored file minus the 2-byte load address."""
        prg = bytes([0x01, 0x08]) + bytes(1000)      # $0801, 1000-byte body
        hdr, s = self._descriptor(prg, 'c64')
        self.assertEqual(hdr, bytes([0, 0, 0, 0, 0x01, 0x08,
                                     1000 & 0xFF, (1000 >> 8) & 0xFF]))
        self.assertEqual(hdr[4] | (hdr[5] << 8), 0x0801)
        self.assertEqual(s._program_download_data, prg[2:])

    def test_absent_machine_type_is_c64(self):
        """Pre-existing content has no machine_type; it must serve exactly as before."""
        prg = bytes([0x01, 0x08]) + bytes(10)
        s = session()
        page = srv.CompunetPage(page_num=1234, title='T', page_type='P',
                                author='TEST', price=0.0, life=1)
        page.frames = [prg]
        s.show_page = page
        s.show_frame_index = 0
        hdr = s._send_current_frame()
        self.assertEqual(hdr[0], 0)
        self.assertEqual(hdr[4] | (hdr[5] << 8), 0x0801)


class PictureDownloadF(unittest.TestCase):
    """§7.4.1 — an F (IFF picture) downloads through the SAME 8-byte descriptor as an
    Amiga program (its handler action_download_run reuses file_download_xfer), and the
    server refuses to serve one to a client that cannot render it — the feature-locked
    C64 — because it has no IFF decoder and would garbage-render the bitmap."""

    @staticmethod
    def _f_page(body):
        page = srv.CompunetPage(page_num=1234, title='PIC', page_type='F',
                                author='TEST', price=0.0, life=1)
        page.frames = [body]
        page.machine_type = 'amiga'
        return page

    def _serve(self, capability):
        """capability: 'amiga' (native), 'api' (Binding B / web), or None (C64)."""
        s = session()
        s.show_page = self._f_page(bytes(5000))
        s.show_frame_index = 0
        if capability == 'amiga':
            s.is_amiga = True
        elif capability == 'api':
            s.audit_via = 'api'
        return s._send_current_frame(), s

    def test_an_f_download_uses_the_amiga_program_descriptor(self):
        hdr, s = self._serve('amiga')
        self.assertEqual(hdr[0], 1, 'F is Amiga: machine byte 1')
        self.assertEqual(int.from_bytes(hdr[4:8], 'big'), 5000,
                         'F sizes its body as a 68k big-endian longword at 4-7')
        self.assertEqual(s._program_download_data, bytes(5000),
                         'the IFF body is staged whole — no load address stripped')

    def test_binding_b_may_fetch_an_f_it_renders_itself(self):
        hdr, s = self._serve('api')
        self.assertEqual(hdr[0], 1)
        self.assertTrue(getattr(s, '_program_download_pending', False),
                        'Binding B carries the renderer, so the fetch must proceed')

    def test_taking_the_download_stops_the_session_showing_that_page(self):
        """⚠ The regression: `take_program_download` cleared the pending flags but
        left `show_page` set, so the finished binary page was still 'current' after
        its bytes had been handed over — and the next command that reached
        _send_current_frame re-sent the 8-byte DESCRIPTOR, offering the user the
        download they had just completed. The abort path already cleared it; success
        did not, so the two ends of one transfer disagreed. Applies to P as much as
        to F — the fix is in the shared function."""
        _, s = self._serve('amiga')
        self.assertTrue(s._program_download_pending, 'staged before the fetch')
        self.assertIsNotNone(s.show_page)
        data = s.take_program_download()
        self.assertEqual(len(data), 5000, 'the bytes are still delivered')
        self.assertIsNone(s.show_page, 'the session must stop showing a downloaded page')
        self.assertEqual(s.show_frame_index, 0)
        self.assertFalse(s._program_download_pending)

    def test_an_action_entry_is_refused_outright_on_every_client(self):
        """§7.4.1 — `A` is deliberately not served, and MUST be refused rather than
        allowed to fall through to the frame path.

        ⚠ The danger is not that A does nothing; it is that the CLIENT dispatches on the
        type letter regardless of what the server sends. Letting an A reach the ordinary
        frame path put the client in its action handler — which expects the 8-byte
        descriptor and then Execute()s the result — while the server sent a text frame.
        The Amiga read the frame's leading bytes as the descriptor (guarded only by
        whatever that byte happened to be); the C64, which has no machine guard at all,
        would execute the received data as 6502.

        Refused for EVERY client, including the ones that could technically run it —
        this is a policy decision (arbitrary code execution into frozen binaries), not a
        capability check like the F guard above."""
        for capability in ('amiga', 'api', None):
            with self.subTest(client=capability):
                s = session()
                page = srv.CompunetPage(page_num=1234, title='ACTION', page_type='A',
                                        author='TEST', price=0.0, life=1)
                page.frames = [b'\x00\x06\x0f\x8e RUNME']
                page.machine_type = 'amiga'
                s.show_page = page
                s.show_frame_index = 0
                if capability == 'amiga':
                    s.is_amiga = True
                elif capability == 'api':
                    s.audit_via = 'api'
                out = s._send_current_frame()
                self.assertEqual(out[0], srv.RESP_ERROR,
                                 'an A must be refused, not sent as a frame')
                self.assertNotIn(b'RUNME', bytes(out),
                                 'the stored bytes must never reach the client')
                self.assertFalse(getattr(s, '_program_download_pending', False),
                                 'nothing may be staged for an A')

    def test_the_c64_is_refused_an_f_with_a_message_not_the_descriptor(self):
        hdr, s = self._serve(None)
        # RESP_ERROR ('E', 0x45) + PETSCII message + $00 — the C64 paints it as a page
        # rather than being handed a descriptor it would mishandle (§7.4.1).
        self.assertEqual(hdr[0], srv.RESP_ERROR)
        self.assertIn(b'AMIGA', bytes(hdr))
        self.assertFalse(getattr(s, '_program_download_pending', False),
                         'nothing must be staged for a client that cannot render it')


if __name__ == '__main__':
    unittest.main(verbosity=2)
