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

USER, PASSWORD = 'TEST', 'SECRET'
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
        s._save_directory()

        self.assertIn('directory', self._jungle_entry(GRAPHICS),
                      'saving deleted an empty sub-directory')

    def test_a_populated_sub_directory_survives_a_save(self):
        """The control: the same field on a directory that does have children."""
        s = session()
        self.assertTrue(s.directory.pages[MORE_DIR].children, 'fixture precondition')
        s._save_directory()
        self.assertIn('directory', self._jungle_entry(MORE_DIR))


if __name__ == '__main__':
    unittest.main(verbosity=2)
