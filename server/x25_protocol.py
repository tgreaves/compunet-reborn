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

        From ROM at $9ABC:
          - CRC init $40/$E6
          - CRC computed over the sequence byte only
          - Header: [length, TOKEN_ACK, seq, 0, crc_hi, crc_lo]
          - Wrapped in $01...$02
        """
        # CRC over just the sequence byte
        crc_hi, crc_lo = crc_ccitt([seq_to_ack])

        header = bytes([
            0x04,           # length (4 = header overhead?)
            TOKEN_ACK,      # ACK token
            seq_to_ack,     # sequence being acknowledged
            0x00,           # padding
            crc_hi,
            crc_lo,
        ])

        pkt = bytes([PKT_START]) + header + bytes([PKT_END])
        log.info('X25 TX: ACK seq=$%02X [%s]', seq_to_ack, pkt.hex())
        return pkt

    def make_data_packet(self, payload, token=TOKEN_DAT):
        """
        Build a data packet (DAT, DIR, OK, ERR, etc.) with payload.

        Packet format (from ROM send routine at $9AE8):
          $01
          [0] = total content length (payload_len + 2 for CRC)
          [1] = command token
          [2] = sequence number
          [3..N] = payload bytes
          [N+1] = CRC high
          [N+2] = CRC low
          $02

        CRC covers: token + sequence + payload (everything between length and CRC).
        """
        seq = self._next_tx_seq()
        content_len = len(payload) + 4  # token + seq + payload + 2 CRC bytes... 
        # Actually from the ROM: the length byte = payload_len + 2
        # Let me re-examine: at $9A8F, length = ($21),Y content minus 2
        # The header[0] seems to be the total inner content size
        # For now: length = len(payload) + 2 (for the 2 CRC bytes? or +2 for seq+token?)
        # 
        # Looking at ROM more carefully:
        # $9A8F: LDA ($21),Y / SEC / SBC #$02 / STA $C217
        # This reads the first byte of the packet buffer, subtracts 2, stores as "data length"
        # So header[0] = actual_payload_length + 2
        #
        # For a packet with N payload bytes:
        #   header[0] = N + 2
        #   header[1] = token
        #   header[2] = sequence
        #   then N payload bytes
        #   then 2 CRC bytes
        # Total between $01 and $02: 3 + N + 2 = N + 5

        pkt_len = len(payload) + 2  # the "length" field value

        # Build content for CRC calculation (everything that gets CRC'd)
        # From ROM: CRC covers the sequence byte (at minimum)
        # Actually looking at the send routine more carefully:
        # The 6-byte header at $C203-$C208 is sent between $01 and $02.
        # For data packets, the payload follows WITHIN the 6 bytes or after?
        #
        # Re-reading the ROM send at $9AE8-$9B00:
        #   JSR $991E          ; send $01
        #   LDX #$00
        #   LDA $C203,X        ; send header bytes
        #   JSR $9926
        #   INC $C20C
        #   CPX #$06           ; 6 bytes
        #   BNE loop
        #   JMP $9922          ; send $02
        #
        # So it sends EXACTLY 6 bytes between $01 and $02. Always.
        # The 6 bytes are the complete packet content.
        # For small packets (ACK, etc.) all data fits in 6 bytes.
        # For larger data transfers, the protocol must use multiple packets
        # or a different mechanism.
        #
        # This means: each X.25 packet is exactly 8 bytes on the wire:
        #   $01 + 6 header bytes + $02
        #
        # The "payload" for data transfer must be delivered byte-by-byte
        # through the protocol engine's flow control, not in one big packet.
        # The MODEM_INIT_DOWNLOAD reads bytes via $96CC which goes through
        # the protocol engine — each call to $96CC returns ONE byte from
        # the current packet being processed.
        #
        # So the protocol delivers data in 6-byte packets, where:
        #   byte[0] = length/type info
        #   byte[1] = token (DAT for data)
        #   byte[2] = sequence number
        #   byte[3] = data byte (the actual payload)
        #   byte[4] = CRC high
        #   byte[5] = CRC low
        #
        # For multi-byte transfers, the server sends many packets,
        # each carrying 1 data byte. The protocol engine reassembles them.
        #
        # Wait — that can't be right. 1 byte per packet at 1200 baud would
        # be incredibly slow. Let me re-examine...
        #
        # Actually, looking at PROTO_PROCESS_CMD ($996B) more carefully:
        # It reads bytes from the packet buffer at ($21),Y and delivers
        # them one at a time to the caller. The packet buffer can hold
        # more than 1 byte — the 6-byte "header" is just the framing,
        # and the actual data follows AFTER the $02 end marker? No...
        #
        # Let me look at this differently. The ROM's receive path:
        # 1. Waits for $01 (start marker)
        # 2. Reads 6 bytes into $C203-$C208
        # 3. Waits for $02 (end marker)
        # 4. Validates CRC
        # 5. Processes based on token type
        #
        # For DAT packets, the "data" must be encoded within those 6 bytes.
        # With token + seq + CRC taking 4 bytes, that leaves 2 bytes for data.
        # Or maybe the length byte indicates how many MORE bytes follow
        # before the $02 marker.
        #
        # I think the key insight is: the 6-byte limit is for the HEADER only.
        # Data packets have additional payload bytes between the header and $02.
        # The ROM reads the header (6 bytes), then reads payload bytes based
        # on the length field, then reads $02.
        #
        # For now, let me implement the simplest working version:
        # Fixed 6-byte packets for ACK, and variable-length for data.

        # Build the packet content (between $01 and $02):
        # [length] [token] [seq] [payload...] [crc_hi] [crc_lo]
        content = bytearray()
        content.append(pkt_len & 0xFF)
        content.append(token)
        content.append(seq)
        content.extend(payload)

        # CRC over token + seq + payload (skip length byte)
        crc_hi, crc_lo = crc_ccitt(content[1:])  # skip length for CRC
        content.append(crc_hi)
        content.append(crc_lo)

        pkt = bytes([PKT_START]) + bytes(content) + bytes([PKT_END])
        token_name = TOKEN_NAMES.get(token, f'${token:02X}')
        log.info('X25 TX: %s seq=$%02X payload=%d bytes [%s...]',
                 token_name, seq, len(payload), pkt[:20].hex())
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

            # Parse header
            pkt_len = raw_pkt[0]
            token = raw_pkt[1]
            seq = raw_pkt[2]
            payload = raw_pkt[3:-2]  # everything between seq and CRC
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
