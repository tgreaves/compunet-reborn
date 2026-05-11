"""
X.25-derived packet protocol for Compunet TCP interface.

Implements the wire-level framing as reverse-engineered from the ROM at $96C0-$9BFF.
This runs over TCP — TCP provides reliable delivery, while X.25 framing provides
the packet boundaries and sequencing the ROM's protocol engine expects.

Wire format:
  $01 <6-byte header> $02

Header bytes ($C203-$C208 in ROM):
  [0] = packet length (payload + overhead)
  [1] = command token
  [2] = sequence number
  [3] = (varies by packet type)
  [4] = CRC high byte
  [5] = CRC low byte

Command tokens:
  ACK=$20, DIR=$21, DAT=$22, OK=$23, ERR=$24, FTL=$25, COM=$26

CRC: CRC-CCITT polynomial $1021, init $40E6 (from ROM at $9ABC)

Sequence numbers: range $20-$5F, window size 4

Connection handshake:
  Client sends $20 (space) via modem register 3
  Server responds with $20 (space)
  Then protocol state initializes with $C20E/$C20F = $20
"""

import logging

log = logging.getLogger('compunet.x25')

# Framing
PKT_START = 0x01
PKT_END = 0x02

# Command tokens
TOKEN_ACK = 0x20
TOKEN_DIR = 0x21
TOKEN_DAT = 0x22
TOKEN_OK = 0x23
TOKEN_ERR = 0x24
TOKEN_FTL = 0x25
TOKEN_COM = 0x26

TOKEN_NAMES = {
    0x20: 'ACK', 0x21: 'DIR', 0x22: 'DAT', 0x23: 'OK',
    0x24: 'ERR', 0x25: 'FTL', 0x26: 'COM',
}

# Sequence number range
SEQ_MIN = 0x20
SEQ_MAX = 0x5F
WINDOW_SIZE = 4

# Handshake byte
HANDSHAKE = 0x20


def crc_ccitt(data, crc_hi=0x40, crc_lo=0xE6):
    """
    CRC-CCITT as implemented in ROM at $9B10.
    Polynomial $1021. Default init $40/$E6 (from ACK send at $9ABC).

    Standard CRC-CCITT MSB-first algorithm.
    Note: the original implementation in this file was buggy (used a
    bit-shift chain that didn't match standard CRC-CCITT). This version
    produces correct results that match the ROM's output.
    """
    crc = (crc_hi << 8) | crc_lo
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return (crc >> 8) & 0xFF, crc & 0xFF


class X25Connection:
    """
    Server-side X.25 protocol handler for one TCP connection.

    Handles:
    - Connection handshake (space exchange)
    - Packet framing ($01 header $02)
    - CRC computation
    - Sequence numbering and ACK generation
    - Extracting client commands from received packets
    """

    def __init__(self):
        self.tx_seq = SEQ_MIN + 1   # start at $21 to avoid collision with login echo
        self.rx_seq = SEQ_MIN       # next expected receive sequence
        self.connected = False
        self._rx_buffer = bytearray()

    def _advance_seq(self, seq):
        """Advance a sequence number (wraps $5F -> $20)."""
        seq += 1
        if seq > SEQ_MAX:
            seq = SEQ_MIN
        return seq

    def _next_tx_seq(self):
        """Get and advance transmit sequence number."""
        seq = self.tx_seq
        self.tx_seq = self._advance_seq(self.tx_seq)
        return seq

    # ------------------------------------------------------------------
    # Handshake
    # ------------------------------------------------------------------

    def make_handshake(self):
        """
        Server handshake response.
        The client sends $20 (space). Server responds with $20.
        """
        log.info('X25 TX: handshake response ($20)')
        return bytes([HANDSHAKE])

    # ------------------------------------------------------------------
    # Packet construction
    # ------------------------------------------------------------------

    def _byte_stuff(self, data):
        """
        Apply byte stuffing to raw packet content.
        Bytes $01-$03 are escaped as $03 + (byte + $20).
        $00 and $04+ are sent as-is.
        """
        result = bytearray()
        for b in data:
            if 0x01 <= b <= 0x03:
                result.append(0x03)
                result.append(b + 0x20)
            else:
                result.append(b)
        return bytes(result)

    def make_ack(self, seq_to_ack):
        """
        Build an ACK packet for a received sequence number.

        ACK packet format (same structure as all packets):
          $01 [length=06] [token=$20=ACK] [$20] [seq_being_acked] [CRC_hi] [CRC_lo] $02

        The ROM's receive handler at $9C98 checks token byte ($C485).
        If token=$20 (ACK), it matches the seq against outgoing slots
        and clears the retransmit flag.

        CRC init: $00/$00 (same as all packets for receive path).
        Byte stuffing applied to content between markers.
        """
        # Build raw content: length + token + fixed_byte + seq
        content = bytearray([0x06, 0x20, 0x20, seq_to_ack])
        crc_hi, crc_lo = crc_ccitt(content, crc_hi=0x00, crc_lo=0x00)
        content.append(crc_hi)
        content.append(crc_lo)
        # Apply byte stuffing then frame
        stuffed = self._byte_stuff(content)
        pkt = bytes([PKT_START]) + stuffed + bytes([PKT_END])
        log.info('X25 TX: ACK seq=$%02X [%s]', seq_to_ack, pkt.hex())
        return pkt

    def make_data_packet(self, payload, token=TOKEN_DAT):
        """
        Build a data packet containing payload bytes.

        Packet format (raw content between $01 and $02, before byte stuffing):
          [0] = packet length (total UNESCAPED bytes between $01 and $02)
          [1] = token ($22=DAT, $26=COM, etc.)
          [2] = sequence number (range $20-$5F)
          [3..N-2] = payload bytes
          [N-1] = CRC high
          [N] = CRC low

        Length byte = total unescaped byte count between markers (including itself).
        CRC covers: all unescaped bytes between $01 and $02 except CRC itself.
        CRC init: $00/$00 (ROM receive path at $9E41 inits CRC to 0).
        Byte stuffing applied after CRC computation.

        Total wire: $01 + [byte-stuffed content] + $02
        """
        seq = self._next_tx_seq()

        # Total unescaped bytes between $01 and $02:
        # len(1) + token(1) + seq(1) + payload(N) + CRC(2) = N + 5
        pkt_len = len(payload) + 5

        # Build raw content (before byte stuffing)
        content = bytearray()
        content.append(pkt_len)
        content.append(token)
        content.append(seq)
        content.extend(payload)

        # Compute CRC over raw content with init $00/$00
        crc_hi, crc_lo = crc_ccitt(content, crc_hi=0x00, crc_lo=0x00)
        content.append(crc_hi)
        content.append(crc_lo)

        # Apply byte stuffing then frame
        stuffed = self._byte_stuff(content)
        pkt = bytes([PKT_START]) + stuffed + bytes([PKT_END])

        if len(payload) <= 4:
            log.debug('X25 TX: DAT seq=$%02X payload=%s [%s]',
                      seq, payload.hex(), pkt.hex())
        else:
            log.debug('X25 TX: DAT seq=$%02X %d bytes', seq, len(payload))
        return pkt

    # ------------------------------------------------------------------
    # Packet parsing (receive from client)
    # ------------------------------------------------------------------

    def feed_data(self, data):
        """
        Feed raw bytes from TCP into the protocol parser.
        Returns list of parsed packets (token, seq, payload).
        """
        self._rx_buffer.extend(data)
        packets = []

        while True:
            # Find start marker
            try:
                start = self._rx_buffer.index(PKT_START)
            except ValueError:
                self._rx_buffer.clear()
                break

            # Discard anything before start
            if start > 0:
                discarded = self._rx_buffer[:start]
                log.debug('X25 RX: discarded %d bytes before $01: %s',
                          len(discarded), discarded.hex())
                self._rx_buffer = self._rx_buffer[start:]

            # Find end marker
            try:
                end = self._rx_buffer.index(PKT_END, 1)
            except ValueError:
                break  # incomplete packet, wait for more data

            # Extract packet (between markers, exclusive)
            raw_wire = bytes(self._rx_buffer[1:end])
            self._rx_buffer = self._rx_buffer[end + 1:]

            # De-stuff: reverse byte stuffing ($03 $2X → $0X)
            raw_pkt = bytearray()
            i = 0
            while i < len(raw_wire):
                if raw_wire[i] == 0x03 and i + 1 < len(raw_wire):
                    raw_pkt.append(raw_wire[i + 1] - 0x20)
                    i += 2
                else:
                    raw_pkt.append(raw_wire[i])
                    i += 1
            raw_pkt = bytes(raw_pkt)

            if len(raw_pkt) < 5:  # minimum: len + token + seq + crc_hi + crc_lo
                log.warning('X25 RX: packet too short (%d bytes): %s',
                            len(raw_pkt), raw_pkt.hex())
                continue

            # Parse packet content (between $01 and $02)
            # Format: [length] [token] [seq] [payload...] [crc_hi] [crc_lo]
            pkt_len = raw_pkt[0]
            token = raw_pkt[1]
            seq = raw_pkt[2]
            payload = raw_pkt[3:-2] if len(raw_pkt) > 5 else b''
            crc_hi_rx = raw_pkt[-2]
            crc_lo_rx = raw_pkt[-1]

            # Verify CRC (init $00/$00 over all bytes except CRC)
            crc_hi, crc_lo = crc_ccitt(raw_pkt[:-2], crc_hi=0x00, crc_lo=0x00)
            if crc_hi != crc_hi_rx or crc_lo != crc_lo_rx:
                log.warning('X25 RX: CRC mismatch! expected=%02X%02X got=%02X%02X pkt=%s',
                            crc_hi, crc_lo, crc_hi_rx, crc_lo_rx, raw_pkt.hex())

            token_name = TOKEN_NAMES.get(token, f'${token:02X}')
            log.info('X25 RX: %s seq=$%02X len=%d payload=%d bytes [%s]',
                     token_name, seq, pkt_len, len(payload), raw_pkt.hex())

            packets.append((token, seq, payload))

            # Track receive sequence
            if token == TOKEN_COM:
                self.rx_seq = self._advance_seq(seq)

        return packets

    def check_handshake(self, data):
        """
        Check if data contains the handshake byte ($20).
        Returns (found, remaining_data).
        """
        if HANDSHAKE in data:
            idx = data.index(HANDSHAKE)
            log.info('X25 RX: handshake received ($20) at offset %d', idx)
            return True, data[idx + 1:]
        return False, data
