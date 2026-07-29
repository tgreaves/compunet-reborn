#!/usr/bin/env python3
"""Regression tests for the header-frame validator (server/header_frame.py).

Run:  python server/tests/test_header_frame.py            (or -v)

Issue #120 lets users supply the PETSCII header a directory draws in rows 0-5
(§7.2 Part 1). Before it, those bytes only ever came from an operator editing a
JSON file by hand; after it they arrive from the public internet, and nothing
else in this tree validates frame bytes at all.

The rules being guarded are not stylistic. Each one exists because a specific
renderer breaks without it, and — importantly — the three renderers break
DIFFERENTLY, so a header that looks correct in the web client can still destroy
the C64 screen. These tests therefore assert against the strictest consumer.

Two groups:

  1. ShippedHeadersStillPass — the headers the service already ships must remain
     valid. A validator that rejects the service's own artwork is wrong, and
     this is the cheapest possible detector for a rule that is too strict.
  2. HostileHeadersAreRejected — one test per attack or accident, named for what
     it does to the screen rather than for the byte it contains.

MatchesTheRealRenderer cross-checks the simulation against
api_binding.frame_to_cells, which is the code that actually draws these frames
for the modern client. The validator mirrors that loop; if the two ever drift,
the validator is approving frames it cannot really predict.
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_SERVER)

sys.path.insert(0, _SERVER)

import header_frame as hf                       # noqa: E402
import api_binding as api                       # noqa: E402

_CONTENT_TEST = os.path.join(_SERVER, 'data', 'content.test')
_CONTENT = os.path.join(_SERVER, 'data', 'content')

#: The headers the live service and the fixture tree already carry. Sizes are
#: 134-341 bytes, which is also the evidence for the 512-byte cap being roomy.
SHIPPED = [
    os.path.join(_CONTENT_TEST, 'root', 'header.seq'),
    os.path.join(_CONTENT_TEST, 'root', 'jungle', 'header.seq'),
    os.path.join(_CONTENT_TEST, 'root', 'jungle', 'ash-and-dave', 'header.seq'),
    os.path.join(_CONTENT, 'courier-header.seq'),
]


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def _row_of_first_ink_below(cells, last_ok_row):
    """First row below `last_ok_row` carrying a non-blank cell, or None.

    Blank is either space glyph, since a lower-case frame blanks with $A0.
    """
    for row in range(last_ok_row + 1, 24):
        for col in range(40):
            cell = cells[row * 40 + col]
            if cell['g'] not in (0x20, 0xA0) or cell['rv']:
                return row
    return None


class ShippedHeadersStillPass(unittest.TestCase):
    """The service's own headers must remain valid."""

    def test_every_shipped_header_validates(self):
        for path in SHIPPED:
            with self.subTest(header=os.path.basename(os.path.dirname(path))):
                self.assertTrue(os.path.exists(path), '%s is missing' % path)
                self.assertEqual([], hf.validate_header_frame(_read(path)))

    def test_shipped_headers_are_well_inside_the_size_cap(self):
        for path in SHIPPED:
            with self.subTest(path=path):
                self.assertLessEqual(len(_read(path)), hf.MAX_BYTES)

    def test_describe_reports_rows_used(self):
        desc = hf.describe_header_frame(_read(SHIPPED[0]))
        self.assertIsNotNone(desc)
        self.assertGreater(desc['rows_used'], 0)
        self.assertLessEqual(desc['rows_used'], hf.LAST_HEADER_ROW + 1)


class HostileHeadersAreRejected(unittest.TestCase):

    def test_an_empty_file_is_refused(self):
        self.assertTrue(hf.validate_header_frame(b''))

    def test_a_header_over_the_cap_is_refused(self):
        reasons = hf.validate_header_frame(b'A' * (hf.MAX_BYTES + 1))
        self.assertTrue(any('Too large' in r for r in reasons))

    def test_a_header_at_the_cap_is_not_refused_for_size(self):
        # Exactly at the limit: it overflows the row budget (513 'A's cannot fit
        # in six rows), but it must NOT be complained about for its size.
        reasons = hf.validate_header_frame(b'A' * hf.MAX_BYTES)
        self.assertFalse(any('Too large' in r for r in reasons))

    def test_an_embedded_nul_is_refused(self):
        # ⚠ The C64's Part-1 store loop is byte-level (compunet.s:3252): it
        # copies until the first $00 with no RLE awareness, so everything after
        # this byte is misparsed as Part 2/3/4 and the directory desynchronises.
        reasons = hf.validate_header_frame(b'AB\x00CD')
        self.assertTrue(any('$00' in r for r in reasons))

    def test_a_nul_used_only_as_a_repeat_count_is_still_refused(self):
        # $06 $00 is a legal single space in the frame format, and Binding B
        # renders it happily — but the C64 store loop stops dead at that $00.
        # This is the case a naive "does it render?" check waves through.
        reasons = hf.validate_header_frame(b'\x06\x00ABC')
        self.assertTrue(any('$00' in r for r in reasons))

    def test_a_clear_screen_is_refused(self):
        # Part 1 is drawn AFTER the template (compunet.s:3258-3264), so one $93
        # wipes the border, breadcrumb and entry list.
        reasons = hf.validate_header_frame(b'AB\x93CD')
        self.assertTrue(any('clear-screen' in r for r in reasons))

    def test_a_clear_screen_hidden_inside_a_repeat_run_is_refused(self):
        # $07 $93 $27 is forty clear-screens in three bytes. A byte-level
        # blocklist over the raw file would pass this straight through, which is
        # why the checks run over the EXPANDED stream.
        reasons = hf.validate_header_frame(b'AB\x07\x93\x27CD')
        self.assertTrue(any('clear-screen' in r for r in reasons))

    def test_a_lowercase_charset_switch_is_refused(self):
        # Nothing re-issues $8E after Part 1, so the rest of the screen is drawn
        # in the wrong set.
        reasons = hf.validate_header_frame(b'AB\x0ECD')
        self.assertTrue(any('lower-case' in r for r in reasons))

    def test_drawing_on_row_six_is_refused(self):
        # Row 6 is the template's top border. Six CRs put the cursor on row 6.
        reasons = hf.validate_header_frame(b'\x0d' * 6 + b'X')
        self.assertTrue(any('row 6' in r for r in reasons))

    def test_drawing_far_below_the_header_region_is_refused(self):
        reasons = hf.validate_header_frame(b'\x0d' * 8 + b'X')
        self.assertTrue(any('row 8' in r for r in reasons))

    def test_ending_the_cursor_on_row_six_without_drawing_is_allowed(self):
        # Every shipped header does exactly this: it finishes with a CR, leaving
        # the cursor on row 6 having printed nothing there. Rejecting the cursor
        # position rather than the ink would fail all four.
        self.assertEqual([], hf.validate_header_frame(b'X' + b'\x0d' * 6))

    def test_a_truncated_space_run_is_refused(self):
        reasons = hf.validate_header_frame(b'AB\x06')
        self.assertTrue(any('Truncated space-run' in r for r in reasons))

    def test_a_truncated_repeat_run_is_refused(self):
        reasons = hf.validate_header_frame(b'AB\x07\x41')
        self.assertTrue(any('Truncated repeat-run' in r for r in reasons))

    def test_leaving_reverse_video_on_is_refused(self):
        reasons = hf.validate_header_frame(b'\x12ABC')
        self.assertTrue(any('reverse video' in r for r in reasons))

    def test_reverse_video_closed_before_the_end_is_accepted(self):
        self.assertEqual([], hf.validate_header_frame(b'\x12ABC\x92'))

    def test_a_carriage_return_also_clears_reverse(self):
        # The C64 drops the reverse flag at end of line, and the simulation must
        # agree or it would reject the service's own headers.
        self.assertEqual([], hf.validate_header_frame(b'\x12ABC\x0d'))

    def test_reasons_name_the_byte_offset(self):
        # The author is looking at a binary file made in another tool; a reason
        # without a position is close to useless.
        reasons = hf.validate_header_frame(b'ABCD\x93')
        self.assertTrue(any('offset 4' in r for r in reasons))


class MatchesTheRealRenderer(unittest.TestCase):
    """The validator's simulation must agree with the renderer it stands in for."""

    def test_accepted_headers_leave_the_entry_list_untouched(self):
        # The whole point of the row rule: after rendering through the code that
        # actually draws these frames, nothing may be inked below row 5.
        for path in SHIPPED:
            with self.subTest(path=os.path.basename(os.path.dirname(path))):
                body = _read(path)
                self.assertEqual([], hf.validate_header_frame(body))
                frame = api.frame_to_cells(bytes([0x00, 0xF4, 0xFF, 0x8E]) + body)
                self.assertIsNone(
                    _row_of_first_ink_below(frame['cells'], hf.LAST_HEADER_ROW))

    def test_a_frame_the_validator_rejects_really_does_reach_the_entry_list(self):
        # Inverse check — proves the rule is detecting a real effect rather than
        # being conservative for its own sake.
        body = b'\x0d' * 8 + b'XYZ'
        self.assertTrue(hf.validate_header_frame(body))
        frame = api.frame_to_cells(bytes([0x00, 0xF4, 0xFF, 0x8E]) + body)
        self.assertEqual(
            8, _row_of_first_ink_below(frame['cells'], hf.LAST_HEADER_ROW))


class PreviewRendersFromTheSpecFont(unittest.TestCase):
    """The website's header preview (#120).

    ⚠ It must draw from `assets.json` — generated from the specification's own
    palette (§A.3) and 256-glyph font (§A.5) — and not from a font of its own. A
    preview that disagreed with the real clients about what a header looks like
    would be worse than showing nothing, because the author would trust it.
    """

    def setUp(self):
        import header_preview
        self.hp = header_preview
        self.hp._assets = None          # never reuse a cache between tests
        self.assets = self.hp.load_assets(_SERVER, os.path.join(_ROOT, 'client', 'web'))
        if not self.assets:
            self.skipTest('client/web/assets.json not present')

    def test_the_font_and_palette_are_the_full_sets(self):
        self.assertEqual(16, len(self.assets['palette']))
        self.assertEqual(256, len(self.assets['font']))
        self.assertTrue(all(len(g) == 8 for g in self.assets['font']),
                        'glyphs are 8 bytes tall (§A.5)')

    def test_a_shipped_header_renders_to_a_valid_png(self):
        body = _read(SHIPPED[2])        # ash-and-dave
        frame = api.frame_to_cells(bytes([0x00, 0xF4, 0xFF, 0x8E]) + body)
        png = self.hp.cells_to_png(frame['cells'], self.assets)

        self.assertEqual(b'\x89PNG\r\n\x1a\n', png[:8])
        import struct
        width, height = struct.unpack('>II', png[16:24])
        self.assertEqual(self.hp.PREVIEW_COLS * 8 * self.hp.SCALE, width)
        self.assertEqual(self.hp.PREVIEW_ROWS * 8 * self.hp.SCALE, height)
        self.assertEqual(b'IEND', png[-8:-4])

    def test_the_preview_covers_exactly_the_header_region(self):
        """Six rows — the rows a header may use (§7.7). Fewer would crop
        someone's artwork; more would show template chrome they cannot change."""
        self.assertEqual(hf.LAST_HEADER_ROW + 1, self.hp.PREVIEW_ROWS)

    def test_something_was_actually_drawn(self):
        """Guards the whole point: a renderer that emitted a blank image would
        pass every structural check above."""
        body = _read(SHIPPED[2])
        frame = api.frame_to_cells(bytes([0x00, 0xF4, 0xFF, 0x8E]) + body)
        png = self.hp.cells_to_png(frame['cells'], self.assets)
        blank = self.hp.cells_to_png(
            [{'g': 0x20, 'fg': 1, 'bg': 0, 'rv': 0}] * (40 * 24), self.assets)
        self.assertNotEqual(blank, png, 'the preview rendered nothing')


if __name__ == '__main__':
    unittest.main(verbosity=2 if '-v' in sys.argv else 1)
