#!/usr/bin/env python3
"""Conformance checks for the reference client (client/web) against the spec.

Run:  python server/tests/test_client_conformance.py            (or -v)

This is CONFORMANCE.md section E — "Command table vs implementation, both
directions… *Zero* drift either way — implemented-but-undocumented is as much a
defect as the reverse." It parses §4.7/§4.8 out of `docs/spec/` and diffs them
against `client/web/src/main.ts`, so the two cannot drift apart silently.

⚠ This suite proves only that the client offers the right COMMANDS in the right
CONTEXTS. It says nothing about whether they behave correctly. CONFORMANCE.md
sections A-D — the selection bar leaving the divider intact, SHOW refusing a
paid page, capture preserving colour — are explicitly answerable "by looking,
not by reasoning about the code", and no test here substitutes for that pass.

It reads both files as text rather than importing anything: the client is
TypeScript, and the point is to compare the two documents of record.
"""

import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
SPEC = os.path.join(_ROOT, 'docs', 'spec', '04-commands.md')
CLIENT = os.path.join(_ROOT, 'client', 'web', 'src', 'main.ts')


def _section(text, start, end):
    return text[text.index(start):text.index(end)]


def spec_contexts():
    """§4.8's table: {context name -> [commands]}, including the commands its
    notes column places beyond the displayed count."""
    body = _section(open(SPEC, encoding='utf-8').read(), '## 4.8', '## 4.9')
    out = {}
    for line in body.split('\n'):
        m = re.match(r'\| \*\*(.+?)\*\*(.*?)\| (.+?) \|(.*)', line)
        if not m:
            continue
        name = re.sub(r'\s*\(.*?\)\s*', ' ', m.group(1)).strip()
        cmds = re.findall(r'`([A-Z]+)`', m.group(3))
        if cmds:
            out[name] = cmds
    return out


def spec_vocabulary():
    """Every command name §4.7 and §4.8 name, including prose mentions."""
    text = open(SPEC, encoding='utf-8').read()
    body = _section(text, '## 4.7', '## 4.9')
    # Command names are upper-case words in backticks; filter out wire bytes
    # (single letters) and prose shouting.
    names = set(re.findall(r'`([A-Z]{2,6})`', body))
    return {n for n in names if n not in {'MUST', 'NOT', 'SHOULD', 'MAY', 'DIR',
                                          'CLOSED', 'AND', 'OR'}} | {'DIR'}


def client_contexts():
    """CONTEXT_COMMANDS from main.ts: {context -> [commands]}."""
    ts = open(CLIENT, encoding='utf-8').read()
    blk = _section(ts, 'const CONTEXT_COMMANDS', '/** Commands that act on the highlighted')
    return {m.group(1): re.findall(r"'([A-Z]+)'", m.group(2))
            for m in re.finditer(r"(\w+):\s*\[([^\]]*)\]", blk, re.S)}


def client_commands():
    """Every command the client can actually invoke.

    Found by locating each `Record<string, () => void>` action table and taking
    its top-level keys — discovered rather than listed, so a new context's table
    is covered the moment it is written."""
    ts = open(CLIENT, encoding='utf-8').read()
    impl = set()
    for m in re.finditer(r'const \w+: Record<string, \(\) => void> = \{', ts):
        body = ts[m.end():ts.index('\n};', m.end())]
        impl |= set(re.findall(r'^  ([A-Z]+):', body, re.M))
    assert impl, 'no action tables found in main.ts — the scanner has gone stale'
    return impl


class CommandCoverage(unittest.TestCase):
    """Both directions, zero drift (CONFORMANCE.md §E)."""

    def test_every_command_the_spec_places_in_a_context_is_implemented(self):
        declared = set()
        for cmds in spec_contexts().values():
            declared |= set(cmds)
        missing = declared - client_commands()
        self.assertEqual(missing, set(),
                         'commands §4.8 offers that the client cannot invoke: %s'
                         % ' '.join(sorted(missing)))

    def test_the_client_invents_no_commands(self):
        """§4.7's vocabulary is CLOSED — an invented command is a conformance
        failure even if it is useful, because Binding A has no counterpart."""
        invented = client_commands() - spec_vocabulary()
        self.assertEqual(invented, set(),
                         'commands the client offers that §4.7 does not define: %s'
                         % ' '.join(sorted(invented)))


class ContextCoverage(unittest.TestCase):
    """§4.8 is the authoritative table of which commands belong where (§4.6)."""

    # §4.8's rows, mapped to the client's context keys. Rows whose command set
    # is "none" (single-frame reading, ID results) are deliberately absent from
    # CONTEXT_COMMANDS: they are PRESS ANY KEY screens, not command rows.
    # Keys are §4.8's row labels as parsed (bold text, section refs stripped).
    MAPPING = {
        'Directory listing': 'directory',
        'Reading a multi-frame page': 'frame',
        'Mail': 'mail',
        'Mail composition': 'courierSend',
        'Editor': 'editor',
        'Upload / send': 'upload',
    }

    def test_the_mapping_names_real_spec_rows(self):
        """Guard against the mapping silently going stale if §4.8 is reworded:
        a row that no longer parses would otherwise make its context test
        vacuously compare against an empty list."""
        spec = spec_contexts()
        self.assertEqual([r for r in self.MAPPING if r not in spec], [],
                         'MAPPING names rows that §4.8 no longer contains')

    def test_every_spec_context_exists_in_the_client(self):
        client = client_contexts()
        missing = [(row, key) for row, key in self.MAPPING.items() if key not in client]
        self.assertEqual(missing, [],
                         'contexts §4.8 defines that the client does not implement: %s'
                         % ', '.join('%s -> %s' % (r, k) for r, k in missing))

    def test_each_context_offers_exactly_the_specified_commands(self):
        spec, client = spec_contexts(), client_contexts()
        # §4.8's directory row lists 11 and names six more in prose as reachable
        # beyond the displayed count; §4.9.4 makes the loop all seventeen.
        continuation = ['PRINT', 'LIFE', 'BUY', 'LOAD', 'UPLD', 'VOTE']
        for row, key in self.MAPPING.items():
            if key not in client:
                continue                      # reported by the test above
            expected = list(spec[row])
            if key == 'directory':
                expected += continuation
            self.assertEqual(client[key], expected,
                             '%s: client row does not match §4.8' % key)

    def test_the_welcome_row_is_the_directory_row(self):
        """§4.8: the welcome frame 'carries the directory row'."""
        client = client_contexts()
        self.assertEqual(client['welcome'], client['directory'][:len(client['welcome'])])

    def test_contexts_the_spec_says_have_no_duckshoot_have_none(self):
        """§4.8 has rows whose command set is "none — no duckshoot at all", and
        a client that fills them in has invented a context the original lacks.

        - `mailFrame`: reading a mail message. SHOW downloads the whole message
          and ends on PRESS ANY KEY (§8.2) — there is nothing to choose.
        - `partyline`: chat, none of the normal commands apply.
        - `idle`: no session means no Compunet screen, so no row (§8.4.2) —
          NOT because the editor is unavailable offline, which it is not."""
        client = client_contexts()
        for ctx in ('mailFrame', 'partyline', 'idle'):
            self.assertEqual(client[ctx], [], '%s must offer no commands' % ctx)


if __name__ == '__main__':
    unittest.main(verbosity=2)
