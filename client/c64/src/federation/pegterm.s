; =================================================================
; FEDERATION CLIENT — Downloaded and executed by the C64 terminal
; =================================================================
; Draws the Federation UI, then enters main loop:
;   - Polls NMI ring buffer for incoming server messages
;   - Polls keyboard for user input
;   - Transmits on RETURN via ACIA
;   - Cursor up/down scrolls back through chat history
;   - Exits only on *EXIT: the host ends the session, never the user
; =================================================================

.segment "CODE"

; --- KERNAL ---
GETIN           = $FFE4

; --- VIC-II ---
VIC_BORDER      = $D020
VIC_BGCOL0      = $D021

; --- Screen/Colour RAM ---
SCREEN          = $0400
COLOUR          = $D800

; --- ACIA (SwiftLink) ---
ACIA_DATA       = $DE00
ACIA_STATUS     = $DE01
ACIA_CTRL       = $DE03

; ⚠ LINE SPEED IS NOT PEGTERM'S BUSINESS. The original modem fixed it at
; 1200/75 in hardware; the ROM's SwiftLink stand-in runs it at 38400 ($1F,
; and SwiftLink doubles the 6551 table). pegterm draws a line slower than
; 38400 delivers one, overruns the 256-byte NMI ring and loses whole laps
; of it. So, reluctantly, it reprograms the ROM's ACIA to 1200 for the
; session and puts it back on exit. compunet.s is feature-locked; the
; trespass stays here. Table rate 600 x 2 = 1200.
ACIA_BPS_MASK   = $0F           ; control register bits 0-3: bit rate
ACIA_BPS_1200   = $07           ; 600 in the 6551 table, doubled

; --- NMI Ring Buffer ---
NMI_BUF         = $C500         ; 256-byte ring buffer (must match compunet.s)
NMI_BUF_TAIL    = $029B         ; Write pointer (NMI advances)
NMI_BUF_HEAD    = $029C         ; Read pointer (we advance)

; --- Zero-page temporaries ---
ZP_PTR1         = $FB           ; general pointer low
ZP_PTR1_HI      = $FC           ; general pointer high
ZP_PTR2         = $FD           ; general pointer low
ZP_PTR2_HI      = $FE           ; general pointer high

; --- Constants ---
CR              = $0D           ; carriage return
DEL_KEY         = $14           ; DEL key code from GETIN
CURSOR_UP       = $91           ; cursor up key code from GETIN
CURSOR_DOWN     = $11           ; cursor down key code from GETIN
CURSOR_CHAR     = $1F           ; left-arrow cursor character
SPACE           = $20           ; space screen code

; --- Colours ---
COL_BLACK       = $00
COL_TEXT        = $0F           ; light grey

; --- Screen layout ---
;   row  0     header (reverse video)
;   rows 1-22  output
;   row  23    divider
;   row  24    input
LINE_CHAR       = $40           ; horizontal line screen code
DIVIDER_ROW     = 23

; --- Chat area parameters ---
CHAT_TOP_ROW    = 1             ; first content row
CHAT_BOT_ROW    = 22            ; last content row
CHAT_LEFT_COL   = 0            ; first content column
CHAT_RIGHT_COL  = 39           ; last content column (inclusive)
CHAT_WIDTH      = 40           ; columns available (0..39)
CHAT_ROWS       = 22           ; rows available (1..22)

; --- Scrollback split (active while scroll_offset > 0) ---
;   rows 1-10   scrollback
;   row  11     bar
;   rows 12-22  live output
; Closes when the scrollback's last line meets the live pane's first.
BAR_CHAR        = LINE_CHAR      ; same divider as above the input row
SB_ROWS         = (CHAT_ROWS - 1) / 2
LIVE_ROWS       = CHAT_ROWS - 1 - SB_ROWS
SPLIT_BAR_ROW   = CHAT_TOP_ROW + SB_ROWS
LIVE_TOP_ROW    = SPLIT_BAR_ROW + 1
SPLIT_LINES     = SB_ROWS + LIVE_ROWS   ; history lines on screen when split

; --- Input area parameters ---
INPUT_TOP_ROW   = 24            ; only input row
INPUT_WIDTH     = 40           ; columns available (0..39)
INPUT_VIEW      = INPUT_WIDTH - 1   ; text columns; the last is the cursor's
INPUT_SCREEN    = SCREEN + INPUT_TOP_ROW*40

; --- History buffer parameters ---
; Ring of 40-byte lines from the end of this program to the Compunet ROM
; image at $8000. $0200-$7FFF is program space (compunet.s clears it).
;
;   $2000 [ pegterm code+data ][ hist_buf ...................... ] $8000
HIST_LINE_SIZE  = 40            ; same as CHAT_WIDTH
HIST_END        = $8000         ; Compunet ROM image starts here
HIST_LINES      = (HIST_END - hist_buf) / HIST_LINE_SIZE
HIST_LIMIT      = hist_buf + HIST_LINES * HIST_LINE_SIZE  ; one past last line
SB_MAX          = HIST_LINES - SPLIT_LINES  ; max scroll_offset

; =================================================================
; ENTRY POINT
; =================================================================

start:
    ; --- Set colours: black border and background, grey text ---
    LDA #COL_BLACK
    STA VIC_BORDER
    STA VIC_BGCOL0

    ; --- Switch to lowercase character set ---
    LDA #$17
    STA $D018

    ; --- Clear screen RAM with spaces ---
    LDA #SPACE
    LDX #$00
@clr:
    STA SCREEN,X
    STA SCREEN+$100,X
    STA SCREEN+$200,X
    STA SCREEN+$300,X
    DEX
    BNE @clr

    ; --- Set colour RAM: whole screen grey ---
    LDA #COL_TEXT
    LDX #$00
@col_text:
    STA COLOUR,X
    STA COLOUR+$100,X
    STA COLOUR+$200,X
    STA COLOUR+$300,X
    DEX
    BNE @col_text

    ; --- Row 0: header (reverse video = grey bar, black text) ---
    ; --- Row 23: divider line ---
    LDX #$00
@hdr:
    LDA header_sc,X
    STA SCREEN,X
    LDA #LINE_CHAR
    STA SCREEN+DIVIDER_ROW*40,X
    INX
    CPX #$28
    BNE @hdr

    ; --- Initialize variables ---
    LDA #$00
    STA chat_cur_row            ; next chat row (0-based within chat area)
    STA rx_line_len             ; receive line buffer length
    STA tx_buf_len              ; transmit buffer length
    STA exit_flag               ; flag: time to exit
    STA hist_count              ; total history lines stored
    STA hist_count+1
    STA scroll_offset           ; lines scrolled back (0 = live)
    STA scroll_offset+1

    ; History starts empty at hist_buf. Not zeroed: no line is drawn
    ; before it has been written.
    LDA #<hist_buf
    STA hist_write
    LDA #>hist_buf
    STA hist_write+1

    ; --- Place cursor in input area ---
    JSR draw_input

    ; --- Borrow the ROM's ACIA: 1200 baud, or we can't keep up ---
    ; Not ours to set (see ACIA_BPS_1200); do_exit restores.
    LDA ACIA_CTRL
    STA saved_ctrl
    AND #<~ACIA_BPS_MASK        ; keep framing, replace rate
    ORA #ACIA_BPS_1200
    STA ACIA_CTRL

; =================================================================
; MAIN LOOP
; =================================================================

main_loop:
    ; --- Check exit flag ---
    LDA exit_flag
    BNE do_exit

    ; --- Check carrier (DCD bit 5 of ACIA status, high = lost) ---
    LDA ACIA_STATUS
    AND #$20
    BNE do_exit

    ; --- Poll receive buffer ---
    JSR poll_receive

    ; --- Poll keyboard ---
    JSR poll_keyboard

    ; --- Loop ---
    JMP main_loop

; =================================================================
; EXIT SEQUENCE
; =================================================================

do_exit:
    ; Hand the ROM back its own bit rate before X.25 resumes
    LDA saved_ctrl
    STA ACIA_CTRL

    ; Restore colours and charset
    LDA #$0E
    STA VIC_BORDER
    LDA #$06
    STA VIC_BGCOL0
    LDA #$15
    STA $D018                   ; restore uppercase charset
    RTS

; =================================================================
; POLL RECEIVE — Check NMI ring buffer for incoming bytes
; =================================================================

poll_receive:
    LDA NMI_BUF_HEAD
    CMP NMI_BUF_TAIL
    BEQ @rx_done                ; buffer empty

    ; Read byte from ring buffer
    TAX
    LDA NMI_BUF,X
    INC NMI_BUF_HEAD           ; advance read pointer

    ; Check for CR (end of line)
    CMP #CR
    BEQ @rx_line_complete

    ; Store in rx line buffer
    LDX rx_line_len
    CPX #CHAT_WIDTH             ; don't overflow line buffer
    BCS @rx_done                ; discard if too long
    STA rx_line_buf,X
    INC rx_line_len
@rx_done:
    RTS

@rx_line_complete:
    ; Check for the ONE sentinel: *EXIT. Everything else the server sends is
    ; text, including a line that happens to start with '*' — the far end of a
    ; Federation link is another service, and its chat is not our vocabulary.
    LDA rx_line_buf
    CMP #$2A                    ; '*'
    BNE @not_sentinel

    ; Check for *EXIT
    LDA rx_line_len
    CMP #$05                    ; "*EXIT" = 5 chars
    BNE @not_sentinel
    LDA rx_line_buf+1
    CMP #$45                    ; 'E' (EXIT)
    BNE @not_sentinel
    LDA rx_line_buf+2
    CMP #$58                    ; 'X'
    BNE @not_sentinel
    LDA rx_line_buf+3
    CMP #$49                    ; 'I'
    BNE @not_sentinel
    LDA rx_line_buf+4
    CMP #$54                    ; 'T'
    BNE @not_sentinel
    ; Got *EXIT — set exit flag
    LDA #$01
    STA exit_flag
    LDA #$00
    STA rx_line_len
    RTS

@not_sentinel:
    ; Display the received line in chat area
    JSR display_rx_line
    ; Reset rx line buffer
    LDA #$00
    STA rx_line_len
    RTS

; =================================================================
; DISPLAY_RX_LINE — Show a received line in the chat area
; =================================================================

display_rx_line:
    ; --- Convert the line to screen codes straight into its history slot ---
    LDA hist_write
    STA ZP_PTR2
    LDA hist_write+1
    STA ZP_PTR2_HI
    LDY #$00
@conv_char:
    CPY rx_line_len
    BCS @conv_pad
    LDA rx_line_buf,Y
    JSR petscii_to_screencode
    JMP @conv_put
@conv_pad:
    LDA #SPACE
@conv_put:
    STA (ZP_PTR2),Y
    INY
    CPY #HIST_LINE_SIZE
    BCC @conv_char

    ; Advance hist_write, wrapping round the ring
    JSR hist_next
    LDA ZP_PTR2
    STA hist_write
    LDA ZP_PTR2_HI
    STA hist_write+1

    ; Increment hist_count, saturate at HIST_LINES
    LDA hist_count
    CMP #<HIST_LINES
    LDA hist_count+1
    SBC #>HIST_LINES
    BCS @count_full
    INC hist_count
    BNE @count_full
    INC hist_count+1
@count_full:

    ; --- Split view open? ---
    LDA scroll_offset
    ORA scroll_offset+1
    BNE @scrolled_back

    ; --- Live mode: scroll if full, then draw the newest line ---
    LDA chat_cur_row
    CMP #CHAT_ROWS
    BCC @no_scroll
    JSR scroll_chat
    DEC chat_cur_row            ; stay on last row after scroll
@no_scroll:
    LDA #$01
    JSR hist_back_a             ; ZP_PTR2 = newest line
    LDA chat_cur_row
    CLC
    ADC #CHAT_TOP_ROW           ; absolute screen row
    LDX #$01
    JSR draw_hist_rows
    INC chat_cur_row
    RTS

@scrolled_back:
    ; Split view: increment scroll_offset so the scrollback pane stays
    ; stable (cap at max), then redraw so the live pane shows the new line.
    LDA scroll_offset
    CMP #<SB_MAX
    LDA scroll_offset+1
    SBC #>SB_MAX
    BCS @offset_capped
    INC scroll_offset
    BNE @offset_capped
    INC scroll_offset+1
@offset_capped:
    JSR redraw_chat_from_history
    ; Keep chat_cur_row at maximum (screen is full when scrolled)
    LDA #CHAT_ROWS
    STA chat_cur_row
    RTS

; =================================================================
; SCROLL_CHAT — Scroll chat area up by one row
; =================================================================

scroll_chat:
    ; Copy rows 3..16 up to rows 2..15 (in screen RAM)
    ; Source: row (CHAT_TOP_ROW+1), Dest: row CHAT_TOP_ROW
    ; We copy (CHAT_ROWS-1) rows

    ; Set dest = first chat row
    LDA #<(SCREEN + CHAT_TOP_ROW*40 + CHAT_LEFT_COL)
    STA ZP_PTR1
    LDA #>(SCREEN + CHAT_TOP_ROW*40 + CHAT_LEFT_COL)
    STA ZP_PTR1_HI

    ; Set source = second chat row
    LDA #<(SCREEN + (CHAT_TOP_ROW+1)*40 + CHAT_LEFT_COL)
    STA ZP_PTR2
    LDA #>(SCREEN + (CHAT_TOP_ROW+1)*40 + CHAT_LEFT_COL)
    STA ZP_PTR2_HI

    LDX #(CHAT_ROWS - 1)       ; rows to copy
@scroll_row:
    LDY #$00
@scroll_col:
    LDA (ZP_PTR2),Y
    STA (ZP_PTR1),Y
    INY
    CPY #CHAT_WIDTH
    BCC @scroll_col

    ; Advance both pointers by 40
    CLC
    LDA ZP_PTR1
    ADC #$28
    STA ZP_PTR1
    BCC @s1
    INC ZP_PTR1_HI
@s1:
    CLC
    LDA ZP_PTR2
    ADC #$28
    STA ZP_PTR2
    BCC @s2
    INC ZP_PTR2_HI
@s2:
    DEX
    BNE @scroll_row

    ; Clear the last row (row 16, col 3)
    LDY #$00
    LDA #SPACE
@clear_last:
    STA (ZP_PTR1),Y
    INY
    CPY #CHAT_WIDTH
    BCC @clear_last

    RTS

; =================================================================
; POLL KEYBOARD — Read key and handle input
; =================================================================

poll_keyboard:
    JSR GETIN
    CMP #$00
    BEQ @no_key                 ; no key pressed

    ; --- Cursor up: scroll back ---
    CMP #CURSOR_UP
    BNE @not_cup
    JSR scroll_back
    JMP @no_key
@not_cup:
    ; --- Cursor down: scroll forward ---
    CMP #CURSOR_DOWN
    BNE @not_cdn
    JSR scroll_forward
    JMP @no_key
@not_cdn:

    ; --- DEL key ---
    CMP #DEL_KEY
    BEQ @do_del

    ; --- RETURN ---
    CMP #CR
    BEQ @do_return

    ; --- Printable character ---
    ; Only allow: $20-$5F (space, numbers, lowercase, punctuation)
    ;             $C1-$DA (shifted uppercase letters)
    CMP #$20
    BCC @no_key                 ; reject $00-$1F (control codes)
    CMP #$60
    BCC @char_ok                ; $20-$5F accepted
    CMP #$C1
    BCC @no_key                 ; reject $60-$C0 (graphics chars)
    CMP #$DB
    BCS @no_key                 ; reject $DB-$FF
@char_ok:
    ; Store in transmit buffer
    LDX tx_buf_len
    CPX #TX_BUF_SIZE
    BCS @no_key                 ; buffer full, ignore
    STA tx_buf,X
    INC tx_buf_len
    JSR draw_input

@no_key:
    RTS

@do_del:
    ; Check if anything to delete
    LDA tx_buf_len
    BEQ @no_key                 ; nothing to delete
    DEC tx_buf_len
    JMP draw_input

@do_return:
    ; Single-line input: RETURN sends; empty line ignored
    LDA tx_buf_len
    BEQ @no_key

    ; Transmit the buffer contents + CR
    JSR transmit_buffer
    ; Empty the input row
    LDA #$00
    STA tx_buf_len
    JMP draw_input

; =================================================================
; SCROLL_BACK — Scroll chat view one line back into history
; =================================================================

scroll_back:
    ; Max scrollback = hist_count - SPLIT_LINES; none if <= 0
    SEC
    LDA hist_count
    SBC #SPLIT_LINES
    STA hist_n
    LDA hist_count+1
    SBC #$00
    STA hist_n+1
    BCC @cant                   ; everything already on screen
    ORA hist_n
    BEQ @cant                   ; everything already on screen

    ; Already at max?
    LDA scroll_offset
    CMP hist_n
    LDA scroll_offset+1
    SBC hist_n+1
    BCS @cant

    INC scroll_offset
    BNE @redraw
    INC scroll_offset+1
@redraw:
    JSR redraw_chat_from_history
@cant:
    RTS

; =================================================================
; SCROLL_FORWARD — Scroll chat view one line forward toward live
; =================================================================

scroll_forward:
    LDA scroll_offset
    ORA scroll_offset+1
    BEQ @cant                   ; already at live
    LDA scroll_offset
    BNE @lo
    DEC scroll_offset+1
@lo:
    DEC scroll_offset
    JSR redraw_chat_from_history
@cant:
    RTS

; =================================================================
; REDRAW_CHAT_FROM_HISTORY — Redraw the output area from hist_buf
; =================================================================
; scroll_offset = 0: one pane, the newest CHAT_ROWS lines.
; scroll_offset > 0: split. Live pane = newest LIVE_ROWS lines; the
; scrollback pane ends scroll_offset lines above the live pane's first,
; so scroll_offset 1 hides exactly the one line under the bar.
;
;   history:  ... [ scrollback ] <offset gap> [ live ] | hist_write

redraw_chat_from_history:
    LDA scroll_offset
    ORA scroll_offset+1
    BNE @split

    ; --- Closed: full-height live pane ---
    LDA #CHAT_ROWS
    JSR hist_back_a
    LDA #CHAT_TOP_ROW
    LDX #CHAT_ROWS
    JMP draw_hist_rows

@split:
    ; --- Bar between the panes ---
    LDA #BAR_CHAR
    LDX #$27
@bar:
    STA SCREEN+SPLIT_BAR_ROW*40,X
    DEX
    BPL @bar

    ; --- Scrollback pane: scroll_offset + SPLIT_LINES back ---
    CLC
    LDA scroll_offset
    ADC #SPLIT_LINES
    STA hist_n
    LDA scroll_offset+1
    ADC #$00
    STA hist_n+1
    JSR hist_back
    LDA #CHAT_TOP_ROW
    LDX #SB_ROWS
    JSR draw_hist_rows

    ; --- Live pane ---
    LDA #LIVE_ROWS
    JSR hist_back_a
    LDA #LIVE_TOP_ROW
    LDX #LIVE_ROWS
    JMP draw_hist_rows

; =================================================================
; HIST_BACK — ZP_PTR2 = the line hist_n lines before hist_write
; =================================================================
; Input: hist_n = lines back (1..HIST_LINES), or A via hist_back_a.
; Steps back one line at a time: no multiply, ~50 cycles a line.

hist_back_a:
    STA hist_n
    LDA #$00
    STA hist_n+1

hist_back:
    LDA hist_write
    STA ZP_PTR2
    LDA hist_write+1
    STA ZP_PTR2_HI
@loop:
    JSR hist_prev
    LDA hist_n
    BNE @lo
    DEC hist_n+1
@lo:
    DEC hist_n
    LDA hist_n
    ORA hist_n+1
    BNE @loop
    RTS

; =================================================================
; HIST_NEXT / HIST_PREV — Step ZP_PTR2 one line through the ring
; =================================================================
; The ring is hist_buf .. HIST_LIMIT-1; stepping off either end wraps.

hist_next:
    CLC
    LDA ZP_PTR2
    ADC #HIST_LINE_SIZE
    STA ZP_PTR2
    BCC @cmp
    INC ZP_PTR2_HI
@cmp:
    ; Past the last line? Wrap to the first.
    LDA ZP_PTR2
    CMP #<HIST_LIMIT
    LDA ZP_PTR2_HI
    SBC #>HIST_LIMIT
    BCC @ok
    LDA #<hist_buf
    STA ZP_PTR2
    LDA #>hist_buf
    STA ZP_PTR2_HI
@ok:
    RTS

hist_prev:
    SEC
    LDA ZP_PTR2
    SBC #HIST_LINE_SIZE
    STA ZP_PTR2
    BCS @cmp
    DEC ZP_PTR2_HI
@cmp:
    ; Before the first line? Wrap to the last.
    LDA ZP_PTR2
    CMP #<hist_buf
    LDA ZP_PTR2_HI
    SBC #>hist_buf
    BCS @ok
    LDA #<(HIST_LIMIT - HIST_LINE_SIZE)
    STA ZP_PTR2
    LDA #>(HIST_LIMIT - HIST_LINE_SIZE)
    STA ZP_PTR2_HI
@ok:
    RTS

; =================================================================
; DRAW_HIST_ROWS — Copy X history lines, from ZP_PTR2, to screen
; =================================================================
; Input: A = first screen row, X = line count, ZP_PTR2 = first line.
; Output area is full width, so a line maps straight onto a row.

draw_hist_rows:
    STA hist_draw_row           ; absolute screen row counter
@draw_loop:
    STX hist_draw_cnt           ; calc_row_addr clobbers X
    LDA hist_draw_row
    JSR calc_row_addr           ; ZP_PTR1 = screen row start

    LDY #$00
@copy_hist:
    LDA (ZP_PTR2),Y
    STA (ZP_PTR1),Y
    INY
    CPY #CHAT_WIDTH
    BCC @copy_hist

    JSR hist_next
    INC hist_draw_row
    LDX hist_draw_cnt
    DEX
    BNE @draw_loop
    RTS

; =================================================================
; TRANSMIT_BUFFER — Send tx_buf contents via ACIA, CR-terminated
; =================================================================

transmit_buffer:
    LDX #$00
@tx_loop:
    CPX tx_buf_len
    BCS @tx_cr                  ; done with data, send CR
    LDA tx_buf,X
    JSR acia_send_byte
    INX
    BNE @tx_loop                ; always branches (X wraps at 256 max)
@tx_cr:
    LDA #CR
    JSR acia_send_byte
    RTS

; =================================================================
; ACIA_SEND_BYTE — Send byte in A via ACIA TX
; =================================================================

acia_send_byte:
    PHA
@wait_tx:
    LDA ACIA_STATUS
    AND #$10                    ; bit 4 = TDRE
    BEQ @wait_tx
    PLA
    STA ACIA_DATA
    RTS

; =================================================================
; DRAW_INPUT — Render the input row from tx_buf, cursor after the text
; =================================================================
; Shows the last INPUT_VIEW chars. Once the line reaches INPUT_VIEW,
; each new char scrolls the view left by one and the cursor stays
; pinned in the last column:
;
;   len 10:  hello worl_
;   len 45:  ...(first 6 hidden)...last 39 chars_

draw_input:
    ; First tx_buf index shown = max(0, len - INPUT_VIEW)
    LDA tx_buf_len
    SEC
    SBC #INPUT_VIEW
    BCS @view_ok
    LDA #$00
@view_ok:
    STA input_view

    ; Fill every column: text, then spaces
    LDY #$00                    ; screen column
@col:
    TYA
    CLC
    ADC input_view              ; tx_buf index (max 216+39, no carry)
    CMP tx_buf_len
    BCS @blank
    TAX
    LDA tx_buf,X
    JSR petscii_to_screencode
    JMP @put
@blank:
    LDA #SPACE
@put:
    STA INPUT_SCREEN,Y
    INY
    CPY #INPUT_WIDTH
    BCC @col

    ; Cursor in the column after the last char shown
    LDA tx_buf_len
    SEC
    SBC input_view
    TAY
    LDA #CURSOR_CHAR
    STA INPUT_SCREEN,Y
    RTS

; =================================================================
; CALC_ROW_ADDR — Given row number in A, set ZP_PTR1 to screen addr
; =================================================================
; Input: A = row (0-24)
; Output: ZP_PTR1/ZP_PTR1_HI = SCREEN + row*40

calc_row_addr:
    ; Multiply A by 40 using lookup table
    TAX
    LDA row_addr_lo,X
    STA ZP_PTR1
    LDA row_addr_hi,X
    STA ZP_PTR1_HI
    RTS

; =================================================================
; PETSCII_TO_SCREENCODE — Convert PETSCII byte to screen code
; =================================================================
; Input: A = PETSCII byte
; Output: A = screen code

petscii_to_screencode:
    ; $20-$3F -> $20-$3F (space, digits, punctuation)
    CMP #$20
    BCC @ctrl_range
    CMP #$40
    BCC @done                   ; $20-$3F unchanged

    ; $40-$5F -> $00-$1F (uppercase letters @ A-Z etc)
    CMP #$60
    BCC @upper
    ; $60-$7F -> $40-$5F (appears as lowercase in lc mode)
    ; Wait: in C64 lowercase mode:
    ;   PETSCII $41-$5A (uppercase) -> screen code $01-$1A
    ;   PETSCII $C1-$DA (shifted uppercase) -> screen code $41-$5A
    ;   PETSCII $61-$7A (lowercase) -> no direct PETSCII...
    ; Actually the server sends standard ASCII over the wire.
    ; ASCII $41-$5A = uppercase = PETSCII $C1-$DA
    ; ASCII $61-$7A = lowercase = PETSCII $41-$5A
    ; But wait — the server is sending raw ASCII text.
    ; Let's handle ASCII properly:
    ;
    ; ASCII $20-$3F -> screen code $20-$3F (same)
    ; ASCII $41-$5A (A-Z) -> screen code $01-$1A (uppercase in lc charset)
    ; ASCII $61-$7A (a-z) -> screen code $01-$1A (show as lowercase)
    ;   Actually in lc charset: screen $01-$1A = lowercase a-z
    ;   screen $41-$5A = uppercase A-Z
    ; So: ASCII a-z ($61-$7A) -> screen $01-$1A (lowercase)
    ;     ASCII A-Z ($41-$5A) -> screen $41-$5A (uppercase) ... no wait
    ;     Let me think again.
    ;
    ; C64 lowercase charset screen codes:
    ;   $00 = @
    ;   $01-$1A = lowercase a-z
    ;   $41-$5A = uppercase A-Z
    ;
    ; Server sends raw bytes. Assuming server sends PETSCII-ish:
    ;   lowercase a-z = $41-$5A (standard PETSCII lowercase)
    ;   uppercase A-Z = $C1-$DA (standard PETSCII uppercase)
    ;
    ; But since protocol is "raw CR-terminated text lines", server likely
    ; sends ASCII. Let's handle both by mapping ranges:

    ; $60-$7F range (ASCII lowercase a-z at $61-$7A)
    CMP #$80
    BCC @ascii_lower

    ; $80-$9F -> control, map to space
    CMP #$A0
    BCC @to_space

    ; $A0-$BF -> $60-$7F (graphics in screen codes)
    CMP #$C0
    BCC @range_a0

    ; $C0-$DF -> uppercase in PETSCII ($C1-$DA = A-Z)
    CMP #$E0
    BCC @petscii_upper

    ; $E0-$FF -> $60-$7F (more graphics)
    SEC
    SBC #$80
    RTS

@ctrl_range:
    ; $00-$1F -> show as space (non-printable)
    LDA #SPACE
    RTS

@done:
    RTS

@upper:
    ; $40-$5F: in PETSCII, $41-$5A = lowercase a-z
    ; screen code for lowercase in lc charset = $01-$1A
    ; $40 (@) -> $00
    SEC
    SBC #$40
    RTS

@ascii_lower:
    ; $60-$7F: ASCII lowercase a-z ($61-$7A)
    ; screen code for lowercase = $01-$1A
    ; $60 -> $20 (backtick, map to space)
    CMP #$61
    BCC @to_space
    CMP #$7B
    BCS @to_space
    ; $61-$7A -> $01-$1A
    SEC
    SBC #$60
    RTS

@to_space:
    LDA #SPACE
    RTS

@range_a0:
    ; $A0-$BF -> screen $60-$7F
    SEC
    SBC #$40
    RTS

@petscii_upper:
    ; $C0-$DF: PETSCII uppercase A-Z at $C1-$DA
    ; screen code for uppercase in lc charset = $41-$5A
    ; $C1-$DA -> $41-$5A
    SEC
    SBC #$80
    RTS

; =================================================================
; ROW ADDRESS LOOKUP TABLE
; =================================================================

row_addr_lo:
    .byte <(SCREEN+0*40), <(SCREEN+1*40), <(SCREEN+2*40), <(SCREEN+3*40)
    .byte <(SCREEN+4*40), <(SCREEN+5*40), <(SCREEN+6*40), <(SCREEN+7*40)
    .byte <(SCREEN+8*40), <(SCREEN+9*40), <(SCREEN+10*40), <(SCREEN+11*40)
    .byte <(SCREEN+12*40), <(SCREEN+13*40), <(SCREEN+14*40), <(SCREEN+15*40)
    .byte <(SCREEN+16*40), <(SCREEN+17*40), <(SCREEN+18*40), <(SCREEN+19*40)
    .byte <(SCREEN+20*40), <(SCREEN+21*40), <(SCREEN+22*40), <(SCREEN+23*40)
    .byte <(SCREEN+24*40)

row_addr_hi:
    .byte >(SCREEN+0*40), >(SCREEN+1*40), >(SCREEN+2*40), >(SCREEN+3*40)
    .byte >(SCREEN+4*40), >(SCREEN+5*40), >(SCREEN+6*40), >(SCREEN+7*40)
    .byte >(SCREEN+8*40), >(SCREEN+9*40), >(SCREEN+10*40), >(SCREEN+11*40)
    .byte >(SCREEN+12*40), >(SCREEN+13*40), >(SCREEN+14*40), >(SCREEN+15*40)
    .byte >(SCREEN+16*40), >(SCREEN+17*40), >(SCREEN+18*40), >(SCREEN+19*40)
    .byte >(SCREEN+20*40), >(SCREEN+21*40), >(SCREEN+22*40), >(SCREEN+23*40)
    .byte >(SCREEN+24*40)

; =================================================================
; SCREEN CODE DATA (UI frame)
; =================================================================

; Row 0 header: "FEDERATION ][        Type HELP for help!"
; Reversed characters (bit 7 set): grey bar, black text
header_sc:
    .byte $C6,$C5,$C4,$C5,$D2,$C1,$D4,$C9,$CF,$CE  ; "FEDERATION"
    .byte $A0,$9D,$9B,$A0,$A0,$A0,$A0,$A0,$A0,$A0  ; " ][      "
    .byte $A0,$D4,$99,$90,$85,$A0,$C8,$C5,$CC,$D0  ; "  Type HELP"
    .byte $A0,$86,$8F,$92,$A0,$88,$85,$8C,$90,$A1  ; " for help!"

; =================================================================
; VARIABLES (in code segment, mutable)
; =================================================================

chat_cur_row:   .byte $00       ; next available chat row (0-based, max CHAT_ROWS-1)
input_view:     .byte $00       ; first tx_buf index shown on the input row
rx_line_len:    .byte $00       ; bytes accumulated in rx_line_buf
tx_buf_len:     .byte $00       ; bytes in transmit buffer
exit_flag:      .byte $00       ; flag: exit main loop
saved_ctrl:     .byte $00       ; ACIA control register on entry

; --- History scrollback variables ---
hist_write:      .word hist_buf ; next line to write (address in ring)
hist_count:      .word $0000    ; total lines stored (saturates at HIST_LINES)
scroll_offset:   .word $0000    ; lines scrolled back from live (0 = live mode)
hist_n:          .word $0000    ; temp: line count for hist_back / scroll_back
hist_draw_row:   .byte $00      ; temp: current screen row during redraw
hist_draw_cnt:   .byte $00      ; temp: loop counter during redraw

; =================================================================
; BUFFERS
; =================================================================

TX_BUF_SIZE = 255               ; max line; tx_buf_len is one byte

rx_line_buf:    .res CHAT_WIDTH, $00   ; incoming line buffer (one line at a time)
tx_buf:         .res TX_BUF_SIZE, $00  ; outgoing message buffer

; --- History ring buffer: from here to HIST_END. Must stay last. ---
; Not in the binary: this label marks the end of the program.
hist_buf:
