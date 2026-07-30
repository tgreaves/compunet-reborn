#!/usr/bin/env python3
"""Regression tests for the X.25 framing layer (server/x25_protocol.py).

Run:  python server/tests/test_x25.py            (or -v)

These exist because of one shipped crash and one near-miss:

  1. THE LENGTH FIELD IS ONE BYTE AND WRAPS. It is advisory — both parsers frame on
     the $01/$02 markers and derive the payload length from where the end marker fell.
     make_data_packet used to `bytearray.append(len(payload) + 5)`, which raises
     ValueError for any payload over 250 and drops the connection mid-transfer. It went
     unnoticed for as long as every send was 100 bytes; widening program downloads to
     4000 hit it immediately, and the Amiga reported "Fatal error: Comms problem".

     Note the asymmetry that hid it: this server has always *received* 4000-byte frames
     from the Amiga client (which truncates with `(UBYTE)(len + 5)` and logs here as
     `DAT seq=$2E len=165 payload=4000 bytes`) — only the send path was limited.

  2. Byte stuffing must survive payloads containing $01/$02/$03 at any size, or a frame
     ends early at a false marker.
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVER = os.path.dirname(_HERE)
sys.path.insert(0, _SERVER)

import x25_protocol as x25  # noqa: E402


class LengthFieldWraps(unittest.TestCase):
    """A payload over 250 bytes must build, not raise."""

    def test_payloads_over_250_do_not_raise(self):
        conn = x25.X25Connection()
        for n in (251, 500, 1000, 4000):
            conn.make_data_packet(bytes(n), x25.TOKEN_DAT)   # must not raise

    def test_length_byte_is_the_low_8_bits(self):
        """Matches the client's `(UBYTE)(len + 5)` exactly — the CRC covers this byte,
        so a different value on either side would fail every frame."""
        conn = x25.X25Connection()
        for n, expect in ((100, 105), (250, 255), (251, 0), (4000, 165)):
            pkt = conn.make_data_packet(bytes(n), x25.TOKEN_DAT)
            self.assertEqual(pkt[1], expect, 'payload %d' % n)

    def test_the_4000_byte_case_that_crashed(self):
        """The exact size program downloads use for Amiga clients."""
        conn = x25.X25Connection()
        pkt = conn.make_data_packet(bytes(4000), x25.TOKEN_DAT)
        self.assertEqual(pkt[0], 0x01)      # start marker
        self.assertEqual(pkt[-1], 0x02)     # end marker


class FramingRoundTrip(unittest.TestCase):
    """What is built must parse back byte-for-byte, at every size."""

    def _round_trip(self, payload):
        tx, rx = x25.X25Connection(), x25.X25Connection()
        got = rx.feed_data(tx.make_data_packet(payload, x25.TOKEN_DAT))
        self.assertEqual(len(got), 1, 'expected exactly one packet')
        token, _seq, parsed = got[0]
        self.assertEqual(token, x25.TOKEN_DAT)
        self.assertEqual(parsed, payload)

    def test_small_payload(self):
        self._round_trip(b'hello world')

    def test_every_byte_value_including_the_markers(self):
        """$01/$02/$03 are the frame markers and the escape; they must survive stuffing."""
        self._round_trip(bytes(range(256)))

    def test_large_payload_with_markers_throughout(self):
        self._round_trip((bytes(range(256)) * 15) + b'ABC')   # 3843 bytes

    def test_full_4000_byte_block(self):
        self._round_trip(bytes([(i * 7) & 0xFF for i in range(4000)]))

    def test_worst_case_all_escaped(self):
        """Every byte in $01-$03 doubles on the wire — the stuffing ceiling."""
        payload = bytes([1, 2, 3] * 800)                      # 2400 bytes, all escaped
        self._round_trip(payload)

    def test_empty_payload_is_the_eos_frame(self):
        self._round_trip(b'')


if __name__ == '__main__':
    unittest.main(verbosity=2)
