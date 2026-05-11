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

    Algorithm (per byte, MSB first):
      For each of 8 bits:
        ROL temp byte (shift out MSB to carry)
        ROL CRC low (shift carry in from right)
        ROL CRC high (shift carry in from right)
        If carry out of CRC high: XOR CRC with $1021
    """
    for byte in data:
        temp = byte
        for _ in range(8):
            # ROL temp
            carry = (temp >> 7) & 1
            temp = (temp << 1) & 0xFF

            # ROL crc_lo
            new_carry = (crc_lo >> 7) & 1
            crc_lo = ((crc_lo << 1) | carry) & 0xFF
            carry = new_carry

            # ROL crc_hi
            new_carry = (crc_hi >> 7) & 1
            crc_hi = ((crc_hi << 1) | carry) & 0xFF
            carry = new_carry

            # XOR if carry out
            if carry:
                crc_hi ^= 0x10
                crc_lo ^= 0x21

    return crc_hi, crc_lo


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
        self.tx_seq = SEQ_MIN       # next sequence number to send
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

    def make_ack(self, seq_to_ack):
        """
        Build an ACK packet for a received sequence number.

        ACK packet format (6 bytes between $01 and $02):
          [0] = $41 'A' \
          [1] = $43 'C'  } = "ACK" literal (from ROM table at $9C0B)
          [2] = $4B 'K' /
          [3] = sequence number being acknowledged
          [4] = CRC high
          [5] = CRC low
        
        CRC is computed over just the sequence byte, with init $40/$E6.
        Total wire format: $01 "ACK" <seq> <crc_hi> <crc_lo> $02 (8 bytes)
        """
        crc_hi, crc_lo = crc_ccitt([seq_to_ack])
        pkt = bytes([PKT_START, 0x41, 0x43, 0x4B, seq_to_ack, crc_hi, crc_lo, PKT_END])
        log.info('X25 TX: ACK seq=$%02X [%s]', seq_to_ack, pkt.hex())
        return pkt

    def make_data_packet(self, payload, token=TOKEN_DAT):
        """
        Build a data packet containing payload bytes.

        Packet format (between $01 and $02):
          [0] = sequence number (range $20-$5F)
          [1] = token ($43=COM, $22=DAT, etc.)
          [2..N-2] = payload bytes
          [N-1] = CRC high
          [N] = CRC low

        CRC covers: all bytes except CRC itself (seq + token + payload).
        CRC init: $40/$E6.

        Total wire: $01 + [seq, token, payload..., CRC_hi, CRC_lo] + $02
        """
        seq = self._next_tx_seq()

        # Build content for CRC
        content = bytearray()
        content.append(seq)
        content.append(token)
        content.extend(payload)

        # Compute CRC
        crc_hi, crc_lo = crc_ccitt(content)
        content.append(crc_hi)
        content.append(crc_lo)

        pkt = bytes([PKT_START]) + bytes(content) + bytes([PKT_END])

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
            raw_pkt = bytes(self._rx_buffer[1:end])
            self._rx_buffer = self._rx_buffer[end + 1:]

            if len(raw_pkt) < 5:  # minimum: len + token + seq + crc_hi + crc_lo
                log.warning('X25 RX: packet too short (%d bytes): %s',
                            len(raw_pkt), raw_pkt.hex())
                continue

            # Parse packet content (between $01 and $02)
            # Format: [seq] [token] [flags] [payload...] [crc_hi] [crc_lo]
            # The sequence number is the FIRST byte (range $20-$5F)
            # Token is the second byte ($43 = COM, "ACK" = ACK packet)
            seq = raw_pkt[0]
            token = raw_pkt[1]
            # Payload is everything between byte 2 and the last 2 CRC bytes
            # But byte 2 might be flags/length - include it in payload for now
            payload = raw_pkt[2:-2] if len(raw_pkt) > 4 else b''
            crc_hi_rx = raw_pkt[-2]
            crc_lo_rx = raw_pkt[-1]

            # Verify CRC (over everything except length and CRC itself)
            crc_hi, crc_lo = crc_ccitt(raw_pkt[1:-2])
            if crc_hi != crc_hi_rx or crc_lo != crc_lo_rx:
                log.warning('X25 RX: CRC mismatch! expected=%02X%02X got=%02X%02X pkt=%s',
                            crc_hi, crc_lo, crc_hi_rx, crc_lo_rx, raw_pkt.hex())
                # Continue anyway for now (CRC might be computed differently)

            token_name = TOKEN_NAMES.get(token, f'${token:02X}')
            log.info('X25 RX: %s seq=$%02X payload=%d bytes [%s]',
                     token_name, seq, len(payload), raw_pkt.hex())

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
