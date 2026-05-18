; =================================================================
; COMPUNET TERMINAL SOFTWARE (cnet.prg) - DISASSEMBLY
; =================================================================
; Runtime address: $9FF0-$BE02
; Size: 7699 bytes (7.5 KB)
; This is the code downloaded during "linking" phase.
; It provides: directory navigation, duckshoot, SHOW, BUY,
;   MAIL (Courier), UPLOAD, VOTE, account management, etc.
;
; Calls ROM routines via jump table at $8100-$815F
; Calls protocol layer at $96C0-$96D8
; Uses workspace at $C000-$C0FF
; =================================================================

    * = $9FF0

    .byte 18 08 35 32 39 38 39 38...  ; $9FF0 "..529898888888881E .."
    A9 00         LDA #$00
    8D 00 C0      STA $C000
    8D 04 C0      STA $C004
    8D 27 C0      STA $C027
    8D 29 C0      STA $C029
    8D 4C C0      STA $C04C
    A6 2B         LDX $2B
    A4 2C         LDY $2C
    8E 0D C0      STX $C00D
    8C 0E C0      STY $C00E
    A2 86         LDX #$86
    A0 AC         LDY #$AC
    8E FE 80      STX $80FE
    8C FF 80      STY $80FF
    A2 76         LDX #$76
    A0 A1         LDY #$A1
    20 15 81      JSR $8115 ; JT_PROTOCOL_RESET
    A9 0B         LDA #$0B
    8D 1E A2      STA $A21E
    A9 01         LDA #$01
    8D 33 80      STA $8033

SUB_A03B:
    A2 1E         LDX #$1E
    A0 A2         LDY #$A2
    8E 1F C0      STX $C01F
    8C 20 C0      STY $C020
    20 66 A0      JSR $A066 ; SUB_A066
    BC 1E A2      LDY $A21E,X
    A2 00         LDX #$00
    B9 76 A1      LDA $A176,Y
    29 3F         AND #$3F
    09 80         ORA #$80
    9D C0 07      STA $07C0,X
    C8            INY 
    E8            INX 
    E0 06         CPX #$06
    D0 F0         BNE $A04D
    20 31 A2      JSR $A231 ; SUB_A231
    20 91 A7      JSR $A791 ; SUB_A791
    4C 3B A0      JMP $A03B ; SUB_A03B

SUB_A066:
    A9 08         LDA #$08
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    AE 1F C0      LDX $C01F
    AC 20 C0      LDY $C020
    20 18 81      JSR $8118 ; JT_DUCKSHOOT
    B0 14         BCS $A08A
    2C 00 C0      BIT $C000
    10 08         BPL $A083

SUB_A07B:
    A5 D6         LDA $D6
    38            SEC 
    E9 0A         SBC #$0A
    8D 04 C0      STA $C004
    20 51 81      JSR $8151 ; JT_WHITE_BAR
    AE 33 80      LDX $8033
    60            RTS 
    2C 00 C0      BIT $C000
    10 D7         BPL $A066
    C9 13         CMP #$13
    D0 04         BNE $A097
    A2 00         LDX #$00
    F0 19         BEQ $A0B0
    C9 11         CMP #$11
    D0 0B         BNE $A0A6
    AE 04 C0      LDX $C004
    E8            INX 
    EC 03 C0      CPX $C003
    F0 C2         BEQ $A066
    D0 0A         BNE $A0B0
    C9 91         CMP #$91
    D0 1F         BNE $A0C9
    AE 04 C0      LDX $C004
    F0 B7         BEQ $A066
    CA            DEX 
    8A            TXA 
    48            PHA 
    20 F8 A6      JSR $A6F8 ; SUB_A6F8
    68            PLA 
    8D 04 C0      STA $C004
    18            CLC 
    69 0A         ADC #$0A
    AA            TAX 
    A0 00         LDY #$00
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    20 D9 A6      JSR $A6D9 ; SUB_A6D9
    4C 66 A0      JMP $A066 ; SUB_A066
    C9 88         CMP #$88
    D0 06         BNE $A0D3
    20 03 A1      JSR $A103 ; SUB_A103
    4C 66 A0      JMP $A066 ; SUB_A066
    C9 8C         CMP #$8C
    D0 06         BNE $A0DD
    20 10 A1      JSR $A110 ; SUB_A110
    4C 66 A0      JMP $A066 ; SUB_A066
    B0 FB         BCS $A0DA
    E9 84         SBC #$84
    90 F7         BCC $A0DA
    0A            ASL A
    0A            ASL A
    0A            ASL A
    69 80         ADC #$80
    85 1D         STA $1D
    A9 D5         LDA #$D5
    85 1E         STA $1E
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    C9 00         CMP #$00
    F0 E5         BEQ $A0DA
    AE 33 80      LDX $8033
    8E 07 C0      STX $C007
    A2 12         LDX #$12
    8E 33 80      STX $8033
    4C 7B A0      JMP $A07B ; SUB_A07B

SUB_A103:
    AE 02 C0      LDX $C002
    EC 01 C0      CPX $C001
    D0 02         BNE $A10D
    A2 00         LDX #$00
    E8            INX 
    D0 09         BNE $A119

SUB_A110:
    AE 02 C0      LDX $C002
    CA            DEX 
    D0 03         BNE $A119
    AE 01 C0      LDX $C001
    8E 02 C0      STX $C002

SUB_A11C:
    20 9B A7      JSR $A79B ; SUB_A79B
    20 6E A5      JSR $A56E ; SUB_A56E
    AE 02 C0      LDX $C002
    CA            DEX 
    8A            TXA 
    0A            ASL A
    0A            ASL A
    0A            ASL A
    18            CLC 
    69 1E         ADC #$1E
    85 1D         STA $1D
    A9 D6         LDA #$D6
    85 1E         STA $1E
    A2 00         LDX #$00
    8E 09 C0      STX $C009
    A9 02         LDA #$02
    8D 86 02      STA $0286
    18            CLC 
    AD 09 C0      LDA $C009
    69 0A         ADC #$0A
    AA            TAX 
    A0 1F         LDY #$1F
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A2 08         LDX #$08
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    CA            DEX 
    D0 F7         BNE $A14C
    18            CLC 
    A5 1D         LDA $1D
    69 56         ADC #$56
    85 1D         STA $1D
    90 02         BCC $A160
    E6 1E         INC $1E
    A9 06         LDA #$06
    8D 86 02      STA $0286
    EE 09 C0      INC $C009
    AE 09 C0      LDX $C009
    EC 03 C0      CPX $C003
    D0 CD         BNE $A13D
    20 A6 A7      JSR $A7A6 ; SUB_A7A6
    4C D9 A6      JMP $A6D9 ; SUB_A6D9
    .byte 20 48 45 4C 50 20 20 44...  ; $A176 " HELP  DIR   SHOW  BACK  GOTO  UCAT  MAI"
    .byte 4C 20 41 43 43 4E 54 20...  ; $A19E "L ACCNT EDITR LEAVE PRINT  LIFE  BUY   U"
    .byte 50 4C 44 20 20 56 4F 54...  ; $A1C6 "PLD  VOTE  MORE  ALL   SEND FINISHABORT "
    .byte 20 4C 4F 41 44 20 20 53...  ; $A1EE " LOAD  SAVE  LAST  NEXT  GET   DOS    ID"
    .byte 20 20 20 44 4F 4E 45 20...  ; $A216 "   DONE .......$*~06<BHxNT."

SUB_A231:
    AD 33 80      LDA $8033
    0A            ASL A
    AA            TAX 
    BD 3E A2      LDA $A23E,X
    48            PHA 
    BD 3D A2      LDA $A23D,X
    48            PHA 
    60            RTS 
    .byte 62 A2 57 A3 8B A9 51 A3 E9 A2 4D A3 DA AD 9B A8 ; $A23F
    .byte 93 AC 6F A2 C2 A2 C4 A7 BC B1 C4 A9 9C A2 80 B2 ; $A24F
    .byte 1D A9 29 A3 A2 0C A0 BB 20 24 81 20 48 81 4C 2D ; $A25F
    .byte A7 20 82 A2 4C 2D A7 20 82 A2                   ; $A26F

SUB_A279:
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    4C 24 81      JMP $8124 ; JT_FRAME_WRITE

SUB_A282:
    A9 FF         LDA #$FF
    8D 4B 80      STA $804B
    8D 4C 80      STA $804C
    AD 33 80      LDA $8033
    48            PHA 
    20 03 81      JSR $8103 ; JT_EDITOR
    A2 76         LDX #$76
    A0 A1         LDY #$A1
    20 15 81      JSR $8115 ; JT_PROTOCOL_RESET
    68            PLA 
    8D 33 80      STA $8033
    60            RTS 
    .byte 20 9B A7 AD 86 02 8D 0A C0 4E 28 C0 A2 01 A0 08 ; $A29D
    .byte 86 2B 8E 0D C0 84 2C 8C 0E C0 20 DA B6 AD 0A C0 ; $A2AD
    .byte 8D 86 02 4C A6 A7 A9 45 8D 00 C1 A0 01 20 84 A7 ; $A2BD
    .byte 20 D2 96 B0 CA 20 21 81 20 C0 96 A9 0E 8D 20 D0 ; $A2CD
    .byte 20 86 AC 68 68 20 48 81 A9 93 4C D2 FF 20 9B A7 ; $A2DD
    .byte AD 86 02 8D 0A C0 A2 23 A0 A3 20 42 81 A2 06 A0 ; $A2ED
    .byte 01 A9 00 18 20 1B 81 A2 01 A0 C1 20 1E 81 08 20 ; $A2FD
    .byte 91 A7 AD 0A C0 8D 86 02 20 A6 A7 28 90 01 60 A9 ; $A30D
    .byte 4C A4 1A C8 D0 3C 47 4F 54 4F 3F 20 00 AD 07 C0 ; $A31D
    .byte 8D 33 80 C6 1D A2 01 20 D5 A5 C9 00 F0 0D 9D 00 ; $A32D
    .byte C1 29 3F 09 80 9D C5 07 E8 D0 EC 8A A8 A9 4C D0 ; $A33D
    .byte 11 A9 43 D0 02 A9 42 A0 01 D0 07                ; $A34D

SUB_A358:
    20 13 A7      JSR $A713 ; SUB_A713
    A9 50         LDA #$50
    A0 03         LDY #$03

SUB_A35F:
    8D 00 C1      STA $C100
    20 84 A7      JSR $A784 ; SUB_A784
    20 D2 96      JSR $96D2 ; PROTO_SEND_DATA
    90 01         BCC $A36B
    60            RTS 
    20 FE A4      JSR $A4FE ; SUB_A4FE
    F0 15         BEQ $A385
    A2 00         LDX #$00
    A0 D0         LDY #$D0
    86 1D         STX $1D
    84 1E         STY $1E
    20 95 A5      JSR $A595 ; SUB_A595
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    20 95 A5      JSR $A595 ; SUB_A595
    C9 00         CMP #$00
    D0 F6         BNE $A37B
    A2 E1         LDX #$E1
    A0 BC         LDY #$BC
    20 24 81      JSR $8124 ; JT_FRAME_WRITE
    20 8C A7      JSR $A78C ; SUB_A78C
    A2 00         LDX #$00
    A0 D0         LDY #$D0
    20 04 A5      JSR $A504 ; SUB_A504
    20 FE A4      JSR $A4FE ; SUB_A4FE
    D0 03         BNE $A39E
    4C 27 A4      JMP $A427 ; SUB_A427
    48            PHA 
    A2 80         LDX #$80
    A0 D5         LDY #$D5
    86 1D         STX $1D
    84 1E         STY $1E
    A9 00         LDA #$00
    20 95 A5      JSR $A595 ; SUB_A595
    A6 1D         LDX $1D
    D0 F9         BNE $A3A9
    68            PLA 
    A2 00         LDX #$00
    A0 D3         LDY #$D3
    86 1D         STX $1D
    84 1E         STY $1E
    A2 02         LDX #$02
    D0 03         BNE $A3C0
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    20 95 A5      JSR $A595 ; SUB_A595
    C9 00         CMP #$00
    F0 60         BEQ $A427
    C9 0D         CMP #$0D
    D0 F2         BNE $A3BD
    CA            DEX 
    D0 EF         BNE $A3BD
    A9 00         LDA #$00
    20 95 A5      JSR $A595 ; SUB_A595

SUB_A3D3:
    20 FE A4      JSR $A4FE ; SUB_A4FE
    F0 4F         BEQ $A427
    29 0F         AND #$0F
    AA            TAX 
    F0 14         BEQ $A3F1
    E0 07         CPX #$07
    B0 10         BCS $A3F1
    BD F7 A4      LDA $A4F7,X
    85 1D         STA $1D
    A9 D5         LDA #$D5
    85 1E         STA $1E
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    C9 3D         CMP #$3D
    F0 0D         BEQ $A3FE
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    C9 00         CMP #$00
    F0 15         BEQ $A40D
    C9 0D         CMP #$0D
    D0 F5         BNE $A3F1
    F0 D5         BEQ $A3D3
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    C9 0D         CMP #$0D
    D0 08         BNE $A40D
    A9 00         LDA #$00
    20 95 A5      JSR $A595 ; SUB_A595
    4C D3 A3      JMP $A3D3 ; SUB_A3D3
    C9 07         CMP #$07
    D0 0F         BNE $A420
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    48            PHA 
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    AA            TAX 
    68            PLA 
    20 95 A5      JSR $A595 ; SUB_A595
    CA            DEX 
    D0 FA         BNE $A41A
    20 95 A5      JSR $A595 ; SUB_A595
    C9 00         CMP #$00
    D0 D7         BNE $A3FE

SUB_A427:
    A2 16         LDX #$16
    A0 00         LDY #$00
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A2 00         LDX #$00
    A0 D3         LDY #$D3
    20 04 A5      JSR $A504 ; SUB_A504
    20 FE A4      JSR $A4FE ; SUB_A4FE
    F0 15         BEQ $A450
    A2 00         LDX #$00
    A0 D4         LDY #$D4
    86 1D         STX $1D
    84 1E         STY $1E
    20 95 A5      JSR $A595 ; SUB_A595
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    20 95 A5      JSR $A595 ; SUB_A595
    C9 00         CMP #$00
    D0 F6         BNE $A446
    20 44 A5      JSR $A544 ; SUB_A544
    20 FE A4      JSR $A4FE ; SUB_A4FE
    F0 3D         BEQ $A495
    A2 00         LDX #$00
    A0 D5         LDY #$D5
    86 1D         STX $1D
    84 1E         STY $1E
    A2 08         LDX #$08
    A0 00         LDY #$00
    8C 01 C0      STY $C001
    F0 09         BEQ $A472
    A2 08         LDX #$08

SUB_A46B:
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    C9 0D         CMP #$0D
    F0 0B         BEQ $A47D
    C9 2C         CMP #$2C
    F0 07         BEQ $A47D
    20 95 A5      JSR $A595 ; SUB_A595
    CA            DEX 
    4C 6B A4      JMP $A46B ; SUB_A46B
    48            PHA 
    EE 01 C0      INC $C001
    A9 20         LDA #$20
    E0 00         CPX #$00
    F0 06         BEQ $A48D
    20 95 A5      JSR $A595 ; SUB_A595
    CA            DEX 
    D0 FA         BNE $A487
    68            PLA 
    C9 0D         CMP #$0D
    D0 D7         BNE $A469
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    A9 01         LDA #$01
    8D 02 C0      STA $C002
    20 6E A5      JSR $A56E ; SUB_A56E
    20 FE A4      JSR $A4FE ; SUB_A4FE
    F0 30         BEQ $A4D2
    A2 00         LDX #$00
    A0 D6         LDY #$D6
    86 1D         STX $1D
    84 1E         STY $1E
    8E 05 C0      STX $C005
    8C 06 C0      STY $C006
    48            PHA 
    A2 0A         LDX #$0A
    A0 00         LDY #$00
    8C 09 C0      STY $C009
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    68            PLA 
    20 EA A5      JSR $A5EA ; SUB_A5EA
    B0 08         BCS $A4CA
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    20 EA A5      JSR $A5EA ; SUB_A5EA
    90 F8         BCC $A4C2
    AE 09 C0      LDX $C009
    8E 03 C0      STX $C003
    10 03         BPL $A4D5
    20 3E A6      JSR $A63E ; SUB_A63E
    38            SEC 
    6E 00 C0      ROR $C000
    A2 0A         LDX #$0A
    A0 00         LDY #$00
    8C 04 C0      STY $C004
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A2 11         LDX #$11
    A0 19         LDY #$19
    B1 D1         LDA ($D1),Y
    C9 15         CMP #$15
    D0 02         BNE $A4F0
    A2 0F         LDX #$0F
    8E 1E A2      STX $A21E
    20 D9 A6      JSR $A6D9 ; SUB_A6D9
    18            CLC 
    60            RTS 
    .byte 80 A0 88 A8 90 B0                               ; $A4F8

SUB_A4FE:
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    C9 00         CMP #$00
    60            RTS 

SUB_A504:
    86 1D         STX $1D
    84 1E         STY $1E
    A9 00         LDA #$00
    8D 07 C0      STA $C007

SUB_A50D:
    20 AA A5      JSR $A5AA ; SUB_A5AA
    C9 00         CMP #$00
    F0 16         BEQ $A52A
    C9 0D         CMP #$0D
    D0 0C         BNE $A524
    20 2A A5      JSR $A52A ; SUB_A52A
    90 05         BCC $A522
    A9 91         LDA #$91
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 0D         LDA #$0D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 0D A5      JMP $A50D ; SUB_A50D

SUB_A52A:
    A5 D3         LDA $D3
    C9 28         CMP #$28
    F0 02         BEQ $A532
    18            CLC 
    60            RTS 
    38            SEC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A0 00         LDY #$00
    B5 D9         LDA $D9,X
    09 80         ORA #$80
    95 D9         STA $D9,X
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    38            SEC 
    60            RTS 

SUB_A544:
    A2 00         LDX #$00
    A0 D4         LDY #$D4
    86 1D         STX $1D
    84 1E         STY $1E
    A2 07         LDX #$07
    A0 01         LDY #$01
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A9 06         LDA #$06
    8D 86 02      STA $0286
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    C9 00         CMP #$00
    F0 0D         BEQ $A56D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    C9 0D         CMP #$0D
    D0 F2         BNE $A559
    A9 01         LDA #$01
    85 D3         STA $D3
    D0 EC         BNE $A559
    60            RTS 

SUB_A56E:
    A2 08         LDX #$08
    A0 1F         LDY #$1F
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A9 06         LDA #$06
    8D 86 02      STA $0286
    AE 02 C0      LDX $C002
    CA            DEX 
    8A            TXA 
    0A            ASL A
    0A            ASL A
    0A            ASL A
    85 1D         STA $1D
    A9 D5         LDA #$D5
    85 1E         STA $1E
    A2 07         LDX #$07
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    CA            DEX 
    10 F7         BPL $A58B
    60            RTS 

SUB_A595:
    A0 34         LDY #$34
    78            SEI 
    84 01         STY $01
    A0 00         LDY #$00
    91 1D         STA ($1D),Y
    A0 36         LDY #$36
    84 01         STY $01
    58            CLI 
    E6 1D         INC $1D
    D0 02         BNE $A5A9
    E6 1E         INC $1E
    60            RTS 

SUB_A5AA:
    AD 07 C0      LDA $C007
    F0 07         BEQ $A5B6
    CE 07 C0      DEC $C007
    AD 08 C0      LDA $C008
    60            RTS 
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    C9 06         CMP #$06
    D0 04         BNE $A5C1
    A9 20         LDA #$20
    D0 07         BNE $A5C8
    C9 07         CMP #$07
    D0 0F         BNE $A5D4
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    8D 08 C0      STA $C008
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    8D 07 C0      STA $C007
    AD 08 C0      LDA $C008
    60            RTS 

SUB_A5D5:
    A0 34         LDY #$34
    78            SEI 
    84 01         STY $01
    A0 00         LDY #$00
    B1 1D         LDA ($1D),Y
    A0 36         LDY #$36
    84 01         STY $01
    58            CLI 
    E6 1D         INC $1D
    D0 02         BNE $A5E9
    E6 1E         INC $1E
    60            RTS 

SUB_A5EA:
    20 F3 A5      JSR $A5F3 ; SUB_A5F3
    08            PHP 
    20 61 A6      JSR $A661 ; SUB_A661
    28            PLP 
    60            RTS 

SUB_A5F3:
    20 95 A5      JSR $A595 ; SUB_A595
    A2 01         LDX #$01

SUB_A5F8:
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    08            PHP 
    C9 2C         CMP #$2C
    F0 08         BEQ $A608
    20 95 A5      JSR $A595 ; SUB_A595
    E8            INX 
    28            PLP 
    4C F8 A5      JMP $A5F8 ; SUB_A5F8
    A9 20         LDA #$20
    E0 1E         CPX #$1E
    F0 06         BEQ $A614
    20 95 A5      JSR $A595 ; SUB_A595
    E8            INX 
    D0 F6         BNE $A60A
    A2 08         LDX #$08

SUB_A616:
    28            PLP 
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    08            PHP 
    C9 0D         CMP #$0D
    F0 0B         BEQ $A62A
    C9 2C         CMP #$2C
    F0 07         BEQ $A62A
    20 95 A5      JSR $A595 ; SUB_A595
    CA            DEX 
    4C 16 A6      JMP $A616 ; SUB_A616
    48            PHA 
    A9 20         LDA #$20
    E0 00         CPX #$00
    F0 06         BEQ $A637
    20 95 A5      JSR $A595 ; SUB_A595
    CA            DEX 
    D0 FA         BNE $A631
    68            PLA 
    C9 2C         CMP #$2C
    F0 D8         BEQ $A614
    28            PLP 
    60            RTS 

SUB_A63E:
    A2 0A         LDX #$0A
    A0 00         LDY #$00
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A2 00         LDX #$00
    A0 D6         LDY #$D6
    8E 05 C0      STX $C005
    8C 06 C0      STY $C006
    A2 00         LDX #$00
    8E 09 C0      STX $C009
    20 61 A6      JSR $A661 ; SUB_A661
    AE 09 C0      LDX $C009
    EC 03 C0      CPX $C003
    D0 F5         BNE $A655
    60            RTS 

SUB_A661:
    AE 05 C0      LDX $C005
    AC 06 C0      LDY $C006
    86 1D         STX $1D
    84 1E         STY $1E
    AD 21 D0      LDA $D021
    29 0F         AND #$0F
    8D 86 02      STA $0286
    A0 01         LDY #$01
    84 D3         STY $D3
    A2 06         LDX #$06
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    CA            DEX 
    D0 F7         BNE $A679
    A9 06         LDA #$06
    AE 09 C0      LDX $C009
    D0 02         BNE $A68B
    A9 02         LDA #$02
    8D 86 02      STA $0286
    A2 17         LDX #$17
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    CA            DEX 
    D0 F7         BNE $A690
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    A0 1F         LDY #$1F
    84 D3         STY $D3
    AE 02 C0      LDX $C002
    CA            DEX 
    8A            TXA 
    0A            ASL A
    0A            ASL A
    0A            ASL A
    18            CLC 
    65 1D         ADC $1D
    85 1D         STA $1D
    90 02         BCC $A6B1
    E6 1E         INC $1E
    A2 08         LDX #$08
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    CA            DEX 
    D0 F7         BNE $A6B3
    EE 09 C0      INC $C009
    18            CLC 

SUB_A6C0:
    AD 05 C0      LDA $C005
    69 5E         ADC #$5E
    8D 05 C0      STA $C005
    85 1D         STA $1D
    AD 06 C0      LDA $C006
    69 00         ADC #$00
    8D 06 C0      STA $C006
    85 1E         STA $1E
    A9 0D         LDA #$0D
    4C D2 FF      JMP $FFD2 ; KERNAL_CHROUT

SUB_A6D9:
    20 24 EA      JSR $EA24
    A2 06         LDX #$06
    AD 04 C0      LDA $C004
    D0 02         BNE $A6E5
    A2 02         LDX #$02
    A0 26         LDY #$26
    C0 1E         CPY #$1E
    F0 09         BEQ $A6F4
    B1 D1         LDA ($D1),Y
    09 80         ORA #$80
    91 D1         STA ($D1),Y
    8A            TXA 
    91 F3         STA ($F3),Y
    88            DEY 
    D0 F0         BNE $A6E7
    60            RTS 

SUB_A6F8:
    A0 27         LDY #$27
    B1 D1         LDA ($D1),Y
    29 7F         AND #$7F
    91 D1         STA ($D1),Y
    88            DEY 
    10 F7         BPL $A6FA
    20 24 EA      JSR $EA24
    AD 21 D0      LDA $D021
    29 0F         AND #$0F
    A0 06         LDY #$06
    91 F3         STA ($F3),Y
    88            DEY 
    D0 FB         BNE $A70D
    60            RTS 

SUB_A713:
    A9 30         LDA #$30
    8D 01 C1      STA $C101
    AD 04 C0      LDA $C004

SUB_A71B:
    C9 0A         CMP #$0A
    90 08         BCC $A727
    EE 01 C1      INC $C101
    E9 0A         SBC #$0A
    4C 1B A7      JMP $A71B ; SUB_A71B
    69 30         ADC #$30
    8D 02 C1      STA $C102
    60            RTS 

SUB_A72D:
    2C 00 C0      BIT $C000
    30 19         BMI $A74B
    A9 00         LDA #$00
    8D 04 C0      STA $C004
    20 B0 A7      JSR $A7B0 ; SUB_A7B0
    A9 8E         LDA #$8E
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    AD 12 80      LDA $8012
    8D 20 D0      STA $D020
    A9 0F         LDA #$0F
    8D 21 D0      STA $D021
    60            RTS 
    A2 E1         LDX #$E1
    A0 BC         LDY #$BC
    20 24 81      JSR $8124 ; JT_FRAME_WRITE
    20 8C A7      JSR $A78C ; SUB_A78C
    A2 00         LDX #$00
    A0 D0         LDY #$D0
    20 04 A5      JSR $A504 ; SUB_A504
    A2 16         LDX #$16
    A0 00         LDY #$00
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A2 00         LDX #$00
    A0 D3         LDY #$D3
    20 04 A5      JSR $A504 ; SUB_A504
    20 44 A5      JSR $A544 ; SUB_A544
    20 6E A5      JSR $A56E ; SUB_A56E
    20 3E A6      JSR $A63E ; SUB_A63E
    AD 04 C0      LDA $C004
    18            CLC 
    69 0A         ADC #$0A
    AA            TAX 
    A0 00         LDY #$00
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    4C D9 A6      JMP $A6D9 ; SUB_A6D9

SUB_A784:
    A9 43         LDA #$43
    8D 34 80      STA $8034
    4C 09 81      JMP $8109 ; JT_DISCONNECT_MSG

SUB_A78C:
    A9 13         LDA #$13
    4C D2 FF      JMP $FFD2 ; KERNAL_CHROUT

SUB_A791:
    A9 92         LDA #$92
    4C D2 FF      JMP $FFD2 ; KERNAL_CHROUT

SUB_A796:
    A9 12         LDA #$12
    4C D2 FF      JMP $FFD2 ; KERNAL_CHROUT

SUB_A79B:
    38            SEC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    8E 0B C0      STX $C00B
    8C 0C C0      STY $C00C
    60            RTS 

SUB_A7A6:
    18            CLC 
    AE 0B C0      LDX $C00B
    AC 0C C0      LDY $C00C
    4C F0 FF      JMP $FFF0 ; KERNAL_PLOT

SUB_A7B0:
    A9 93         LDA #$93
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 51 81      JSR $8151 ; JT_WHITE_BAR
    20 91 A7      JSR $A791 ; SUB_A791
    A9 00         LDA #$00
    8D 15 D0      STA $D015
    A9 0E         LDA #$0E
    4C D2 FF      JMP $FFD2 ; KERNAL_CHROUT
    .byte AD FA 80 0D FB 80 F0 03 6C FA 80 2C 00 C0 30 01 ; $A7C5
    .byte 60 A9 04 AE F9 80 D0 01 AA A0 00 20 BA FF A9 00 ; $A7D5
    .byte 20 BD FF 20 C0 FF A2 04 20 C9 FF 90 23 20 CC FF ; $A7E5
    .byte A9 04 20 C3 FF A2 07 A0 A8 20 45 81 20 4B 81 4C ; $A7F5
    .byte 51 81 50 52 49 4E 54 45 52 20 45 52 52 4F 52 00 ; $A805
    .byte A2 1E A9 20 20 D2 FF CA D0 FA A2 00 A0 D5 86 1D ; $A815
    .byte 84 1E 20 64 A8 A9 0D 20 D2 FF A2 00 A0 D6 86 1D ; $A825
    .byte 84 1E A2 00 8E 09 C0 20 E4 FF C9 03 F0 19 A2 1E ; $A835
    .byte 20 D5 A5 20 D2 FF CA D0 F7 20 64 A8 EE 09 C0 AE ; $A845
    .byte 09 C0 EC 03 C0 D0 E0 20 CC FF A9 04 4C C3 FF    ; $A855

SUB_A864:
    18            CLC 
    6E 17 C0      ROR $C017
    A2 01         LDX #$01
    8E 18 C0      STX $C018
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A2 08         LDX #$08
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    2C 17 C0      BIT $C017
    30 03         BMI $A87F
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    CA            DEX 
    D0 F2         BNE $A874
    AE 18 C0      LDX $C018
    E0 08         CPX #$08
    F0 0E         BEQ $A897
    EC 01 C0      CPX $C001
    D0 04         BNE $A892
    38            SEC 
    6E 17 C0      ROR $C017
    EE 18 C0      INC $C018
    D0 D6         BNE $A86D
    A9 0D         LDA #$0D
    4C D2 FF      JMP $FFD2 ; KERNAL_CHROUT
    .byte A9 41 8D 00 C1 A0 01 20 84 A7 20 D2 96 90 01 60 ; $A89C
    .byte 20 0C 81 20 9B A7 AD 86 02 8D 0A C0 A2 FE A0 A8 ; $A8AC
    .byte 20 42 81 A2 00 BD 00 C1 C9 20 D0 03 E8 10 F6 C9 ; $A8BC
    .byte 2D 08 F0 03 20 D2 FF E8 BD 00 C1 20 D2 FF E8 E0 ; $A8CC
    .byte 0A 90 F5 28 F0 06 A2 07 A0 A9 D0 04 A2 13 A0 A9 ; $A8DC
    .byte 20 3F 81 20 91 A7 20 4B 81 AD 0A C0 8D 86 02 4C ; $A8EC
    .byte A6 A7 59 4F                                     ; $A8FC

SUB_A900:
    55 20         EOR $20,X
    41 52         EOR ($52,X)
    45 20         EOR $20
    00            BRK 
    .byte 20 49 4E 20 43 52 45 44...  ; $A907 " IN CREDIT.. IN DEBIT...V... .. ...m.. B"
    .byte 81...               ; $A92F "."

SUB_A930:
    A2 01         LDX #$01
    A0 01         LDY #$01
    A9 00         LDA #$00
    38            SEC 
    20 1B 81      JSR $811B ; JT_SETUP_INPUT
    A2 00         LDX #$00
    A0 02         LDY #$02
    20 1E 81      JSR $811E ; JT_INPUT_LINE
    B0 27         BCS $A96A
    AD 00 02      LDA $0200
    C9 30         CMP #$30
    D0 0B         BNE $A955
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 30 A9      JMP $A930 ; SUB_A930
    8D 03 C1      STA $C103
    8D 81 A9      STA $A981
    A2 7A         LDX #$7A
    A0 A9         LDY #$A9
    20 45 81      JSR $8145 ; JT_STATUS_BAR
    A0 04         LDY #$04
    20 84 A7      JSR $A784 ; SUB_A784
    20 D2 96      JSR $96D2 ; PROTO_SEND_DATA
    4C A6 A7      JMP $A7A6 ; SUB_A7A6
    .byte 56 4F 54 45 20 28 31 2D...  ; $A96D "VOTE (1-9)? .VOTING  .TCALPSL..,........"
    .byte 20 54 81 A2 05 DD 83 A9...  ; $A995 " T...........`.... F....... E.LK.PLEASE "
    .byte 55 53 45 20 42 55 59 00...  ; $A9BD "USE BUY..3.....D..."

SUB_A9D0:
    20 13 A7      JSR $A713 ; SUB_A713
    A0 17         LDY #$17
    B1 D1         LDA ($D1),Y
    C9 A0         CMP #$A0
    D0 05         BNE $A9E0
    88            DEY 
    C0 08         CPY #$08
    B0 F5         BCS $A9D5
    AA            TAX 
    98            TYA 
    38            SEC 
    E9 07         SBC #$07
    8D 3B C0      STA $C03B
    8A            TXA 
    20 54 81      JSR $8154 ; JT_MODEM_STATUS
    99 23 C0      STA $C023,Y
    88            DEY 
    B1 D1         LDA ($D1),Y
    C0 08         CPY #$08
    B0 F3         BCS $A9E9
    A0 19         LDY #$19
    B1 D1         LDA ($D1),Y
    29 7F         AND #$7F
    20 54 81      JSR $8154 ; JT_MODEM_STATUS
    A2 05         LDX #$05
    DD 83 A9      CMP $A983,X
    F0 04         BEQ $AA0A
    CA            DEX 
    10 F8         BPL $AA01
    60            RTS 
    8D 19 C0      STA $C019
    E0 05         CPX #$05
    6E 28 C0      ROR $C028
    20 46 AC      JSR $AC46 ; SUB_AC46
    8D 12 C0      STA $C012
    F0 53         BEQ $AA6D
    20 9B A7      JSR $A79B ; SUB_A79B
    A2 16         LDX #$16
    A0 AC         LDY #$AC
    20 42 81      JSR $8142 ; JT_DUCK_ITEM
    20 A6 A7      JSR $A7A6 ; SUB_A7A6
    AE 04 C0      LDX $C004
    BC 7B AC      LDY $AC7B,X
    BD 70 AC      LDA $AC70,X
    18            CLC 
    69 1E         ADC #$1E
    90 01         BCC $AA36
    C8            INY 
    85 1D         STA $1D
    84 1E         STY $1E
    A2 09         LDX #$09
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    C9 20         CMP #$20
    F0 F9         BEQ $AA3C
    09 80         ORA #$80
    9D C0 07      STA $07C0,X
    E8            INX 
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    C9 20         CMP #$20
    D0 F3         BNE $AA43
    8A            TXA 
    A8            TAY 
    A2 18         LDX #$18
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A2 20         LDX #$20
    A0 AC         LDY #$AC
    20 3F 81      JSR $813F ; JT_PRINT_STR
    20 4E 81      JSR $814E ; JT_INPUT_PROMPT
    08            PHP 
    20 A6 A7      JSR $A7A6 ; SUB_A7A6
    20 91 A7      JSR $A791 ; SUB_A791
    28            PLP 
    F0 01         BEQ $AA6D
    60            RTS 
    AD 19 C0      LDA $C019
    C9 54         CMP #$54
    F0 07         BEQ $AA7B
    C9 43         CMP #$43
    F0 03         BEQ $AA7B
    20 86 AC      JSR $AC86 ; SUB_AC86
    AD 19 C0      LDA $C019
    C9 4C         CMP #$4C
    D0 1C         BNE $AA9E
    A2 02         LDX #$02
    BD 01 08      LDA $0801,X
    DD 89 A9      CMP $A989,X
    D0 12         BNE $AA9E
    CA            DEX 
    10 F5         BPL $AA84
    A2 04         LDX #$04
    BD 04 08      LDA $0804,X
    9D 03 C1      STA $C103,X
    CA            DEX 
    10 F7         BPL $AA91
    A0 08         LDY #$08
    D0 02         BNE $AAA0
    A0 03         LDY #$03
    20 84 A7      JSR $A784 ; SUB_A784
    20 D2 96      JSR $96D2 ; PROTO_SEND_DATA
    B0 3C         BCS $AAE4
    AD 19 C0      LDA $C019
    C9 4C         CMP #$4C
    F0 0F         BEQ $AABE
    C9 41         CMP #$41
    D0 26         BNE $AAD9
    A9 00         LDA #$00
    8D 01 08      STA $0801
    8D 02 08      STA $0802
    8D 03 08      STA $0803
    A9 00         LDA #$00
    8D 4C C0      STA $C04C
    8D 27 C0      STA $C027
    20 0F 81      JSR $810F ; JT_MODEM_INIT_DL
    A2 76         LDX #$76
    A0 A1         LDY #$A1
    20 15 81      JSR $8115 ; JT_PROTOCOL_RESET
    AD 1A C0      LDA $C01A
    8D 33 80      STA $8033
    4C 2D A7      JMP $A72D ; SUB_A72D
    C9 53         CMP #$53
    F0 04         BEQ $AAE1
    C9 50         CMP #$50
    D0 04         BNE $AAE5
    4C 67 AB      JMP $AB67 ; SUB_AB67
    60            RTS 
    BA            TSX 
    8E 15 C0      STX $C015
    A9 44         LDA #$44
    8D 16 C0      STA $C016
    20 57 AB      JSR $AB57 ; SUB_AB57

SUB_AAF1:
    AD 35 80      LDA $8035
    10 14         BPL $AB0A
    A9 01         LDA #$01
    8D 33 80      STA $8033
    A2 16         LDX #$16
    A0 AB         LDY #$AB
    20 18 81      JSR $8118 ; JT_DUCKSHOOT
    B0 F7         BCS $AAFB
    20 1A AB      JSR $AB1A ; SUB_AB1A
    4C F1 AA      JMP $AAF1 ; SUB_AAF1
    20 48 81      JSR $8148 ; JT_PRESS_KEY
    AD 1A C0      LDA $C01A
    8D 33 80      STA $8033
    4C 2D A7      JMP $A72D ; SUB_A72D
    .byte 03 5A 60 6C...      ; $AB16 ".Z`l"

SUB_AB1A:
    AD 33 80      LDA $8033
    0A            ASL A
    AA            TAX 
    BD 27 AB      LDA $AB27,X
    48            PHA 
    BD 26 AB      LDA $AB26,X
    48            PHA 
    60            RTS 
    .byte 43 AB 2D AB 36 AB 20 44...  ; $AB28 "C.-.6. D..5.0.`"
    AE 15 C0      LDX $C015
    9A            TXS 
    AD 1A C0      LDA $C01A
    8D 33 80      STA $8033
    4C 2D A7      JMP $A72D ; SUB_A72D

SUB_AB44:
    20 51 81      JSR $8151 ; JT_WHITE_BAR
    AD 16 C0      LDA $C016
    8D 00 C1      STA $C100
    A0 01         LDY #$01
    20 84 A7      JSR $A784 ; SUB_A784
    20 D2 96      JSR $96D2 ; PROTO_SEND_DATA
    B0 E0         BCS $AB37

SUB_AB57:
    20 30 81      JSR $8130 ; JT_NEW_PAGE
    A2 3A         LDX #$3A
    A0 AC         LDY #$AC
    20 45 81      JSR $8145 ; JT_STATUS_BAR
    20 21 81      JSR $8121 ; JT_FRAME_READ
    4C 27 81      JMP $8127 ; JT_DISK_LOAD

SUB_AB67:
    A2 03         LDX #$03
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    CA            DEX 
    10 FA         BPL $AB69
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    8D 0D C0      STA $C00D
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    8D 0E C0      STA $C00E
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    85 1F         STA $1F
    18            CLC 
    6D 0D C0      ADC $C00D
    8D 0F C0      STA $C00F
    08            PHP 
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    85 20         STA $20
    28            PLP 
    6D 0E C0      ADC $C00E
    8D 10 C0      STA $C010
    18            CLC 
    A5 2B         LDA $2B
    85 1D         STA $1D
    65 1F         ADC $1F
    85 1F         STA $1F
    A5 2C         LDA $2C
    85 1E         STA $1E
    65 20         ADC $20
    C5 38         CMP $38
    90 1C         BCC $ABC3
    D0 06         BNE $ABAF
    A5 1F         LDA $1F
    C5 37         CMP $37
    90 14         BCC $ABC3
    A2 2B         LDX #$2B
    A0 AC         LDY #$AC
    20 45 81      JSR $8145 ; JT_STATUS_BAR
    A9 41         LDA #$41
    8D 34 80      STA $8034
    A0 01         LDY #$01
    20 09 81      JSR $8109 ; JT_DISCONNECT_MSG
    4C 4B 81      JMP $814B ; JT_CLEAR_STATUS
    A2 3A         LDX #$3A
    A0 AC         LDY #$AC
    20 45 81      JSR $8145 ; JT_STATUS_BAR
    A9 40         LDA #$40
    8D 34 80      STA $8034
    A0 01         LDY #$01
    20 09 81      JSR $8109 ; JT_DISCONNECT_MSG
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    08            PHP 
    A0 00         LDY #$00
    91 1D         STA ($1D),Y
    E6 1D         INC $1D
    D0 02         BNE $ABE2
    E6 1E         INC $1E
    28            PLP 
    90 EF         BCC $ABD4
    A5 1D         LDA $1D
    85 2D         STA $2D
    A5 1E         LDA $1E
    85 2E         STA $2E
    AD 28 C0      LDA $C028
    8D 29 C0      STA $C029
    38            SEC 
    6E 27 C0      ROR $C027
    AE 3B C0      LDX $C03B
    8E 4C C0      STX $C04C
    CA            DEX 
    30 08         BMI $AC08
    BD 2B C0      LDA $C02B,X
    9D 3C C0      STA $C03C,X
    D0 F5         BNE $ABFD
    20 94 AC      JSR $AC94 ; SUB_AC94
    4C 2D A7      JMP $A72D ; SUB_A72D
    .byte 4C 49 4E 4B 49 4E 47 00...  ; $AC0E "LINKING.BUY FOR \.. - SURE? .NO ROOM IN "
    .byte 52 41 4D 00 44 4F 57 4E...  ; $AC36 "RAM.DOWNLOADING."

SUB_AC46:
    AE 04 C0      LDX $C004
    BC 7B AC      LDY $AC7B,X
    BD 70 AC      LDA $AC70,X
    18            CLC 
    69 1E         ADC #$1E
    90 01         BCC $AC55
    C8            INY 
    85 1D         STA $1D
    84 1E         STY $1E
    A2 08         LDX #$08
    20 D5 A5      JSR $A5D5 ; SUB_A5D5
    C9 20         CMP #$20
    F0 08         BEQ $AC6A
    C9 30         CMP #$30
    F0 04         BEQ $AC6A
    C9 2E         CMP #$2E
    D0 05         BNE $AC6F
    CA            DEX 
    D0 EE         BNE $AC5B
    A9 00         LDA #$00
    60            RTS 
    .byte 00 5E BC 1A 78 D6 34 92 F0 4E AC D6 D6 D6 D7 D7 ; $AC70
    .byte D7 D8 D8 D8 D9 D9                               ; $AC80

SUB_AC86:
    2C 27 C0      BIT $C027
    10 E4         BPL $AC6F
    20 9B A7      JSR $A79B ; SUB_A79B
    A2 65         LDX #$65
    A0 AD         LDY #$AD
    D0 0C         BNE $ACA0

SUB_AC94:
    AD 4C C0      LDA $C04C
    F0 D6         BEQ $AC6F
    20 9B A7      JSR $A79B ; SUB_A79B

SUB_AC9C:
    A2 60         LDX #$60
    A0 AD         LDY #$AD

SUB_ACA0:
    20 71 AD      JSR $AD71 ; SUB_AD71
    90 03         BCC $ACA8
    4C A6 A7      JMP $A7A6 ; SUB_A7A6
    84 19         STY $19
    2C 29 C0      BIT $C029
    30 57         BMI $AD06
    20 B6 AD      JSR $ADB6 ; SUB_ADB6
    90 52         BCC $AD06
    A5 19         LDA $19
    A2 1E         LDX #$1E
    A0 80         LDY #$80
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    A2 01         LDX #$01
    A0 00         LDY #$00
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    AE 0D C0      LDX $C00D
    AC 0E C0      LDY $C00E
    86 C1         STX $C1
    84 C2         STY $C2
    AE 0F C0      LDX $C00F
    AC 10 C0      LDY $C010
    86 AE         STX $AE
    84 AF         STY $AF
    A2 45         LDX #$45
    A0 AC         LDY #$AC
    20 42 81      JSR $8142 ; JT_DUCK_ITEM
    20 38 F8      JSR $F838
    B0 1F         BCS $AD03
    A9 01         LDA #$01
    20 6A F7      JSR $F76A
    B0 18         BCS $AD03
    A6 2B         LDX $2B
    A4 2C         LDY $2C
    86 C1         STX $C1
    84 C2         STY $C2
    A6 2D         LDX $2D
    A4 2E         LDY $2E
    86 AE         STX $AE
    84 AF         STY $AF
    20 7C F6      JSR $F67C
    B0 03         BCS $AD03

SUB_AD00:
    4E 27 C0      LSR $C027
    4C 2D A7      JMP $A72D ; SUB_A72D
    A9 57         LDA #$57
    A2 50         LDX #$50
    2C 29 C0      BIT $C029
    10 02         BPL $AD11
    A2 53         LDX #$53
    A4 19         LDY $19
    20 5A 81      JSR $815A ; JT_FILE_DL
    90 03         BCC $AD1B
    4C 9C AC      JMP $AC9C ; SUB_AC9C
    A2 08         LDX #$08
    20 C9 FF      JSR $FFC9 ; KERNAL_CHKOUT
    2C 29 C0      BIT $C029
    30 0C         BMI $AD31
    AD 0D C0      LDA $C00D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    AD 0E C0      LDA $C00E
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A5 2B         LDA $2B
    85 1D         STA $1D
    A5 2C         LDA $2C
    85 1E         STA $1E
    A0 00         LDY #$00
    B1 1D         LDA ($1D),Y
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    E6 1D         INC $1D
    D0 02         BNE $AD46
    E6 1E         INC $1E
    A5 1D         LDA $1D
    C5 2D         CMP $2D
    D0 EF         BNE $AD3B
    A5 1E         LDA $1E
    C5 2E         CMP $2E
    D0 E9         BNE $AD3B
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    20 5D 81      JSR $815D ; JT_CNLOAD_ERR
    B0 03         BCS $AD5D
    4E 27 C0      LSR $C027
    4C A6 A7      JMP $A7A6 ; SUB_A7A6
    .byte 53 41 56 45 00 4E 4F 54...  ; $AD60 "SAVE.NOT SAVED -."

SUB_AD71:
    20 42 81      JSR $8142 ; JT_DUCK_ITEM
    A2 AA         LDX #$AA
    A0 AD         LDY #$AD
    20 3F 81      JSR $813F ; JT_PRINT_STR
    A2 10         LDX #$10
    A0 00         LDY #$00
    A9 00         LDA #$00
    18            CLC 
    20 1B 81      JSR $811B ; JT_SETUP_INPUT
    A2 1E         LDX #$1E
    A0 80         LDY #$80
    20 1E 81      JSR $811E ; JT_INPUT_LINE
    B0 1B         BCS $ADA9
    C0 00         CPY #$00
    D0 16         BNE $ADA8
    AD 4C C0      LDA $C04C
    F0 12         BEQ $ADA9
    C6 D3         DEC $D3
    B9 3C C0      LDA $C03C,Y
    99 1E 80      STA $801E,Y
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    C8            INY 
    CC 4C C0      CPY $C04C
    90 F1         BCC $AD99
    18            CLC 
    60            RTS 
    .byte 20 46 49 4C 45 4E 41 4D...  ; $ADAA " FILENAME? ."

SUB_ADB6:
    A9 00         LDA #$00
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    A9 0F         LDA #$0F
    A8            TAY 
    AE F8 80      LDX $80F8
    D0 02         BNE $ADC5
    A2 08         LDX #$08
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    20 C0 FF      JSR $FFC0 ; KERNAL_OPEN
    A2 0F         LDX #$0F
    20 C9 FF      JSR $FFC9 ; KERNAL_CHKOUT
    08            PHP 
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    A9 0F         LDA #$0F
    20 C3 FF      JSR $FFC3 ; KERNAL_CLOSE
    28            PLP 
    60            RTS 
    .byte A9 4D A0 01 20 5F A3 90 01 60 A9 01 8D 33 80    ; $ADDB

SUB_ADEA:
    A2 15         LDX #$15
    A0 AE         LDY #$AE
    8E 1F C0      STX $C01F
    8C 20 C0      STY $C020
    20 66 A0      JSR $A066 ; SUB_A066
    8E 1A C0      STX $C01A
    BC 15 AE      LDY $AE15,X
    A2 00         LDX #$00
    B9 76 A1      LDA $A176,Y
    29 3F         AND #$3F
    09 80         ORA #$80
    9D C0 07      STA $07C0,X
    C8            INY 
    E8            INX 
    E0 06         CPX #$06
    D0 F0         BNE $ADFF
    20 1C AE      JSR $AE1C ; SUB_AE1C
    4C EA AD      JMP $ADEA ; SUB_ADEA
    .byte 06 66 0C 5A 9C 30 A2                            ; $AE15

SUB_AE1C:
    AD 33 80      LDA $8033
    0A            ASL A
    AA            TAX 
    BD 29 AE      LDA $AE29,X
    48            PHA 
    BD 28 AE      LDA $AE28,X
    48            PHA 
    60            RTS 
    .byte 35 AE 0A B0 38 B0 3F B0 6F A2 63 B1 A9 55 8D 00 ; $AE2A
    .byte C1 A2 77 A0 BD 20 24 81 A2 0B A0 D4 86 1D 84 1E ; $AE3A
    .byte A2 06 A0 0A 18 20 F0 FF A9 06 8D 86 02 20 D5 A5 ; $AE4A
    .byte C9 00 F0 0D 20 D2 FF C9 0D D0 F2 A9 0A 85 D3 D0 ; $AE5A
    .byte EC A2 DC A0 AF 20 42 81 A2 10 A0 01 A9 00 18 20 ; $AE6A
    .byte 1B 81 A2 01 A0 C1 20 1E 81 B0 56 A6 1A A9 20 9D ; $AE7A
    .byte 01 C1 E8 E0 10 90 F8 A2 0C A0 0D 18 20 F0 FF 20 ; $AE8A
    .byte 91 A7 A9 06 8D 86 02 A2 00 BD 01 C1 C9 2C D0 05 ; $AE9A
    .byte A9 20 9D 01 C1 20 D2 FF E8 E0 10 90 EC A9 54 8D ; $AEAA
    .byte 11 C1 A2 00 8E 21 C0 A2 E6 A0 AF 20 42 81 A2 08 ; $AEBA
    .byte A0 00 A9 00 18 20 1B 81 A2 00 A0 02 20 1E 81 90 ; $AECA
    .byte 03 4C 2D A7 A6 1A F0 47 A9 20 9D 00 02 E8 E0 08 ; $AEDA
    .byte 90 F8 AD 21 C0 18 69 10 AA A0 03 18 20 F0 FF 20 ; $AEEA
    .byte 91 A7 A9 06 8D 86 02 AD 21 C0 0A 0A 0A AA A0 00 ; $AEFA
    .byte B9 00 02 C9 2C D0 02 A9 20 9D 12 C1 20 D2 FF E8 ; $AF0A
    .byte C8 C0 08 D0 EB EE 21 C0 AD 21 C0 C9 05 90 98 A2 ; $AF1A
    .byte FE A0 AF 20 45 81 AD 21 C0 F0 A6 0A 0A 0A 18 69 ; $AF2A
    .byte 12 A8 20 84 A7 20 D2 96 B0 97 A2 10 20 EA B0 10 ; $AF3A
    .byte 06 20 48 81 4C 2D A7 A2 F7 A0 AF 20 42 81 20 4E ; $AF4A
    .byte 81 F0 03 4C CC AF 20 79 A2 A9 01 8D 33 80       ; $AF5A

SUB_AF68:
    A2 77         LDX #$77
    A0 AF         LDY #$AF
    20 18 81      JSR $8118 ; JT_DUCKSHOOT
    B0 F7         BCS $AF68
    20 7D AF      JSR $AF7D ; SUB_AF7D
    4C 68 AF      JMP $AF68 ; SUB_AF68
    .byte 05 66 6C 84 8A 30                               ; $AF77

SUB_AF7D:
    AD 33 80      LDA $8033
    0A            ASL A
    AA            TAX 
    BD 8A AF      LDA $AF8A,X
    48            PHA 
    BD 89 AF      LDA $AF89,X
    48            PHA 
    60            RTS 
    .byte 94 AF C4 AF 32 81 35 81 75 A2 A2 FE A0 AF 20 45 ; $AF8B
    .byte 81 A9 55 8D 00 C1 A0 01 20 84 A7 20 D2 96 B0 10 ; $AF9B
    .byte A2 03 A0 B0 20 45 81 20 75 B1 20 D2 96 B0 01 60 ; $AFAB
    .byte 68 68 A9 01 8D 33 80 4C 2D A7 68 68 A9 01 8D 33 ; $AFBB
    .byte 80                                              ; $AFCB

SUB_AFCC:
    20 51 81      JSR $8151 ; JT_WHITE_BAR
    A9 4E         LDA #$4E
    8D 00 C1      STA $C100
    A0 01         LDY #$01
    20 84 A7      JSR $A784 ; SUB_A784
    4C 2D A7      JMP $A72D ; SUB_A72D
    .byte 53 55 42 4A 45 43 54 3F...  ; $AFDC "SUBJECT? .DESTINATION ID? .OKAY? .SEND.S"
    .byte 45 4E 44 49 4E 47 00 A9...  ; $B004 "ENDING..D...... .... .. ....`.... W."

SUB_B028:
    AD 35 80      LDA $8035
    10 06         BPL $B033
    20 44 AB      JSR $AB44 ; SUB_AB44
    4C 28 B0      JMP $B028 ; SUB_B028
    20 48 81      JSR $8148 ; JT_PRESS_KEY
    4C 2D A7      JMP $A72D ; SUB_A72D
    .byte A9 4D A0 01 4C 5F A3 A9 49 8D 00 C1 A2 D6 A0 BD ; $B039
    .byte 20 24 81 A2 00 8E 21 C0 A2 D9 A0 B0 20 42 81 A2 ; $B049
    .byte 08 A0 00 A9 00 18 20 1B 81 A2 00 A0 02 20 1E 81 ; $B059
    .byte 90 03 4C 2D A7 A6 1A F0 41 A9 20 9D 00 02 E8 E0 ; $B069
    .byte 08 90 F8 AD 21 C0 18 69 06 AA A0 03 18 20 F0 FF ; $B079
    .byte 20 91 A7 A9 06 8D 86 02 AD 21 C0 0A 0A 0A AA A0 ; $B089
    .byte 00 B9 00 02 9D 01 C1 20 D2 FF E8 C8 C0 08 D0 F1 ; $B099
    .byte EE 21 C0 AD 21 C0 C9 05 90 9E A2 E7 A0 B0 20 45 ; $B0A9
    .byte 81 AD 21 C0 F0 AC 0A 0A 0A 18 69 01 A8 20 84 A7 ; $B0B9
    .byte 20 D2 96 B0 9D A2 06 20 EA B0 20 48 81 4C 2D A7 ; $B0C9
    .byte 49 44 20 54 4F 20 43 48 45 43 4B 3F 20 00 49 44 ; $B0D9
    .byte 00                                              ; $B0E9

SUB_B0EA:
    A0 00         LDY #$00
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    20 91 A7      JSR $A791 ; SUB_A791
    A9 06         LDA #$06
    8D 86 02      STA $0286
    4E 23 C0      LSR $C023
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A2 08         LDX #$08
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    CA            DEX 
    D0 F7         BNE $B108
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 3A         LDA #$3A
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    08            PHP 
    C9 1E         CMP #$1E
    F0 0E         BEQ $B136
    28            PLP 
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 CC 96      JSR $96CC ; PROTO_RECV_BYTE
    08            PHP 
    C9 1E         CMP #$1E
    D0 F4         BNE $B128
    F0 0B         BEQ $B141
    A2 4D         LDX #$4D
    A0 B1         LDY #$B1
    20 3F 81      JSR $813F ; JT_PRINT_STR
    38            SEC 
    6E 23 C0      ROR $C023
    A9 0D         LDA #$0D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    28            PLP 
    90 B2         BCC $B0FB
    AD 23 C0      LDA $C023
    60            RTS 
    .byte 90 2A 2A 2A 20 4E 4F 20...  ; $B14D ".*** NO SUCH USER ***...N.. _...hh...3.`"

SUB_B175:
    A9 22         LDA #$22
    8D 34 80      STA $8034
    AD 19 80      LDA $8019
    85 1D         STA $1D
    AD 1A 80      LDA $801A
    85 1E         STA $1E
    A9 00         LDA #$00
    48            PHA 
    E6 1D         INC $1D
    D0 02         BNE $B18D
    E6 1E         INC $1E
    A2 34         LDX #$34
    A0 00         LDY #$00
    78            SEI 
    86 01         STX $01
    B1 1D         LDA ($1D),Y
    A2 36         LDX #$36
    86 01         STX $01
    58            CLI 
    C9 00         CMP #$00
    F0 09         BEQ $B1A8
    AA            TAX 
    68            PLA 
    18            CLC 
    20 C9 96      JSR $96C9 ; PROTO_RECV_FRAME
    8A            TXA 
    D0 DE         BNE $B186
    68            PLA 
    38            SEC 
    4C C9 96      JMP $96C9 ; PROTO_RECV_FRAME

SUB_B1AD:
    A2 02         LDX #$02
    B5 7C         LDA $7C,X
    DD DE CC      CMP $CCDE,X
    D0 05         BNE $B1BB
    CA            DEX 
    10 F6         BPL $B1AF
    18            CLC 
    60            RTS 
    38            SEC 
    60            RTS 
    .byte A0 19 B1 D1 C9 84 F0 08 C9 85 F0 04 C9 95 D0 0A ; $B1BD
    .byte A2 53 A0 B2 20 45 81 4C 4B 81 A9 58 8D 00 C1 20 ; $B1CD
    .byte 13 A7 AD 86 02 8D 0A C0 20 9B A7 A2 60 A0 B2 20 ; $B1DD
    .byte 42 81 A2 04 A0 01 A9 2D 38 20 1B 81 A2 00 A0 02 ; $B1ED
    .byte 20 1E 81 08 20 91 A7 20 A6 A7 AD 0A C0 8D 86 02 ; $B1FD
    .byte 28 90 01 60 A6 1A A9 20 9D 00 02 E8 E0 04 90 F8 ; $B20D
    .byte AD 00 02 8D 03 C1 A2 03 BD 00 02 C9 2D F0 AB 9D ; $B21D
    .byte 03 C1 CA D0 F3 A0 07 20 84 A7 20 D2 96 B0 D4    ; $B22D

SUB_B23C:
    A2 6C         LDX #$6C
    A0 B2         LDY #$B2
    20 45 81      JSR $8145 ; JT_STATUS_BAR
    A9 0B         LDA #$0B
    8D 1E A2      STA $A21E
    A9 00         LDA #$00
    8D 00 C0      STA $C000
    8D 04 C0      STA $C004
    4C 58 A3      JMP $A358 ; SUB_A358
    .byte 43 41 4E 27 54 20 45 58 54 45 4E 44 00 45 58 54 ; $B253
    .byte 45 4E 44 20 42 59 3F 20 00 4F 4B 20 2D 20 47 45 ; $B263
    .byte 54 54 49 4E 47 20 4E 45 57 20 44 49 52 00 AD 03 ; $B273
    .byte C0 C9 0B D0 0A A2 66 A0 B9 20 45 81 4C 4B 81 20 ; $B283
    .byte F8 A6 AD 03 C0 18 69 0A AA A0 00 18 20 F0 FF AD ; $B293
    .byte 04 C0 48 AD 03 C0 8D 04 C0 20 D9 A6 68 8D 04 C0 ; $B2A3
    .byte A9 55 8D 00 C1 A2 9C A0 B9 20 42 81 A2 10 A0 01 ; $B2B3
    .byte A9 00 18 20 1B 81 A2 01 A0 C1 20 1E 81 B0 5B 8C ; $B2C3
    .byte 3B C0 AE 3B C0 BD 00 C1 9D 2A C0 CA D0 F7 A9 20 ; $B2D3
    .byte 99 01 C1 C8 C0 10 90 F8 AD 03 C0 18 69 0A AA A0 ; $B2E3
    .byte 08 18 20 F0 FF A9 06 8D 86 02 A2 00 BD 01 C1 C9 ; $B2F3
    .byte 2C D0 05 A9 20 9D 01 C1 20 D2 FF E8 E0 10 D0 EC ; $B303
    .byte A2 B0 A0 B9 20 42 81 A2 01 A0 01 A9 00 18 20 1B ; $B313
    .byte 81 A2 11 A0 C1 20 1E 81 90 03 4C 2D A7 AC 11 C1 ; $B323
    .byte 4E 28 C0 C0 54 F0 27 C0 43 F0 23 C0 26 F0 10 C0 ; $B333
    .byte 50 F0 0C C0 41 F0 08 C0 53 D0 C5 38 6E 28 C0 AE ; $B343
    .byte 3B C0 8E 4C C0 BD 2A C0 9D 3B C0 CA D0 F7 8C 19 ; $B353
    .byte C0 AD 03 C0 18 69 0A AA A0 19 18 20 F0 FF A9 06 ; $B363
    .byte 8D 86 02 AD 19 C0 C9 26 D0 05 A9 50 20 D2 FF 20 ; $B373
    .byte D2 FF A2 05 BD 60 B9 9D 12 C1 CA 10 F7 A2 C3 A0 ; $B383
    .byte B9 20 42 81 A2 06 A0 01 A9 2E 38 20 1B 81 A2 00 ; $B393
    .byte A0 02 20 1E 81 90 03 4C 2D A7 A9 00 A6 1A 9D 00 ; $B3A3
    .byte 02 AA BD 00 02 F0 2B C9 2E F0 07 E8 E0 04 D0 F2 ; $B3B3
    .byte F0 CB BD 01 02 F0 C6 C9 2E F0 C2 BD 02 02 F0 BD ; $B3C3
    .byte C9 2E F0 B9 BC 03 02 D0 B4 8D 17 C1 BD 01 02 8D ; $B3D3
    .byte 16 C1 A0 02 CA 30 0A BD 00 02 99 12 C1 88 CA 10 ; $B3E3
    .byte F6 AE 03 C0 BD 70 AC 85 1D BD 7B AC 85 1E 18 A5 ; $B3F3
    .byte 1D 69 1E 85 1D 90 02 E6 1E A0 34 78 84 01 A9 20 ; $B403
    .byte A0 3F 91 1D 88 10 FB A0 00 B9 12 C1 91 1D C8 C0 ; $B413
    .byte 06 D0 F6 A0 36 84 01 58 20 92 B8 AD 19 C0 C9 43 ; $B423
    .byte D0 03 4C A8 B4 A9 30 8D 18 C1 8D 19 C1 8D 1A C1 ; $B433
    .byte A2 CB A0 B9 20 42 81 A2 03 A0 01 A9 00 38 20 1B ; $B443
    .byte 81 A2 00 A0 02 20 1E 81 90 03 4C 2D A7 A0 02 A6 ; $B453
    .byte 1A CA BD 00 02 99 18 C1 88 CA 10 F6 AE 03 C0 BD ; $B463
    .byte 70 AC 85 1D BD 7B AC 85 1E AC 01 C0 88 98 0A 0A ; $B473
    .byte 0A 18 69 20 65 1D 85 1D 90 02 E6 1E A0 34 78 84 ; $B483
    .byte 01 A0 00 B9 18 C1 91 1D C8 C0 03 D0 F6 A0 36 84 ; $B493
    .byte 01 58 20 CF B8                                  ; $B4A3

SUB_B4A8:
    A2 D6         LDX #$D6
    A0 B9         LDY #$B9
    20 42 81      JSR $8142 ; JT_DUCK_ITEM
    A9 00         LDA #$00
    85 C6         STA $C6
    85 D4         STA $D4

SUB_B4B5:
    A9 5F         LDA #$5F
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT

SUB_B4BF:
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    F0 FB         BEQ $B4BF
    C9 03         CMP #$03
    F0 66         BEQ $B52E
    C9 59         CMP #$59
    F0 18         BEQ $B4E4
    C9 4E         CMP #$4E
    F0 14         BEQ $B4E4
    C9 88         CMP #$88
    D0 06         BNE $B4DA
    20 4A B5      JSR $B54A ; SUB_B54A
    4C BF B4      JMP $B4BF ; SUB_B4BF
    C9 8C         CMP #$8C
    D0 E1         BNE $B4BF
    20 53 B5      JSR $B553 ; SUB_B553
    4C BF B4      JMP $B4BF ; SUB_B4BF
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    85 19         STA $19
    A9 5F         LDA #$5F
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT

SUB_B4F3:
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    F0 FB         BEQ $B4F3
    C9 03         CMP #$03
    F0 32         BEQ $B52E
    C9 14         CMP #$14
    D0 10         BNE $B510
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C B5 B4      JMP $B4B5 ; SUB_B4B5
    C9 88         CMP #$88
    D0 06         BNE $B51A
    20 4A B5      JSR $B54A ; SUB_B54A
    4C F3 B4      JMP $B4F3 ; SUB_B4F3
    C9 8C         CMP #$8C
    D0 06         BNE $B524
    20 53 B5      JSR $B553 ; SUB_B553
    4C F3 B4      JMP $B4F3 ; SUB_B4F3
    C9 0D         CMP #$0D
    D0 CB         BNE $B4F3
    A5 19         LDA $19
    C9 59         CMP #$59
    F0 03         BEQ $B531
    4C 2D A7      JMP $A72D ; SUB_A72D
    20 91 A7      JSR $A791 ; SUB_A791
    AD 19 C0      LDA $C019
    C9 50         CMP #$50
    F0 67         BEQ $B5A2
    C9 26         CMP #$26
    F0 63         BEQ $B5A2
    C9 53         CMP #$53
    F0 5F         BEQ $B5A2
    C9 41         CMP #$41
    F0 5B         BEQ $B5A2
    4C 1D B8      JMP $B81D ; SUB_B81D

SUB_B54A:
    20 5C B5      JSR $B55C ; SUB_B55C
    20 03 A1      JSR $A103 ; SUB_A103
    4C 87 B5      JMP $B587 ; SUB_B587

SUB_B553:
    20 5C B5      JSR $B55C ; SUB_B55C
    20 10 A1      JSR $A110 ; SUB_A110
    4C 87 B5      JMP $B587 ; SUB_B587

SUB_B55C:
    20 91 A7      JSR $A791 ; SUB_A791
    AD 86 02      LDA $0286
    8D 1E C0      STA $C01E
    A5 D3         LDA $D3
    8D 1D C0      STA $C01D
    18            CLC 
    AD 03 C0      LDA $C003
    69 0A         ADC #$0A
    AA            TAX 
    A0 00         LDY #$00
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    AD 04 C0      LDA $C004
    8D 1C C0      STA $C01C
    AD 03 C0      LDA $C003
    8D 04 C0      STA $C004
    EE 03 C0      INC $C003
    60            RTS 

SUB_B587:
    CE 03 C0      DEC $C003
    AD 1E C0      LDA $C01E
    8D 86 02      STA $0286
    AD 1C C0      LDA $C01C
    8D 04 C0      STA $C004
    A2 18         LDX #$18
    AC 1D C0      LDY $C01D
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    4C 96 A7      JMP $A796 ; SUB_A796
    A9 01         LDA #$01
    8D 33 80      STA $8033
    A0 04         LDY #$04
    20 AD B1      JSR $B1AD ; SUB_B1AD
    90 01         BCC $B5AF
    88            DEY 
    8C C1 B5      STY $B5C1

SUB_B5B2:
    A2 C1         LDX #$C1
    A0 B5         LDY #$B5
    20 18 81      JSR $8118 ; JT_DUCKSHOOT
    B0 F7         BCS $B5B2
    20 C6 B5      JSR $B5C6 ; SUB_B5C6
    4C B2 B5      JMP $B5B2 ; SUB_B5B2
    .byte 00 78 66 72 96...   ; $B5C1 ".xfr."

SUB_B5C6:
    AD 33 80      LDA $8033
    0A            ASL A
    AA            TAX 
    BD D3 B5      LDA $B5D3,X
    48            PHA 
    BD D2 B5      LDA $B5D2,X
    48            PHA 
    60            RTS 
    .byte D9 B6 DB B5 C5 B6 0F B8 AD 28 C0 4D 29 C0 30 17 ; $B5D4
    .byte 38 A5 2D E5 2B 85 1F A5 2E E5 2C 85 20 90 08 D0 ; $B5E4
    .byte 10 A5 1F C9 03 B0 0A A2 8C A0 B9 20 45 81 4C 4B ; $B5F4
    .byte 81 A5 2B 85 1D A5 2C 85 1E A2 7B A0 B9 20 45 81 ; $B604
    .byte A0 1B 20 84 A7 20 D2 96 90 03 4C C6 B6 A2 82 A0 ; $B614
    .byte B9 20 45 81 A9 22 8D 34 80 A9 00 18 20 C9 96 AE ; $B624
    .byte 19 C0 E0 26 D0 02 A9 01 18 20 C9 96 A2 00 A0 00 ; $B634
    .byte AD 19 C0 C9 41 D0 28 A4 2E C0 08 90 1C D0 06 A6 ; $B644
    .byte 2D E0 1A 90 14 A2 05 BD 14 08 DD E5 B9 D0 0A CA ; $B654
    .byte 10 F5 A2 1B A0 08 4C 73 B6 AE 0D C0 AC 0E C0    ; $B664

SUB_B673:
    20 D0 B6      JSR $B6D0 ; SUB_B6D0
    A2 00         LDX #$00
    A0 00         LDY #$00
    2C 28 C0      BIT $C028
    30 06         BMI $B685
    AE 0D C0      LDX $C00D
    AC 0E C0      LDY $C00E
    20 D0 B6      JSR $B6D0 ; SUB_B6D0
    A5 1F         LDA $1F
    18            CLC 
    20 C9 96      JSR $96C9 ; PROTO_RECV_FRAME
    A5 20         LDA $20
    48            PHA 
    68            PLA 
    18            CLC 
    20 C9 96      JSR $96C9 ; PROTO_RECV_FRAME
    A0 00         LDY #$00
    B1 1D         LDA ($1D),Y
    48            PHA 
    E6 1D         INC $1D
    D0 02         BNE $B6A1
    E6 1E         INC $1E
    A5 1D         LDA $1D
    C5 2D         CMP $2D
    D0 EA         BNE $B691
    A5 1E         LDA $1E
    C5 2E         CMP $2E
    D0 E4         BNE $B691
    68            PLA 
    38            SEC 
    20 C9 96      JSR $96C9 ; PROTO_RECV_FRAME
    20 D2 96      JSR $96D2 ; PROTO_SEND_DATA
    08            PHP 
    20 16 B9      JSR $B916 ; SUB_B916
    28            PLP 
    B0 0A         BCS $B6C6
    68            PLA 
    68            PLA 
    A9 10         LDA #$10
    8D 33 80      STA $8033
    4C 3C B2      JMP $B23C ; SUB_B23C

SUB_B6C6:
    68            PLA 
    68            PLA 
    A9 10         LDA #$10
    8D 33 80      STA $8033
    4C 2D A7      JMP $A72D ; SUB_A72D

SUB_B6D0:
    8A            TXA 
    18            CLC 
    20 C9 96      JSR $96C9 ; PROTO_RECV_FRAME
    98            TYA 
    18            CLC 
    4C C9 96      JMP $96C9 ; PROTO_RECV_FRAME

SUB_B6DA:
    20 B6 AD      JSR $ADB6 ; SUB_ADB6
    6E 1B C0      ROR $C01B
    20 86 AC      JSR $AC86 ; SUB_AC86
    A2 C7         LDX #$C7
    A0 B7         LDY #$B7
    20 71 AD      JSR $AD71 ; SUB_AD71
    90 01         BCC $B6ED
    60            RTS 
    84 19         STY $19
    2C 28 C0      BIT $C028
    30 7A         BMI $B76E
    2C 1B C0      BIT $C01B
    10 75         BPL $B76E
    A5 19         LDA $19
    A2 1E         LDX #$1E
    A0 80         LDY #$80
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    A2 01         LDX #$01
    A0 00         LDY #$00
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    A6 2B         LDX $2B
    A4 2C         LDY $2C
    86 C3         STX $C3
    84 C4         STY $C4
    A9 00         LDA #$00
    85 93         STA $93
    85 90         STA $90
    20 F3 B7      JSR $B7F3 ; SUB_B7F3
    20 17 F8      JSR $F817
    B0 45         BCS $B764
    20 AF F5      JSR $F5AF
    A5 B7         LDA $B7
    F0 0A         BEQ $B730
    20 EA F7      JSR $F7EA
    90 0C         BCC $B737
    F0 37         BEQ $B764
    4C 04 F7      JMP $F704
    20 2C F7      JSR $F72C
    F0 2F         BEQ $B764
    B0 F6         BCS $B72D
    A5 90         LDA $90
    29 10         AND #$10
    38            SEC 
    D0 26         BNE $B764
    E0 01         CPX #$01
    F0 0A         BEQ $B74C
    E0 03         CPX #$03
    D0 DC         BNE $B722
    A0 00         LDY #$00
    A9 01         LDA #$01
    91 B2         STA ($B2),Y
    A0 01         LDY #$01
    B1 B2         LDA ($B2),Y
    8D 0D C0      STA $C00D
    C8            INY 
    B1 B2         LDA ($B2),Y
    8D 0E C0      STA $C00E
    4E 27 C0      LSR $C027
    20 79 F5      JSR $F579
    20 05 B8      JSR $B805 ; SUB_B805
    90 03         BCC $B767
    4C 05 B8      JMP $B805 ; SUB_B805
    86 2D         STX $2D
    84 2E         STY $2E
    4C C0 B7      JMP $B7C0 ; SUB_B7C0
    A9 52         LDA #$52
    A2 50         LDX #$50
    2C 28 C0      BIT $C028
    10 02         BPL $B779
    A2 53         LDX #$53
    A4 19         LDY $19
    20 5A 81      JSR $815A ; JT_FILE_DL
    B0 46         BCS $B7C6
    4E 27 C0      LSR $C027
    A5 2B         LDA $2B
    85 1D         STA $1D
    A5 2C         LDA $2C
    85 1E         STA $1E
    A2 08         LDX #$08
    20 C6 FF      JSR $FFC6 ; KERNAL_CHKIN
    2C 28 C0      BIT $C028
    30 0C         BMI $B7A1
    20 CF FF      JSR $FFCF
    8D 0D C0      STA $C00D
    20 CF FF      JSR $FFCF
    8D 0E C0      STA $C00E
    A0 00         LDY #$00
    20 CF FF      JSR $FFCF
    91 1D         STA ($1D),Y
    E6 1D         INC $1D
    D0 02         BNE $B7AE
    E6 1E         INC $1E
    A5 90         LDA $90
    F0 F1         BEQ $B7A3
    A5 1D         LDA $1D
    85 2D         STA $2D
    A5 1E         LDA $1E
    85 2E         STA $2E
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    20 5D 81      JSR $815D ; JT_CNLOAD_ERR

SUB_B7C0:
    AD 28 C0      LDA $C028
    8D 29 C0      STA $C029
    60            RTS 
    .byte 4C 4F 41 44 00 C9 0D D0 04 38 66 19 60 24 19 10 ; $B7C7
    .byte 18 18 66 19 48 8A 48 98 48 20 51 81 A2 18 A0 00 ; $B7D7
    .byte 18 20 F0 FF 68 A8 68 AA 68 4C CA F1             ; $B7E7

SUB_B7F3:
    A2 CC         LDX #$CC
    A0 B7         LDY #$B7
    8E 26 03      STX $0326
    8C 27 03      STY $0327
    18            CLC 
    66 19         ROR $19
    A9 80         LDA #$80
    4C 90 FF      JMP $FF90

SUB_B805:
    A2 CA         LDX #$CA
    A0 F1         LDY #$F1
    8E 26 03      STX $0326
    8C 27 03      STY $0327
    60            RTS 
    .byte 20 3C 81 2C 2A C0 10 F7 A9 93 4C D2 FF          ; $B810

SUB_B81D:
    38            SEC 
    6E 14 C0      ROR $C014
    20 79 A2      JSR $A279 ; SUB_A279
    A9 01         LDA #$01
    8D 33 80      STA $8033

SUB_B829:
    A2 77         LDX #$77
    A0 AF         LDY #$AF
    20 18 81      JSR $8118 ; JT_DUCKSHOOT
    B0 F7         BCS $B829
    20 38 B8      JSR $B838 ; SUB_B838
    4C 29 B8      JMP $B829 ; SUB_B829

SUB_B838:
    AD 33 80      LDA $8033
    0A            ASL A
    AA            TAX 
    BD 45 B8      LDA $B845,X
    48            PHA 
    BD 44 B8      LDA $B844,X
    48            PHA 
    60            RTS 
    .byte 4F B8 7F B8 32 81 35 81 75 A2 A2 7B A0 B9 20 45 ; $B846
    .byte 81 A9 55 A0 1B 8D 00 C1 2C 14 C0 30 02 A0 01 20 ; $B856
    .byte 84 A7 20 D2 96 B0 13 A2 82 A0 B9 20 45 81 20 75 ; $B866
    .byte B1 20 D2 96 B0 04 6E 14 C0 60 68 68 A9 10 8D 33 ; $B876
    .byte 80 2C 14 C0 10 03 4C 2D A7 4C 3C B2             ; $B886

SUB_B892:
    20 9B A7      JSR $A79B ; SUB_A79B
    20 91 A7      JSR $A791 ; SUB_A791
    A2 01         LDX #$01
    8E 02 C0      STX $C002
    20 1C A1      JSR $A11C ; SUB_A11C
    20 96 A7      JSR $A796 ; SUB_A796
    AD 03 C0      LDA $C003
    18            CLC 
    69 0A         ADC #$0A
    AA            TAX 
    A0 1F         LDY #$1F
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A9 06         LDA #$06
    8D 86 02      STA $0286
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A2 00         LDX #$00
    BD 12 C1      LDA $C112,X
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    E8            INX 
    E0 06         CPX #$06
    D0 F5         BNE $B8BC
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C A6 A7      JMP $A7A6 ; SUB_A7A6

SUB_B8CF:
    20 9B A7      JSR $A79B ; SUB_A79B
    20 91 A7      JSR $A791 ; SUB_A791
    AE 01 C0      LDX $C001
    8E 02 C0      STX $C002
    20 1C A1      JSR $A11C ; SUB_A11C
    20 96 A7      JSR $A796 ; SUB_A796
    AD 03 C0      LDA $C003
    18            CLC 
    69 0A         ADC #$0A
    AA            TAX 
    A0 1F         LDY #$1F
    18            CLC 
    20 F0 FF      JSR $FFF0 ; KERNAL_PLOT
    A9 06         LDA #$06
    8D 86 02      STA $0286
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A2 00         LDX #$00
    BD 18 C1      LDA $C118,X
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    E8            INX 
    E0 03         CPX #$03
    D0 F5         BNE $B8FD
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C A6 A7      JMP $A7A6 ; SUB_A7A6

SUB_B916:
    A2 18         LDX #$18
    BD 44 B9      LDA $B944,X
    9D 00 D4      STA $D400,X
    CA            DEX 
    10 F7         BPL $B918
    A9 21         LDA #$21
    20 3A B9      JSR $B93A ; SUB_B93A
    A9 0C         LDA #$0C
    85 1A         STA $1A
    A2 07         LDX #$07
    A0 FF         LDY #$FF
    88            DEY 
    D0 FD         BNE $B92E
    CA            DEX 
    D0 FA         BNE $B92E
    C6 1A         DEC $1A
    D0 F2         BNE $B92A
    A9 20         LDA #$20

SUB_B93A:
    8D 04 D4      STA $D404
    8D 0B D4      STA $D40B
    8D 12 D4      STA $D412
    60            RTS 
    .byte C7 70 00 00 20 01 E0 31...  ; $B944 ".p.. ..1... ..c8.. ..c8...D.000.00NO ROO"
    .byte 4D 20 4F 4E 20 54 48 49...  ; $B96C "M ON THIS PAGE.UPLOAD.UPLOADING.NOTHING "
    .byte 54 4F 20 53 45 4E 44 00...  ; $B994 "TO SEND.UPLOAD PAGE TITLE? .UPLOAD PAGE "
    .byte 54 59 50 45 3F 20 00 50...  ; $B9BC "TYPE? .PRICE? .LIFETIME? .NEW ENTRY OK? "
    .byte 00 57 4F 4D 42 41 54 31...  ; $B9E4 ".WOMBAT1.22"
    60            RTS 

SUB_B9F0:
    4E 2A C0      LSR $C02A
    AE 09 80      LDX $8009
    AC 0A 80      LDY $800A
    86 1D         STX $1D
    84 1E         STY $1E
    A0 12         LDY #$12
    B1 1D         LDA ($1D),Y
    D9 D9 B9      CMP $B9D9,Y
    D0 E9         BNE $B9EF
    C8            INY 
    C0 16         CPY #$16
    D0 F4         BNE $B9FF
    38            SEC 
    6E 2A C0      ROR $C02A
    A9 72         LDA #$72
    8D 02 80      STA $8002
    A9 12         LDA #$12
    8D 48 80      STA $8048
    A9 B4         LDA #$B4
    8D 49 80      STA $8049
    A9 03         LDA #$03
    8D 4A 80      STA $804A
    A9 4C         LDA #$4C
    A2 52         LDX #$52
    A0 8D         LDY #$8D
    8D 34 8D      STA $8D34
    8E 35 8D      STX $8D35
    8C 36 8D      STY $8D36
    A2 F5         LDX #$F5
    A0 BA         LDY #$BA
    8E B1 8F      STX $8FB1
    8C B6 8F      STY $8FB6
    A2 02         LDX #$02
    A0 BB         LDY #$BB
    8E B2 8F      STX $8FB2
    8C B7 8F      STY $8FB7
    A9 F8         LDA #$F8
    8D EC 94      STA $94EC
    AD BF 96      LDA $96BF
    D0 9F         BNE $B9EF
    AE D9 96      LDX $96D9
    D0 9A         BNE $B9EF
    AC DA 96      LDY $96DA
    C0 C8         CPY #$C8
    D0 93         BNE $B9EF
    A9 4C         LDA #$4C
    8D 26 99      STA $9926
    A2 E2         LDX #$E2
    A0 BA         LDY #$BA
    8E 27 99      STX $9927
    8C 28 99      STY $9928
    A2 9A         LDX #$9A
    A0 BA         LDY #$BA
    8E 31 9C      STX $9C31
    8C 33 9C      STY $9C33
    A9 20         LDA #$20
    8D 63 9D      STA $9D63
    A2 BD         LDX #$BD
    A0 BA         LDY #$BA
    8E 64 9D      STX $9D64
    8C 65 9D      STY $9D65
    8D E1 9F      STA $9FE1
    A2 BB         LDX #$BB
    A0 BA         LDY #$BA
    8E E2 9F      STX $9FE2
    8C E3 9F      STY $9FE3
    A2 03         LDX #$03
    8E 7C 9E      STX $9E7C
    8E 9F 9F      STX $9F9F
    60            RTS 
    .byte A2 00 20 FA 94 20 BE BA D0 11 A2 B5 A0 BA 8E 14 ; $BA9A
    .byte 03 8C 15 03 A2 03 A9 20 20 F0 94 20 7D 9C 4C 31 ; $BAAA
    .byte EA 98 24 8A                                     ; $BABA

SUB_BABE:
    29 20         AND #$20
    F0 0B         BEQ $BACD
    A9 00         LDA #$00
    8D 25 C0      STA $C025
    8D 26 C0      STA $C026
    A9 01         LDA #$01
    60            RTS 
    A9 A1         LDA #$A1
    20 50 9E      JSR $9E50
    AD 26 C0      LDA $C026
    C9 12         CMP #$12
    F0 08         BEQ $BAE1
    EE 25 C0      INC $C025
    D0 03         BNE $BAE1
    EE 26 C0      INC $C026
    60            RTS 
    .byte C9 18 F0 08 C9 00 F0 08...  ; $BAE2 ".............L..L..CARRIER LOST.TIMED OU"
    .byte 54 00 00 F3 F3 0E 1F C1...  ; $BB0A "T.......T .ONNECT...T .NY .IME\n.TO ACCES"
    .byte 53 20 54 48 45 06 08 54...  ; $BB32 "S THE..TO ACCESS THE FULL\nMAIN .IRECTORY"
    .byte 06 07 D5 53 45 52 20 C7...  ; $BB5A "...SER .UIDE\n\n * SELECT .....* SELECT .."
    .byte D4 CF 2C 0D 06 02 28 55...  ; $BB82 "..,\n..(USING CURSOR..KEY .ETURN\n..<=> KE"
    .byte 59 29 06 08 2A 20 45 4E...  ; $BBAA "Y)..* ENTER 120,\n * KEY .ETURN..KEY .ETU"
    .byte 52 4E 07 0D 04 1F C4 C9...  ; $BBD2 "RN.\n.............\n\n.EADING .: KEY F7 OR "
    .byte 46 38 20 54 4F 20 52 4F...  ; $BBFA "F8 TO ROTATE THE\n..WINDOW FOR .RICE,.UTH"
    .byte 4F 52 2C 45 54 43 2E 0D...  ; $BC22 "OR,ETC.\n\n..ELECTING .:\n .) USE CURSOR UP"
    .byte 2F 44 4F 57 4E 20 54 4F...  ; $BC4A "/DOWN TO HIGHLIGHT ITEM\n .) USE CURSOR L"
    .byte 45 46 54 2F 52 49 47 48...  ; $BC72 "EFT/RIGHT <=> TO SELECT\n..COMMAND  (EG ."
    .byte C9 D2 3D 47 45 54 20 C4...  ; $BC9A "..=GET .IRECTORY FOR\n..THE ITEM, ....=DO"
    .byte 57 4E 4C 4F 41 44 20 54...  ; $BCC2 "WNLOAD THE ITEM)\n .) KEY .ETURN.....\n..."
    .byte 07 C3 1B C0 B2 07 C0 07...  ; $BCEA ".........\n.......\n.......\n............\n."
    .byte 06 1C C2 06 07 C2 0D DD...  ; $BD12 "......\n.......\n.......\n.......\n.......\n."
    .byte 06 1C C2 06 07 C2 0D DD...  ; $BD3A "......\n.......\n.......\n.......\n.......\n."
    .byte 06 1C C2 06 07 C2 0D CA...  ; $BD62 "......\n.....<F7)(F8>......\n....COURIER\n."
    .byte 02 07 A3 06 0D 0D 06 02...  ; $BD8A "....\n\n..FROM :.\n...DATE :\n..TIME :\n\n..SU"
    .byte 42 4A 45 43 54 20 3A 0D...  ; $BDB2 "BJECT :\n\n..TO "

SUB_BDC0:
    3A            .byte $3A
    .byte 0D 0D 06 0B 3A 0D 06 0B 3A 0D 06 0B 3A 0D 06 0B ; $BDC1
    .byte 3A 0D 06 0B 3A 00 F4 F1 8E 07 0D 02 06 02 1C 43 ; $BDD1
    .byte 4F 55 52 49 45 52 0D 06 02 07 A3 06 0D 0D 06 0B ; $BDE1
    .byte 3A 0D 06 0B 3A 0D 06 0B 3A 0D 06 0B 3A 0D 06 0B ; $BDF1
    .byte 3A 00                                           ; $BE01
