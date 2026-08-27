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

import json
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


class TheShippedTreesHaveUniquePageNumbers(unittest.TestCase):
    """A guard, not a formality.

    `data.example` and the fixture both shipped page 700 twice — `DEMOS` under The
    Jungle and `FEBREVIEW FOUR` under THE ZOO — for long enough that it reached
    the tracked content. `GOTO 700` could only ever reach one of them, and an edit
    addressed by number would have acted on whichever loaded second. DEMOS is now
    604, back in sequence with its siblings.

    This fails the moment a duplicate is reintroduced by hand, which is the only
    way one can now appear.
    """

    def test_the_fixture_tree_is_clean(self):
        d = tree()
        self.assertEqual(set(), srv._api_duplicate_page_nums(d))

    def test_every_tree_entry_is_reachable_by_its_number(self):
        """The consequence of uniqueness worth stating: a refused duplicate is a
        page nothing can address."""
        d = tree()
        missing = []

        def walk(page):
            if d.pages.get(page.page_num) is not page:
                missing.append((page.page_num, page.title))
            for child in page.children:
                walk(child)

        walk(d.root)
        self.assertEqual([], missing,
                         'entries not reachable by their own page number')


class AWindowsWrittenTreeStillLoads(unittest.TestCase):
    """The reader must accept what older writers produced (#141).

    ⚠ The tracked trees are clean and `TheShippedTreesUsePortablePaths` keeps
    them that way — but that guards the FIXTURES, not the trees already on disk
    elsewhere. The writer only started normalising separators after the problem
    was found, so every tree written before that still records its children as
    `jungle\\directory.json`, and on this host `os.path.join` turns that into a
    filename nothing matches. The sub-tree then vanishes from the service with
    its files intact.

    So this builds the broken shape deliberately, which is the only way it can
    now occur, and asserts the reader copes.
    """

    def setUp(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix='compunet-winpath-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')

    def tearDown(self):
        import shutil
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _rewrite(self, rel, replacements):
        path = os.path.join(srv.ROOT_DIR, *rel)
        with open(path) as f:
            text = f.read()
        for old, new in replacements:
            self.assertIn(old, text, 'fixture no longer contains %r' % old)
            text = text.replace(old, new)
        with open(path, 'w') as f:
            f.write(text)

    def test_the_pages_inside_a_backslash_path_are_still_reachable(self):
        """⚠ Assert the CONTENTS, not the entry.

        THE ZOO itself survives a broken path — the loader builds the page from
        the parent's node, so it is still listed and still addressable. What
        disappears is everything the sub-directory JSON holds, which is the part
        a user would go looking for. An assertion on `THE_ZOO in d.pages` passes
        with the bug fully present, and that is worth stating: it is the exact
        shape of test that let this survive.
        """
        self._rewrite(('jungle', 'directory.json'),
                      [('"jungle/the-zoo/directory.json"',
                        '"jungle\\\\the-zoo\\\\directory.json"')])
        d = tree()
        self.assertIn(THE_ZOO, d.pages, 'THE ZOO itself should never be lost')
        for page_num, title in ((701, 'MARCH'), (714, 'JULY'), (721, 'ZOO INTERVIEW')):
            self.assertIn(page_num, d.pages,
                          '%s (%d) lost to a Windows separator' % (title, page_num))

    def test_the_sub_trees_own_children_survive_too(self):
        """Normalising only the top level would leave the same hole one level
        down — which is exactly how the fixture sweep went wrong (#138)."""
        self._rewrite(('jungle', 'directory.json'),
                      [('"jungle/the-zoo/directory.json"',
                        '"jungle\\\\the-zoo\\\\directory.json"')])
        d = tree()
        zoo = d.pages[THE_ZOO]
        self.assertTrue(zoo.children, 'THE ZOO loaded but lost its own children')

    def test_an_unresolvable_sub_directory_is_reported(self):
        """⚠ The other half, and the reason this went unnoticed for so long:
        the loader skipped a sub-directory it could not find WITHOUT SAYING SO.
        The only symptom was a listing that was shorter than it should be."""
        self._rewrite(('jungle', 'directory.json'),
                      [('"jungle/the-zoo/directory.json"',
                        '"jungle/nowhere-at-all/directory.json"')])
        with self.assertLogs('compunet', level='WARNING') as captured:
            tree()
        blob = '\n'.join(captured.output)
        self.assertIn('nowhere-at-all', blob, 'the broken path is not named')
        self.assertIn(str(THE_ZOO), blob, 'the page it belongs to is not named')


class TheShippedTreesUsePortablePaths(unittest.TestCase):
    """A sub-directory recorded with a Windows separator is INVISIBLE on the
    host that serves this tree.

    `content.test` recorded its children as `jungle\\directory.json`. That
    resolves on Windows and nowhere else, so on macOS and on the Linux host the
    sub-tree simply was not there — the whole of `test_terminal` and 41 of this
    file's 55 tests failed, and `test_api_binding` reported entries missing by
    page number (#138). The tree WRITER already normalises this and says why;
    the tracked fixture predated it.

    ⚠ Walk to ANY DEPTH. The first pass at this fixed `root.json` and
    `jungle/directory.json` and declared victory, because the check only looked
    two levels down — `jungle/the-zoo/directory.json` kept four more, and every
    test still passed because nothing happened to descend that far. A guard that
    stops where the bug was last seen is not a guard.
    """

    # ⚠ `data.example` holds its tree under `content/`, not at its own root.
    # The first version of this named the directory itself, so the existence
    # check below hit `if not os.path.isdir(...): continue` and skipped the
    # whole tree in silence — a guard quietly guarding nothing, which is the
    # very shape of bug it was written to catch. It was hiding three dangling
    # entries (GRAPHICS, MUSIC and DEMOS).
    TREES = ('data/content.test', 'data.example/content')

    def test_no_sub_directory_path_uses_a_windows_separator(self):
        offenders = []
        for rel in self.TREES:
            for base, _dirs, files in os.walk(os.path.join(_SERVER, rel)):
                for name in files:
                    if not name.endswith('.json'):
                        continue
                    path = os.path.join(base, name)
                    with open(path, encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                        except ValueError:
                            continue
                    if not isinstance(data, dict):
                        continue
                    for page in data.get('pages', []):
                        target = isinstance(page, dict) and page.get('directory')
                        if target and '\\' in target:
                            offenders.append('%s -> %s'
                                             % (os.path.relpath(path, _SERVER), target))
        self.assertEqual([], offenders,
                         'sub-directory paths that will not resolve off Windows')

    def test_every_sub_directory_path_exists_on_disk(self):
        """The other half: a path that resolves but points nowhere is the same
        invisible sub-tree, and separator-only checking would not catch it."""
        missing = []
        for rel in self.TREES:
            root = os.path.join(_SERVER, rel)
            content_root = os.path.join(root, 'root')
            self.assertTrue(os.path.isdir(content_root),
                            'no tree at %s — this guard would silently pass' % content_root)
            for base, _dirs, files in os.walk(content_root):
                for name in files:
                    if name != 'directory.json' and name != 'root.json':
                        continue
                    path = os.path.join(base, name)
                    with open(path, encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                        except ValueError:
                            continue
                    for page in data.get('pages', []):
                        target = isinstance(page, dict) and page.get('directory')
                        if target and not os.path.exists(
                                os.path.join(content_root, target)):
                            missing.append('%s -> %s'
                                           % (os.path.relpath(path, _SERVER), target))
        self.assertEqual([], missing, 'sub-directory entries pointing nowhere')


class ADuplicatePageNumberIsRefused(unittest.TestCase):
    """⚠ Page numbers are the tree's identity: `GOTO` resolves through them and
    every edit addresses a page by one. A repeated number is therefore ambiguous,
    and the loader used to accept it silently — a plain `pages[num] = page`, so the
    later entry overwrote the earlier one, which stayed visible in its listing
    while becoming unreachable.

    The duplicate is deliberately NOT auto-renumbered: that would change a
    user-visible identifier nobody asked to change, break bookmarks and `GOTO`,
    and disagree with what is on disk. First occurrence wins, so the outcome does
    not depend on load order, and the collision is reported.

    The trees no longer contain one, so this builds it — which also tests the only
    way it can now happen, a hand-edited file.
    """

    def setUp(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix='compunet-dupe-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')

        # Give GRAPHICS the number THE ZOO already has.
        import json
        path = os.path.join(srv.ROOT_DIR, 'jungle', 'directory.json')
        with open(path) as f:
            data = json.load(f)
        for node in data['pages']:
            if node['title'] == 'GRAPHICS':
                node['page_num'] = THE_ZOO
                break
        else:
            self.skipTest('fixture has no GRAPHICS entry')
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def tearDown(self):
        import shutil
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_the_collision_is_reported(self):
        self.assertIn(THE_ZOO, srv._api_duplicate_page_nums(tree()))

    def test_the_first_entry_keeps_the_number(self):
        """Deterministic rather than load-order dependent. THE ZOO is listed
        before GRAPHICS in the fixture, so it keeps 699."""
        d = tree()
        self.assertEqual('THE ZOO', d.pages[THE_ZOO].title)

    def test_the_lookup_table_alone_cannot_reveal_it(self):
        """Why the loader records duplicates instead of anything recounting them
        from `pages` afterwards: the refused entry never gets in there."""
        d = tree()
        self.assertEqual(1, sum(1 for n in d.pages if n == THE_ZOO))
        self.assertIn(THE_ZOO, srv._api_duplicate_page_nums(d))

    def test_both_colliding_entries_are_locked(self):
        d = tree()
        dupes = srv._api_duplicate_page_nums(d)
        found = []

        def walk(page):
            if page.page_num == THE_ZOO:
                editable, why = srv._api_is_editable(d, page, dupes)
                found.append((page.title, editable, why))
            for child in page.children:
                walk(child)

        walk(d.root)
        self.assertEqual(2, len(found), 'expected two entries sharing the number')
        for title, editable, why in found:
            self.assertFalse(editable, '%s should be locked' % title)
            self.assertIn(str(THE_ZOO), why)

    def test_an_unaffected_page_stays_editable(self):
        d = tree()
        editable, why = srv._api_is_editable(d, d.pages[JUNGLE],
                                            srv._api_duplicate_page_nums(d))
        self.assertTrue(editable, why)

    def test_a_new_page_number_avoids_the_hidden_entry(self):
        """`max(pages)` cannot see a refused duplicate, so allocation walks the
        tree instead — otherwise a new upload could be handed a number already in
        use further down."""
        d = tree()
        used = set()

        def walk(page):
            used.add(page.page_num)
            for child in page.children:
                walk(child)

        walk(d.root)
        self.assertNotIn(d.next_page_num(), used)


class RenamingMovesTheFolderToo(unittest.TestCase):
    """A page's folder is named from its title (`<parent>/<slug(title)>`), so a
    rename is a filesystem operation — which is why rename and move are one
    function. These run against a temp copy of the fixture."""

    def setUp(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix='compunet-rename-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')
        self.d = tree()

    def tearDown(self):
        import shutil
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _rel(self, path):
        return os.path.relpath(path, srv.ROOT_DIR).replace(os.sep, '/')

    def _save(self, affected):
        for node in affected:
            srv.save_one_directory(node, srv.ROOT_DIR)

    def test_the_folder_follows_the_title(self):
        page = self.d.pages[ASH_AND_DAVE]
        old_dir = page._dir_path
        self.assertTrue(os.path.isdir(old_dir), 'fixture precondition')

        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_title='ASH PLUS DAVE'))

        self.assertFalse(os.path.exists(old_dir), 'the old folder is still there')
        self.assertTrue(os.path.isdir(page._dir_path))
        self.assertEqual('jungle/ash-plus-dave', self._rel(page._dir_path))

    def test_a_renamed_directory_keeps_its_header(self):
        """⚠ THE failure this rewrite exists to stop.

        A header is stored as a path relative to ROOT_DIR (#120), not relative to
        the directory that owns it. Rename the directory and the folder moves, so
        the stored path points at nothing — and the header simply stops appearing,
        in every binding, with nothing logged. Nothing else in the tree stores a
        path like that, which is exactly why it is easy to miss.
        """
        page = self.d.pages[ASH_AND_DAVE]
        self.assertEqual('jungle/ash-and-dave/header.seq', page.header,
                         'fixture precondition')

        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_title='ASH PLUS DAVE'))

        self.assertEqual('jungle/ash-plus-dave/header.seq', page.header)
        self.assertTrue(
            os.path.exists(os.path.join(srv.ROOT_DIR, *page.header.split('/'))),
            'the header path does not resolve to a file')

        # And it survives a reload — the value was persisted, not just patched
        # in memory.
        reloaded = tree().pages[ASH_AND_DAVE]
        self.assertEqual('jungle/ash-plus-dave/header.seq', reloaded.header)

    def test_descendants_follow_and_stay_loadable(self):
        page = self.d.pages[THE_ZOO]
        before = {p.page_num for p in srv._subtree(page)}
        self.assertGreater(len(before), 1, 'fixture precondition: ZOO has children')

        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_title='THE ZOO ANNEX'))

        reloaded = tree()
        after = {p.page_num for p in srv._subtree(reloaded.pages[THE_ZOO])}
        self.assertEqual(before, after,
                         'the subtree did not survive the rename')
        for node in srv._subtree(reloaded.pages[THE_ZOO]):
            self.assertTrue(os.path.isdir(node._dir_path),
                            '%s has no folder' % node.title)

    def test_a_colliding_title_is_refused(self):
        """Two entries in one directory cannot share a folder."""
        jungle = self.d.pages[JUNGLE]
        victim = self.d.pages[ASH_AND_DAVE]
        other = next(c for c in jungle.children if c is not victim)
        with self.assertRaises(srv.RelocateError) as caught:
            srv.relocate_page(self.d, victim, srv.ROOT_DIR,
                              new_title=other.title)
        self.assertIn('same folder', str(caught.exception))

    def test_an_empty_title_is_refused(self):
        with self.assertRaises(srv.RelocateError):
            srv.relocate_page(self.d, self.d.pages[ASH_AND_DAVE], srv.ROOT_DIR,
                              new_title='   ')

    def test_a_title_is_truncated_not_rejected(self):
        page = self.d.pages[ASH_AND_DAVE]
        srv.relocate_page(self.d, page, srv.ROOT_DIR,
                          new_title='A' * 40)
        self.assertEqual(srv.MAX_TITLE, len(page.title))

    def test_the_root_cannot_be_renamed(self):
        with self.assertRaises(srv.RelocateError):
            srv.relocate_page(self.d, self.d.root, srv.ROOT_DIR, new_title='NOPE')

    def test_renaming_touches_only_the_directories_involved(self):
        """The Phase 2 rule still holds for a rename: everything it writes is
        something it changed."""
        def mtimes():
            found = {}
            for base, _dirs, files in os.walk(srv.ROOT_DIR):
                for name in files:
                    if name in ('directory.json', 'root.json'):
                        p = os.path.join(base, name)
                        found[p] = os.stat(p).st_mtime_ns
            return found

        before = mtimes()
        page = self.d.pages[ASH_AND_DAVE]
        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_title='ASH PLUS DAVE'))
        touched = {p for p, t in mtimes().items() if before.get(p) != t}
        # Its parent (the entry list) and its own JSON (moved, so its child
        # `directory` paths changed). Not the root, not its siblings' subtrees.
        allowed = {os.path.join(srv.ROOT_DIR, 'jungle', 'directory.json'),
                   os.path.join(srv.ROOT_DIR, 'jungle', 'ash-plus-dave',
                                'directory.json')}
        self.assertFalse(touched - allowed,
                         'rename rewrote unrelated directories: %s'
                         % sorted(self._rel(p) for p in touched - allowed))


class MovingBetweenDirectories(unittest.TestCase):
    """The same `relocate_page` as a rename, with a destination. Run against a
    temp copy of the fixture."""

    def setUp(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix='compunet-move-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')
        self.d = tree()

    def tearDown(self):
        import shutil
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _save(self, affected):
        for node in affected:
            srv.save_one_directory(node, srv.ROOT_DIR)

    def _rel(self, path):
        return os.path.relpath(path, srv.ROOT_DIR).replace(os.sep, '/')

    def test_an_entry_lands_in_the_destination(self):
        page = self.d.pages[ASH_AND_DAVE]        # in JUNGLE
        dest = self.d.pages[THE_ZOO]
        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR, new_parent=dest))

        reloaded = tree()
        moved = reloaded.pages[ASH_AND_DAVE]
        self.assertEqual(THE_ZOO, moved.parent.page_num)
        self.assertNotIn(ASH_AND_DAVE,
                         [c.page_num for c in reloaded.pages[JUNGLE].children])
        self.assertTrue(os.path.isdir(moved._dir_path))

    def test_the_page_number_is_unchanged(self):
        """Why moving is safe to offer: `GOTO <n>` and keyword lookups survive
        it, because the number is not derived from the location."""
        page = self.d.pages[ASH_AND_DAVE]
        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_parent=self.d.pages[THE_ZOO]))
        self.assertEqual(ASH_AND_DAVE, tree().pages[ASH_AND_DAVE].page_num)

    def test_a_moved_directory_keeps_its_header(self):
        """The same silent failure as a rename: a header is stored relative to
        ROOT_DIR, so the path is wrong the moment the folder moves."""
        page = self.d.pages[ASH_AND_DAVE]
        self.assertEqual('jungle/ash-and-dave/header.seq', page.header,
                         'fixture precondition')
        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_parent=self.d.pages[THE_ZOO]))

        reloaded = tree().pages[ASH_AND_DAVE]
        self.assertEqual('jungle/the-zoo/ash-and-dave/header.seq',
                         reloaded.header)
        self.assertTrue(os.path.exists(
            os.path.join(srv.ROOT_DIR, *reloaded.header.split('/'))))

    def test_the_whole_subtree_comes_along(self):
        page = self.d.pages[ASH_AND_DAVE]
        before = {p.page_num for p in srv._subtree(page)}
        self.assertGreater(len(before), 1, 'fixture precondition')

        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_parent=self.d.pages[THE_ZOO]))

        reloaded = tree()
        after = {p.page_num for p in srv._subtree(reloaded.pages[ASH_AND_DAVE])}
        self.assertEqual(before, after)
        for node in srv._subtree(reloaded.pages[ASH_AND_DAVE]):
            self.assertTrue(os.path.isdir(node._dir_path),
                            '%s lost its folder' % node.title)

    def test_a_directory_cannot_be_moved_into_itself(self):
        """It would be moved inside its own child: unreachable from the root
        while still sitting on disk."""
        zoo = self.d.pages[THE_ZOO]
        inside = next(c for c in zoo.children if c.children) if any(
            c.children for c in zoo.children) else zoo.children[0]
        with self.assertRaises(srv.RelocateError) as caught:
            srv.relocate_page(self.d, zoo, srv.ROOT_DIR, new_parent=inside)
        self.assertIn('into itself', str(caught.exception))

    def test_a_directory_cannot_be_moved_into_its_own_child_directory(self):
        zoo = self.d.pages[THE_ZOO]
        with self.assertRaises(srv.RelocateError):
            srv.relocate_page(self.d, zoo, srv.ROOT_DIR, new_parent=zoo)

    def test_a_full_destination_is_refused(self):
        """A directory holds at most 11 entries."""
        dest = self.d.pages[THE_ZOO]
        page = self.d.pages[ASH_AND_DAVE]
        # Pad the destination to the limit with stand-in children.
        while len(dest.children) < 11:
            filler = srv.CompunetPage(
                page_num=self.d.next_page_num(), title='FILL%d' % len(dest.children),
                page_type='T')
            filler.parent = dest
            filler._dir_path = os.path.join(dest._dir_path, 'fill')
            dest.children.append(filler)
            self.d.pages[filler.page_num] = filler

        with self.assertRaises(srv.RelocateError) as caught:
            srv.relocate_page(self.d, page, srv.ROOT_DIR, new_parent=dest)
        self.assertIn('full', str(caught.exception))

    def test_a_colliding_title_in_the_destination_is_refused(self):
        page = self.d.pages[ASH_AND_DAVE]
        dest = self.d.pages[THE_ZOO]
        clash = dest.children[0]
        with self.assertRaises(srv.RelocateError) as caught:
            srv.relocate_page(self.d, page, srv.ROOT_DIR, new_parent=dest,
                              new_title=clash.title)
        self.assertIn('same folder', str(caught.exception))

    def test_moving_touches_only_the_directories_involved(self):
        def mtimes():
            found = {}
            for base, _dirs, files in os.walk(srv.ROOT_DIR):
                for name in files:
                    if name in ('directory.json', 'root.json'):
                        p = os.path.join(base, name)
                        found[p] = os.stat(p).st_mtime_ns
            return found

        before = mtimes()
        page = self.d.pages[ASH_AND_DAVE]
        self._save(srv.relocate_page(self.d, page, srv.ROOT_DIR,
                                     new_parent=self.d.pages[THE_ZOO]))
        touched = {p for p, t in mtimes().items() if before.get(p) != t}
        allowed = {
            os.path.join(srv.ROOT_DIR, 'jungle', 'directory.json'),        # source
            os.path.join(srv.ROOT_DIR, 'jungle', 'the-zoo', 'directory.json'),
            os.path.join(srv.ROOT_DIR, 'jungle', 'the-zoo', 'ash-and-dave',
                         'directory.json'),                                # itself
        }
        self.assertFalse(touched - allowed,
                         'a move rewrote unrelated directories: %s'
                         % sorted(self._rel(p) for p in touched - allowed))


class ReorderingChangesTheListing(unittest.TestCase):

    def setUp(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix='compunet-reorder-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')
        self.d = tree()

    def tearDown(self):
        import shutil
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_an_entry_moves_to_the_position_asked_for(self):
        jungle = self.d.pages[JUNGLE]
        last = jungle.children[-1]
        srv.reorder_child(jungle, last, 0)
        self.assertIs(last, jungle.children[0])

    def test_the_new_order_survives_a_reload(self):
        """The listing order IS the JSON order, so this is the whole feature."""
        jungle = self.d.pages[JUNGLE]
        last = jungle.children[-1]
        srv.reorder_child(jungle, last, 0)
        srv.save_one_directory(jungle, srv.ROOT_DIR)

        reloaded = tree().pages[JUNGLE]
        self.assertEqual(last.page_num, reloaded.children[0].page_num)

    def test_nothing_is_lost_or_duplicated(self):
        jungle = self.d.pages[JUNGLE]
        before = [c.page_num for c in jungle.children]
        srv.reorder_child(jungle, jungle.children[2], 0)
        self.assertEqual(sorted(before),
                         sorted(c.page_num for c in jungle.children))

    def test_a_position_outside_the_listing_is_refused(self):
        jungle = self.d.pages[JUNGLE]
        for bad in (-1, len(jungle.children)):
            with self.assertRaises(srv.RelocateError):
                srv.reorder_child(jungle, jungle.children[0], bad)

    def test_reordering_writes_no_files_on_disk(self):
        """It changes one list. Nothing moves."""
        jungle = self.d.pages[JUNGLE]
        folders = sorted(d for d, _s, _f in os.walk(srv.ROOT_DIR))
        srv.reorder_child(jungle, jungle.children[-1], 0)
        srv.save_one_directory(jungle, srv.ROOT_DIR)
        self.assertEqual(folders, sorted(d for d, _s, _f in os.walk(srv.ROOT_DIR)))


class DeletingArchivesEverythingFirst(unittest.TestCase):
    """Delete follows the path negative `LIFE` already took — archive, then
    remove — so the same act through two interfaces leaves the same trace.

    ⚠ The archiver did NOT recurse. It copied a page's own frames and stopped, so
    removing a *directory* left its whole subtree on disk: unreachable and
    unarchived, content silently lost, from a command users already had. That
    became urgent once a directory's owner could delete the directory with other
    people's pages inside it.
    """

    def setUp(self):
        import shutil
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix='compunet-del-')
        shutil.copytree(os.path.join(_SERVER, 'data', 'content.test', 'root'),
                        os.path.join(self._tmp, 'root'))
        self._saved_root = srv.ROOT_DIR
        srv.ROOT_DIR = os.path.join(self._tmp, 'root')
        self._data = self._tmp                 # archive/ lands beside root/
        self.d = tree()

    def tearDown(self):
        import shutil
        srv.ROOT_DIR = self._saved_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _archived(self):
        base = os.path.join(self._data, 'archive')
        return sorted(os.listdir(base)) if os.path.isdir(base) else []

    def test_a_leaf_is_archived_and_removed(self):
        page = next(c for c in self.d.pages[THE_ZOO].children if not c.children)
        num, title, parent = page.page_num, page.title, page.parent

        archived, _refunds = srv.delete_page(self.d, page, self._data, srv.ROOT_DIR)
        # The caller persists, exactly as relocate_page leaves it to the caller —
        # without this the entry is gone from memory and disk while its parent's
        # JSON still lists it, so a reload brings back a page with no files.
        srv.save_one_directory(parent, srv.ROOT_DIR)

        self.assertEqual(1, len(archived))
        self.assertNotIn(num, tree().pages)
        self.assertTrue(any(str(num) in name for name in self._archived()),
                        '%s was not archived' % title)

    def test_a_directory_takes_its_whole_subtree_to_the_archive(self):
        """The regression. Every descendant gets its own archive folder, so the
        subtree arrives as recoverable entries rather than vanishing."""
        page = self.d.pages[ASH_AND_DAVE]
        doomed = srv._subtree(page)
        self.assertGreater(len(doomed), 1, 'fixture precondition')
        expected = {p.page_num for p in doomed}

        archived, _refunds = srv.delete_page(self.d, page, self._data, srv.ROOT_DIR)

        self.assertEqual(len(expected), len(archived),
                         'not every entry in the subtree was archived')
        names = ' '.join(self._archived())
        for num in expected:
            self.assertIn(str(num), names, 'page %d missing from the archive' % num)

    def test_every_archived_entry_carries_metadata(self):
        page = self.d.pages[ASH_AND_DAVE]
        archived, _ = srv.delete_page(self.d, page, self._data, srv.ROOT_DIR)
        for dest in archived:
            meta_path = os.path.join(dest, 'metadata.json')
            self.assertTrue(os.path.exists(meta_path), dest)
            with open(meta_path) as f:
                meta = json.load(f)
            for key in ('page_num', 'title', 'author', 'life', 'reason'):
                self.assertIn(key, meta)
            self.assertEqual('deleted', meta['reason'])

    def test_a_descendant_records_where_it_sat(self):
        """Nothing reads the archive back, so the metadata has to be enough to
        rebuild the shape by hand — not just the files."""
        page = self.d.pages[ASH_AND_DAVE]
        archived, _ = srv.delete_page(self.d, page, self._data, srv.ROOT_DIR)
        found = []
        for dest in archived:
            with open(os.path.join(dest, 'metadata.json')) as f:
                meta = json.load(f)
            if meta['page_num'] != ASH_AND_DAVE:
                found.append(meta)
        self.assertTrue(found, 'expected descendants')
        for meta in found:
            self.assertIn('was_inside', meta)
            self.assertIn('was_inside_page', meta)

    def test_a_directory_header_is_archived_too(self):
        """A header is the directory's own artwork, and would otherwise be the one
        thing not recoverable."""
        page = self.d.pages[ASH_AND_DAVE]
        self.assertTrue(page.header, 'fixture precondition')
        header_name = page.header.split('/')[-1]

        archived, _ = srv.delete_page(self.d, page, self._data, srv.ROOT_DIR)

        own = next(d for d in archived if ('%d-' % ASH_AND_DAVE) in os.path.basename(d))
        self.assertTrue(os.path.exists(os.path.join(own, header_name)),
                        'the header was not archived')

    def test_the_files_are_gone_afterwards(self):
        page = self.d.pages[ASH_AND_DAVE]
        page_dir = page._dir_path
        self.assertTrue(os.path.isdir(page_dir), 'fixture precondition')
        srv.delete_page(self.d, page, self._data, srv.ROOT_DIR)
        self.assertFalse(os.path.exists(page_dir))

    def test_the_tree_reloads_clean(self):
        page = self.d.pages[ASH_AND_DAVE]
        gone = {p.page_num for p in srv._subtree(page)}
        srv.delete_page(self.d, page, self._data, srv.ROOT_DIR)
        srv.save_one_directory(page.parent if page.parent else self.d.root,
                              srv.ROOT_DIR)

        reloaded = tree()
        self.assertEqual(set(), gone & set(reloaded.pages),
                         'deleted entries came back after a reload')
        self.assertEqual(set(), srv._api_duplicate_page_nums(reloaded))

    def test_storage_is_refunded_to_each_author_not_the_deleter(self):
        """⚠ An admin clearing someone's directory must not credit or charge
        themselves. The quota the content consumed belongs to its author."""
        page = self.d.pages[ASH_AND_DAVE]
        authors = {p.author for p in srv._subtree(page) if p.life > 0}
        self.assertTrue(authors, 'fixture precondition: something has life')

        _archived, refunds = srv.delete_page(self.d, page, self._data,
                                             srv.ROOT_DIR)

        self.assertTrue(refunds)
        self.assertTrue(set(refunds) <= authors,
                        'refunded someone who did not author the content')
        for author, units in refunds.items():
            self.assertGreater(units, 0)

    def test_the_refund_matches_frames_times_life(self):
        """The same formula negative LIFE uses, so the two routes agree."""
        page = next(c for c in self.d.pages[THE_ZOO].children
                    if not c.children and c.life > 0 and c.frames)
        expected = len(page.frames) * page.life
        author = page.author

        _archived, refunds = srv.delete_page(self.d, page, self._data,
                                             srv.ROOT_DIR)
        self.assertEqual(expected, refunds.get(author))

    def test_the_root_cannot_be_deleted(self):
        with self.assertRaises(srv.RelocateError):
            srv.delete_page(self.d, self.d.root, self._data, srv.ROOT_DIR)


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
        grandchild = self.zoo.children[0]
        self.assertFalse(srv._api_may_edit(grandchild, 'JUNGLE', PLAIN))
        self.assertTrue(srv._api_may_edit(grandchild, 'PIMAN', PLAIN))


class SomeEntriesCannotBeEditedByAnyone(unittest.TestCase):

    def setUp(self):
        self.d = tree()

    def _reason(self, page):
        return srv._api_is_editable(self.d, page)[1]

    def test_the_root_cannot_be_restructured(self):
        """It has no parent, so nowhere to move it and no siblings to reorder
        within; and its title is hardcoded in the loader rather than stored in
        root.json, so a rename would have nothing to write to."""
        editable, why = srv._api_is_editable(self.d, self.d.root)
        self.assertFalse(editable)
        self.assertIn('cannot be moved, renamed or deleted', why)

    def test_the_root_can_still_have_its_settings_changed(self):
        """⚠ The case that forces `_api_is_editable` and `_api_may_configure_dir`
        apart. The root cannot be restructured, but root.json carries a `header`
        and always has — gating the header control on editability hid it in the
        tree while /directories/settings went on offering it, so the two views
        disagreed about the same directory."""
        self.assertFalse(srv._api_is_editable(self.d, self.d.root)[0])
        self.assertTrue(
            srv._api_may_configure_dir(self.d, self.d.root, 'NOBODY', ADMIN),
            'an admin must still be able to set the root header')
        self.assertTrue(
            srv._api_may_configure_dir(self.d, self.d.root, 'NOBODY', EDITOR))

    def test_an_ordinary_user_cannot_configure_the_root(self):
        self.assertFalse(
            srv._api_may_configure_dir(self.d, self.d.root, 'TEST', PLAIN))

    def test_something_that_is_not_a_directory_is_not_configurable(self):
        """Only a directory has a header frame or an upload setting.

        ⚠ "not a directory" is not the same as "type T". An entry can be BOTH a
        page and a directory — that is the latent-directory model (§7.3) — so a
        text page with a directory.json of its own does legitimately have a header.
        The test has to select on `_api_is_directory`, not on page type; selecting
        on type T asserted the opposite of the rule and failed.
        """
        plain = [p for p in self.d.pages.values()
                 if not srv._api_is_directory(self.d, p)]
        if not plain:
            self.skipTest('every fixture entry doubles as a directory')
        for page in plain:
            with self.subTest(page=page.title):
                self.assertFalse(
                    srv._api_may_configure_dir(self.d, page, 'NOBODY', ADMIN))

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
