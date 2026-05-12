; =================================================================
; COMPUNET REBORN — 8K Cartridge ROM for C64
; =================================================================
; Target: 6551 ACIA (SwiftLink) via tcpser + TCP server
; Assembler: ca65 (cc65 suite)
; Build: make
;
; This is a clean rewrite of the Compunet Terminal ROM v1.22,
; replacing the custom modem hardware layer with ACIA/SwiftLink
; and the IRQ-driven packet assembly with direct buffer polling.
;
; The X.25 wire protocol (framing, CRC, byte stuffing, sequencing)
; is preserved. The user experience is identical to the original.
; =================================================================

.segment "HEADER"

; --- Cartridge header ---
; Bytes $8000-$8008: entry vectors + CBM80 signature
; The C64 KERNAL checks for "CBM80" at $8004 to detect a cartridge.
; If found, it jumps to the address at $8000 (cold) or $8002 (warm).

.word   COLD_START          ; $8000: Cold start vector
.word   COLD_START          ; $8002: Warm start vector (reuse cold)
.byte   $C3, $C2, $CD       ; $8004: "CBM" (part of CBM80 signature)
.byte   $38, $30             ; $8007: "80"

.segment "CODE"

; =================================================================
; COLD_START — Initialize C64 hardware and display version
; =================================================================
COLD_START:
    JSR $FF84               ; KERNAL IOINIT
    JSR $FF87               ; KERNAL RAMTAS
    JSR $FF8A               ; KERNAL RESTOR
    JSR $FF81               ; KERNAL CINT
    CLI
    LDA #$01
    STA $0286               ; Set text colour (white)

    ; Print version string
    LDX #<version_str
    LDY #>version_str
    JSR print_string

    ; Enter BASIC (warm start)
    JSR $E453               ; BASIC INIT
    JSR $E3BF               ; BASIC main loop
    JMP ($A002)             ; Should not reach here

; =================================================================
; print_string — Print null-terminated string
; Entry: X=low byte, Y=high byte of string address
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
; Version string
; =================================================================
version_str:
    .byte $0D               ; Carriage return
    .byte " COMPUNET REBORN 1.00"
    .byte $0D
    .byte " 2026 - REBUILT FOR SWIFTLINK"
    .byte $0D, $0D, $00
