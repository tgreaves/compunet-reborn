; =================================================================
; PARTYLINE CLIENT — Downloaded and executed by the C64 terminal
; =================================================================
; Draws the partyline UI, then enters main loop:
;   - Polls NMI ring buffer for incoming server messages
;   - Polls keyboard for user input
;   - Transmits on double-RETURN via ACIA
;   - Exits on RUN/STOP or *EXIT from server
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

; --- NMI Ring Buffer ---
NMI_BUF         = $CE00         ; 256-byte ring buffer
NMI_BUF_TAIL    = $029B         ; Write pointer (NMI advances)
NMI_BUF_HEAD    = $029C         ; Read pointer (we advance)

; --- Zero-page temporaries ---
ZP_PTR1         = $FB           ; general pointer low
ZP_PTR1_HI     = $FC           ; general pointer high
ZP_PTR2         = $FD           ; general pointer low
ZP_PTR2_HI     = $FE           ; general pointer high

; --- Constants ---
CR              = $0D           ; carriage return
RUNSTOP         = $03           ; RUN/STOP key code
DEL_KEY         = $14           ; DEL key code from GETIN
CURSOR_CHAR     = $1F           ; left-arrow cursor character
SPACE           = $20           ; space screen code

; --- Chat area parameters ---
CHAT_TOP_ROW    = 2             ; first content row
CHAT_BOT_ROW    = 16            ; last content row
CHAT_LEFT_COL   = 3            ; first content column
CHAT_RIGHT_COL  = 37           ; last content column (inclusive)
CHAT_WIDTH      = 35           ; columns available (3..37)
CHAT_ROWS       = 15           ; rows available (2..16)

; --- Input area parameters ---
INPUT_TOP_ROW   = 19            ; first input row (row 18 = border top)
INPUT_BOT_ROW   = 22            ; last input row
INPUT_LEFT_COL  = 4            ; first input column
INPUT_RIGHT_COL = 38           ; last input column (inclusive)
INPUT_WIDTH     = 35           ; columns available (4..38)
INPUT_ROWS      = 4            ; rows available (19..22)

; =================================================================
; ENTRY POINT
; =================================================================

start:
    ; --- Set colours: purple border, white background ---
    LDA #$04
    STA VIC_BORDER
    LDA #$01
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

    ; --- Set colour RAM: rows 0-17 = blue ($06) ---
    LDA #$06
    LDX #$00
@col_blue:
    STA COLOUR,X
    STA COLOUR+$100,X
    STA COLOUR+$200,X
    DEX
    BNE @col_blue

    ; --- Rows 18-23 (offset $02D0-$03BF) = green ($05) ---
    LDA #$05
    LDX #$00
@col_green:
    STA COLOUR+$02D0,X
    DEX
    BNE @col_green

    ; --- Row 0: header (reversed, purple) ---
    LDX #$00
@hdr:
    LDA header_sc,X
    STA SCREEN,X
    LDA #$04                    ; purple
    STA COLOUR,X
    INX
    CPX #$28
    BNE @hdr

    ; --- Row 1: chat box top border ---
    LDX #$00
@top:
    LDA chat_top,X
    STA SCREEN+40,X
    INX
    CPX #$28
    BNE @top

    ; --- Rows 2-16: chat box sides (col 2 and col 38 = pipe) ---
    LDA #<(SCREEN+80)
    STA ZP_PTR1
    LDA #>(SCREEN+80)
    STA ZP_PTR1_HI
    LDX #CHAT_ROWS             ; 15 rows
@sides:
    LDY #$02
    LDA #$5D                    ; pipe character
    STA (ZP_PTR1),Y
    LDY #$26                    ; col 38
    STA (ZP_PTR1),Y
    LDY #$27                    ; col 39
    STA (ZP_PTR1),Y
    ; Advance pointer by 40
    CLC
    LDA ZP_PTR1
    ADC #$28
    STA ZP_PTR1
    BCC @no_inc1
    INC ZP_PTR1_HI
@no_inc1:
    DEX
    BNE @sides

    ; --- Row 17: chat box bottom border ---
    LDX #$00
@bot:
    LDA chat_bot,X
    STA SCREEN+$02A8,X         ; row 17 = offset $2A8
    INX
    CPX #$28
    BNE @bot

    ; --- Rows 18-22: input box sides (col 3 and col 39 = pipe) ---
    LDA #<(SCREEN+$02D0)
    STA ZP_PTR1
    LDA #>(SCREEN+$02D0)
    STA ZP_PTR1_HI
    LDX #$05                    ; 5 rows (18-22)
@isides:
    LDY #$03
    LDA #$5D                    ; pipe
    STA (ZP_PTR1),Y
    LDY #$27                    ; col 39
    STA (ZP_PTR1),Y
    CLC
    LDA ZP_PTR1
    ADC #$28
    STA ZP_PTR1
    BCC @no_inc2
    INC ZP_PTR1_HI
@no_inc2:
    DEX
    BNE @isides

    ; --- Row 23: input box bottom border ---
    LDX #$00
@ibot:
    LDA input_bot,X
    STA SCREEN+$0398,X         ; row 23 = offset $398
    INX
    CPX #$28
    BNE @ibot

    ; --- Green corner on row 2 col 39 ---
    LDA #$6E                    ; upper-right corner
    STA SCREEN+80+39
    LDA #$05                    ; green
    STA COLOUR+80+39

    ; --- Green colour for col 39 rows 3-17 ---
    LDA #<(COLOUR+120+39)
    STA ZP_PTR1
    LDA #>(COLOUR+120+39)
    STA ZP_PTR1_HI
    LDX #$0F                    ; 15 rows
@grn_right:
    LDY #$00
    LDA #$05
    STA (ZP_PTR1),Y
    CLC
    LDA ZP_PTR1
    ADC #$28
    STA ZP_PTR1
    BCC @no_inc3
    INC ZP_PTR1_HI
@no_inc3:
    DEX
    BNE @grn_right

    ; --- Green colour for input box rows (18-23) ---
    LDX #$00
@gcol:
    LDA #$05
    STA COLOUR+$02D0,X
    STA COLOUR+$0398,X
    INX
    CPX #$28
    BNE @gcol

    ; --- Initialize variables ---
    LDA #$00
    STA chat_cur_row            ; next chat row (0-based within chat area)
    STA input_col               ; cursor col within input area (0-based)
    STA input_row               ; cursor row within input area (0-based)
    STA rx_line_len             ; receive line buffer length
    STA tx_buf_len              ; transmit buffer length
    STA last_was_return         ; flag: last key was RETURN
    STA exit_flag               ; flag: time to exit

    ; --- Place cursor in input area ---
    JSR draw_input_cursor

; =================================================================
; MAIN LOOP
; =================================================================

main_loop:
    ; --- Check exit flag ---
    LDA exit_flag
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
    CPX #INPUT_WIDTH            ; don't overflow line buffer
    BCS @rx_done                ; discard if too long
    STA rx_line_buf,X
    INC rx_line_len
@rx_done:
    RTS

@rx_line_complete:
    ; Check for *EXIT sentinel
    LDA rx_line_len
    CMP #$05                    ; "*EXIT" = 5 chars
    BNE @not_exit
    LDA rx_line_buf
    CMP #$2A                    ; '*'
    BNE @not_exit
    LDA rx_line_buf+1
    CMP #$45                    ; 'E'
    BNE @not_exit
    LDA rx_line_buf+2
    CMP #$58                    ; 'X'
    BNE @not_exit
    LDA rx_line_buf+3
    CMP #$49                    ; 'I'
    BNE @not_exit
    LDA rx_line_buf+4
    CMP #$54                    ; 'T'
    BNE @not_exit

    ; Got *EXIT — set exit flag
    LDA #$01
    STA exit_flag
    LDA #$00
    STA rx_line_len
    RTS

@not_exit:
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
    ; If chat area is full, scroll up first
    LDA chat_cur_row
    CMP #CHAT_ROWS
    BCC @no_scroll
    JSR scroll_chat
    DEC chat_cur_row            ; stay on last row after scroll
@no_scroll:
    ; Calculate screen address for current chat row
    ; Row = CHAT_TOP_ROW + chat_cur_row, Col = CHAT_LEFT_COL
    LDA chat_cur_row
    CLC
    ADC #CHAT_TOP_ROW           ; absolute screen row
    JSR calc_row_addr           ; result in ZP_PTR1
    ; Add left column offset
    CLC
    LDA ZP_PTR1
    ADC #CHAT_LEFT_COL
    STA ZP_PTR1
    BCC @no_c1
    INC ZP_PTR1_HI
@no_c1:
    ; Copy rx_line_buf to screen (converting PETSCII to screen codes)
    LDX #$00
    LDY #$00
@copy_char:
    CPX rx_line_len
    BCS @pad_rest
    LDA rx_line_buf,X
    JSR petscii_to_screencode
    STA (ZP_PTR1),Y
    INX
    INY
    CPY #CHAT_WIDTH
    BCC @copy_char
    BCS @done_display           ; line full
@pad_rest:
    ; Clear remaining columns with spaces
    LDA #SPACE
    CPY #CHAT_WIDTH
    BCS @done_display
@pad_loop:
    STA (ZP_PTR1),Y
    INY
    CPY #CHAT_WIDTH
    BCC @pad_loop
@done_display:
    INC chat_cur_row
    RTS

; =================================================================
; SCROLL_CHAT — Scroll chat area up by one row
; =================================================================

scroll_chat:
    ; Copy rows 3..16 up to rows 2..15 (in screen RAM)
    ; Source: row (CHAT_TOP_ROW+1), Dest: row CHAT_TOP_ROW
    ; We copy (CHAT_ROWS-1) rows

    ; Set dest = row 2, col 3
    LDA #<(SCREEN + 2*40 + CHAT_LEFT_COL)
    STA ZP_PTR1
    LDA #>(SCREEN + 2*40 + CHAT_LEFT_COL)
    STA ZP_PTR1_HI

    ; Set source = row 3, col 3
    LDA #<(SCREEN + 3*40 + CHAT_LEFT_COL)
    STA ZP_PTR2
    LDA #>(SCREEN + 3*40 + CHAT_LEFT_COL)
    STA ZP_PTR2_HI

    LDX #(CHAT_ROWS - 1)       ; 14 rows to copy
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

    ; --- RUN/STOP ---
    CMP #RUNSTOP
    BEQ @do_runstop

    ; --- DEL key ---
    CMP #DEL_KEY
    BEQ @do_del

    ; --- RETURN ---
    CMP #CR
    BEQ @do_return

    ; --- Printable character ---
    ; Clear last_was_return flag since we got a regular char
    PHA
    LDA #$00
    STA last_was_return
    PLA

    ; Store in transmit buffer
    LDX tx_buf_len
    CPX #TX_BUF_SIZE
    BCS @no_key                 ; buffer full, ignore
    STA tx_buf,X
    INC tx_buf_len

    ; Display character in input area
    PHA
    JSR erase_input_cursor
    PLA
    JSR petscii_to_screencode
    JSR put_input_char

    ; Draw cursor at new position
    JSR draw_input_cursor

@no_key:
    RTS

@do_runstop:
    ; Send *quit + CR
    JSR send_quit
    ; Wait for *EXIT (with timeout)
    JSR wait_for_exit
    ; Set exit flag
    LDA #$01
    STA exit_flag
    RTS

@do_del:
    ; Clear last_was_return
    LDA #$00
    STA last_was_return
    ; Check if anything to delete
    LDA tx_buf_len
    BEQ @no_key                 ; nothing to delete
    ; Decrease buffer length
    DEC tx_buf_len
    ; Move cursor back
    JSR erase_input_cursor
    JSR cursor_back
    JSR draw_input_cursor
    RTS

@do_return:
    ; Check if this is a second consecutive RETURN (or RETURN on empty after text)
    LDA last_was_return
    BNE @transmit               ; second RETURN — send!

    ; First RETURN
    LDA tx_buf_len
    BEQ @no_key                 ; empty line, ignore first RETURN

    ; Mark that RETURN was pressed
    LDA #$01
    STA last_was_return

    ; Move to next input row
    JSR erase_input_cursor
    JSR input_next_row
    JSR draw_input_cursor
    RTS

@transmit:
    ; Transmit the buffer contents + CR
    JSR transmit_buffer
    ; Clear input area and reset
    JSR clear_input_area
    LDA #$00
    STA last_was_return
    STA input_col
    STA input_row
    STA tx_buf_len
    JSR draw_input_cursor
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
; SEND_QUIT — Send "*quit\r" via ACIA
; =================================================================

send_quit:
    LDX #$00
@sq_loop:
    LDA quit_str,X
    BEQ @sq_done
    JSR acia_send_byte
    INX
    BNE @sq_loop
@sq_done:
    LDA #CR
    JSR acia_send_byte
    RTS

quit_str:
    .byte "*quit", $00

; =================================================================
; WAIT_FOR_EXIT — Wait for *EXIT from server (with timeout)
; =================================================================

wait_for_exit:
    ; Simple timeout: loop a counter
    LDA #$00
    STA wait_cnt
    STA wait_cnt+1
@wfe_loop:
    ; Check ring buffer
    LDA NMI_BUF_HEAD
    CMP NMI_BUF_TAIL
    BEQ @wfe_no_data

    ; Read byte
    TAX
    LDA NMI_BUF,X
    INC NMI_BUF_HEAD

    ; Check for CR
    CMP #CR
    BNE @wfe_accum

    ; Got a line — check if it's *EXIT
    LDA rx_line_len
    CMP #$05
    BNE @wfe_reset
    LDA rx_line_buf
    CMP #$2A                    ; '*'
    BNE @wfe_reset
    LDA rx_line_buf+1
    CMP #$45                    ; 'E'
    BNE @wfe_reset
    LDA rx_line_buf+2
    CMP #$58                    ; 'X'
    BNE @wfe_reset
    LDA rx_line_buf+3
    CMP #$49                    ; 'I'
    BNE @wfe_reset
    LDA rx_line_buf+4
    CMP #$54                    ; 'T'
    BNE @wfe_reset
    ; Got it — done
    LDA #$00
    STA rx_line_len
    RTS

@wfe_reset:
    LDA #$00
    STA rx_line_len
    JMP @wfe_loop

@wfe_accum:
    LDX rx_line_len
    CPX #INPUT_WIDTH
    BCS @wfe_loop               ; discard overflow
    STA rx_line_buf,X
    INC rx_line_len
    JMP @wfe_loop

@wfe_no_data:
    ; Increment timeout counter
    INC wait_cnt
    BNE @wfe_loop
    INC wait_cnt+1
    LDA wait_cnt+1
    CMP #$40                    ; ~16384 outer iterations timeout
    BCC @wfe_loop
    ; Timeout — exit anyway
    LDA #$00
    STA rx_line_len
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
; PUT_INPUT_CHAR — Write screen code in A at current input position
; =================================================================

put_input_char:
    ; Calculate screen address for input position
    PHA
    LDA input_row
    CLC
    ADC #INPUT_TOP_ROW          ; absolute row
    JSR calc_row_addr           ; ZP_PTR1 = row start
    CLC
    LDA ZP_PTR1
    ADC #INPUT_LEFT_COL
    STA ZP_PTR1
    BCC @pi1
    INC ZP_PTR1_HI
@pi1:
    ; Add column offset
    LDY input_col
    PLA
    STA (ZP_PTR1),Y

    ; Advance cursor position
    INC input_col
    LDA input_col
    CMP #INPUT_WIDTH
    BCC @pi_done
    ; Wrap to next row
    JSR input_next_row
@pi_done:
    RTS

; =================================================================
; INPUT_NEXT_ROW — Move input cursor to start of next row
; =================================================================

input_next_row:
    LDA #$00
    STA input_col
    INC input_row
    LDA input_row
    CMP #INPUT_ROWS
    BCC @inr_ok
    ; Wrapped past bottom — stay on last row (discard)
    DEC input_row
@inr_ok:
    RTS

; =================================================================
; CURSOR_BACK — Move input cursor one position back
; =================================================================

cursor_back:
    LDA input_col
    BNE @just_dec
    ; At column 0 — go to end of previous row
    LDA input_row
    BEQ @cb_done                ; already at top-left, can't go back
    DEC input_row
    LDA #(INPUT_WIDTH - 1)
    STA input_col
    RTS
@just_dec:
    DEC input_col
    ; Clear the character at the new cursor position
    LDA input_row
    CLC
    ADC #INPUT_TOP_ROW
    JSR calc_row_addr
    CLC
    LDA ZP_PTR1
    ADC #INPUT_LEFT_COL
    STA ZP_PTR1
    BCC @cb2
    INC ZP_PTR1_HI
@cb2:
    LDY input_col
    LDA #SPACE
    STA (ZP_PTR1),Y
@cb_done:
    RTS

; =================================================================
; DRAW_INPUT_CURSOR — Draw cursor character at current input pos
; =================================================================

draw_input_cursor:
    LDA input_row
    CLC
    ADC #INPUT_TOP_ROW
    JSR calc_row_addr
    CLC
    LDA ZP_PTR1
    ADC #INPUT_LEFT_COL
    STA ZP_PTR1
    BCC @dc1
    INC ZP_PTR1_HI
@dc1:
    LDY input_col
    LDA #CURSOR_CHAR
    STA (ZP_PTR1),Y
    RTS

; =================================================================
; ERASE_INPUT_CURSOR — Remove cursor character at current input pos
; =================================================================

erase_input_cursor:
    LDA input_row
    CLC
    ADC #INPUT_TOP_ROW
    JSR calc_row_addr
    CLC
    LDA ZP_PTR1
    ADC #INPUT_LEFT_COL
    STA ZP_PTR1
    BCC @ec1
    INC ZP_PTR1_HI
@ec1:
    LDY input_col
    LDA #SPACE
    STA (ZP_PTR1),Y
    RTS

; =================================================================
; CLEAR_INPUT_AREA — Clear rows 19-22 cols 4-38 with spaces
; =================================================================

clear_input_area:
    LDA #INPUT_TOP_ROW
    JSR calc_row_addr
    CLC
    LDA ZP_PTR1
    ADC #INPUT_LEFT_COL
    STA ZP_PTR1
    BCC @ci1
    INC ZP_PTR1_HI
@ci1:
    LDX #INPUT_ROWS             ; 4 rows
@ci_row:
    LDY #$00
    LDA #SPACE
@ci_col:
    STA (ZP_PTR1),Y
    INY
    CPY #INPUT_WIDTH
    BCC @ci_col
    ; Next row: advance pointer by 40
    CLC
    LDA ZP_PTR1
    ADC #$28
    STA ZP_PTR1
    BCC @ci2
    INC ZP_PTR1_HI
@ci2:
    DEX
    BNE @ci_row
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

; Row 0 header: "Partyline.          Type *help for help!"
; Reversed characters (bit 7 set) for purple-background appearance
header_sc:
    .byte $D0,$81,$92,$94,$99,$8C,$89,$8E,$85,$AE  ; "Partyline."
    .byte $A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0  ; spaces
    .byte $D4,$99,$90,$85,$A0,$AA,$88,$85,$8C,$90  ; "Type *help"
    .byte $A0,$86,$8F,$92,$A0,$88,$85,$8C,$90,$A1  ; " for help!"

; Row 1: chat top border
chat_top:
    .byte $20,$20,$70,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$6E,$20

; Row 17: chat bottom border
chat_bot:
    .byte $20,$20,$6D,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$7D,$5D

; Row 23: input bottom border
input_bot:
    .byte $20,$20,$20,$6D,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$7D

; =================================================================
; VARIABLES (in code segment, mutable)
; =================================================================

chat_cur_row:   .byte $00       ; next available chat row (0-based, max CHAT_ROWS-1)
input_col:      .byte $00       ; cursor column in input area (0-based)
input_row:      .byte $00       ; cursor row in input area (0-based)
rx_line_len:    .byte $00       ; bytes accumulated in rx_line_buf
tx_buf_len:     .byte $00       ; bytes in transmit buffer
last_was_return: .byte $00      ; flag: last key was RETURN
exit_flag:      .byte $00       ; flag: exit main loop
wait_cnt:       .word $0000     ; timeout counter for wait_for_exit

; =================================================================
; BUFFERS
; =================================================================

TX_BUF_SIZE = 140               ; 4 rows * 35 cols = 140 max

rx_line_buf:    .res 40, $00    ; incoming line buffer (one line at a time)
tx_buf:         .res TX_BUF_SIZE, $00  ; outgoing message buffer
