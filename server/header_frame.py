"""Validation for user-supplied directory header frames (Part 1, §7.2).

A directory header is the PETSCII drawn in the **header region, rows 0-5** (§7.7),
above the entry list. Operators have always been able to set one by putting a
`"header"` path in a directory JSON; issue #120 lets users supply one for a
directory they own, which means these bytes now arrive from outside and must be
checked before they reach disk.

Nothing else in this tree validates frame bytes — uploads are stored verbatim in
both bindings — so this is the first such check, and every rule below exists
because a specific renderer misbehaves without it. The rules are NOT cosmetic
preferences:

  * Part 1 is drawn **after** the built-in template (§7.5) and printed straight
    through the KERNAL, so anything it emits overwrites chrome that is already on
    screen. There is no clipping anywhere in the C64 path.
  * The three renderers disagree about malformed input. A file that merely "looks
    fine" in the web client can destroy the C64 screen. Validation therefore
    targets the STRICTEST consumer, which is always the real hardware.

Everything here is a pure function over bytes: no I/O, no server imports. That
keeps it directly unit-testable (see tests/test_header_frame.py) and usable from
the REST handler without dragging the server module in.
"""

#: Largest accepted header. The hard ceiling is 768: the C64 stores Part 1 at
#: $D000 with **no length counter and no bounds check** (compunet.s:3244-3256),
#: and the Part 2 buffer begins at $D300, so byte 769 silently corrupts Parts
#: 2/4/5/6. 512 keeps real headroom below that — the largest header shipped with
#: the service is 341 bytes — so a later change to the buffer layout does not
#: turn stored, previously-valid headers into memory corruption on real hardware.
MAX_BYTES = 512

#: Last row of the header region (§7.7). Row 6 is the template's top border.
LAST_HEADER_ROW = 5

COLS = 40
ROWS = 24

# Control codes rejected outright. Both are legal PETSCII that the format
# permits in a frame generally — they are refused *here* because of what Part 1
# specifically is composed onto.
_CLEAR_SCREEN = 0x93
_CHARSET_LOWER = 0x0E

_COLOUR_CODES = frozenset(
    (0x05, 0x1C, 0x1E, 0x1F, 0x81, 0x90, 0x9C, 0x9E, 0x9F,
     0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B))


def _is_control(b):
    """§5.6 — matches api_binding._is_control."""
    return b <= 0x1F or 0x80 <= b <= 0x9F


def _hx(b):
    return '$%02X' % b


def validate_header_frame(data):
    """Check user-supplied header bytes.

    `data` is the frame BODY only — no 4-byte frame header (§7.2) and no
    trailing $00; the server appends its own terminator when it builds Part 1.

    Returns a list of human-readable reasons. Empty means the frame is safe to
    store. Every reason names the byte offset, because the author has to find
    the problem in a binary file they made in some other tool.
    """
    reasons = []

    if not data:
        return ['The file is empty.']

    if len(data) > MAX_BYTES:
        reasons.append(
            'Too large: %d bytes, limit %d. The C64 stores the header in a '
            '%d-byte buffer with no bounds check, and overrunning it corrupts '
            'the rest of the directory.' % (len(data), MAX_BYTES, 768))

    # ⚠ Scanned over the RAW bytes, deliberately, and not as part of the token
    # walk below. Verified at compunet.s:3252: the C64's Part-1 store loop is
    # BYTE-LEVEL — fetch, store, `CMP #$00`, repeat — and knows nothing about
    # RLE. So a $00 serving merely as a repeat-count operand still ends the
    # copy; everything after it is parsed as Part 2/3/4 and the six-part stream
    # desynchronises on real hardware. A token-level check misses exactly that
    # case, which is the one worth catching.
    #
    # §6.4 now forbids a $00 operand outright, for the whole frame format
    # rather than just here — it was the spec contradicting itself (a zero
    # count is "one space" by §6.4 and end-of-frame by §6.3/§6.1), which is why
    # the two bindings drew different screens from the same file.
    nul_at = data.find(b'\x00')
    if nul_at >= 0:
        reasons.append(
            'Contains a $00 byte at offset %d. A header may not contain $00 '
            'anywhere, not even as a repeat-count, because the C64 stops '
            'copying the header at the first $00 and the rest of the directory '
            'is then misread.' % nul_at)

    # --- The cursor simulation -------------------------------------------
    #
    # Mirrors the §6.3 processing loop in api_binding.frame_to_cells so that
    # what we accept renders the same way the client will draw it. We track
    # where glyphs LAND rather than where the cursor ends up: a header may
    # legitimately leave the cursor on row 6 (all four shipped headers do,
    # having ended with a CR) — what it must never do is PRINT there.
    #
    # Part 1 is preceded by $8E on the wire (compunet_server.py) and by a
    # synthetic $8E in Binding B, so the frame starts in the uppercase set.
    lower = False
    reverse = 0
    row = col = 0
    just_wrapped = False
    worst_ink_row = 0
    first_overflow_at = None

    def place(offset):
        nonlocal row, col, just_wrapped, worst_ink_row, first_overflow_at
        if row > worst_ink_row:
            worst_ink_row = row
        if row > LAST_HEADER_ROW and first_overflow_at is None:
            first_overflow_at = (offset, row)
        col += 1
        if col >= COLS:
            col = 0
            if row < ROWS - 1:
                row += 1
            just_wrapped = True
        else:
            just_wrapped = False

    def control(b):
        nonlocal row, col, reverse, lower, just_wrapped
        if b in _COLOUR_CODES:
            return
        if b in (0x0D, 0x8D):            # CR (§5.6.1 auto-wrap guard)
            col = 0
            reverse = 0
            if not just_wrapped and row < ROWS - 1:
                row += 1
            just_wrapped = False
        elif b == 0x11:                  # cursor down
            row = min(row + 1, ROWS - 1); just_wrapped = False
        elif b == 0x91:                  # cursor up
            row = max(row - 1, 0); just_wrapped = False
        elif b == 0x1D:                  # cursor right (wraps)
            col += 1
            if col >= COLS:
                col = 0; row = min(row + 1, ROWS - 1)
            just_wrapped = False
        elif b == 0x9D:                  # cursor left (wraps)
            col -= 1
            if col < 0:
                col = COLS - 1; row = max(row - 1, 0)
            just_wrapped = False
        elif b == 0x13:                  # home
            row = col = 0; just_wrapped = False
        elif b == 0x93:                  # clear + home
            row = col = 0; just_wrapped = False
        elif b == 0x12:
            reverse = 1
        elif b == 0x92:
            reverse = 0
        elif b == 0x0E:
            lower = True
        elif b == 0x8E:
            lower = False

    banned_seen = {}

    def process(b, offset):
        # ⚠ Applied to the EXPANDED stream, not the raw file. `$07 $93 $27` is
        # forty clear-screens hidden in three bytes (§6.4), so a byte-level scan
        # of the file would wave it straight through.
        if b in (_CLEAR_SCREEN, _CHARSET_LOWER) and b not in banned_seen:
            banned_seen[b] = offset
        if _is_control(b):
            control(b)
        else:
            place(offset)

    i, n = 0, len(data)
    while i < n:
        offset = i
        b = data[i]; i += 1

        if b == 0x00:
            # Already reported by the raw scan above; stop walking, because this
            # is where every renderer stops reading too.
            break

        if b == 0x06:                    # space run (§6.4): 1+N spaces
            if i >= n:
                reasons.append(
                    'Truncated space-run at offset %d: $06 must be followed by '
                    'a count byte.' % offset)
                break
            count = data[i]; i += 1
            for _ in range(1 + count):
                place(offset)
        elif b == 0x07:                  # char/control run (§6.4): c, 1+N times
            if i + 1 >= n:
                reasons.append(
                    'Truncated repeat-run at offset %d: $07 must be followed '
                    'by a character and a count byte.' % offset)
                break
            c = data[i]; count = data[i + 1]; i += 2
            for _ in range(1 + count):
                process(c, offset)
        else:
            process(b, offset)

    if _CLEAR_SCREEN in banned_seen:
        reasons.append(
            'Contains a clear-screen ($93) at offset %d. The header is drawn '
            'on top of the directory template, so a clear-screen erases the '
            'whole screen — border, entry list and all.'
            % banned_seen[_CLEAR_SCREEN])

    if _CHARSET_LOWER in banned_seen:
        reasons.append(
            'Contains a lower-case charset switch ($0E) at offset %d. Nothing '
            'restores the character set after the header, so the rest of the '
            'directory would be drawn in the wrong set.'
            % banned_seen[_CHARSET_LOWER])

    if first_overflow_at is not None:
        offset, bad_row = first_overflow_at
        reasons.append(
            'Draws on row %d (from offset %d). A header may only use rows 0-%d '
            '— row %d is the top of the directory frame, and anything below '
            'that overwrites the entry list.'
            % (bad_row, offset, LAST_HEADER_ROW, LAST_HEADER_ROW + 1))

    if reverse:
        reasons.append(
            'Ends with reverse video still switched on. Add $92 to turn it off, '
            'or the next line drawn starts reversed.')

    return reasons


def describe_header_frame(data):
    """Rows actually used, for reporting a valid frame back to the author.

    There is no preview on the upload form yet, so this is the only feedback an
    author gets about where their artwork landed.
    """
    reasons = validate_header_frame(data)
    if reasons:
        return None
    rows = 0
    lower = False
    reverse = 0
    row = col = 0
    just_wrapped = False
    # Re-walk with the same rules; validate_header_frame has already proved the
    # stream is well-formed, so this cannot run off the end.
    i, n = 0, len(data)

    def _place():
        nonlocal row, col, just_wrapped, rows
        if row + 1 > rows:
            rows = row + 1
        col += 1
        if col >= COLS:
            col = 0
            if row < ROWS - 1:
                row += 1
            just_wrapped = True
        else:
            just_wrapped = False

    while i < n:
        b = data[i]; i += 1
        if b == 0x06:
            count = data[i]; i += 1
            for _ in range(1 + count):
                _place()
            continue
        if b == 0x07:
            c = data[i]; count = data[i + 1]; i += 2
            for _ in range(1 + count):
                if _is_control(c):
                    if c in (0x0D, 0x8D):
                        col = 0
                        if not just_wrapped and row < ROWS - 1:
                            row += 1
                        just_wrapped = False
                else:
                    _place()
            continue
        if _is_control(b):
            if b in (0x0D, 0x8D):
                col = 0
                if not just_wrapped and row < ROWS - 1:
                    row += 1
                just_wrapped = False
            elif b == 0x11:
                row = min(row + 1, ROWS - 1); just_wrapped = False
            elif b == 0x91:
                row = max(row - 1, 0); just_wrapped = False
            elif b == 0x13:
                row = col = 0; just_wrapped = False
        else:
            _place()

    return {'bytes': len(data), 'rows_used': rows}
