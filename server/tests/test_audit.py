#!/usr/bin/env python3
"""Regression tests for the audit log (#127, #128).

Run:  python server/tests/test_audit.py            (or -v)

⚠ NOTHING COVERED AUDITING BEFORE THIS FILE, which is exactly how the gap it
guards against shipped: when the JSON API was added it reused the core happily,
and nobody noticed that mail sent through it was recorded nowhere — because no
test asked. Every suite passed the whole time.

The rule these tests exist to hold: **an action is audited by the function that
performs it, not by the caller that reached it.** So each surface is exercised
independently and asserted to produce the event. A future binding that reuses the
core inherits the coverage for free; one that reimplements an action fails here.
"""

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
import api_binding as api         # noqa: E402
import partyline as pl            # noqa: E402

api._bind_server(srv)

USER, PASSWORD = 'TEST', 'SECRET'


class AuditTestCase(unittest.TestCase):
    """Redirects the audit log to a temp file so tests never touch the real one."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix='compunet-audit-')
        self._saved_path = srv.AUDIT_LOG_PATH
        self._saved_mail = srv.MAIL_DIR
        srv.AUDIT_LOG_PATH = os.path.join(self._tmp, 'audit.jsonl')
        srv.MAIL_DIR = os.path.join(self._tmp, 'mail')

    def tearDown(self):
        srv.AUDIT_LOG_PATH = self._saved_path
        srv.MAIL_DIR = self._saved_mail
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

    def api_session(self, ip='203.0.113.9'):
        s = api._new_session(ip)
        s.handle_login(USER, PASSWORD)
        if not s.authenticated:
            self.skipTest('fixture account %s cannot log in' % USER)
        return s


class TheRegistryIsAuthoritative(AuditTestCase):
    """An event name that is not declared must fail loudly, at the call site."""

    def test_an_unknown_event_raises(self):
        with self.assertRaises(ValueError):
            srv.audit_log('something_nobody_declared', user='TEST')

    def test_every_declared_event_has_a_known_kind(self):
        for event, kind in srv.AUDIT_EVENTS.items():
            self.assertIn(kind, srv.AUDIT_KINDS, event)

    def test_every_entry_carries_a_kind(self):
        srv.audit_log('page_read', user='TEST', page=100)
        self.assertEqual(self.events()[0]['kind'], 'browse')


class ViaAndIpComeFromTheSession(AuditTestCase):
    """They were per-call-site arguments, present on all ten of terminal.py's
    events and almost none of Binding A's. Deriving them means a new call site
    cannot omit them."""

    def test_session_supplies_ip_and_via(self):
        s = self.api_session('198.51.100.4')
        srv.audit_log('page_read', session=s, page=100)
        entry = self.events('page_read')[0]
        self.assertEqual(entry['ip'], '198.51.100.4')
        self.assertEqual(entry['via'], 'api')
        self.assertEqual(entry['user'], USER)

    def test_amiga_is_distinguished_from_c64(self):
        """The one surface the server infers for itself, during identification.

        ⚠ This test USED TO PASS while the server was wrong, because it cleared
        `audit_via` before checking the is_amiga fallback — a sequence the real code
        never performs. It now drives identification the way the handler does."""
        s = self.api_session()
        s.audit_via = 'c64'                       # what the socket sets on connect
        self.assertEqual(srv.audit_via(s), 'c64')
        srv.identify_binding_a_client(s, True)    # what identification then learns
        self.assertEqual(srv.audit_via(s), 'amiga')
        self.assertTrue(s.is_amiga)

    def test_identification_labels_a_c64_as_c64(self):
        s = self.api_session()
        s.audit_via = 'c64'
        srv.identify_binding_a_client(s, False)
        self.assertEqual(srv.audit_via(s), 'c64')
        self.assertFalse(s.is_amiga)

    def test_an_identified_amiga_is_logged_as_amiga(self):
        """⚠ The regression, end to end: every Amiga action was recorded `via: c64`,
        so the log could not tell the two Binding-A machines apart at all. Asserted on
        a written ENTRY, not just the helper — the helper was never the broken part."""
        s = self.api_session('192.0.2.7')
        s.audit_via = 'c64'
        srv.identify_binding_a_client(s, True)
        srv.audit_log('page_downloaded', session=s, page=952,
                      title='COLOUR BARS', bytes=30800)
        entry = self.events('page_downloaded')[0]
        self.assertEqual(entry['via'], 'amiga',
                         'an identified Amiga must not be recorded as a C64')
        self.assertEqual(entry['ip'], '192.0.2.7')

    def test_setting_is_amiga_alone_is_not_how_it_is_done(self):
        """Guards the fix itself. Setting only `is_amiga` leaves the label stale,
        which is exactly what shipped; the shared function exists so no call site
        can do half the job. If this ever returns 'amiga', someone has made
        audit_via() infer again and the two fields can drift apart once more."""
        s = self.api_session()
        s.audit_via = 'c64'
        s.is_amiga = True                          # the half-update that caused #127
        self.assertEqual(srv.audit_via(s), 'c64',
                         'explicit still wins — which is why the helper is required')

    def test_an_explicit_value_wins(self):
        srv.audit_log('user_updated', user='X', via='admin', ip='10.0.0.1')
        entry = self.events('user_updated')[0]
        self.assertEqual(entry['via'], 'admin')


class EverySurfaceAudits(AuditTestCase):
    """The heart of it. Same action, different door, same record."""

    def test_binding_b_mail_send_is_audited(self):
        """The reported gap. mail_sent was logged by Binding A and the terminal at
        their own call sites; Binding B calls _complete_mail_send directly and was
        recorded nowhere."""
        s = self.api_session()
        api.handle_message(s, {'type': 'mail.send', 'to': ['ADMIN'],
                               'subject': 'HELLO', 'frames': [{'raw': 'SGk='}]})
        sent = self.events('mail_sent')
        self.assertEqual(len(sent), 1, 'Binding B mail must be audited')
        self.assertEqual(sent[0]['via'], 'api')
        self.assertEqual(sent[0]['to'], ['ADMIN'])

    def test_mail_send_is_audited_once_not_per_caller(self):
        """Moving the call into the shared function must not leave a duplicate
        behind — two entries for one mail is its own kind of wrong."""
        s = self.api_session()
        api.handle_message(s, {'type': 'mail.send', 'to': ['ADMIN'],
                               'subject': 'ONE', 'frames': [{'raw': 'SGk='}]})
        self.assertEqual(len(self.events('mail_sent')), 1)

    def test_session_start_and_end_are_audited(self):
        s = self.api_session()
        self.assertEqual(len(self.events('session_started')), 1)
        srv._user_disconnect(s.user_id, s)
        ended = self.events('session_ended')
        self.assertEqual(len(ended), 1, 'Binding B session end must be audited')
        self.assertEqual(ended[0]['via'], 'api')

    def test_disconnecting_a_user_who_is_not_online_records_nothing(self):
        """Guards against a teardown path firing twice."""
        srv._user_disconnect('NOBODYHERE', None)
        self.assertEqual(self.events('session_ended'), [])

    def test_partyline_entry_is_audited_from_the_shared_join(self):
        """All three surfaces reach partyline_log('join'); only two audited it."""
        pl.partyline_log('join', user='TEST')
        entered = self.events('partyline_entered')
        self.assertEqual(len(entered), 1)
        self.assertEqual(entered[0]['kind'], 'partyline')

    def test_a_download_is_audited_when_it_is_taken(self):
        s = self.api_session()
        s._program_download_data = b'\x01\x02\x03'
        s._program_download_pending = True
        s._download_page_num, s._download_title = 1234, 'A PROGRAM'
        data = s.take_program_download()
        self.assertEqual(data, b'\x01\x02\x03')
        got = self.events('page_downloaded')
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]['page'], 1234)
        self.assertEqual(got[0]['bytes'], 3)

    def test_a_declined_download_records_nothing(self):
        """Decided deliberately: the user obtained nothing."""
        s = self.api_session()
        s._program_download_data = None
        self.assertIsNone(s.take_program_download())
        self.assertEqual(self.events('page_downloaded'), [])


class AdminActionsAreAudited(AuditTestCase):
    """The events an audit log exists for, and none of them were recorded."""

    def test_a_user_edit_records_what_changed(self):
        before = {'credit': 10.0, 'editor': False, 'name': 'Old'}
        after = {'credit': 25.0, 'editor': True, 'name': 'Old'}
        changes = srv._audit_diff(before, after)
        self.assertIn("credit: 10.0 -> 25.0", changes)
        self.assertIn("editor: False -> True", changes)
        self.assertNotIn('name', ' '.join(changes), 'unchanged fields must not appear')

    def test_a_password_change_is_never_valued(self):
        """Naming the field is useful; putting credential material in a log an
        admin reads in a browser is not."""
        changes = srv._audit_diff({'password': 'aaa'}, {'password': 'bbb'})
        self.assertEqual(changes, ['password: changed'])
        self.assertNotIn('aaa', ' '.join(changes))
        self.assertNotIn('bbb', ' '.join(changes))


class SearchAndFilter(AuditTestCase):
    """#128 — the viewer's filters, applied server-side."""

    def seed(self):
        srv.audit_log('page_read', user='ZARD', via='c64', ip='1.1.1.1', page=100,
                      title='DEMOS')
        srv.audit_log('page_uploaded', user='ZARD', via='amiga', ip='1.1.1.1',
                      title='A MODULE')
        srv.audit_log('mail_sent', user='MW20', via='api', ip='2.2.2.2',
                      to=['ZARD'], subject='HELLO')
        srv.audit_log('user_updated', user='TEST', via='admin', ip='3.3.3.3',
                      changed=['editor: False -> True'])

    def search(self, **kw):
        return srv._audit_search(srv._AuditQuery(**kw), 1, 50, count_all=True)

    def test_no_filter_returns_everything_newest_first(self):
        self.seed()
        r = self.search()
        self.assertEqual(r['matched'], 4)
        self.assertEqual(r['entries'][0]['event'], 'user_updated')

    def test_filter_by_user_is_case_insensitive(self):
        self.seed()
        self.assertEqual(self.search(user='zard')['matched'], 2)

    def test_filter_by_kind(self):
        self.seed()
        self.assertEqual(self.search(kinds=['admin'])['matched'], 1)
        self.assertEqual(self.search(kinds=['browse'])['matched'], 1)

    def test_filter_by_event_accepts_several(self):
        self.seed()
        self.assertEqual(
            self.search(events=['page_read', 'mail_sent'])['matched'], 2)

    def test_filter_by_via(self):
        self.seed()
        self.assertEqual(self.search(via='amiga')['matched'], 1)

    def test_filter_by_ip(self):
        self.seed()
        self.assertEqual(self.search(ip='1.1.1.1')['matched'], 2)

    def test_free_text_searches_detail_fields(self):
        """Page titles and mail subjects must be findable without naming the field
        they live in — that is the point of the search box."""
        self.seed()
        self.assertEqual(self.search(text='a module')['matched'], 1)
        self.assertEqual(self.search(text='hello')['matched'], 1)
        self.assertEqual(self.search(text='editor')['matched'], 1)

    def test_filters_combine(self):
        self.seed()
        self.assertEqual(self.search(user='ZARD', kinds=['content'])['matched'], 1)

    def test_date_range_is_inclusive(self):
        self.seed()
        today = self.events()[0]['time'][:10]
        self.assertEqual(self.search(date_from=today, date_to=today)['matched'], 4)
        self.assertEqual(self.search(date_from='2099-01-01')['matched'], 0)

    def test_paging_walks_backwards_without_repeating(self):
        for i in range(25):
            srv.audit_log('page_read', user='X', page=i)
        q = srv._AuditQuery()
        first = srv._audit_search(q, 1, 10)
        second = srv._audit_search(q, 2, 10)
        self.assertEqual(len(first['entries']), 10)
        self.assertEqual(len(second['entries']), 10)
        overlap = ({e['page'] for e in first['entries']} &
                   {e['page'] for e in second['entries']})
        self.assertEqual(overlap, set(), 'pages must not repeat entries')
        self.assertTrue(first['has_more'])

    def test_it_stops_reading_once_the_page_is_full(self):
        """The reason for reading backwards: cost must not track file size."""
        for i in range(500):
            srv.audit_log('page_read', user='X', page=i)
        r = srv._audit_search(srv._AuditQuery(), 1, 10)
        self.assertLess(r['scanned'], 50,
                        'should stop shortly after filling the page, not scan 500')
        self.assertFalse(r['matched_exact'],
                         'a count it did not establish must not be claimed as exact')

    def test_an_exact_count_is_available_on_request(self):
        for i in range(60):
            srv.audit_log('page_read', user='X', page=i)
        r = srv._audit_search(srv._AuditQuery(), 1, 10, count_all=True)
        self.assertTrue(r['matched_exact'])
        self.assertEqual(r['matched'], 60)

    def test_a_malformed_line_does_not_break_the_reader(self):
        self.seed()
        with open(srv.AUDIT_LOG_PATH, 'a') as f:
            f.write('this is not json\n')
        self.assertEqual(self.search()['matched'], 4)

    def test_reading_backwards_matches_reading_forwards(self):
        """The chunked reverse reader must not lose or split a line — it stitches
        partial lines across 64 KB block boundaries."""
        for i in range(300):
            srv.audit_log('page_read', user='X', page=i, note='x' * 200)
        with open(srv.AUDIT_LOG_PATH) as f:
            forwards = [json.loads(l) for l in f if l.strip()]
        backwards = [json.loads(l) for l in srv._audit_iter_reversed(srv.AUDIT_LOG_PATH)]
        self.assertEqual(len(backwards), len(forwards))
        self.assertEqual(backwards, list(reversed(forwards)))


class TheDocumentationMatchesTheRegistry(unittest.TestCase):
    """docs/audit-log.md lists all 34 events. A list that long drifts the moment
    someone adds a feature, and a stale reference is worse than none — so the
    drift fails here instead of being discovered by whoever trusted it."""

    DOC = os.path.join(os.path.dirname(_SERVER), 'docs', 'audit-log.md')

    def setUp(self):
        if not os.path.exists(self.DOC):
            self.skipTest('docs/audit-log.md not present')
        with open(self.DOC, encoding='utf-8') as f:
            self.text = f.read()

    def test_every_event_is_documented(self):
        undocumented = [e for e in srv.AUDIT_EVENTS
                        if '`%s`' % e not in self.text]
        self.assertEqual([], undocumented,
                         'events missing from docs/audit-log.md: %s' % undocumented)

    def test_every_kind_is_documented(self):
        for kind in srv.AUDIT_KINDS:
            self.assertIn('`%s`' % kind, self.text, kind)

    def test_the_doc_lists_no_event_that_does_not_exist(self):
        """The other direction: a renamed event must not linger in the table."""
        import re
        # Event names in the doc's bullet lists, e.g. "- `page_read`"
        listed = set(re.findall(r'^- `([a-z_]+)`$', self.text, re.M))
        unknown = sorted(listed - set(srv.AUDIT_EVENTS))
        self.assertEqual([], unknown,
                         'documented events that no longer exist: %s' % unknown)


class _FakeRequest:
    """Enough of an aiohttp request for `_client_ip`: headers and a peer."""

    def __init__(self, remote=None, **headers):
        self.remote = remote
        self.headers = {k.replace('_', '-'): v for k, v in headers.items()}


class TheAuditedAddressIsTheVisitorNotTheProxy(unittest.TestCase):
    """#135. Every `via=api` entry recorded `172.18.0.4` — the cloudflared
    container — for as long as the `ip` field had existed.

    ⚠ WHY NOTHING CAUGHT IT. The suite asserted that events are written and that
    they carry `ip` and `via`, and `ViaAndIpComeFromTheSession` above builds a
    session with an address handed straight to it. None of that exercises the
    step where the address is DERIVED FROM A REQUEST, so a handler reading the
    peer instead of the forwarded header passed every existing test. Asserting a
    field is present is not asserting it is right.
    """

    def test_cloudflare_header_wins(self):
        self.assertEqual(
            api._client_ip(_FakeRequest(remote='172.18.0.4',
                                        CF_Connecting_IP='198.51.100.7')),
            '198.51.100.7')

    def test_forwarded_for_is_used_when_cloudflare_header_is_absent(self):
        self.assertEqual(
            api._client_ip(_FakeRequest(remote='172.18.0.4',
                                        X_Forwarded_For='198.51.100.8')),
            '198.51.100.8')

    def test_forwarded_for_is_a_chain_and_only_the_first_entry_is_the_client(self):
        """The client appends to XFF too, so every entry after the first is a hop.
        Taking the last would record our own edge; taking the whole string would
        record a list where a filterable address belongs."""
        self.assertEqual(
            api._client_ip(_FakeRequest(remote='172.18.0.4',
                                        X_Forwarded_For='198.51.100.9, 10.0.0.1, 172.18.0.4')),
            '198.51.100.9')

    def test_cloudflare_header_beats_forwarded_for(self):
        self.assertEqual(
            api._client_ip(_FakeRequest(remote='172.18.0.4',
                                        CF_Connecting_IP='198.51.100.7',
                                        X_Forwarded_For='203.0.113.1')),
            '198.51.100.7')

    def test_the_peer_is_the_fallback_for_a_direct_connection(self):
        """No proxy in front — the peer IS the client, and must still be recorded.
        This is also why the fix cannot regress: with no headers present the
        behaviour is exactly what it replaced."""
        self.assertEqual(api._client_ip(_FakeRequest(remote='198.51.100.10')),
                         '198.51.100.10')

    def test_ipv6_survives_intact(self):
        """Production's first correct entry was IPv6; a naive split on ':' to strip
        a port would have destroyed it."""
        v6 = '2a0e:cb01:ae:be00:8c22:4322:1ec2:990f'
        self.assertEqual(api._client_ip(_FakeRequest(remote='172.18.0.4',
                                                     CF_Connecting_IP=v6)), v6)

    def test_the_gateway_resolves_the_address_rather_than_taking_the_peer(self):
        """⚠ A STRUCTURAL check, and it earns its place. The bug was not in the
        helper — the helper was always correct — it was one handler not calling
        it. The suite runs no sockets, so this pins the regression at its actual
        location: `ws_gateway` must resolve through `_client_ip` and must not read
        `request.remote` itself.

        If the gateway is ever rewritten to take a real request in a socket test,
        replace this with that test.
        """
        import inspect
        # ⚠ Strip comments before looking. The fix's own comment NAMES the thing it
        # replaced, so a naive substring search fails on the explanation of the bug
        # rather than on the bug — which it duly did the first time this ran.
        src = '\n'.join(l.split('#')[0] for l in
                        inspect.getsource(api.ws_gateway).splitlines())
        self.assertIn('_client_ip(request)', src,
                      'ws_gateway must resolve the client address, not take the peer')
        self.assertNotIn('request.remote', src,
                         'ws_gateway reads the peer again — that is #135 returning')


class TheAdminApiRecordsTheVisitorNotTheWebsite(unittest.TestCase):
    """The SECOND instance of #135, found by sweeping for the same mistake and
    confirmed on production: `registration_requested` and six sibling events were
    stamped 172.18.0.3 — the website container — while `login_succeeded` beside
    them carried real addresses, because sign-in was the one route that passed an
    address explicitly.

    The server's peer on this API is always the website, so the website forwards
    the address it resolved and the server prefers it."""

    def test_the_forwarded_header_is_preferred_over_the_peer(self):
        self.assertEqual(
            srv._api_caller_ip(_FakeRequest(remote='172.18.0.3',
                                            X_Compunet_Client_IP='198.51.100.11')),
            '198.51.100.11')

    def test_the_peer_remains_the_fallback(self):
        """An older website that sends no header must not break — it simply gets
        the behaviour this replaced, rather than something worse."""
        self.assertEqual(srv._api_caller_ip(_FakeRequest(remote='172.18.0.3')),
                         '172.18.0.3')

    def test_no_admin_route_reads_the_peer_directly_any_more(self):
        """The structural half. Seven call sites had `ip=request.remote`; the
        helper only helps if they all go through it, and a new route added later
        is exactly how this comes back."""
        import inspect
        src = '\n'.join(l.split('#')[0] for l in
                        inspect.getsource(srv).splitlines())
        self.assertNotIn('ip=request.remote', src,
                         'an admin route audits the peer instead of the visitor')


if __name__ == '__main__':
    unittest.main(verbosity=2 if '-v' in sys.argv else 1)
