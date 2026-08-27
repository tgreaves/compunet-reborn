#!/usr/bin/env python3
"""The account the suites log in as, supplied only when the real one is absent.

`server/cfg/users.json` holds live accounts and their password hashes, so it is
gitignored and cannot be committed. The suites log in as TEST/SECRET, and on a
clean checkout that account simply does not exist — which made 61 of
`test_api_binding`'s tests skip SILENTLY and one fail outright (#137). A skip
reads as a pass, so the suite that exists because "every clean-room run of
Binding B has found bugs introduced by the previous round of fixes" was not in
fact guarding those paths for anybody who had not hand-built an account.

⚠ A MACHINE THAT ALREADY HAS A WORKING TEST ACCOUNT KEEPS USING IT. `ensure()`
supplies one only when the real configuration cannot authenticate, so a
developer with a set-up environment sees no change at all: their `users.json` is
read to answer that one question and is never written to, moved, or replaced.
The fallback redirects `srv.CFG_DIR` at a temp directory instead, which also
means a test that writes users back (`_save_users`) cannot reach the real file.

The account is deliberately minimal — enough credit for the paid-page paths and
nothing else. If a test ever needs more than that, add it here rather than in
the test, so both suites keep agreeing about who TEST is.
"""

import atexit
import hashlib
import json
import os
import shutil
import tempfile

USER, PASSWORD = 'TEST', 'SECRET'

#: Enough to buy the fixture tree's paid pages several times over. The tests
#: that care assert on the DELTA, not the balance, so the figure is arbitrary.
CREDIT = 100.0

#: ⚠ ADMIN is here because it is a RECIPIENT, not because anything logs in as
#: it: the audit suite sends mail to ADMIN, and without the account the send is
#: refused with "no such user" — which surfaces as "Binding B mail must be
#: audited" and reads exactly like the audit bug that test was written to guard.
#: `data/mail.test` ships mailboxes for TEST and ADMIN and nobody else, so that
#: pair is what the fixture set has always assumed.
#:
#: Neither account carries `admin` or `editor`. Those flags short-circuit the
#: upload permission check (§ _may_upload_here), so granting them would quietly
#: stop the open_upload paths from being tested at all.
ACCOUNTS = {
    USER: {'credit': CREDIT, 'purchased': []},
    'ADMIN': {'credit': 0.0, 'purchased': []},
}


def _hashed(password):
    """Exactly what CompunetSession._hash_password does — SHA-256 of the
    upper-cased password, since handle_login upper-cases before comparing."""
    return hashlib.sha256(password.upper().strip().encode('utf-8')).hexdigest()


def _already_works(cfg_dir):
    """Can the REAL configuration log TEST in? Read-only, and never raises: a
    missing, unreadable or malformed users.json simply means "no"."""
    path = os.path.join(cfg_dir, 'users.json')
    try:
        with open(path, 'r') as f:
            users = json.load(f)
    except (OSError, ValueError):
        return False
    user = users.get(USER)
    return bool(user) and user.get('password') == _hashed(PASSWORD)


def ensure(srv):
    """Guarantee USER/PASSWORD can log in.

    Returns 'existing' when the machine's own configuration already works and
    nothing was changed, or 'synthetic' when a temporary account was created and
    `srv.CFG_DIR` repointed at it for the life of the process.
    """
    if _already_works(srv.CFG_DIR):
        return 'existing'

    tmp = tempfile.mkdtemp(prefix='compunet-cfg-')
    users = {name: dict(rec, password=_hashed(PASSWORD))
             for name, rec in ACCOUNTS.items()}
    with open(os.path.join(tmp, 'users.json'), 'w') as f:
        json.dump(users, f)
    srv.CFG_DIR = tmp
    atexit.register(shutil.rmtree, tmp, True)
    return 'synthetic'
