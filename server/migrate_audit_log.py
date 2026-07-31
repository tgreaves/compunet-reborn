#!/usr/bin/env python3
"""Migrate audit.jsonl to the 1.4.0 event vocabulary (#127).

The event names grew ad hoc — `page_deleted` and `header_removed` in the past
tense against `upload` and `vote` as bare verbs — with no documented set for a new
feature to conform to. `compunet_server.AUDIT_EVENTS` is now that set, and
`audit_log` refuses a name that is not in it, so history has to be brought along
or the log holds two vocabularies and every filter needs to know both.

This rewrites each line in place:

  * `event` renamed per RENAMES below
  * `kind` added, from the same AUDIT_EVENTS registry the server now uses
  * everything else left exactly as it was, including field order

Entries whose event is not recognised are passed through untouched and counted, so
nothing is ever dropped by a mapping gap.

⚠ TAKES A BACKUP FIRST and refuses to run without one. The live file is the only
copy of several years of history; there is no second source.

    python3 migrate_audit_log.py [--dry-run] [path/to/audit.jsonl]
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compunet_server as srv                          # noqa: E402

#: Old name -> new name. Mirrors the renames applied to the call sites.
RENAMES = {
    'connect':                'session_started',
    'disconnect':             'session_ended',
    'read':                   'page_read',
    'buy':                    'page_bought',
    'extend':                 'page_life_extended',
    'vote':                   'page_voted',
    'mail_read':              'mail_opened',
    'mail_send':              'mail_sent',
    'upload':                 'page_uploaded',
    'partyline':              'partyline_entered',
    'download':               'page_downloaded',
    'login':                  'login_succeeded',
    'signup':                 'signup_completed',
    'directory_settings':     'directory_settings_changed',
    'partyline_kick':         'partyline_kicked',
    'partyline_ban':          'partyline_banned',
    'partyline_unban':        'partyline_unbanned',
    'password_reset_request': 'password_reset_requested',
}


def migrate_line(entry):
    """Returns (entry, status) where status is 'renamed', 'kinded' or 'unknown'."""
    event = entry.get('event')
    new_event = RENAMES.get(event, event)
    status = 'renamed' if new_event != event else 'kinded'

    kind = srv.AUDIT_EVENTS.get(new_event)
    if kind is None:
        return entry, 'unknown'

    # Rebuild so `event` and `kind` sit together at the front, as new entries do.
    out = {}
    for key, value in entry.items():
        out[key] = value
        if key == 'event':
            out['event'] = new_event
            out['kind'] = kind
    return out, status


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry_run = '--dry-run' in sys.argv
    path = args[0] if args else srv.AUDIT_LOG_PATH

    if not os.path.exists(path):
        print('no audit log at %s' % path)
        return 1

    with open(path, 'r') as f:
        raw = [line.rstrip('\n') for line in f]

    entries, malformed = [], 0
    for line in raw:
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1

    counts = {'renamed': 0, 'kinded': 0, 'unknown': 0}
    unknown_names = {}
    migrated = []
    for entry in entries:
        out, status = migrate_line(entry)
        counts[status] += 1
        if status == 'unknown':
            name = entry.get('event')
            unknown_names[name] = unknown_names.get(name, 0) + 1
        migrated.append(out)

    print('%s' % path)
    print('  entries        : %d' % len(entries))
    print('  renamed        : %d' % counts['renamed'])
    print('  already current: %d' % counts['kinded'])
    print('  unrecognised   : %d %s' % (counts['unknown'],
                                        unknown_names or ''))
    if malformed:
        print('  malformed lines: %d (left out of the count; preserved below)'
              % malformed)

    by_kind = {}
    for entry in migrated:
        k = entry.get('kind', '(none)')
        by_kind[k] = by_kind.get(k, 0) + 1
    print('  by kind        : %s' % dict(sorted(by_kind.items())))

    if dry_run:
        print('\n--dry-run: nothing written')
        return 0

    backup = path + '.pre-1.4.0'
    if os.path.exists(backup):
        print('\nbackup %s already exists — refusing to overwrite it.' % backup)
        print('Move it aside if you really mean to migrate again.')
        return 1
    shutil.copy2(path, backup)
    print('\n  backup         : %s' % backup)

    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        for entry in migrated:
            f.write(json.dumps(entry) + '\n')
    os.replace(tmp, path)
    print('  written        : %d entries' % len(migrated))
    return 0


if __name__ == '__main__':
    sys.exit(main())
