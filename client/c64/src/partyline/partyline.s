; =================================================================
; PARTYLINE CLIENT — Downloaded and executed by the C64 terminal
; =================================================================
; Draws the partyline UI by writing directly to screen RAM ($0400)
; and colour RAM ($D800), matching the original Compunet layout.
; RTS returns to the terminal.
; =================================================================

.segment "CODE"

GETIN           = $FFE4
VIC_BORDER      = $D020
VIC_BGCOL0      = $D021
SCREEN          = $0400
COLOUR          = $D800

start:
    ; Set colours: purple border, white background
    LDA #$04
    STA VIC_BORDER
    LDA #$01
    STA VIC_BGCOL0

    ; Switch to lowercase/uppercase character set
    LDA #$17
    STA $D018

    ; Clear screen RAM with spaces
    LDA #$20
    LDX #$00
@clr:
    STA SCREEN,X
    STA SCREEN+$100,X
    STA SCREEN+$200,X
    STA SCREEN+$300,X
    DEX
    BNE @clr

    ; Set colour RAM: row 0 = blue ($06), rows 1-17 = blue, rows 18-23 = green ($05)
    LDA #$06
    LDX #$00
@col_blue:
    STA COLOUR,X
    STA COLOUR+$100,X
    STA COLOUR+$200,X
    DEX
    BNE @col_blue
    ; Rows 18-23 (offset $02D0-$03BF) = green
    LDA #$05
    LDX #$00
@col_green:
    STA COLOUR+$02D0,X
    DEX
    BNE @col_green

    ; Row 0: header "Partyline.          Type *help for help!"
    ; Uses reversed chars (bit 7 set) with purple colour = purple background
    LDX #$00
@hdr:
    LDA header_sc,X
    STA SCREEN,X
    LDA #$04                ; purple (reversed = purple bg, white text)
    STA COLOUR,X
    INX
    CPX #$28
    BNE @hdr

    ; Row 1: chat box top border (cols 2-38)
    LDX #$00
@top:
    LDA chat_top,X
    STA SCREEN+40,X
    INX
    CPX #$28
    BNE @top

    ; Rows 2-16: chat box sides (col 2 = │, col 38 = │, col 39 = │)
    LDA #<(SCREEN+80)
    STA $FB
    LDA #>(SCREEN+80)
    STA $FC
    LDY #$00
    LDX #$0F                ; 15 rows
@sides:
    LDA #$5D                ; │
    LDY #$02
    STA ($FB),Y
    LDY #$26                ; col 38
    STA ($FB),Y
    LDY #$27                ; col 39
    STA ($FB),Y
    ; Advance pointer by 40
    CLC
    LDA $FB
    ADC #$28
    STA $FB
    BCC @no_inc1
    INC $FC
@no_inc1:
    DEX
    BNE @sides

    ; Row 17: chat box bottom border
    LDX #$00
@bot:
    LDA chat_bot,X
    STA SCREEN+$02A8,X      ; row 17 = offset $2A8
    INX
    CPX #$28
    BNE @bot

    ; Rows 18-22: input box sides (col 3 = │, col 39 = │)
    LDA #<(SCREEN+$02D0)
    STA $FB
    LDA #>(SCREEN+$02D0)
    STA $FC
    LDX #$05                ; 5 rows
@isides:
    LDY #$03
    LDA #$5D                ; │
    STA ($FB),Y
    LDY #$27                ; col 39
    STA ($FB),Y
    CLC
    LDA $FB
    ADC #$28
    STA $FB
    BCC @no_inc2
    INC $FC
@no_inc2:
    DEX
    BNE @isides

    ; Row 23: input box bottom border
    LDX #$00
@ibot:
    LDA input_bot,X
    STA SCREEN+$0398,X      ; row 23 = offset $398
    INX
    CPX #$28
    BNE @ibot

    ; Green corner on row 2 col 39
    LDA #$6E                ; ╮ upper-right corner
    STA SCREEN+80+39
    LDA #$05                ; green
    STA COLOUR+80+39

    ; Green colour for col 39 rows 3-17 (right side of green border)
    LDA #<(COLOUR+120+39)
    STA $FB
    LDA #>(COLOUR+120+39)
    STA $FC
    LDX #$0F                ; 15 rows
@grn_right:
    LDY #$00
    LDA #$05
    STA ($FB),Y
    CLC
    LDA $FB
    ADC #$28
    STA $FB
    BCC @no_inc3
    INC $FC
@no_inc3:
    DEX
    BNE @grn_right

    ; Green colour for input box rows (18-23)
    LDX #$00
@gcol:
    LDA #$05
    STA COLOUR+$02D0,X
    STA COLOUR+$0398,X
    INX
    CPX #$28
    BNE @gcol

    ; Cursor in input area (row 18, col 4)
    LDA #$1F                ; underscore cursor
    STA SCREEN+$02D0+4

    ; Welcome message in chat area (row 2, col 3 = right after left border)
    LDX #$00
@welcome:
    LDA welcome_sc,X
    BEQ @welcome_done
    STA SCREEN+83,X         ; row 2, col 3
    INX
    BNE @welcome
@welcome_done:

    ; "Press RUN/STOP to exit" (row 3, col 3)
    LDX #$00
@exit_msg:
    LDA exit_sc,X
    BEQ @exit_done
    STA SCREEN+123,X        ; row 3, col 3
    INX
    BNE @exit_msg
@exit_done:

    ; Wait for RUN/STOP ($03)
@wait:
    JSR GETIN
    CMP #$03
    BNE @wait

    ; Restore colours, charset, and return
    LDA #$0E
    STA VIC_BORDER
    LDA #$06
    STA VIC_BGCOL0
    LDA #$15
    STA $D018                ; restore uppercase charset
    RTS

; =================================================================
; Screen code data
; =================================================================

; Row 0 header: "Partyline.          Type *help for help!"
; In C64 lowercase mode screen codes: uppercase = $01-$1A, lowercase = $41-$5A? No.
; Actually in standard C64 lowercase charset:
; Screen code $01-$1A = uppercase A-Z
; Screen code $41-$5A = lowercase a-z... NO that's not right either.
;
; C64 lowercase mode screen codes:
; $00 = @, $01 = A, $02 = B ... $1A = Z (uppercase)
; Let me just use the EXACT bytes from the monitor dump:
header_sc:
    .byte $D0,$81,$92,$94,$99,$8C,$89,$8E,$85,$AE  ; "Partyline."
    .byte $A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0,$A0  ; spaces
    .byte $D4,$99,$90,$85,$A0,$AA,$88,$85,$8C,$90  ; "Type *help"
    .byte $A0,$86,$8F,$92,$A0,$88,$85,$8C,$90,$A1  ; " for help!"

; Row 1: "  ╰──────────────────────────────────╮ "
chat_top:
    .byte $20,$20,$70,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$6E,$20

; Row 17: "  ╯──────────────────────────────────╯│"
chat_bot:
    .byte $20,$20,$6D,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$7D,$5D

; Row 23: "   ╯───────────────────────────────────╯"
input_bot:
    .byte $20,$20,$20,$6D,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$40
    .byte $40,$40,$40,$40,$40,$40,$40,$40,$40,$7D

; Screen codes in C64 lowercase mode:
; Uppercase A-Z = $41-$5A, Lowercase a-z = $01-$1A
;
; "Hello Compunet Corner!"
welcome_sc:
    .byte $48,$05,$0C,$0C,$0F           ; "Hello"
    .byte $20                           ; " "
    .byte $43,$0F,$0D,$10,$15,$0E,$05,$14  ; "Compunet"
    .byte $20                           ; " "
    .byte $43,$0F,$12,$0E,$05,$12,$21   ; "Corner!"
    .byte $00

; "Partyline coming soon..."
exit_sc:
    .byte $50,$01,$12,$14,$19,$0C,$09,$0E,$05  ; "Partyline"
    .byte $20                            ; " "
    .byte $03,$0F,$0D,$09,$0E,$07       ; "coming"
    .byte $20                            ; " "
    .byte $13,$0F,$0F,$0E,$2E,$2E,$2E   ; "soon..."
    .byte $00
