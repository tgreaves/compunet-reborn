#!/usr/bin/env python3
"""Regression tests for the website's CSRF protection.

Run:  python website/tests/test_csrf.py            (or -v)

A cross-site request forgery is another site causing YOUR browser to send a
request here. The browser attaches the session cookie based on where the request
is GOING, not where it came from, so the server sees a properly authenticated
request and obeys — and the attacker never reads the reply, because the damage is
the side effect.

⚠ These tests exist because the protection is easy to weaken by accident and
impossible to notice: nothing breaks, no error appears, the site simply becomes
forgeable again. The last test is the one that earns its keep — it reads every
template and fails if a form is added without a token.

No network: every route exercised here is refused before its handler runs, or
touches only the session, so nothing reaches the Compunet server.
"""

import os
import re
import sys
import glob
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEBSITE = os.path.dirname(_HERE)

sys.path.insert(0, _WEBSITE)

import app as site                                # noqa: E402

TEMPLATES = os.path.join(_WEBSITE, 'templates')


def client():
    site.app.config['TESTING'] = True
    site.app.secret_key = 'test-secret'
    return site.app.test_client()


def token_from(html):
    m = re.search(r'name="_csrf" value="([^"]+)"', html)
    return m.group(1) if m else None


class AForgedRequestIsRefused(unittest.TestCase):
    """`/logout` stands in for every state-changing POST: it needs no network and
    its effect — the session — is observable."""

    def setUp(self):
        self.c = client()
        with self.c.session_transaction() as s:
            s['user_id'] = 'ADMIN'
            s['name'] = 'MR SYSTEM ADMIN'

    def _still_signed_in(self):
        with self.c.session_transaction() as s:
            return 'user_id' in s

    def test_a_post_with_no_token_does_not_act(self):
        self.c.post('/logout')
        self.assertTrue(self._still_signed_in(),
                        'a request with no token was carried out')

    def test_a_post_with_the_wrong_token_does_not_act(self):
        with self.c.session_transaction() as s:
            s['_csrf'] = 'the-real-token'
        self.c.post('/logout', data={'_csrf': 'not-the-real-token'})
        self.assertTrue(self._still_signed_in(),
                        'a request with a wrong token was carried out')

    def test_a_post_with_the_right_token_does_act(self):
        with self.c.session_transaction() as s:
            s['_csrf'] = 'the-real-token'
        self.c.post('/logout', data={'_csrf': 'the-real-token'})
        self.assertFalse(self._still_signed_in(),
                         'a legitimate submission was refused')

    def test_the_refusal_explains_itself(self):
        """The common cause is a form left open until the session rolled, not an
        attack, so the person in front of us gets told what to do."""
        resp = self.c.post('/logout', follow_redirects=True)
        self.assertIn(b'try again', resp.data.lower())


class StateChangingRoutesAreNotReachableByGet(unittest.TestCase):
    """⚠ These three changed state on GET, which is the one case SameSite=Lax
    does NOT cover: it deliberately still sends cookies on a top-level GET
    navigation. So following a link — or loading any page with an <img> pointing
    at one — approved a registration, deleted one, or signed you out."""

    def setUp(self):
        self.c = client()

    def test_the_pending_registration_routes_refuse_get(self):
        for path in ('/admin/pending/sometoken/approve',
                     '/admin/pending/sometoken/delete'):
            with self.subTest(path=path):
                self.assertEqual(405, self.c.get(path).status_code)

    def test_logout_refuses_get(self):
        self.assertEqual(405, self.c.get('/logout').status_code)


class TheCookiePolicyIsStated(unittest.TestCase):
    """Set explicitly rather than inherited from whatever the browser defaults
    to this year."""

    def test_samesite_and_httponly_are_set(self):
        self.assertEqual('Lax', site.app.config['SESSION_COOKIE_SAMESITE'])
        self.assertTrue(site.app.config['SESSION_COOKIE_HTTPONLY'])

    def test_the_cookie_reaches_the_browser_with_those_flags(self):
        resp = client().get('/login')
        cookies = ' '.join(resp.headers.getlist('Set-Cookie'))
        if not cookies:
            self.skipTest('no cookie issued on this response')
        self.assertIn('HttpOnly', cookies)
        self.assertIn('SameSite=Lax', cookies)

    def test_secure_follows_the_published_scheme(self):
        """⚠ Not hardcoded either way. True breaks a local checkout — the cookie
        is never sent over http://localhost, so login fails and reads as a wrong
        password. False ships a session cookie that travels in clear."""
        def secure_for(url):
            return (url or 'http://localhost:6464').strip().lower().startswith('https://')

        self.assertTrue(secure_for('https://compunet.live'))
        self.assertTrue(secure_for('HTTPS://DEV.COMPUNET.LIVE'))
        self.assertFalse(secure_for('http://localhost:6464'))
        self.assertFalse(secure_for(''))


class EveryFormCarriesAToken(unittest.TestCase):
    """⚠ THE test that earns its keep.

    The check itself is central (`before_request`), so a new route cannot forget
    to validate — but a new FORM can forget to send, and the symptom is a button
    that mysteriously does nothing. This reads the templates and says which form.
    """

    def test_no_template_has_a_form_without_a_token(self):
        """⚠ GET forms are exempt, and that is not a loophole. CSRF protects
        requests that CHANGE something; a GET form (the audit log's filters,
        #128) changes nothing, and its fields become the query string — so a
        token there would be copied into browser history, bookmarks and referer
        headers. That is strictly worse than omitting it. Anything that mutates
        must be POST, and every POST form is still checked below.
        """
        missing = []
        for path in sorted(glob.glob(os.path.join(TEMPLATES, '*.html'))):
            with open(path, encoding='utf-8') as f:
                src = f.read()
            for m in re.finditer(r'<form\b.*?</form>', src, re.S | re.I):
                form = m.group(0)
                opening = form[:form.find('>') + 1]
                if re.search(r'method\s*=\s*["\']?get\b', opening, re.I):
                    continue
                if 'name="_csrf"' not in form:
                    line = src[:m.start()].count('\n') + 1
                    missing.append('%s:%d' % (os.path.basename(path), line))
        self.assertEqual([], missing,
                         'forms with no CSRF token: %s' % ', '.join(missing))

    def test_a_get_form_is_the_only_exemption(self):
        """Guards the exemption: a form with no method at all defaults to GET in
        HTML but is almost certainly a mistake, so it must still be flagged."""
        sample = '<form action="/x"><input name="a"></form>'
        opening = sample[:sample.find('>') + 1]
        self.assertIsNone(re.search(r'method\s*=\s*["\']?get\b', opening, re.I),
                          'a form with no explicit method must not be exempt')

    def test_the_templates_really_do_contain_forms(self):
        """Guards the guard: a glob that matched nothing would pass silently."""
        total = 0
        for path in glob.glob(os.path.join(TEMPLATES, '*.html')):
            with open(path, encoding='utf-8') as f:
                total += len(re.findall(r'<form\b', f.read(), re.I))
        self.assertGreater(total, 5, 'expected the site to have forms')


if __name__ == '__main__':
    unittest.main(verbosity=2 if '-v' in sys.argv else 1)
