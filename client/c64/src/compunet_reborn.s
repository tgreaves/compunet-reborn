; =================================================================
; COMPUNET REBORN — 8K Cartridge ROM for C64
; =================================================================
; Target: 6551 ACIA (SwiftLink) via tcpser + TCP server
; Assembler: ca65 (cc65 suite)
; Build: make
; =================================================================

.segment "HEADER"

; --- Cartridge header ---
.word   COLD_START          ; $8000: Cold start vector
.word   COLD_START          ; $8002: Warm start vector
.byte   $C3, $C2, $CD       ; $8004: "CBM"
.byte   $38, $30             ; $8007: "80"

.segment "CODE"

; =================================================================
; COLD_START — matches original Compunet ROM sequence
; =================================================================
COLD_START:
    JSR $FF84               ; KERNAL IOINIT
    JSR $FF87               ; KERNAL RAMTAS
    JSR $FF8A               ; KERNAL RESTOR
    JSR $FF81               ; KERNAL CINT
    CLI
    LDA #$01
    STA $D021               ; Background = white (like original)
    JSR $E453               ; BASIC_RUNC (init runtime)
    JSR $E3BF               ; BASIC_MAIN (prints banner, returns)
    JSR $E422               ; BASIC_LINKPRG (link program lines)

    ; Print our version string (after BASIC banner)
    LDX #<version_str
    LDY #>version_str
    JSR print_string

    ; Enter BASIC main loop (prints READY. and accepts input)
    JMP $A474               ; BASIC warm start (READY. prompt)

; =================================================================
; print_string — Print PETSCII null-terminated string at X(lo)/Y(hi)
; =================================================================
print_string:
    STX $FB
    STY $FC
    LDY #$00
@loop:
    LDA ($FB),Y
    BEQ @done
    JSR $FFD2               ; KERNAL CHROUT
    INY
    BNE @loop
@done:
    RTS

; =================================================================
; Version strings (PETSCII uppercase)
; =================================================================
version_str:
    .byte $0D               ; CR
    .byte $20, $43, $4F, $4D, $50, $55, $4E, $45, $54  ; " COMPUNET"
    .byte $20, $54, $45, $52, $4D, $49, $4E, $41, $4C  ; " TERMINAL"
    .byte $20, $31, $2E, $32, $32                        ; " 1.22"
    .byte $0D               ; CR
    .byte $20, $52, $45, $42, $4F, $52, $4E             ; " REBORN"
    .byte $20, $31, $2E, $30, $30                        ; " 1.00"
    .byte $0D, $0D, $00     ; CR, CR, null
