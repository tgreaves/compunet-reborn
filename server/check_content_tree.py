#!/usr/bin/env python3
"""Report content-tree entries the server will silently fail to load.

    python3 server/check_content_tree.py [CONTENT_DIR]

With no argument it uses $COMPUNET_CONTENT_DIR, falling back to
server/data/content — the same resolution the server does, so running it on the
host with the service's own environment checks the tree actually being served.

READ-ONLY. It opens JSON files and stats paths; it writes nothing and needs no
dependencies beyond the standard library, so it can be dropped onto a server and
run without installing anything.

Two faults, both of which make a whole branch of the service vanish while every
file for it sits on disk:

  SEPARATOR   `"directory": "jungle\\directory.json"` resolves on Windows and
              nowhere else. The writer has normalised to forward slashes since
              it learned this; trees written before that fix still carry them.

  MISSING     A `directory` value that resolves but points at no file. Same
              symptom, different cause, and a separator-only check misses it.

Exit status is 1 if anything is found, so it can be wired into a deploy check.
"""

import json
import os
import sys


def _entries(path):
    """Yield (page_num, title, directory_value) for one JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print('  ?? unreadable: %s (%s)' % (path, exc))
        return
    if not isinstance(data, dict):
        return
    for page in data.get('pages', []):
        if isinstance(page, dict) and page.get('directory'):
            yield page.get('page_num'), page.get('title'), page['directory']


def check(content_dir):
    root = os.path.join(content_dir, 'root')
    if not os.path.isdir(root):
        print('No tree at %s (expected a "root" directory inside it)' % content_dir)
        return 2

    separator, missing, files = [], [], 0
    # ⚠ Walk to ANY DEPTH. A check that stops where the fault was last seen is
    # not a check: the first sweep of the test fixture looked two levels down,
    # fixed six entries, and left four untouched three levels below (#138).
    for base, _dirs, names in os.walk(root):
        for name in names:
            if not name.endswith('.json'):
                continue
            path = os.path.join(base, name)
            files += 1
            for page_num, title, value in _entries(path):
                where = '%s  page %s "%s"' % (os.path.relpath(path, content_dir),
                                              page_num, title)
                if '\\' in value:
                    separator.append('%s\n      -> %s' % (where, value))
                    continue
                if not os.path.exists(os.path.join(root, value)):
                    missing.append('%s\n      -> %s' % (where, value))

    print('Checked %d JSON files under %s\n' % (files, root))
    for label, hits in (('Windows separators (invisible off Windows)', separator),
                        ('Sub-directories that do not exist', missing)):
        if hits:
            print('%s: %d' % (label, len(hits)))
            for h in hits:
                print('   %s' % h)
            print()
    if not separator and not missing:
        print('No unreachable sub-directories found.')
        return 0
    print('Each entry above is a branch of the service that is currently '
          'unreachable.\nThe files are still on disk; only the reference is '
          'broken.')
    return 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = os.environ.get('COMPUNET_CONTENT_DIR') or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', 'content')
    sys.exit(check(target))
