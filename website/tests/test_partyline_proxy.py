#!/usr/bin/env python3
"""Regression tests for the admin Partyline WebSocket proxy.

Run:  python website/tests/test_partyline_proxy.py            (or -v)

The console used to open a socket straight at the server's admin API (6403),
carrying the admin API key in the query string of a URL that was rendered into
the page. That needed 6403 published to the internet, put a key that can act as
any user into the browser, and let the page name whichever user_id it liked.

It is proxied by this site now: the browser opens a same-origin socket, the
session cookie says who it is, and the key is added on the upstream leg here.

⚠ WHICH MOVES THE WHOLE PROBLEM TO ONE FUNCTION. A WebSocket handshake carries
the session cookie whatever page opened it, and no CSRF token can ride along —
so `_partyline_ws_refusal` is the only thing standing between a signed-in
admin's browser and any site that decides to read Partyline through it. Nothing
breaks if it is weakened; the console keeps working. Hence these tests.

No network: the gate is a plain function, and the page render only touches the
session.
"""

import glob
import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEBSITE = os.path.dirname(_HERE)

sys.path.insert(0, _WEBSITE)

import app as site                                # noqa: E402
import config                                     # noqa: E402

TEMPLATES = os.path.join(_WEBSITE, 'templates')
SITE_URL = 'https://compunet.live'


def client():
    site.app.config['TESTING'] = True
    site.app.secret_key = 'test-secret'
    return site.app.test_client()


class OnlyAnAdminsOwnPageMayOpenTheSocket(unittest.TestCase):
    """`_partyline_ws_refusal(origin, user_id)` — None means "may open"."""

    def setUp(self):
        self._saved = os.environ.get('WEBSITE_BASE_URL')
        os.environ['WEBSITE_BASE_URL'] = SITE_URL

    def tearDown(self):
        if self._saved is None:
            os.environ.pop('WEBSITE_BASE_URL', None)
        else:
            os.environ['WEBSITE_BASE_URL'] = self._saved

    def refusal(self, origin, user_id, base=SITE_URL):
        with site.app.test_request_context('/admin/ws/partyline',
                                           base_url=base):
            return site._partyline_ws_refusal(origin, user_id)

    def test_the_consoles_own_page_may_open_it(self):
        self.assertIsNone(self.refusal(SITE_URL, 'ADMIN'))

    def test_the_deployments_own_host_may_open_it(self):
        """⚠ Both are allowed on purpose. A local checkout and a dev container
        are reached on a host that WEBSITE_BASE_URL does not name, and refusing
        there would mean the console only ever works in production — which is
        the deployment where nobody wants to debug it."""
        self.assertIsNone(self.refusal('http://localhost:6464', 'ADMIN',
                                       base='http://localhost:6464'))

    def test_another_site_may_not(self):
        """The attack: an admin, signed in, visits a page that opens this."""
        for origin in ('https://evil.example',
                       'https://compunet.live.evil.example',
                       'https://evil.example/?https://compunet.live',
                       'http://compunet.live:8080'):
            with self.subTest(origin=origin):
                self.assertEqual('cross-site origin',
                                 self.refusal(origin, 'ADMIN'))

    def test_a_handshake_with_no_origin_may_not(self):
        """A browser always sends one, so anything without it is a tool — and
        this endpoint exists only for the console page."""
        for origin in (None, ''):
            with self.subTest(origin=origin):
                self.assertEqual('no origin', self.refusal(origin, 'ADMIN'))

    def test_an_ordinary_user_may_not(self):
        self.assertEqual('not an administrator', self.refusal(SITE_URL, 'ZARD'))

    def test_a_signed_out_visitor_may_not(self):
        """`session.get('user_id')` is None, which must not read as "no origin"
        or fall through: the identity is checked first."""
        self.assertEqual('not an administrator', self.refusal(SITE_URL, None))

    def test_the_admin_check_is_exact(self):
        """Not a prefix, not case-insensitive — the server upper-cases user IDs,
        so anything else here is a different account."""
        for user_id in ('admin', 'ADMINISTRATOR', 'XADMIN', ' ADMIN'):
            with self.subTest(user_id=user_id):
                self.assertEqual('not an administrator',
                                 self.refusal(SITE_URL, user_id))


class TheUpstreamLegStaysInternal(unittest.TestCase):
    """COMPUNET_API_URL is a container address, and that is the point: the
    browser never needs a route to 6403."""

    def upstream(self, api_url):
        saved = os.environ.get('COMPUNET_API_URL')
        os.environ['COMPUNET_API_URL'] = api_url
        try:
            return site._partyline_upstream_url()
        finally:
            if saved is None:
                os.environ.pop('COMPUNET_API_URL', None)
            else:
                os.environ['COMPUNET_API_URL'] = saved

    def test_http_becomes_ws(self):
        self.assertEqual('ws://compunet-server:6403/ws/partyline',
                         self.upstream('http://compunet-server:6403'))

    def test_https_becomes_wss(self):
        self.assertEqual('wss://api.internal/ws/partyline',
                         self.upstream('https://api.internal'))

    def test_a_trailing_slash_does_not_double_up(self):
        self.assertEqual('ws://localhost:6403/ws/partyline',
                         self.upstream('http://localhost:6403/'))

    def test_the_path_is_the_servers_route(self):
        """⚠ `/ws/partyline`, NOT `/api/ws/partyline`. The route is registered
        outside the /api prefix (compunet_server.py) and a wrong path here fails
        as "upstream unavailable", which reads as the server being down."""
        self.assertTrue(self.upstream('http://x:6403').endswith('/ws/partyline'))


class TheBrowserIsToldNothing(unittest.TestCase):
    """⚠ The page used to receive the admin API key as a JavaScript literal.
    Anyone who could see that page — or a saved copy of it, or a browser
    extension reading it — held a credential that can act as any user across the
    whole admin API."""

    def setUp(self):
        self.c = client()
        with self.c.session_transaction() as s:
            s['user_id'] = 'ADMIN'
        self._saved = os.environ.get('COMPUNET_API_KEY')
        os.environ['COMPUNET_API_KEY'] = 'the-key-must-not-be-rendered'

    def tearDown(self):
        if self._saved is None:
            os.environ.pop('COMPUNET_API_KEY', None)
        else:
            os.environ['COMPUNET_API_KEY'] = self._saved

    def page(self):
        resp = self.c.get('/admin/partyline')
        self.assertEqual(200, resp.status_code)
        return resp.get_data(as_text=True)

    def test_the_api_key_is_not_in_the_page(self):
        self.assertNotIn('the-key-must-not-be-rendered', self.page())

    def test_the_socket_is_same_origin(self):
        """No hostname to configure, so no PARTYLINE_WS_URL to point at a host
        that has since been retired — which is exactly how this broke."""
        html = self.page()
        self.assertIn('location.host', html)
        self.assertIn('/admin/ws/partyline', html)

    def test_no_user_id_is_sent_from_the_browser(self):
        """The server takes user_id from the query because the WEBSITE tells it
        who it authenticated. If the page passed it, the browser would be
        choosing whose name appears in Partyline and in the audit log.

        Both parameters are checked by name: the socket URL is built in script,
        so what matters is that neither ever appears in a query string here.
        """
        html = self.page()
        self.assertNotIn('user_id=', html)
        self.assertNotIn('token=', html)

    def test_a_non_admin_cannot_even_load_the_page(self):
        with self.c.session_transaction() as s:
            s['user_id'] = 'ZARD'
        self.assertEqual(302, self.c.get('/admin/partyline').status_code)


class TheConsoleSaysSoWhenItCannotWork(unittest.TestCase):
    """⚠ flask-sock and websocket-client are a guarded import: a container built
    before they were added must still serve the whole site. That state has to be
    VISIBLE, or the console looks broken rather than absent."""

    def test_the_page_carries_the_availability_flag(self):
        c = client()
        with c.session_transaction() as s:
            s['user_id'] = 'ADMIN'
        html = c.get('/admin/partyline').get_data(as_text=True)
        if site.sock is None:
            self.assertIn('unavailable', html.lower())
        else:
            self.assertIn('new WebSocket', html)

    def test_the_route_only_exists_when_the_proxy_can_run(self):
        routes = {r.rule for r in site.app.url_map.iter_rules()}
        self.assertEqual(site.sock is not None,
                         '/admin/ws/partyline' in routes)


class NoTemplateLeaksACredential(unittest.TestCase):
    """⚠ THE test that earns its keep. The key reaching the browser was a single
    template variable, and it read as ordinary configuration for three releases.
    This fails on the next one, wherever it is added."""

    def test_no_template_mentions_the_api_key(self):
        offenders = []
        for path in sorted(glob.glob(os.path.join(TEMPLATES, '*.html'))):
            with open(path, encoding='utf-8') as f:
                src = f.read()
            for m in re.finditer(r'API_KEY|api_key|apiKey', src):
                offenders.append('%s:%d' % (os.path.basename(path),
                                            src[:m.start()].count('\n') + 1))
        self.assertEqual([], offenders,
                         'templates naming a credential: %s'
                         % ', '.join(offenders))

    def test_the_scan_really_reads_the_templates(self):
        """Guards the guard: a glob that matched nothing would pass silently."""
        self.assertGreater(len(glob.glob(os.path.join(TEMPLATES, '*.html'))), 5)


if __name__ == '__main__':
    unittest.main(verbosity=2 if '-v' in sys.argv else 1)
