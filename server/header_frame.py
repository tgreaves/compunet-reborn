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

Everything here is a pure function over bytes and does no I/O, which keeps it
directly unit-testable (see tests/test_header_frame.py) and usable from the REST
handler without dragging the server module in.

One exception, added with #126: `_invisible_cells` imports `frame_to_cells` from
`api_binding` to find ink drawn in the background colour. Deliberately reusing the
renderer rather than writing a second cursor walk — a warning that disagreed with
the real renderer about where a character landed would be worse than none. The
import is local and guarded, so the validator still works standalone.
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


def normalise_header_frame(data):
    """Make an editor-saved page frame usable as a header. Returns `(body, notes)`.

    ⚠ THE ONLY PETSCII TOOL USERS HAVE IS THE CLIENT'S OWN EDITOR, AND IT SAVES
    PAGE FRAMES, NOT HEADER BODIES. A frame begins with the three-byte
    `[flags][border][background]` prefix (§7.2); a header body starts straight
    into PETSCII. Requiring authors to strip that by hand made the feature
    effectively operator-only, which is the opposite of what it was built for.

    Two adjustments, both safe, both reported back so nothing happens silently:

    1. **A leading frame header is removed.** Detection is unambiguous: a valid
       header body can never contain `$00` anywhere (see the validator), so a
       first byte of `$00`/`$80` — the only two flag values — cannot be artwork.
       There is no false positive to trade against.

    2. **A trailing `$92` is appended if reverse video is left on.** Design a
       header ending in a reversed bar to the screen edge and the editor has no
       reason to emit one; rejecting the file taught the author nothing they
       could act on, and the fix is a single byte the server can add itself.

    Everything genuinely dangerous is still REJECTED by the validator and never
    repaired here: `$00` inside the artwork, `$93`, `$0E`, ink below row 5, a
    truncated RLE escape. The rule is: repair what is merely untidy, refuse what
    would corrupt the screen.

    Reported by ZARD (#126) on the first real user attempt at the feature — one
    file, both problems.
    """
    notes = []
    body = data

    if body[:1] in (b'\x00', b'\x80') and len(body) >= 3:
        body = body[3:]
        notes.append(
            'Removed the 3-byte page-frame header your editor saved '
            '(flags/border/background) - a directory header holds the PETSCII '
            'only.')

    # Only append when the stream is otherwise well-formed; on a malformed frame
    # the validator's reasons are what the author needs, not a tacked-on byte.
    if body and not validate_header_frame(body, _skip_reverse_check=True):
        if _ends_reversed(body):
            body += b'\x92'
            notes.append(
                'Added $92 at the end to switch reverse video off, so it does '
                'not carry into the directory listing below your header.')

        hidden = _invisible_cells(body)
        if hidden:
            notes.append(
                'Warning: %d character%s on row%s %s drawn in light grey, which '
                'is the directory background colour ($0F, set by the client at '
                'compunet.s:3785) - they will be invisible. Design against light '
                'grey, not the white or black your editor may be showing you.'
                % (sum(hidden.values()),
                   's' if sum(hidden.values()) != 1 else '',
                   's' if len(hidden) != 1 else '',
                   ', '.join(str(r) for r in sorted(hidden))))

    return body, notes


#: The directory screen's background, fixed by the C64 client (`LDA #$0F` /
#: `STA $D021`, compunet.s:3785). A header CANNOT change it — the C64 has one
#: background register for the whole screen (§7 / §8.4.3) — which is why a header
#: is stored body-only and any border/background an editor saved is discarded.
DIRECTORY_BACKGROUND = 0x0F


def _invisible_cells(body):
    """`{row: count}` for ink drawn in the background colour, which cannot be seen.

    Not a rejection — it is a legitimate design choice on some other background,
    and nothing about it corrupts the screen. But it is invisible on the one
    background it will actually be drawn against, and an author working in the
    client's editor has no way to discover that: the editor shows their page's
    own background, not the directory's.
    """
    try:
        from api_binding import frame_to_cells
    except ImportError:                       # validator used standalone
        return {}
    cells = frame_to_cells(
        bytes([0x00, 0x0F, 0x0F]) + body + b'\x00')['cells']
    hidden = {}
    for row in range(LAST_HEADER_ROW + 1):
        n = sum(1 for col in range(40)
                for c in (cells[row * 40 + col],)
                if c['g'] != 32 and not c['rv']
                and c['fg'] == DIRECTORY_BACKGROUND)
        if n:
            hidden[row] = n
    return hidden


def _ends_reversed(data):
    """True if the stream leaves reverse video on. Walks tokens so an RLE
    operand that happens to equal $12/$92 is not mistaken for the control code."""
    reverse = False
    i, n = 0, len(data)
    while i < n:
        b = data[i]
        if b == 0x12:
            reverse = True
            i += 1
        elif b == 0x92:
            reverse = False
            i += 1
        elif b == 0x06:          # $06 <count> — run of spaces
            i += 2
        elif b == 0x07:          # $07 <char> <count> — repeated character
            i += 3
        else:
            i += 1
    return reverse


def validate_header_frame(data, _skip_reverse_check=False):
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

    # normalise_header_frame appends the $92 itself and passes the flag while it
    # decides whether the stream is otherwise sound, so this must not fire then —
    # it would report a fault the caller is about to repair.
    if reverse and not _skip_reverse_check:
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
