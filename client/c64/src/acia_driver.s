; =================================================================
; ACIA DRIVER — SwiftLink/6551 hardware layer
; =================================================================
; Located after terminal code (at $BE03+)
; Called from ROM via JMP trampolines at MODEM_REG_WRITE/MODEM_REG_READ
;
; This replaces the original Compunet brick modem hardware layer.
; The X.25 protocol engine in ROM is unchanged — it still calls
; MODEM_REG_WRITE (X=reg, A=value) and MODEM_REG_READ (X=reg, A=result).
; We translate those register-select calls to ACIA operations.
; =================================================================

.segment "ACIA"

; --- Hardware Registers ---
ACIA_DATA       = $DE00
ACIA_STATUS     = $DE01
ACIA_CMD        = $DE02
ACIA_CTRL       = $DE03

; --- NMI Ring Buffer ---
NMI_BUF         = $CE00   ; 256-byte ring buffer
NMI_BUF_TAIL    = $029B   ; Write pointer (NMI handler advances)
NMI_BUF_HEAD    = $029C   ; Read pointer (main code advances)

; --- System Vectors ---
NMI_VECTOR_LO   = $0318
NMI_VECTOR_HI   = $0319

; =================================================================
; ACIA_INIT — Initialize ACIA and install NMI handler
; Called from MODEM_CHECK trampoline
; =================================================================
ACIA_INIT:
    ; Reset ACIA
    LDA #$00
    STA ACIA_CMD
    ; Configure: 19200 baud, 8N1, 1 stop bit
    LDA #$1F
    STA ACIA_CTRL
    ; Enable DTR + RX interrupt (NMI)
    LDA #$09
    STA ACIA_CMD
    ; Clear ring buffer
    LDA #$00
    STA NMI_BUF_TAIL
    STA NMI_BUF_HEAD
    ; Install NMI handler
    SEI
    LDA #<NMI_HANDLER
    STA NMI_VECTOR_LO
    LDA #>NMI_HANDLER
    STA NMI_VECTOR_HI
    CLI
    RTS

; =================================================================
; NMI_HANDLER — Receive interrupt handler
; Fires when ACIA receives a byte. Stores in ring buffer.
; Disables/re-enables RX IRQ around read (prevents re-entrancy).
; =================================================================
NMI_HANDLER:
    PHA
    TXA
    PHA
    LDA ACIA_STATUS                     ; Read status (acknowledges NMI)
    LDA ACIA_CMD
    ORA #$02                            ; Disable RX IRQ (bit 1)
    STA ACIA_CMD
    LDA ACIA_DATA                       ; Read received byte
    LDX NMI_BUF_TAIL
    STA NMI_BUF,X                      ; Store in ring buffer
    INC NMI_BUF_TAIL                   ; Advance tail
    LDA ACIA_CMD
    AND #$FD                            ; Re-enable RX IRQ (clear bit 1)
    STA ACIA_CMD
    PLA
    TAX
    PLA
    RTI

; =================================================================
; ACIA_REG_WRITE — Replacement for MODEM_REG_WRITE
; Input: X = register number, A = value to write
; X=4: Transmit byte via ACIA
; Other X: ignored (mode control not needed for ACIA)
; =================================================================
ACIA_REG_WRITE:
    CPX #$04
    BNE @skip
    ; Transmit byte with delay
    STA ACIA_DATA
    LDY #$FF
@txdly:
    DEY
    BNE @txdly
@skip:
    RTS

; =================================================================
; ACIA_REG_READ — Replacement for MODEM_REG_READ
; Input: X = register number
; Output: A = value read
; X=0: Return status (bit 7=TX rdy, bit 6=RX avail, bit 5=carrier)
; X=4: Return next byte from NMI ring buffer (non-blocking)
; X=8: Return $40 (carrier detect, bit 6 set)
; =================================================================
ACIA_REG_READ:
    CPX #$04
    BEQ @rxbyte
    CPX #$00
    BEQ @status
    ; X=8 or other: return carrier detect
    LDA #$40
    RTS

@status:
    ; Poke ACIA to trigger VICE socket poll, then check buffer
    LDA ACIA_STATUS
    LDA NMI_BUF_HEAD
    CMP NMI_BUF_TAIL
    BEQ @no_rx
    LDA #$E0                            ; Data available (bits 7+6+5)
    LDX #$00
    RTS
@no_rx:
    LDA #$A0                            ; Empty (bits 7+5 only)
    LDX #$00
    RTS

@rxbyte:
    ; Non-blocking read from NMI ring buffer
    LDX NMI_BUF_HEAD
    CPX NMI_BUF_TAIL
    BEQ @empty
    LDA NMI_BUF,X
    INC NMI_BUF_HEAD
    LDX #$04
    RTS
@empty:
    LDA #$00
    LDX #$04
    RTS

; =================================================================
; ACIA_WAIT_READY — Replacement for MODEM_WAIT_READY
; Input: A = byte to transmit
; Transmits with delay (same interface as original)
; =================================================================
ACIA_WAIT_READY:
    STA ACIA_DATA
    LDY #$FF
@wdly:
    DEY
    BNE @wdly
    RTS

; =================================================================
; ACIA_DIAL — Hayes AT dial sequence
; Sends "ATDT" + phone number from $9FF1 (length in $9FF0) + CR
; Waits for "CONNECT" response (CR-terminated)
; Returns: C=0 success, C=1 failure
; =================================================================
ACIA_DIAL:
    ; Send "ATDT"
    LDA #'A'
    JSR ACIA_WAIT_READY
    LDA #'T'
    JSR ACIA_WAIT_READY
    LDA #'D'
    JSR ACIA_WAIT_READY
    LDA #'T'
    JSR ACIA_WAIT_READY
    ; Send phone number digits
    LDY #$00
@send_digit:
    CPY $9FF0
    BEQ @send_cr
    LDA $9FF1,Y
    CMP #$2D                            ; '-' = pause
    BNE @not_pause
    LDA #','                            ; Hayes pause
@not_pause:
    JSR ACIA_WAIT_READY
    INY
    BNE @send_digit
@send_cr:
    LDA #$0D
    JSR ACIA_WAIT_READY
    ; Re-arm NMI edge detection after TX burst
    LDA #$01
    STA ACIA_CMD                        ; Disable RX IRQ
    LDA #$09
    STA ACIA_CMD                        ; Re-enable (re-arms NMI edge)
    ; Wait for "CONNECT" response — poll for CR
@wait_resp:
    LDA ACIA_STATUS                     ; Poke VICE to check socket
    LDA NMI_BUF_HEAD
    CMP NMI_BUF_TAIL
    BEQ @wait_resp
    TAX
    LDA NMI_BUF,X
    INC NMI_BUF_HEAD
    CMP #$0D                            ; CR = end of response
    BNE @wait_resp
    ; Flush remaining buffer
    LDA NMI_BUF_TAIL
    STA NMI_BUF_HEAD
    CLC                                 ; C=0 = success
    RTS

; =================================================================
; End of ACIA driver
; =================================================================
