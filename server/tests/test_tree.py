#!/usr/bin/env python3
"""Regression tests for the directory hierarchy view (#121).

Run:  python server/tests/test_tree.py            (or -v)

The tree view lets people move, rename, reorder and delete entries, and every one
of those asks the same question: may this user change this entry? Getting that
wrong is how someone loses work, so the permission rules are tested directly
rather than through the HTTP layer.

⚠ Authorisation lives on the SERVER, not in the website. The admin API key
identifies the website rather than a person, so the website is told what a user
may do and never decides it. These tests are the check on that answer.
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_SERVER)

# The fixture tree, selected before importing the server — its data paths are
# module-level constants.
os.environ['COMPUNET_CONTENT_DIR'] = os.path.join(_SERVER, 'data', 'content.test')
sys.path.insert(0, _SERVER)

import compunet_server as srv                    # noqa: E402

ADMIN = {'admin': True}
EDITOR = {'editor': True}
PLAIN = {}

JUNGLE = 600            # authored JUNGLE, holds THE ZOO
THE_ZOO = 699           # authored PIMAN, inside JUNGLE
ASH_AND_DAVE = 612      # authored ASH+DAVE


def tree():
    return srv.CompunetDirectory()


class DuplicatePageNumbersAreRefused(unittest.TestCase):
    """⚠ Page numbers are the tree's identifier, and they are NOT unique.

    `data.example` and the fixture tree both ship page 700 twice — `DEMOS` under
    The Jungle and `FEBREVIEW FOUR` under THE ZOO. Nothing enforces uniqueness on
    load (`self.pages[num] = page` is last-wins), so both render in their listings
    while only one is reachable by number.

    Every edit addresses a page by number. With a duplicate that is ambiguous, and
    an edit would act on whichever entry loaded second — the user asks to move one
    page and a different one moves. So they are detected and refused.
    """

    def test_the_fixture_duplicate_is_found(self):
        self.assertIn(700, srv._api_duplicate_page_nums(tree()))

    def test_counted_from_the_tree_not_the_lookup_table(self):
        """`directory.pages` has already collapsed the duplicate, so counting it
        there would report no duplicates at all."""
        d = tree()
        self.assertEqual(1, sum(1 for n in d.pages if n == 700),
                         'the lookup table cannot see the duplicate')
        self.assertIn(700, srv._api_duplicate_page_nums(d))

    def test_both_duplicated_entries_are_locked(self):
        d = tree()
        dupes = srv._api_duplicate_page_nums(d)
        found = []

        def walk(page):
            if page.page_num == 700:
                editable, why = srv._api_is_editable(d, page, dupes)
                found.append((page.title, editable, why))
            for child in page.children:
                walk(child)

        walk(d.root)
        self.assertEqual(2, len(found), 'expected two entries numbered 700')
        for title, editable, why in found:
            self.assertFalse(editable, '%s should be locked' % title)
            self.assertIn('700', why)

    def test_a_unique_page_is_not_locked_by_the_duplicate(self):
        d = tree()
        editable, why = srv._api_is_editable(d, d.pages[THE_ZOO],
                                            srv._api_duplicate_page_nums(d))
        self.assertTrue(editable, why)


class WhoMayEditWhat(unittest.TestCase):

    def setUp(self):
        self.d = tree()
        self.zoo = self.d.pages[THE_ZOO]          # authored PIMAN
        self.ash = self.d.pages[ASH_AND_DAVE]     # authored ASH+DAVE

    def test_an_admin_may_edit_anything(self):
        self.assertTrue(srv._api_may_edit(self.zoo, 'NOBODY', ADMIN))

    def test_an_editor_may_edit_anything(self):
        self.assertTrue(srv._api_may_edit(self.zoo, 'NOBODY', EDITOR))

    def test_an_author_may_edit_their_own_entry(self):
        self.assertTrue(srv._api_may_edit(self.zoo, 'PIMAN', PLAIN))

    def test_an_unrelated_user_may_not(self):
        self.assertFalse(srv._api_may_edit(self.zoo, 'TEST', PLAIN))
        self.assertFalse(srv._api_may_edit(self.ash, 'PIMAN', PLAIN))

    def test_a_directory_owner_may_edit_what_is_inside_it(self):
        """THE ZOO is authored by PIMAN and sits inside JUNGLE, authored by
        JUNGLE. Owning the directory carries authority over its contents —
        without this a user cannot tidy their own space once someone else has
        uploaded into it, and since they may delete the whole directory,
        protecting the entries inside it would only be decorative."""
        self.assertEqual('PIMAN', self.zoo.author, 'fixture precondition')
        self.assertEqual('JUNGLE', self.zoo.parent.author, 'fixture precondition')
        self.assertTrue(srv._api_may_edit(self.zoo, 'JUNGLE', PLAIN))

    def test_ownership_does_not_reach_a_grandchild(self):
        """One level only: owning JUNGLE does not confer authority over what is
        inside THE ZOO, which PIMAN owns. Otherwise owning a directory near the
        root would carry the whole subtree beneath it."""
        grandchild = next(c for c in self.zoo.children if c.page_num != 700)
        self.assertFalse(srv._api_may_edit(grandchild, 'JUNGLE', PLAIN))
        self.assertTrue(srv._api_may_edit(grandchild, 'PIMAN', PLAIN))


class SomeEntriesCannotBeEditedByAnyone(unittest.TestCase):

    def setUp(self):
        self.d = tree()

    def _reason(self, page):
        return srv._api_is_editable(self.d, page)[1]

    def test_the_root_is_locked(self):
        editable, why = srv._api_is_editable(self.d, self.d.root)
        self.assertFalse(editable)
        self.assertIn('root', why)

    def test_a_generated_page_is_locked(self):
        """WHO IS ONLINE and WHAT'S NEW are built on read — no folder to move,
        no file to archive."""
        dynamic = [p for p in self.d.pages.values() if getattr(p, 'dynamic', None)]
        if not dynamic:
            self.skipTest('fixture has no dynamic page')
        for page in dynamic:
            editable, why = srv._api_is_editable(self.d, page)
            self.assertFalse(editable, page.title)
            self.assertIn('generated', why)

    def test_a_link_is_locked(self):
        links = [p for p in self.d.pages.values() if p.page_type == 'L']
        if not links:
            self.skipTest('fixture has no link entry')
        for page in links:
            editable, why = srv._api_is_editable(self.d, page)
            self.assertFalse(editable, page.title)
            self.assertIn('link', why)

    def test_locked_entries_are_reported_not_hidden(self):
        """Every refusal carries a reason. Filtering these out instead would make
        an admin think the view had lost a page they know exists."""
        for page in self.d.pages.values():
            editable, why = srv._api_is_editable(self.d, page)
            if not editable:
                self.assertTrue(why, '%s locked with no reason' % page.title)


class WhoMayAddHere(unittest.TestCase):
    """`_api_may_add_here` must agree with `_can_upload_here`, which is what the
    clients enforce. It takes a page as an argument because the website is not
    sitting in a directory the way a session is."""

    def setUp(self):
        self.d = tree()

    def _session_says(self, page, user_id, user_data):
        """The same question, asked through the client's own code path."""
        s = srv.CompunetSession(self.d)
        s.user_id = user_id
        s.is_admin = user_data.get('admin', False)
        s.is_editor = user_data.get('editor', False)
        s.current_page = page
        return s._can_upload_here()

    def test_it_matches_the_clients_rule_everywhere(self):
        cases = [('TEST', PLAIN), ('PIMAN', PLAIN), ('JUNGLE', PLAIN),
                 ('NOBODY', ADMIN), ('NOBODY', EDITOR)]
        for page in self.d.pages.values():
            for user_id, user_data in cases:
                with self.subTest(page=page.title, user=user_id,
                                  role=list(user_data) or 'plain'):
                    self.assertEqual(
                        self._session_says(page, user_id, user_data),
                        srv._api_may_add_here(page, user_id, user_data))

    def test_an_explicit_opt_out_still_admits_its_owner(self):
        """THE ZOO sets open_upload false. Its owner is never locked out of their
        own directory by that."""
        zoo = self.d.pages[THE_ZOO]
        self.assertIs(False, getattr(zoo, 'open_upload', None),
                      'fixture precondition')
        self.assertFalse(srv._api_may_add_here(zoo, 'TEST', PLAIN))
        self.assertTrue(srv._api_may_add_here(zoo, 'PIMAN', PLAIN))


if __name__ == '__main__':
    unittest.main(verbosity=2 if '-v' in sys.argv else 1)
