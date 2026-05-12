; =================================================================
; COMPUNET REBORN — Full ROM source (converted from disassembly)
; =================================================================
; Assembler: ca65 (cc65 suite)
; Original: Compunet Terminal v1.22, Ariadne Software Ltd, 1984
; =================================================================

.segment "HEADER"

; =================================================================
; COMPUNET TERMINAL CARTRIDGE v1.22 - ANNOTATED DISASSEMBLY
; =================================================================
; ROM: 8192 bytes at $8000-$9FFF
; Mode: EXROM=0, GAME=1 (8K cartridge)
; Developer: Ariadne Software Ltd, September 1984
; Hardware: Custom 1200/75 baud modem (Viewdata chipset)
;
; Modem I/O:
;   $DE00 = Register select (write register number)
;   $DE01 = Data read/write (access selected register)
;
; Protocol: Modified X.25 with windowed flow control
; Commands: ACK, DIR, DAT, OK, ERR, FTL, COM
;
; RAM workspace:
;   $C100-$C1FF = Terminal state
;   $C200-$C2FF = Protocol state
;   $C800+      = Downloaded code extensions
;
; Main Jump Table at $8100 (32 entries):
;   [00] $81A0 = MAIN_INIT (print version, enter BASIC)
;   [01] $8355 = EDITOR (enter the page editor)
;   [02] $8D30 = MODEM_CHECK (verify modem present/responding)
;   [03] $94C1 = DISCONNECT_MSG ("Disconnected - bad line?")
;   [04] $94D5 = MODEM_REG_READ_STATUS
;   [05] $8EEF = MODEM_INIT_DOWNLOAD (linking phase)
;   [06] $8F47 = MODEM_SEND_CMD (send cmd, handle disconnect)
;   [07] $93C9 = PROTOCOL_RESET
;   [08] $93D0 = DUCKSHOOT (display/handle menu)
;   [09] $90C8 = SETUP_INPUT_PARAMS
;   [10] $90DF = INPUT_LINE
;   [11] $89D0 = FRAME_BUF_READ
;   [12] $89E2 = FRAME_BUF_WRITE
;   [13] $8ABE = DISK_LOAD
;   [14] $8AEB = DISK_SAVE
;   [15] $85E4 = SCREEN_DRAW (print frame)
;   [16] $849B = NEW_PAGE
;   [17] $8446 = LAST_PAGE
;   [18] $8477 = NEXT_PAGE
;   [19] $8500 = GET_FILE
;   [20] $869E = COMMAND_INPUT
;   [21] $90B7 = PRINT_STRING
;   [22] $9093 = DUCKSHOOT_ITEM
;   [23] $907B = STATUS_BAR
;   [24] $8FFB = PRESS_ANY_KEY
;   [25] $9002 = CLEAR_STATUS
;   [26] $901E = INPUT_PROMPT
;   [27] $938B = WHITE_BAR
;   [28] $94A8 = MODEM_STATUS_CHECK
;   [29] $9171 = CNSAVE
;   [30] $91B2 = FILE_DOWNLOAD
;   [31] $92CD = CNLOAD_DISK_ERROR
;
; Protocol command bytes: ACK=$20 DIR=$21 DAT=$22 OK=$23 ERR=$24 FTL=$25 COM=$26
; =================================================================

    * = $8000


; --- Cartridge header ---
    .byte $60, $81, $5E, $FE, $C3, $C2, $CD, $38, $30    ; $8000 `.^....80
    .byte $7C, $80, $A4, $80, $00, $00, $00, $00, $80, $04, $01, $06, $00, $E0, $04, $E0    ; $8009 |...............
    .byte $00, $E0, $40, $30, $3A, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00    ; $8019 ..@0:...........
    .byte $00, $00, $00, $00, $00, $00, $00, $00, $00    ; $8029 .........
    .byte $53, $0D, $43, $00, $02, $A0, $00, $09, $08, $14, $08, $11, $07, $36, $34, $31    ; $8032 S\nC..........641
    .byte $32, $03, $14, $3E, $1A, $00, $03, $24, $01, $FF, $FF, $2A, $43, $4F, $4E, $1D    ; $8042 2..>...$...*CON.
    .byte $43, $20, $43, $4E, $45, $54, $0D, $33, $32, $32, $35, $30, $30, $2F, $31, $30    ; $8052 C CNET\n322500/10
    .byte $30, $0D, $41, $44, $50, $0D, $4E, $4F, $0D, $52, $55, $4E, $0D, $00    ; $8062 0\nADP\nNO\nRUN\n.
    .byte $00, $00, $00, $00, $00, $00, $00, $00, $00, $00    ; $8070 ..........

; --- Version strings ---
    .byte $0D, $20, $43, $4F, $4D, $50, $55, $4E, $45, $54, $20, $54, $45, $52, $4D, $49    ; $807A \n COMPUNET TERMI
    .byte $4E, $41, $4C, $20, $31, $2E, $32, $32, $0D, $00, $20, $53, $45, $50, $54, $45    ; $808A NAL 1.22\n. SEPTE
    .byte $4D, $42, $45, $52, $20, $31, $39, $38, $34, $20, $41, $52, $49, $41, $44, $4E    ; $809A MBER 1984 ARIADN
    .byte $45, $20, $53, $4F, $46, $54, $57, $41, $52, $45, $20, $4C, $54, $44, $2E, $0D    ; $80AA E SOFTWARE LTD.\n
    .byte $0D, $00    ; $80BA \n.
    .byte $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00    ; $80BC ................
    .byte $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00    ; $80CC ................
    .byte $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00    ; $80DC ................
    .byte $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00, $00    ; $80EC ................
    .byte $00, $00, $00, $00    ; $80FC ....
    .byte $4C, $A0, $81, $4C, $55, $83, $4C, $30, $8D, $4C, $C1, $94, $4C, $D5, $94, $4C    ; $8100 L..LU.L0.L..L..L
    .byte $EF, $8E, $4C, $47, $8F, $4C, $C9, $93, $4C, $D0, $93, $4C, $C8, $90, $4C, $DF    ; $8110 ..LG.L..L..L..L.
    .byte $90, $4C, $D0, $89, $4C, $E2, $89, $4C, $BE, $8A, $4C, $EB, $8A, $4C, $E4, $85    ; $8120 .L..L..L..L..L..
    .byte $4C, $9B, $84, $4C, $46, $84, $4C, $77, $84, $4C, $00, $85, $4C, $9E, $86, $4C    ; $8130 L..LF.Lw.L..L..L
    .byte $B7, $90, $4C, $93, $90, $4C, $7B, $90, $4C, $FB, $8F, $4C, $02, $90, $4C, $1E    ; $8140 ..L..L{.L..L..L.
    .byte $90, $4C, $8B, $93, $4C, $A8, $94, $4C, $71, $91, $4C, $B2, $91, $4C, $CD, $92    ; $8150 .L..L..Lq.L..L..

; ============================================================
; COLD_START
; ============================================================
COLD_START:
; Initialize C64 hardware and BASIC, then install command extensions
    JSR $FF84                           ; KERNAL_IOINIT
    JSR $FF87                           ; KERNAL_RAMTAS
    JSR $FF8A                           ; KERNAL_RESTOR
    JSR $FF81                           ; KERNAL_CINT
    CLI
    LDA #$01
    STA $D021                           ; VIC_BGCOL0 = white
    JSR $E453                           ; BASIC_RUNC
    JSR $E3BF                           ; BASIC_MAIN
    JSR $E422                           ; BASIC_LINKPRG
; Copy 5-byte patch to $E000 (BASIC warm start vector area)
; This redirects BASIC's command input to our parser at $81BC
    LDX #$04
    LDA $81B7,X
    STA $E000,X
    DEX
    BPL $817D
; Copy ROM to RAM at $8000-$9FFF (so it can be banked out later)
    LDY #$00
    STY $1D
    LDA #$80
    STA $1E
    LDA ($1D),Y
    STA ($1D),Y
    INY
    BNE $818E
    INC $1E
    LDA $1E
    CMP #$A0
    BNE $818E
; Initialize terminal state
    JSR $8335

; ============================================================
; MAIN_INIT
; Called after COLD_START completes initialization.
; Prints version string, installs BASIC extension vector,
; then drops into BASIC READY prompt.
; User types CONNECT, EDITOR, CNLOAD, CNSAVE, or HELP.
; ============================================================
MAIN_INIT:
; Print " COMPUNET TERMINAL 1.22" version string
    LDX #$7A
    LDY #$80
    JSR $90B7                           ; PRINT_STRING
; Install our command parser at $0302/$0303 (BASIC IGONE vector)
    LDX #$BC
    LDY #$81
    STX $0302
    STY $0303
; Reset stack and enter BASIC
    LDX #$FB
    TXS
    JMP $A474                           ; BASIC_READY

; --- BASIC stub bytes ---
; These 5 bytes are copied to $E000 to patch BASIC's warm start
; They form a JMP to the command parser at $81BC
    .byte $00, $F6, $F1, $0E, $00    ; $81B7 .....

; ============================================================
; BASIC_CMD_PARSER - Intercepts BASIC input to handle custom commands
; Commands: EDITOR, CONNECT, CNLOAD, CNSAVE, HELP
; ============================================================
    JSR $A560
    STX $7A
    STY $7B
    JSR $0073
    TAX
    BEQ $81BC
    LDX #$FF
    STX $3A
    BCS $81D2
    JMP $A49C
; Compare input buffer against command table at $8249
    LDX $7A
    LDY #$00
    STY $1A
    LDA $0200,X
    SEC
    SBC $8249,Y
    BNE $81E5
    INX
    INY
    BNE $81D8
    CMP #$80
    BEQ $81EA
    CLC
    LDA $1A
    BCS $8200
    DEY
    LDX $7A
    INC $1A
    CMP #$05
    BEQ $8237
    INY
    LDA $8249,Y
    BPL $81F7
    INY
    BNE $81D8
; Command matched - save screen state and dispatch
    LDX $D020                           ; VIC_BORDER
    STX $C151                           ; workspace
    LDX $D021                           ; VIC_BGCOL0
    STX $C152                           ; workspace
    LDX $0286
    STX $C153                           ; workspace
    LDX #$36
    STX $01
    JSR $823E
; Restore screen state after command returns
    LDA $C151                           ; workspace
    STA $D020                           ; VIC_BORDER
    LDA $C152                           ; workspace
    STA $D021                           ; VIC_BGCOL0
    LDA $C153                           ; workspace
    STA $0286
    LDX #$37
    STX $01
    LDA #$09
    JSR $FFD2                           ; KERNAL_CHROUT
    JMP $A474                           ; BASIC_READY
; SYNTAX ERROR handler
    LDX #$FF
    LDY #$01
    JMP $A486
; Dispatch via address table at $8269 (RTS trick)
    ASL A
    TAY
    LDA $826A,Y
    PHA
    LDA $8269,Y
    PHA
    RTS

; --- BASIC Command Strings (high bit set on last char) ---
; 0: EDITOR  1: CONNECT  2: CNLOAD  3: CNSAVE  4: HELP
    .byte $45, $44, $49, $54, $4F, $D2, $43, $4F, $4E, $4E, $45, $43, $D4, $43, $4E    ; $8249 EDITO.CONNEC.CN
    JMP $414F
    .byte $C4, $43, $4E, $53, $41, $56, $C5    ; $825B .CNSAV.
    PHA
    EOR $4C
    BNE $82B6
    LSR $C6
    JMP $2F83
    .byte $8D, $AB, $82, $A8, $82, $74, $82, $9D, $82    ; $826C .....t...
    LDX #$7A
    LDY #$80
    JSR $90B7                           ; PRINT_STRING
    LDX #$94
    LDY #$80
    JSR $90B7                           ; PRINT_STRING
    LDX #$06
    LDY #$00
    JSR $906A
    LDA $8249,Y
    PHP
    AND #$7F
    JSR $FFD2                           ; KERNAL_CHROUT
    INY
    PLP
    BPL $828A
    JSR $906E
    DEX
    BNE $8287
    RTS
    LDX #$83
    LDY #$A4
    STX $0302
    STY $0303
    RTS
    SEC
    BCS $82AD
    CLC
    ROR $19
    JSR $92AD
    BCS $82C3
    LDA #$08
    PHA
    BIT $19
    BPL $82C6
    LDA #$07
    LDX #$2E
    LDY #$83
    BNE $82CC
    LDA #$01
    PHA
    LDA #$04
    LDX #$31
    LDY #$83
    JSR $FFBD                           ; KERNAL_SETNAM
    PLA
    TAX
    LDY #$01
    JSR $FFBA                           ; KERNAL_SETLFS
    LDX #$F0
    LDY #$9F
    STX $1D
    STY $1E
    BIT $19
    BPL $82F4
    LDA #$1D
    LDX $8036
    LDY $8037
    JSR $FFD8                           ; KERNAL_SAVE
    JSR $935F
    BNE $8317
    BEQ $832B
    JSR $8335
    LDA #$00
    JSR $FFD5                           ; KERNAL_LOAD
    BCC $8304
    JSR $935F
    JMP $830F
    STX $8036
    STY $8037
    JSR $935F
    BEQ $832B
    JSR $8335
    BIT $C156                           ; workspace
    BMI $832B
    JSR $906E
    LDX #$53
    LDY #$93
    JSR $90B7                           ; PRINT_STRING
    LDX #$00
    LDY #$02
    JSR $90B7                           ; PRINT_STRING
    JSR $906E
    JMP $92E0
    .byte $40, $30, $3A, $43, $4E, $45, $54    ; $832E @0:CNET
    LDA #$00
    STA $9FF0
    LDA #$30
    STA $A000
    STA $A001
    LDX #$02
    LDY #$A0
    STX $8036
    STY $8037
    RTS
    .byte $A9, $FF, $8D, $4B, $80, $8D    ; $834D ...K..
    JMP $2080
    .byte $DC, $89    ; $8356 ..
    LDA $804B
    STA $1D
    LDA $804C
    STA $1E
    LDY #$00
    LDX #$01
    ASL $1E
    ROL $1D
    BCC $8382
    CPX #$0E
    BNE $8377
    JSR $874B
    LDX #$0E
    BCS $8382
    TXA
    STA $C175,Y
    LDA $83FD,X
    STA $C166,Y
    INY
    INX
    CPX #$0F
    BNE $8366
    STY $C165                           ; workspace
    LDX #$AA
    LDY #$83
    JSR $93C9                           ; PROTOCOL_RESET
    LDA #$01
    STA $8033
    LDA #$08
    JSR $FFD2                           ; KERNAL_CHROUT
    LDX #$65
    LDY #$C1
    JSR $93D0                           ; PROTOCOL_CLEANUP
    BCS $8396
    JSR $840C
    JMP $8396

; --- Duckshoot menu text ---
    .byte $20, $48, $45, $4C, $50, $20, $20, $45, $44, $49, $54, $20, $20, $4C, $41, $53    ; $83AA  HELP  EDIT  LAS
    .byte $54, $20, $20, $4E, $45, $58, $54, $20, $20, $4E, $45, $57, $20, $20, $20, $43    ; $83BA T  NEXT  NEW   C
    .byte $4F, $50, $59, $20, $45, $52, $41, $53, $45, $20, $20, $47, $45, $54, $20, $20    ; $83CA OPY ERASE  GET
    .byte $20, $50, $55, $54, $20, $20, $53, $54, $4F, $52, $45, $20, $50, $52, $49, $4E    ; $83DA  PUT  STORE PRIN
    .byte $54, $20, $20, $46, $52, $45, $45, $20, $20, $44, $4F, $53, $20, $20, $52, $45    ; $83EA T  FREE  DOS  RE
    .byte $54, $55, $52, $4E, $00, $06, $0C, $12, $18, $1E    ; $83FA TURN......
    .byte $24, $2A, $30, $36, $3C, $42, $4E    ; $8404 $*06<BN
    PHA
    LDX $8033
    LDA $C174,X
    ASL A
    TAX
    LDA $841C,X
    PHA
    LDA $841B,X
    PHA
    RTS
    .byte $38, $84, $5F, $87, $45, $84, $76, $84, $94, $84, $CA, $84, $D3, $84, $FF, $84    ; $841D 8._.E.v.........
    .byte $40    ; $842D @
    STA $7F
    STA $DD
    STA $9B
    89            .byte $89
    .byte $5A, $87, $9D    ; $8435 Z..
    STX $A2
    89            .byte $89
    LDY #$95
    JSR $89E2                           ; FRAME_BUF_WRITE
    JSR $8FFB                           ; WAIT_KEYPRESS
    JMP $89DC

; ============================================================
; KEYBOARD_SCAN
; ============================================================
KEYBOARD_SCAN:
    LDX $8019
    LDY $801A
    CPX $8015
    BNE $8457
    CPY $8016
    BNE $8457
    RTS
    STX $1D
    STY $1E
    LDA $1D
    BNE $8461
    DEC $1E
    DEC $1D
    JSR $8CB6
    CMP #$00
    BNE $845B
    LDA $1D
    STA $8019
    LDA $1E
    STA $801A
    JMP $89DC

; ============================================================
; KEY_DISPATCH
; ============================================================
KEY_DISPATCH:
    JSR $8CAB
    JSR $8CC5
    LDX $1D
    LDY $1E
    CPX $8017
    BNE $848C
    CPY $8018
    BNE $848C
    RTS
    STX $8019
    STY $801A
    JMP $89DC
    JSR $849B                           ; INPUT_HANDLER
    JMP $89DC

; ============================================================
; INPUT_HANDLER
; ============================================================
INPUT_HANDLER:
    CLC
    LDA $8017
    STA $8019
    STA $1D
    ADC #$04
    TAX
    LDA $8018
    STA $801A
    STA $1E
    ADC #$00
    BCC $84B9
    JSR $8C40
    JMP $849B                           ; INPUT_HANDLER
    STX $8017
    STA $8018
    JSR $8C05
    TXA
    JSR $8BC0
    LDA #$00
    JMP $8BC0
    JSR $849B                           ; INPUT_HANDLER
    JSR $8ABE                           ; DISK_LOAD
    JMP $89DC
    LDX $8019
    LDY $801A
    JSR $8C70
    LDX $8019
    LDY $801A
    CPX $8017
    BNE $84ED
    CPY $8018
    BEQ $84F0
    JMP $89DC
    CPX $8015
    BNE $84FA
    CPY $8016
    BEQ $84FD
    JMP $8446                           ; KEYBOARD_SCAN
    JMP $8495

; ============================================================
; COMMAND_EXEC
; ============================================================
COMMAND_EXEC:
    LDX #$3D
    LDY #$85
    JSR $9093                           ; CURSOR_HOME
    LDA #$52
    LDX #$53
    JSR $9171                           ; FILE_UPLOAD
    BCS $8576
    JSR $8495
    LDA #$8C
    STA $C140                           ; workspace
    LDA #$8A
    STA $C141                           ; workspace
    LDX #$08
    JSR $FFC6                           ; KERNAL_CHKIN
    BCS $8537
    JSR $89F0
    BCS $8537
    JSR $FFCC                           ; KERNAL_CLRCHN
    JSR $8ABE                           ; DISK_LOAD
    LDA $C15D                           ; workspace
    BEQ $8510
    JMP $92CD                           ; FRAME_STORE
    JSR $FFE7
    JMP $84D4
    .byte $47, $45, $54, $00    ; $853D GET.
    LDX #$7C
    LDY #$85
    JSR $9093                           ; CURSOR_HOME
    LDA #$57
    LDX #$53
    JSR $9171                           ; FILE_UPLOAD
    BCS $8576
    JSR $8CAB
    LDX #$08
    JSR $FFC9                           ; KERNAL_CHKOUT
    BCS $8576
    JSR $85D4
    JSR $FFD2                           ; KERNAL_CHROUT
    BCS $8576
    INC $1D
    BNE $8569
    INC $1E
    JSR $8CB6
    CMP #$00
    BNE $855E
    JSR $FFCC                           ; KERNAL_CLRCHN
    JMP $92CD                           ; FRAME_STORE
    JSR $FFE7
    JMP $89DC
    .byte $50, $55, $54, $00    ; $857C PUT.
    LDX #$CE
    LDY #$85
    JSR $9093                           ; CURSOR_HOME
    LDA #$57
    LDX #$53
    JSR $9171                           ; FILE_UPLOAD
    BCS $8576
    LDX $8015
    LDY $8016
    STX $1D
    STY $1E
    LDX #$08
    JSR $FFC9                           ; KERNAL_CHKOUT
    BCS $8576
    JSR $85D4
    JSR $FFD2                           ; KERNAL_CHROUT
    BCS $8576
    INC $1D
    BNE $85AF
    INC $1E
    JSR $8CB6
    CMP #$00
    BNE $85A4
    LDX $1D
    CPX $8017
    BNE $85C4
    LDX $1E
    CPX $8018
    BEQ $8570
    JSR $85D4
    JSR $FFD2                           ; KERNAL_CHROUT
    BCS $8576
    BCC $85A4
    53            .byte $53
    .byte $54, $4F, $52, $45, $00    ; $85CF TORE.
    LDA #$00
    BIT $C156                           ; workspace
    BPL $85DD
    LDA #$01
    RTS
    LDX $8019
    LDY $801A

; ============================================================
; SCREEN_DRAW
; ============================================================
SCREEN_DRAW:
    STX $1D
    STY $1E
    LDA #$81
    STA $C140                           ; workspace
    LDA #$8A
    STA $C141                           ; workspace
    JSR $8A7E
    JSR $8A7E
    JSR $8A7E
    LDA #$00
    STA $C15F                           ; workspace
    JSR $8A4B
    STA $C15E                           ; workspace
    LDA #$04
    TAX
    LDY #$00
    JSR $FFBA                           ; KERNAL_SETLFS
    LDA #$00
    JSR $FFBD                           ; KERNAL_SETNAM
    JSR $FFC0                           ; KERNAL_OPEN
    LDX #$04
    JSR $FFC9                           ; KERNAL_CHKOUT
    BCS $8677
    JSR $FFE4                           ; KERNAL_GETIN
    CMP #$03
    BEQ $8674
    JSR $8A4B
    CMP #$00
    BEQ $8674
    CMP #$0D
    BNE $8637
    JSR $FFD2                           ; KERNAL_CHROUT
    BCS $8677
    JMP $861D
    PHA
    LDX #$14
    JSR $906A
    BCS $8677
    DEX
    BNE $863A
    BIT $C15E                           ; workspace
    BMI $864E
    LDA #$11
    JSR $FFD2                           ; KERNAL_CHROUT
    BCS $8677
    PLA
    BNE $8663
    JSR $8A4B
    CMP #$00
    BEQ $8674
    CMP #$0D
    BNE $8663
    JSR $FFD2                           ; KERNAL_CHROUT
    BCS $8677
    BCC $861D
    LDX #$0F
    CMP $8BF5,X
    BEQ $8651
    DEX
    BPL $8665
    JSR $FFD2                           ; KERNAL_CHROUT
    BCS $8677
    BCC $8651
    JSR $906E
    PHP
    JSR $FFCC                           ; KERNAL_CLRCHN
    LDA #$04
    JSR $FFC3                           ; KERNAL_CLOSE
    PLP
    BCC $86A3
    LDX #$90
    LDY #$86
    JSR $907B                           ; PRINT_STATUS_MSG
    JSR $9002                           ; CLEAR_STATUS
    JMP $938B                           ; PROTOCOL_STATE_INIT
    .byte $50, $52, $49, $4E, $54, $45, $52    ; $8690 PRINTER
    JSR $5245
    52            .byte $52
    .byte $4F, $52, $00    ; $869B OR.

; ============================================================
; FILE_OPS
; ============================================================
FILE_OPS:
    JSR $874B
    BCC $86A4
    RTS
    LDA $8013
    STA $D021                           ; VIC_BGCOL0
    LDA $8014
    STA $0286
    LDX #$2A
    LDY #$87
    JSR $90B7                           ; PRINT_STRING
    LDX $7A
    LDY $7B
    STX $C161                           ; workspace
    STY $C162                           ; workspace
    LDA #$40
    JSR $FFD2                           ; KERNAL_CHROUT
    LDX #$26
    LDA #$00
    TAY
    CLC
    JSR $90C8                           ; SETUP_INPUT_PARAMS
    LDX #$00
    LDY #$02
    STX $7A
    STY $7B
    INX
    JSR $90DF                           ; INPUT_LINE
    BCC $86EA
    LDX $C161                           ; workspace
    LDY $C162                           ; workspace
    STX $7A
    STY $7B
    JMP $89DC
    JSR $906E
    LDA #$00
    LDY $1A
    STA $0201,Y
    LDX $0314
    LDY $0315
    STX $C163                           ; workspace
    STY $C164                           ; workspace
    LDX #$31
    LDY #$EA
    SEI
    STX $0314
    STY $0315
    CLI
    LDX #$37
    STX $01
    LDA #$40
    JSR $CD10
    LDX #$36
    STX $01
    LDX $C163                           ; workspace
    LDY $C164                           ; workspace
    SEI
    STX $0314
    STY $0315
    CLI
    JMP $86C1
    .byte $93    ; $872A .
    ASL $1192
    CMP #$4E
    BVC $8787
    54            .byte $54
    JSR $CFC4
    D3            .byte $D3
    JSR $4F43
    EOR $414D
    LSR $5344
    JSR $524F
    JSR $D4D3
    CF            .byte $CF
    .byte $D0, $0D, $0D, $00    ; $8747 ....
    LDX #$02
    LDA $7C,X
    CMP $CCDE,X
    BNE $8759
    DEX
    BPL $874D
    CLC
    RTS
    SEC
    RTS
    .byte $68, $68    ; $875B hh
    JMP $9062
    LDA #$09
    JSR $FFD2                           ; KERNAL_CHROUT
    LDA #$02
    STA $0286
    LDX #$19
    LDA $D9,X
    ORA #$80
    STA $D9,X
    DEX
    BPL $876C
    CLC
    ROR $C15B                           ; workspace
    LDX #$9B
    LDY #$88
    JSR $907B                           ; PRINT_STATUS_MSG
    JSR $9066
    LDA #$00
    STA $D4
    STA $D8
    JSR $8C26
    LDA $D6
    CMP #$18
    BNE $8797
    LDA #$91
    JSR $FFD2                           ; KERNAL_CHROUT
    LDY $D3
    LDA ($D1),Y
    STA $C157                           ; workspace
    JSR $EA24
    LDA ($F3),Y
    BIT $C15B                           ; workspace
    BPL $87AB
    LDA $0286
    STA $C158                           ; workspace
    LDA #$FF
    STA $C159                           ; workspace
    STA $C15A                           ; workspace
    JSR $FFE4                           ; KERNAL_GETIN
    BNE $87E5
    INC $C159                           ; workspace
    BNE $87B6
    INC $C15A                           ; workspace
    BNE $87B6
    LDA #$E0
    STA $C15A                           ; workspace
    LDY $D3
    LDA ($D1),Y
    EOR #$80
    STA ($D1),Y
    LDX $0286
    TXA
    EOR ($F3),Y
    AND #$0F
    BNE $87DF
    LDX $C158                           ; workspace
    TXA
    STA ($F3),Y
    JMP $87B6
    PHA
    LDA $C157                           ; workspace
    LDY $D3
    STA ($D1),Y
    LDA $C158                           ; workspace
    STA ($F3),Y
    PLA
    CMP #$03
    BNE $886A
    JSR $938B                           ; PROTOCOL_STATE_INIT
    LDX $8019
    LDY $801A
    JSR $8C70
    LDX $8017
    LDY $8018
    JSR $8AEB                           ; DISK_SAVE
    LDX $8017
    LDY $8018
    STX $1F
    STY $20
    LDA $1D
    BNE $881C
    DEC $1E
    DEC $1D
    LDA $1D
    STA $8017
    LDA $1E
    STA $8018
    CPX $8019
    BNE $8832
    CPY $801A
    BEQ $8869
    LDY #$00
    LDX #$34
    SEI
    STX $01
    LDA ($1F),Y
    LDX #$36
    STX $01
    CLI
    STA ($1D),Y
    LDA $1D
    BNE $8848
    DEC $1E
    DEC $1D
    LDA $1F
    BNE $8850
    DEC $20
    DEC $1F
    LDX $1F
    CPX $8019
    BNE $8834
    LDX $20
    CPX $801A
    BNE $8834
    LDX $8019
    LDY $801A
    JSR $8AEB                           ; DISK_SAVE
    RTS
    CMP #$83
    BNE $8871
    JMP $89DC
    CMP #$85
    BCC $888F
    CMP #$8D
    BCC $88A8
    CMP #$93
    BNE $8883
    JSR $FFD2                           ; KERNAL_CHROUT
    JMP $8779
    CMP #$94
    BNE $888F
    LDA #$20
    LDY #$27
    STA ($D1),Y
    LDA #$94
    CMP #$A0
    BNE $8895
    LDA #$20
    JSR $FFD2                           ; KERNAL_CHROUT
    JMP $8783
    .byte $53, $54, $4F, $50    ; $889B STOP
    JSR $4F54
    JSR $5845
    EOR #$54
    BRK
    SEC
    SBC #$85
    ASL A
    TAX
    JSR $88B3
    JMP $8783
    LDA $88BD,X
    PHA
    LDA $88BC,X
    PHA
    RTS
    .byte $BA, $88, $F0, $88, $DE, $88, $CB, $88, $BA, $88, $3D, $89, $E7, $88, $D1, $88    ; $88BC ..........=.....
    .byte $EE, $21, $D0    ; $88CC .!.
    JMP $88D5
    .byte $EE    ; $88D2 .
    JSR $20D0
    8B            .byte $8B
    .byte $93    ; $88D7 .
    LDX #$9B
    LDY #$88
    JMP $907B                           ; PRINT_STATUS_MSG
    LDA $028A
    EOR #$80
    STA $028A
    RTS
    LDA $C15B                           ; workspace
    EOR #$80
    STA $C15B                           ; workspace
    RTS
    .byte $A6, $D6, $F0    ; $88F1 ...
    PHA
    LDA $D1
    STA $1D
    SEC
    SBC #$28
    STA $D1
    STA $1F
    LDA $D2
    STA $1E
    SBC #$00
    STA $D2
    STA $20
    DEC $D6
    JSR $8983
    LDY #$27
    LDA ($1D),Y
    STA ($1F),Y
    LDA ($21),Y
    STA ($23),Y
    DEY
    BPL $8911
    INX
    CPX #$18
    BEQ $8934
    CLC
    LDA $1D
    STA $1F
    ADC #$28
    STA $1D
    LDA $1E
    STA $20
    BCC $890C
    INC $1E
    BCS $890C
    LDA #$20
    LDY #$27
    STA ($1D),Y
    DEY
    BPL $8938
    RTS
    LDA #$98
    STA $1D
    LDA #$07
    STA $1E
    LDA #$70
    STA $1F
    LDA #$07
    STA $20
    LDX #$17
    CPX $D6
    BNE $895E
    LDA #$20
    LDY #$27
    STA ($1D),Y
    DEY
    BPL $8958
    RTS
    JSR $8983
    LDY #$27
    LDA ($1F),Y
    STA ($1D),Y
    LDA ($23),Y
    STA ($21),Y
    DEY
    BPL $8963
    LDA $1F
    STA $1D
    SEC
    SBC #$28
    STA $1F
    LDA $20
    STA $1E
    SBC #$00
    STA $20
    DEX
    JMP $8950
    LDA $1D
    STA $21
    LDA $1F
    STA $23
    LDA $1E
    AND #$03
    ORA #$D8
    STA $22
    LDA $20
    AND #$03
    ORA #$D8
    STA $24
    RTS
    LDX #$CF
    LDY #$89
    JSR $9093                           ; CURSOR_HOME
    SEC
    LDA #$00
    SBC $8017
    TAX
    LDA #$00
    SBC $8018
    LDY #$37
    STY $01
    JSR $BDCD
    LDY #$36
    STY $01
    LDX #$C4
    LDY #$89
    JSR $90B7                           ; PRINT_STRING
    JMP $9002                           ; CLEAR_STATUS
    JSR $4843
    EOR ($52,X)
    53            .byte $53
    JSR $5246
    EOR $45
    BRK

; ============================================================
; FRAME_BUF_READ
; ============================================================
FRAME_BUF_READ:
    LDA #$AD
    STA $C140                           ; workspace
    LDA #$8A
    STA $C141                           ; workspace
    BNE $89F0
    LDX $8019
    LDY $801A

; ============================================================
; FRAME_BUF_WRITE
; ============================================================
FRAME_BUF_WRITE:
    STX $1D
    STY $1E
    LDA #$81
    STA $C140                           ; workspace
    LDA #$8A
    STA $C141                           ; workspace
    LDA #$00
    STA $C15D                           ; workspace
    JSR $8A7E
    BCS $8A3B
    STA $8035
    JSR $9050
    JSR $8A7E
    BCS $8A3B
    STA $D020                           ; VIC_BORDER
    JSR $938B                           ; PROTOCOL_STATE_INIT
    JSR $8A7E
    BCS $8A3B
    STA $D021                           ; VIC_BGCOL0
    LDA #$00
    STA $C15F                           ; workspace
    JSR $8A4B
    BCS $8A3B
    CMP #$00
    BEQ $8A37
    CMP #$0D
    BNE $8A31
    JSR $8C26
    BCC $8A2F
    LDA #$91
    JSR $FFD2                           ; KERNAL_CHROUT
    LDA #$0D
    JSR $FFD2                           ; KERNAL_CHROUT
    JMP $8A18
    JSR $8C26
    CLC
    LDA #$00
    STA $D4
    RTS
    .byte $A0, $00, $91, $D1, $E6, $D1, $D0, $02, $E6, $D2, $60    ; $8A40 ..........`
    LDA $C15F                           ; workspace
    BEQ $8A58
    DEC $C15F                           ; workspace
    LDA $C160                           ; workspace
    CLC
    RTS
    JSR $8A7E
    BCS $8A7D
    CMP #$06
    BNE $8A65
    LDA #$20
    BNE $8A6E
    CMP #$07
    BNE $8A7C
    JSR $8A7E
    BCS $8A7D
    STA $C160                           ; workspace
    JSR $8A7E
    BCS $8A7D
    STA $C15F                           ; workspace
    LDA $C160                           ; workspace
    CLC
    RTS
    JMP ($C140)
    JSR $8CB6
    INC $1D
    BNE $8A8A
    INC $1E
    CLC
    RTS
    LDX $C15D                           ; workspace
    BEQ $8A94
    LDA #$00
    RTS
    LDX #$08
    JSR $FFC6                           ; KERNAL_CHKIN
    BCS $8AAC
    JSR $FFCF                           ; KERNAL_CHRIN
    BCS $8AAC
    CMP #$01
    BNE $8AA6
    LDA #$00
    LDX $90
    STX $C15D                           ; workspace
    CLC
    RTS
    .byte $2C, $5D, $C1, $10, $04    ; $8AAD ,]...
    LDA #$00
    CLC
    RTS
    JSR $96CC
    ROR $C15D                           ; workspace
    CLC
    RTS

; ============================================================
; DISK_LOAD
; ============================================================
DISK_LOAD:
    LDX $8019
    LDY $801A
    JSR $8C70
    LDX $8017
    LDY $8018
    JSR $8AEB                           ; DISK_SAVE
    LDX $8017
    LDY $8018
    STX $8019
    STY $801A
    LDY $1E
    LDX $1D
    BNE $8AE3
    DEY
    DEX
    STX $8017
    STY $8018
    RTS

; ============================================================
; DISK_SAVE
; ============================================================
DISK_SAVE:
    STX $1D
    STY $1E
    JSR $8C05
    STX $19
    LDA #$00
    STA $1A
    LDA #$FF
    STA $C158                           ; workspace
    JSR $9066
    JSR $EA24
    LDA #$12
    STA $C15C                           ; workspace
    LDY #$00
    LDA ($D1),Y
    CMP #$20
    BNE $8B17
    INY
    CPY #$28
    BNE $8B0A
    BEQ $8B69
    CPY #$00
    BEQ $8B27
    STY $D3
    LDA #$20
    JSR $8B7D
    LDY $D3
    DEY
    STY $1A
    LDY $D3
    LDA ($D1),Y
    PHA
    CMP #$20
    BEQ $8B45
    LDA ($F3),Y
    AND #$0F
    CMP $C158                           ; workspace
    BEQ $8B43
    STA $C158                           ; workspace
    TAY
    LDA $8BF5,Y
    JSR $8B7D
    PLA
    PHA
    EOR $C15C                           ; workspace
    BPL $8B58
    LDA $C15C                           ; workspace
    JSR $8B7D
    LDA $C15C                           ; workspace
    EOR #$80
    STA $C15C                           ; workspace
    PLA
    JSR $94A8                           ; MODEM_STATUS_CHECK
    JSR $8B7D
    LDY $D3
    CPY #$27
    BEQ $8B69
    INC $D3
    BNE $8B27
    JSR $906E
    JSR $8B7D
    LDA $D6
    CMP #$18
    BEQ $8B78
    JMP $8B00
    LDA #$00
    JMP $8BC0
    CMP $19
    BNE $8B84
    INC $1A
    RTS
    LDX $19
    STA $19
    CMP #$0D
    BNE $8B95
    CPX #$20
    BNE $8B95
    BIT $C15C                           ; workspace
    BPL $8BBB
    TXA
    LDX $1A
    CPX #$02
    BCS $8BA4
    JSR $8BC0
    DEX
    BPL $8B9C
    BMI $8BBB
    CMP #$20
    BNE $8BAC
    LDA #$06
    BNE $8BB3
    TAX
    LDA #$07
    JSR $8BC0
    TXA
    JSR $8BC0
    LDA $1A
    JSR $8BC0
    LDA #$00
    STA $1A
    RTS
    LDY #$00
    STA ($1D),Y
    INC $1D
    BEQ $8BC9
    RTS
    INC $1E
    BEQ $8BCE
    RTS
    PHA
    TXA
    PHA
    JSR $8C40
    JSR $8CB6
    LDY #$00
    STA ($1F),Y
    INC $1F
    BNE $8BE1
    INC $20
    INC $1D
    BNE $8BD4
    INC $1E
    BNE $8BD4
    LDA $1F
    STA $1D
    LDA $20
    STA $1E
    PLA
    TAX
    PLA
    RTS
    .byte $90, $05, $1C, $9F, $9C, $1E, $1F, $9E, $81, $95, $96, $97, $98, $99, $9A, $9B    ; $8BF5 ................
    LDA #$00
    JSR $8BC0
    LDA $D020                           ; VIC_BORDER
    ORA #$F0
    JSR $8BC0
    LDA $D021                           ; VIC_BGCOL0
    ORA #$F0
    JSR $8BC0
    LDX #$0E
    LDA $D018                           ; VIC_MEMSETUP
    AND #$02
    BNE $8C25
    LDX #$8E
    RTS
    LDA $D3
    CMP #$28
    BEQ $8C2E
    CLC
    RTS
    SEC
    JSR $FFF0
    LDY #$00
    LDA $D9,X
    ORA #$80
    STA $D9,X
    CLC
    JSR $FFF0
    SEC
    RTS
    LDX $8015
    LDY $8016
    JSR $8C70
    LDX $8019
    LDY $801A
    CPX $8015
    BNE $8C59
    CPY $8016
    BEQ $8C6F
    SEC
    TXA
    SBC $1D
    TAX
    TYA
    SBC $1E
    TAY
    CLC
    TXA
    ADC $1F
    STA $8019
    TYA
    ADC $20
    STA $801A
    RTS
    STX $1D
    STX $1F
    STY $1E
    STY $20
    JSR $8CC5
    JSR $8CB6
    LDY #$00
    STA ($1F),Y
    BNE $8C92
    LDA $1D
    CMP $8017
    BNE $8C92
    LDA $1E
    CMP $8018
    BEQ $8CA0
    INC $1D
    BNE $8C98
    INC $1E
    INC $1F
    BNE $8C7B
    INC $20
    BNE $8C7B
    LDA $1F
    STA $8017
    LDA $20
    STA $8018
    RTS
    LDA $8019
    STA $1D
    LDA $801A
    STA $1E
    RTS
    LDY #$34
    SEI
    STY $01
    LDY #$00
    LDA ($1D),Y
    LDY #$36
    STY $01
    CLI
    RTS
    LDY #$34
    SEI
    STY $01
    LDY #$00
    INC $1D
    BNE $8CD2
    INC $1E
    LDA ($1D),Y
    BNE $8CCC
    LDY #$36
    STY $01
    CLI
    RTS
    .byte $0E, $CD, $4F, $44, $45, $4D    ; $8CDC ..ODEM
    JSR $4146
    EOR $4C,X
    54            .byte $54
    .byte $0D, $00, $93, $0E    ; $8CE8 ....
    PHP
    ORA ($C9),Y
    LSR $5550
    54            .byte $54
    JSR $4850
    4F            .byte $4F
    .byte $4E, $45    ; $8CF7 NE
    JSR $554E
    EOR $4542
    52            .byte $52
    .byte $00    ; $8D00 .
    JSR $524F
    JSR $C5D2
    D4            .byte $D4
    .byte $D5, $D2, $CE, $2E, $00, $0D, $11, $CE, $55, $4D, $42, $45, $52, $3F    ; $8D08 ........UMBER?
    JSR $0020
    ORA ($C4),Y
    EOR #$41
    JMP $494C
    .byte $4E, $47    ; $8D20 NG
    JSR $5000
    JMP $4145
    .byte $53, $45    ; $8D28 SE
    JSR $4157
    EOR #$54
    BRK

; ============================================================
; FRAME_RENDER
; ============================================================
FRAME_RENDER:
    TSX
    STX $C154                           ; workspace
    LDX #$03
    LDA #$20
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $94FA                           ; MODEM_REG_READ
    CMP #$20
    BNE $8D4B
    JSR $94FA                           ; MODEM_REG_READ
    BEQ $8D52
    CMP #$20
    BEQ $8D42
    LDX #$DC
    LDY #$8C
    JMP $90B7                           ; PRINT_STRING
    JSR $9050
    LDA $8013
    STA $D021                           ; VIC_BGCOL0
    LDA $8014
    STA $0286
    LDX #$EA
    LDY #$8C
    JSR $90B7                           ; PRINT_STRING
    LDY #$01
    LDA $9FF0
    BEQ $8D78
    LDX #$01
    LDY #$8D
    JSR $90B7                           ; PRINT_STRING
    LDY #$00
    LDX #$10
    LDA #$2D
    SEC
    JSR $90C8                           ; SETUP_INPUT_PARAMS
    LDX #$0D
    LDY #$8D
    JSR $90B7                           ; PRINT_STRING
    LDX #$00
    LDY #$02
    JSR $90DF                           ; INPUT_LINE
    BCC $8D91
    RTS
    JSR $906E
    LDX $1A
    BEQ $8DA4
    STX $9FF0
    LDA $01FF,X
    STA $9FF0,X
    DEX
    BNE $8D9B
    LDX #$19
    LDY #$8D
    JSR $90B7                           ; PRINT_STRING
    JSR $96C0                           ; PROTO_DISPATCH_TABLE
    JSR $96C6
    LDY #$03
    LDX #$08
    LDA #$10
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $94FA                           ; MODEM_REG_READ
    AND #$10
    BEQ $8DCB
    JSR $FFE4                           ; KERNAL_GETIN
    CMP #$03
    BNE $8DBA
    JMP $96C0                           ; PROTO_DISPATCH_TABLE
    DEY
    BNE $8DB5
    LDY #$00
    LDA $9FF1,Y
    JSR $FFD2                           ; KERNAL_CHROUT
    CMP #$2D
    BNE $8DEA
    LDX #$08
    LDA #$10
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $94FA                           ; MODEM_REG_READ
    AND #$10
    BNE $8DE1
    BEQ $8DFC
    AND #$0F
    BNE $8DF0
    LDA #$0A
    ORA #$A0
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $94FA                           ; MODEM_REG_READ
    AND #$20
    BNE $8DF5
    JSR $FFE4                           ; KERNAL_GETIN
    CMP #$03
    BEQ $8E1C
    INY
    CPY $9FF0
    BNE $8DD0
    LDX #$03
    LDA #$90
    JSR $94F0                           ; MODEM_REG_WRITE
    LDX #$08
    LDA #$40
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $96D5
    BCC $8E1F
    JMP $96C0                           ; PROTO_DISPATCH_TABLE
    LDX #$24
    LDY #$8D
    JSR $907B                           ; PRINT_STATUS_MSG
    CLC
    ROR $C155                           ; workspace
    JSR $96D2
    BCC $8E35
    JSR $96C0                           ; PROTO_DISPATCH_TABLE
    JMP $9062
    JSR $9050
    LDX #$07
    LDY #$95
    JSR $89E2                           ; FRAME_BUF_WRITE
    LDA #$02
    STA $0286
    LDA #$5A
    STA $C100                           ; workspace
    LDX #$10
    LDY #$12
    CLC
    JSR $FFF0
    LDX #$08
    LDY #$01
    LDA #$00
    CLC
    JSR $90C8                           ; SETUP_INPUT_PARAMS
    LDX #$01
    LDY #$C1
    JSR $90DF                           ; INPUT_LINE
    BCS $8E38
    LDY $1A
    LDA #$20
    STA $C101,Y
    INY
    CPY #$08
    BCC $8E68
    LDX #$12
    LDY #$0D
    CLC
    JSR $FFF0
    LDX #$00
    LDA #$5F
    JSR $FFD2                           ; KERNAL_CHROUT
    LDA #$9D
    JSR $FFD2                           ; KERNAL_CHROUT
    JSR $9002                           ; CLEAR_STATUS
    CMP #$0D
    BEQ $8EA3
    CPX #$06
    BEQ $8E7A
    STA $C109,X
    CMP #$30
    BCC $8E7A
    CMP #$5B
    BCS $8E7A
    INX
    LDA #$2A
    JSR $FFD2                           ; KERNAL_CHROUT
    JMP $8E7A
    JSR $906A
    LDA #$20
    STA $C109,X
    INX
    CPX #$06
    BCC $8EA8
    LDX #$37
    STX $01
    LDX #$09
    LDA $8039,X
    STA $C10F,X
    DEX
    BPL $8EB6
    LDX #$36
    STX $01
    LDA $A000
    STA $C119                           ; workspace
    LDA $A001
    STA $C11A                           ; workspace
    LDX #$24
    LDY #$8D
    JSR $907B                           ; PRINT_STATUS_MSG
    LDA #$43
    STA $8034
    LDY #$1B
    JSR $94C1                           ; MODEM_REG_WRITE_WAIT
    JSR $96D2
    BCC $8EE8
    JMP $8E38
    JSR $89D0                           ; FRAME_BUF_READ
    SEC
    ROR $C155                           ; workspace

; ============================================================
; MODEM_INIT_DOWNLOAD
; ============================================================
MODEM_INIT_DOWNLOAD:
    JSR $96CC
    JSR $96CC
    JSR $96CC
    STA $1F
    JSR $96CC
    STA $20
    BCS $8F38
    LDX #$3F
    LDY #$8F
    JSR $907B                           ; PRINT_STATUS_MSG
    JSR $96CC
    STA $1D
    JSR $96CC
    STA $1E
    JSR $96CC
    JSR $96CC
    LDY #$00
    JSR $96CC
    STA ($1D),Y
    BCS $8F29
    INC $1D
    BNE $8F1A
    INC $1E
    BNE $8F1A
    BIT $C155                           ; workspace
    BPL $8F38
    LDX $1D
    LDY $1E
    STX $8036
    STY $8037
    CLC
    ROR $C155                           ; workspace
    JMP ($001F)
    JMP $4E49
    .byte $4B, $49, $4E, $47, $00    ; $8F42 KING.

; ============================================================
; MODEM_SEND_CMD
; ============================================================
MODEM_SEND_CMD:
    CPX #$00
    BEQ $8F7E
    STX $C150                           ; workspace
    LDX $C154                           ; workspace
    TXS
    JSR $96C0                           ; PROTO_DISPATCH_TABLE
    JSR $FFCC                           ; KERNAL_CLRCHN
    JSR $8FF2
    LDA $C151                           ; workspace
    STA $D020                           ; VIC_BORDER
    LDY $C150                           ; workspace
    LDX $8FAF,Y
    LDA $8FB4,Y
    TAY
    JSR $907B                           ; PRINT_STATUS_MSG
    JSR $9002                           ; CLEAR_STATUS
    LDA $C153                           ; workspace
    STA $0286
    LDX #$DA
    LDY #$8F
    JMP $90B7                           ; PRINT_STRING
    LDX $C154                           ; workspace
    TXS
    JSR $FFCC                           ; KERNAL_CLRCHN
    LDA $8014
    STA $0286
    LDX #$F4
    LDY #$9C
    JSR $90B7                           ; PRINT_STRING
    LDA $DC01                           ; CIA1_PRB
    CMP $DC01                           ; CIA1_PRB
    BNE $8F92
    CMP #$FF
    BNE $8F92
    LDA #$00
    STA $C6
    BIT $8010
    BPL $8FAA
    JSR $96D8
    JSR $8FF2
    JMP $96C0                           ; PROTO_DISPATCH_TABLE
    .byte $00, $BA, $BB, $D4, $D7, $C1, $8F, $8F, $8F, $8F    ; $8FB0 ..........

; --- Status messages ---
    .byte $20, $44, $49, $53, $43, $4F, $4E, $4E, $45, $43, $54, $45, $44, $20, $2D, $20    ; $8FBA  DISCONNECTED -
    .byte $42, $41, $44, $20, $4C, $49, $4E, $45, $3F, $00, $57, $52, $00, $52, $57, $00    ; $8FCA BAD LINE?.WR.RW.
    .byte $93, $0E, $43, $4F, $4E, $4E, $45, $43, $54, $20, $41, $47, $41, $49, $4E, $20    ; $8FDA ..CONNECT AGAIN
    .byte $50, $4C, $45, $41, $53, $45, $0D, $00, $2C, $55, $C1, $10, $03, $20, $3A, $83    ; $8FEA PLEASE\n.,U... :.
    .byte $60, $A2    ; $8FFA `.
    .byte $10    ; $8FFC .
    LDY #$90
    JSR $907B                           ; PRINT_STATUS_MSG

; ============================================================
; CLEAR_STATUS
; ============================================================
CLEAR_STATUS:
    LDA #$00
    STA $C6
    STX $19
    JSR $FFE4                           ; KERNAL_GETIN
    BEQ $9008
    LDX $19
    RTS
    .byte $50, $52, $45, $53, $53    ; $9010 PRESS
    JSR $4E41
    EOR $4B20,Y
    EOR $59
    BRK

; ============================================================
; STATUS_LINE
; ============================================================
STATUS_LINE:
    LDX #$01
    LDY #$01
    LDA #$00
    CLC
    JSR $90C8                           ; SETUP_INPUT_PARAMS
    LDX #$00
    LDY #$02
    JSR $90DF                           ; INPUT_LINE
    BCS $903E
    LDA $0200
    AND #$DF
    CMP #$59
    BEQ $904D
    CMP #$4E
    BEQ $904D
    LDA #$9D
    JSR $FFD2                           ; KERNAL_CHROUT
    CPY #$00
    BEQ $901E                           ; STATUS_LINE
    JSR $FFD2                           ; KERNAL_CHROUT
    JMP $901E                           ; STATUS_LINE
    CMP #$59
    RTS
    JSR $9062
    JSR $938B                           ; PROTOCOL_STATE_INIT
    JSR $9076
    LDA #$00
    STA $D015
    LDA #$0E
    BNE $9078
    LDA #$93
    BNE $9078
    LDA #$13
    BNE $9078
    LDA #$20
    BNE $9078
    LDA #$0D
    BNE $9078
    LDA #$12
    BNE $9078
    LDA #$92
    JMP $FFD2                           ; KERNAL_CHROUT

; ============================================================
; PRINT_STATUS_MSG
; ============================================================
PRINT_STATUS_MSG:
    STX $1B
    STY $1C
    JSR $93B4
    LDA $0286
    PHA
    JSR $9097
    JSR $9076
    PLA
    STA $0286
    JMP $93BF

; ============================================================
; CURSOR_HOME
; ============================================================
CURSOR_HOME:
    STX $1B
    STY $1C
    JSR $938B                           ; PROTOCOL_STATE_INIT
    JSR $90AF
    JSR $9072
    LDA $D021                           ; VIC_BGCOL0
    AND #$0F
    TAX
    LDA $93A4,X
    STA $0286
    JMP $90BB
    LDX #$18
    LDY #$00
    CLC
    JMP $FFF0

; ============================================================
; PRINT_STRING
; ============================================================
PRINT_STRING:
    STX $1B
    STY $1C
    LDY #$00
    LDA ($1B),Y
    BEQ $90C7
    JSR $FFD2                           ; KERNAL_CHROUT
    INY
    BNE $90BD
    RTS

; ============================================================
; SETUP_INPUT_PARAMS
; ============================================================
SETUP_INPUT_PARAMS:
    STX $C143                           ; workspace
    STY $C144                           ; workspace
    STA $C146                           ; workspace
    TAX
    LDA #$00
    ROR A
    CPX #$00
    BEQ $90DB
    ORA #$40
    STA $C145                           ; workspace
    RTS

; ============================================================
; INPUT_LINE
; ============================================================
INPUT_LINE:
    STX $1D
    STY $1E
    LDY #$00
    STY $1A
    STY $C6
    LDA #$00
    STA $D4
    LDA #$5F
    JSR $FFD2                           ; KERNAL_CHROUT
    LDA #$9D
    JSR $FFD2                           ; KERNAL_CHROUT
    JSR $FFE4                           ; KERNAL_GETIN
    BEQ $90F7
    LDY $1A
    CMP #$03
    BNE $9107
    JSR $906A
    SEC
    RTS
    CPY $C144                           ; workspace
    BCC $9110
    CMP #$0D
    BEQ $916C
    CPY #$00
    BEQ $9128
    CMP #$14
    BNE $9128
    JSR $906A
    LDA #$9D
    JSR $FFD2                           ; KERNAL_CHROUT
    JSR $FFD2                           ; KERNAL_CHROUT
    DEC $1A
    JMP $90E9
    CPY $C143                           ; workspace
    BEQ $90F7
    BIT $C145                           ; workspace
    BVC $9139
    CMP $C146                           ; workspace
    BEQ $9162
    BNE $913B
    BPL $9145
    CMP #$30
    BCC $90F7
    CMP #$3A
    BCS $90F7
    BCC $9162
    CMP #$22
    BEQ $90F7
    CMP #$20
    BCC $90F7
    CMP #$60
    BCC $9162
    TAX
    LDA $D018                           ; VIC_MEMSETUP
    AND #$02
    BEQ $90F7
    TXA
    CMP #$A0
    BCC $90F7
    CMP #$E0
    BCS $90F7
    JSR $FFD2                           ; KERNAL_CHROUT
    STA ($1D),Y
    INC $1A
    JMP $90E9
    JSR $906A
    CLC
    RTS

; ============================================================
; FILE_UPLOAD
; ============================================================
FILE_UPLOAD:
    STA $C147                           ; workspace
    STX $8032
    LDX #$56
    LDY #$92
    JSR $90B7                           ; PRINT_STRING
    JSR $92AD
    LDY #$00
    BCS $9186
    INY
    LDA #$00
    LDX #$10
    CLC
    JSR $90C8                           ; SETUP_INPUT_PARAMS
    LDA $D018                           ; VIC_MEMSETUP
    PHA
    LDX #$1E
    LDY #$80
    JSR $90DF                           ; INPUT_LINE
    STY $19
    PLA
    STA $D018                           ; VIC_MEMSETUP
    PHP
    LDA #$08
    JSR $FFD2                           ; KERNAL_CHROUT
    PLP
    BCC $91AB
    JMP $924C
    BIT $C156                           ; workspace
    BPL $91FA
    BMI $91BF

; ============================================================
; FILE_DOWNLOAD
; ============================================================
FILE_DOWNLOAD:
    STA $C147                           ; workspace
    STX $8032
    STY $19
    JSR $92AD
    BCC $91FA
    LDA $19
    LDX #$1E
    LDY #$80
    JSR $FFBD                           ; KERNAL_SETNAM
    LDA $8032
    CMP #$50
    BEQ $91F7
    LDY #$00
    LDA $C147                           ; workspace
    CMP #$57
    BNE $91D9
    INY
    LDX #$01
    LDA #$08
    JSR $FFBA                           ; KERNAL_SETLFS
    LDX #$6D
    LDY #$92
    JSR $9093                           ; CURSOR_HOME
    JSR $9290
    JSR $FFC0                           ; KERNAL_OPEN
    JSR $92A2
    BCC $9250
    LDA #$08
    JSR $FFC3                           ; KERNAL_CLOSE
    SEC
    BCS $9250
    LDY $19
    LDA $C147                           ; workspace
    STA $8021,Y
    LDA $8032
    STA $801F,Y
    LDA #$2C
    STA $801E,Y
    STA $8020,Y
    TYA
    CLC
    ADC #$06
    STA $C148                           ; workspace
    LDX #$1C
    LDY #$80
    JSR $FFBD                           ; KERNAL_SETNAM
    LDA #$08
    TAX
    TAY
    JSR $FFBA                           ; KERNAL_SETLFS
    JSR $FFC0                           ; KERNAL_OPEN
    JSR $92E8
    BCC $9250
    BPL $9250
    LDX #$64
    LDY #$92
    JSR $9093                           ; CURSOR_HOME
    JSR $901E                           ; STATUS_LINE
    BNE $924C
    JSR $92AD
    BCS $9250
    LDX #$1B
    LDY #$80
    INC $C148                           ; workspace
    LDA $C148                           ; workspace
    BNE $921B
    JSR $92E0
    SEC
    PHP
    JSR $9076
    PLP
    RTS
    .byte $09    ; $9256 .
    JSR $4946
    JMP $2045
    .byte $4E, $41    ; $925D NA
    EOR $3F45
    JSR $5200
    EOR $50
    JMP $4341
    .byte $45, $3F    ; $926A E?
    JSR $C900
    ORA $04D0
    SEC
    ROR $19
    RTS
    .byte $24, $19, $10, $13    ; $9276 $...
    CLC
    ROR $19
    PHA
    TXA
    PHA
    TYA
    PHA
    JSR $938B                           ; PROTOCOL_STATE_INIT
    JSR $90AF
    PLA
    TAY
    PLA
    TAX
    PLA
    JMP $F1CA
    LDX #$6E
    LDY #$92
    STX $0326
    STY $0327
    CLC
    ROR $19
    LDA #$80
    JMP $FF90
    LDX #$CA
    LDY #$F1
    STX $0326
    STY $0327
    RTS
    LDA #$00
    JSR $FFBD                           ; KERNAL_SETNAM
    LDA #$0F
    TAY
    LDX #$08
    JSR $FFBA                           ; KERNAL_SETLFS
    JSR $FFC0                           ; KERNAL_OPEN
    LDX #$0F
    JSR $FFC9                           ; KERNAL_CHKOUT
    PHP
    ROR $C156                           ; workspace
    JSR $FFCC                           ; KERNAL_CLRCHN
    PLP
    BCS $92E0
    RTS

; ============================================================
; FRAME_STORE
; ============================================================
FRAME_STORE:
    JSR $9290
    LDA #$08
    JSR $FFC3                           ; KERNAL_CLOSE
    BCC $92DA
    JSR $FFE7
    JSR $92A2
    JSR $92E8
    PHP
    LDA #$0F
    JSR $FFC3                           ; KERNAL_CLOSE
    PLP
    RTS
    JSR $935F
    PHP
    LDX #$00
    PLP
    BEQ $9306
    LDX #$A0
    CMP #$32
    BEQ $9306
    LDX #$80
    CMP #$36
    BNE $9306
    LDY $0201
    CPY #$33
    BNE $9306
    LDX #$C0
    STX $C149                           ; workspace
    LDA #$20
    BIT $C149                           ; workspace
    BPL $9339
    BVS $9339
    BNE $932B
    LDX #$00
    LDA $0200,X
    INX
    CMP #$2C
    BNE $9316
    LDA $0200,X
    INX
    CMP #$2C
    BNE $931E
    LDA #$00
    STA $01FF,X
    LDX #$53
    LDY #$93
    JSR $9093                           ; CURSOR_HOME
    LDX #$00
    LDY #$02
    JSR $90B7                           ; PRINT_STRING
    ASL $C149                           ; workspace
    BCC $9352
    LDA #$08
    JSR $FFC3                           ; KERNAL_CLOSE
    JSR $92E0
    LDA $C149                           ; workspace
    BMI $9351
    JSR $9002                           ; CLEAR_STATUS
    LDA $C149                           ; workspace
    SEC
    RTS
    .byte $44, $49, $53, $4B    ; $9353 DISK
    JSR $5245
    52            .byte $52
    .byte $4F, $52    ; $935B OR
    JSR $2C00
    LSR $C1,X
    BPL $9367
    LDA #$00
    RTS
    LDX #$0F
    JSR $FFC6                           ; KERNAL_CHKIN
    LDX #$00
    JSR $FFE4                           ; KERNAL_GETIN
    CMP #$0D
    BEQ $937B
    STA $0200,X
    INX
    BNE $936E
    LDA #$00
    STA $0200,X
    STA $90
    JSR $FFCC                           ; KERNAL_CLRCHN
    LDA $0200
    CMP #$30
    RTS

; ============================================================
; PROTOCOL_STATE_INIT
; ============================================================
PROTOCOL_STATE_INIT:
    LDA $D021                           ; VIC_BGCOL0
    AND #$0F
    TAX
    LDA $93A4,X
    TAX
    LDY #$27
    LDA #$A0
    STA $07C0,Y
    TXA
    STA $DBC0,Y
    DEY
    BPL $9397
    RTS
    .byte $01, $00, $01, $00, $01, $01, $01, $00, $00, $01, $00, $01, $01, $00, $01, $00    ; $93A4 ................
    SEC
    JSR $FFF0
    STX $C14A                           ; workspace
    STY $C14B                           ; workspace
    RTS
    CLC
    LDX $C14A                           ; workspace
    LDY $C14B                           ; workspace
    JMP $FFF0

; ============================================================
; PROTOCOL_RESET
; ============================================================
PROTOCOL_RESET:
    STX $C14E                           ; workspace
    STY $C14F                           ; workspace
    RTS

; ============================================================
; PROTOCOL_CLEANUP
; ============================================================
PROTOCOL_CLEANUP:
    STX $1D
    STY $1E
    LDX $C14E                           ; workspace
    LDY $C14F                           ; workspace
    STX $1F
    STY $20
    LDY #$00
    LDA ($1D),Y
    STA $C14C                           ; workspace
    LDX #$00
    JSR $9436
    JSR $9002                           ; CLEAR_STATUS
    CMP #$1D
    BNE $940E
    LDX #$01
    JSR $9436
    JSR $949B
    INX
    CPX #$06
    BNE $93F3
    LDY $8033
    CPY $C14C                           ; workspace
    BNE $9408
    LDY #$00
    INY
    STY $8033
    BNE $93E5
    CMP #$9D
    BNE $942B
    LDY $8033
    DEY
    BNE $941B
    LDY $C14C                           ; workspace
    STY $8033
    LDX #$05
    JSR $9436
    JSR $949B
    DEX
    BNE $9420
    BEQ $93E5
    CMP #$0D
    BNE $9434
    LDA $8033
    CLC
    RTS
    SEC
    RTS
    TXA
    PHA
    STX $1A
    LDA $D021                           ; VIC_BGCOL0
    AND #$0F
    TAX
    LDA $93A4,X
    STA $C142                           ; workspace
    LDA $8033
    SEC
    SBC #$03
    BEQ $9450
    BCS $9456
    CLC
    ADC $C14C                           ; workspace
    BEQ $9450
    STA $19
    LDX #$00
    LDY $19
    LDA ($1D),Y
    CLC
    ADC $1A
    TAY
    LDA ($1F),Y
    AND #$3F
    CPX #$12
    BCC $946E
    CPX #$18
    BCC $9470
    ORA #$80
    STA $07C0,X
    LDA $C142                           ; workspace
    STA $DBC0,X
    INX
    CPX #$28
    BEQ $9498
    INC $1A
    LDA $1A
    CMP #$06
    BNE $945A
    LDA #$00
    STA $1A
    LDY $19
    CPY $C14C                           ; workspace
    BNE $9493
    LDY #$00
    INY
    STY $19
    BNE $945A
    PLA
    TAX
    RTS
    LDA $D011                           ; VIC_CTRL1
    ASL A
    BCS $949B
    LDA $D011                           ; VIC_CTRL1
    ASL A
    BCC $94A1
    RTS

; ============================================================
; MODEM_STATUS_CHECK
; ============================================================
MODEM_STATUS_CHECK:
    AND #$7F
    CMP #$20
    BCS $94B2
    ORA #$40
    BNE $94C0
    CMP #$40
    BCC $94C0
    CMP #$60
    BCS $94BE
    ORA #$80
    BNE $94C0
    EOR #$C0
    RTS

; ============================================================
; MODEM_REG_WRITE_WAIT
; ============================================================
MODEM_REG_WRITE_WAIT:
    STY $C14D                           ; workspace
    LDY #$00
    LDA $C100,Y
    INY
    CPY $C14D                           ; workspace
    PHP
    JSR $96C9
    PLP
    BCC $94C6
    RTS

; ============================================================
; MODEM_REG_READ_STATUS
; ============================================================
MODEM_REG_READ_STATUS:
    LDY #$00
    JSR $96CC
    STA $C100,Y
    INY
    BCC $94D7
    LDA $8034
    RTS

; ============================================================
; MODEM_WAIT_READY
; ============================================================
MODEM_WAIT_READY:
    PHA
    LDX #$00
    JSR $94FA                           ; MODEM_REG_READ
    TAX
    BPL $94E7
    PLA
    LDX #$04

; ============================================================
; MODEM_REG_WRITE
; ============================================================
MODEM_REG_WRITE:
    PHP
    SEI
    STX $DE00                           ; MODEM_REG_SELECT
    STA $DE01                           ; MODEM_DATA
    PLP
    RTS

; ============================================================
; MODEM_REG_READ
; ============================================================
MODEM_REG_READ:
    PHP
    SEI
    STX $DE00                           ; MODEM_REG_SELECT
    LDA $DE01                           ; MODEM_DATA
    LDA $DE01                           ; MODEM_DATA
    PLP
    RTS
    .byte $00, $F4, $FF, $8E, $07, $0D, $0C    ; $9507 .......
    JSR $9020
    BCS $951A
    CPY #$21
    LDX $0D9B

; --- Login screen layout and help text ---
    .byte $20, $20, $90, $DD, $43, $4F, $4D, $50, $55, $4E, $45, $54, $20, $53, $59, $53    ; $9518   ..COMPUNET SYS
    .byte $54, $45, $4D, $20, $4C, $4F, $47, $4F, $4E, $2E, $06, $0B, $DD, $9B, $0D, $20    ; $9528 TEM LOGON.....\n
    .byte $20, $90, $DD, $06, $21, $DD, $9B, $0D, $20, $20, $90, $DD, $1F, $45, $4E, $54    ; $9538  ...!..\n  ...ENT
    .byte $45, $52, $20, $55, $53, $45, $52, $20, $49, $44, $3A, $06, $13, $90, $DD, $9B    ; $9548 ER USER ID:.....
    .byte $0D, $20, $20, $90, $DD, $06, $21, $DD, $9B, $0D, $20, $20, $90, $DD, $1F, $50    ; $9558 \n  ...!..\n  ...P
    .byte $41, $53, $53, $57, $4F, $52, $44, $3A, $06, $18, $90, $DD, $9B, $0D, $20, $20    ; $9568 ASSWORD:.....\n
    .byte $90, $DD, $06, $21, $DD, $9B, $0D, $20, $20, $90, $AD, $07, $C0, $21, $BD, $9B    ; $9578 ...!..\n  ....!..
    .byte $0D, $00, $F6, $FC, $0E, $0D, $06, $02, $1F, $C5, $44, $49, $54, $20, $CB, $45    ; $9588 \n....\n....DIT .E
    .byte $59, $53, $07, $0D, $03, $06, $02, $D3, $D4, $CF, $D0, $20, $CB, $C5, $D9, $06    ; $9598 YS.\n....... ....
    .byte $07, $46, $33, $2F, $34, $0D, $06, $02, $95, $53, $54, $4F, $50, $20, $45, $44    ; $95A8 .F3/4\n...STOP ED
    .byte $49, $54, $2C, $06, $05, $C4, $45, $4C, $45, $54, $45, $2F, $C9, $4E, $53, $45    ; $95B8 IT,...ELETE/.NSE
    .byte $52, $54, $0D, $06, $02, $53, $54, $4F, $52, $45, $20, $46, $52, $41, $4D, $45    ; $95C8 RT\n..STORE FRAME
    .byte $06, $04, $4C, $49, $4E, $45, $20, $41, $42, $4F, $56, $45, $20, $43, $55, $52    ; $95D8 ..LINE ABOVE CUR
    .byte $53, $4F, $52, $0D, $0D, $06, $02, $1F, $D2, $D5, $CE, $20, $CB, $C5, $D9, $06    ; $95E8 SOR\n\n...... ....
    .byte $08, $46, $35, $0D, $06, $02, $95, $52, $45, $53, $54, $4F, $52, $45, $06, $08    ; $95F8 .F5\n...RESTORE..
    .byte $CF, $4E, $2F, $CF, $46, $46, $20, $41, $55, $54, $4F, $2D, $52, $45, $50, $45    ; $9608 .N/.FF AUTO-REPE
    .byte $41, $54, $0D, $06, $02, $4F, $52, $49, $47, $49, $4E, $41, $4C, $0D, $06, $12    ; $9618 AT\n..ORIGINAL\n..
    .byte $1F, $46, $36, $0D, $06, $02, $D3, $C8, $C9, $C6, $D4, $2D, $C3, $3D, $06, $07    ; $9628 .F6\n.......-.=..
    .byte $95, $CF, $4E, $2F, $CF, $46, $46, $20, $43, $4F, $4C, $4F, $55, $52, $0D, $06    ; $9638 ..N/.FF COLOUR\n.
    .byte $02, $43, $48, $41, $4E, $47, $45, $20, $43, $41, $53, $45, $06, $04, $4F, $56    ; $9648 .CHANGE CASE..OV
    .byte $45, $52, $57, $52, $49, $54, $45, $0D, $0D, $06, $12, $1F, $46, $37, $2F, $38    ; $9658 ERWRITE\n\n...F7/8
    .byte $0D, $06, $12, $95, $D3, $43, $52, $45, $45, $4E, $2F, $C2, $4F, $52, $44, $45    ; $9668 \n....CREEN/.ORDE
    .byte $52, $0D, $06, $12, $43, $4F, $4C, $4F, $55, $52, $20, $43, $48, $41, $4E, $47    ; $9678 R\n..COLOUR CHANG
    .byte $45, $07, $0D, $02, $06, $02, $1F, $D3, $45, $45, $20, $C8, $CF, $D7, $20, $D4    ; $9688 E.\n.....EE ... .
    .byte $CF, $20, $C5, $C4, $C9, $D4, $0D, $06, $02, $46, $4F, $52, $20, $46, $55, $4C    ; $9698 . ....\n..FOR FUL
    .byte $4C, $45, $52, $20, $44, $45, $54, $41, $49, $4C, $53, $00, $00, $00, $00, $00    ; $96A8 LER DETAILS.....
    .byte $00, $00, $00, $00, $00, $00, $00, $00    ; $96B8 ........

; ============================================================
; PROTO_DISPATCH_TABLE
; ============================================================
PROTO_DISPATCH_TABLE:
    JMP $9B79                           ; PROTO_SEND_PACKET
    JMP $9B8A                           ; PROTO_RECV_PACKET
    JMP $96DB                           ; PROTO_INIT_REGS
    JMP $97AD                           ; PROTO_RECV_FRAME
    JMP $996B                           ; PROTO_PROCESS_CMD
    JMP $993A                           ; PROTO_ERROR_RECOVERY
    JMP $9B3B                           ; PROTO_FLOW_CONTROL
    JMP $9E69                           ; PROTO_CONNECT
    JMP $C800

; ============================================================
; PROTO_INIT_REGS
; ============================================================
PROTO_INIT_REGS:
    LDX #$02
    LDA #$40
    JSR $94F0                           ; MODEM_REG_WRITE
    LDX #$06
    LDA #$05
    JMP $94F0                           ; MODEM_REG_WRITE

; ============================================================
; PROTO_START_SESSION
; ============================================================
PROTO_START_SESSION:
    BIT $8038
    BVC $96F3
    LDX #$04
    JMP $8F47                           ; MODEM_SEND_CMD
    LDA $C20E                           ; workspace
    STA $C210                           ; workspace
    STA $C211                           ; workspace
    LDA #$80
    STA $8038
    LDX $8043
    LDA #$63
    LDY #$9C
    BNE $971F

; ============================================================
; PROTO_DISCONNECT
; ============================================================
PROTO_DISCONNECT:
    BIT $8038
    BPL $9714
    LDX #$05
    JMP $8F47                           ; MODEM_SEND_CMD
    LDA #$40
    STA $8038
    LDX #$03
    LDA #$5A
    LDY #$9C
    STX $C20A                           ; workspace
    PHA
    LDA $9B03,X
    STA $23
    LDA $9B07,X
    STA $24
    PLA
    JSR $9C3D
    LDX $8046
    STX $DC05
    JSR $9E3C
    LDA #$00
    STA $C209                           ; workspace
    STA $A2
    STA $A1
    STA $C218                           ; workspace
    STA $C219                           ; workspace
    STA $C224                           ; workspace
    LDX #$0B
    STA $C228,X
    DEX
    BPL $974E
    LDA #$34
    STA $21
    LDA #$C2
    STA $22
    LDA #$03
    STA $C20B                           ; workspace
    RTS
    LDY #$01
    LDA ($21),Y
    ORA #$40
    STA ($21),Y
    LDA $C20B                           ; workspace
    CLC
    ADC #$02
    DEY
    STA ($21),Y
    LDY #$00
    STY $C21D                           ; workspace
    STY $C21E                           ; workspace
    LDA ($21),Y
    JSR $9B10
    INY
    CPY $C20B                           ; workspace
    BNE $977B
    JSR $9B0B
    LDA $C21D                           ; workspace
    STA ($21),Y
    INY
    LDA $C21E                           ; workspace
    STA ($21),Y
    LDX $C209                           ; workspace
    LDA #$80
    STA $C22C,X
    JSR $98F5
    LDX $8043
    LDA $C22C,X
    BMI $979C
    DEX
    BPL $97A2
    JMP $9C2D

; ============================================================
; PROTO_RECV_FRAME
; ============================================================
PROTO_RECV_FRAME:
    STA $19
    PHA
    TXA
    PHA
    TYA
    PHA
    PHP
    LDA $19
    PHA
    BIT $8038
    BMI $97C0
    JSR $96E9                           ; PROTO_START_SESSION
    LDX $C209                           ; workspace
    LDA $C22C,X
    BPL $97EA
    CPX $8043
    BNE $97CF
    LDX #$FF
    INX
    STX $C209                           ; workspace
    LDA $9B03,X
    STA $21
    LDA $9B07,X
    STA $22
    LDA #$03
    STA $C20B                           ; workspace
    LDA $C228,X
    BEQ $97EA
    JSR $98F5
    LDA $C20B                           ; workspace
    CMP #$03
    BNE $9824
    LDY #$00
    STY $C21D                           ; workspace
    STY $C21E                           ; workspace
    LDA $8045
    STA ($21),Y
    JSR $9B10
    INY
    LDA $8034
    STA ($21),Y
    JSR $9B10
    INY
    LDA $C20E                           ; workspace
    LDX $C209                           ; workspace
    STA $C228,X
    TAX
    INX
    CPX #$60
    BNE $981C
    LDX #$20
    STX $C20E                           ; workspace
    STA ($21),Y
    JSR $9B10
    LDY $C20B                           ; workspace
    PLA
    STA ($21),Y
    JSR $9B10
    INY
    STY $C20B                           ; workspace
    INY
    INY
    CPY $8045
    BNE $9851
    JSR $9B0B
    LDA $C21D                           ; workspace
    LDY $C20B                           ; workspace
    STA ($21),Y
    INY
    LDA $C21E                           ; workspace
    STA ($21),Y
    LDX $C209                           ; workspace
    LDA #$80
    STA $C22C,X
    PLP
    BCC $985C
    JSR $9762
    LDA #$00
    STA $8038
    PLA
    TAY
    PLA
    TAX
    PLA
    RTS
    LDX $8043
    LDA $C228,X
    CMP $C211                           ; workspace
    BNE $987D
    LDY $C211                           ; workspace
    INY
    CPY #$60
    BNE $9877
    LDY #$20
    STY $C211                           ; workspace
    JMP $988B
    DEX
    BPL $9865
    LDX $C20A                           ; workspace
    CPX $8043
    BNE $988A
    LDX #$FF
    INX
    STX $C20A                           ; workspace
    LDA $C22C,X
    BPL $98F5
    LDA $C228,X
    CMP $C220                           ; workspace
    BNE $98B5
    LDA #$00
    STA $C221                           ; workspace
    STA $C222                           ; workspace
    LDA $804A
    BEQ $98B2
    LDY $C22C,X
    BPL $98F5
    CMP $C222                           ; workspace
    BNE $98A8
    LDA $C228,X
    STA $C220                           ; workspace
    LDX #$19
    LDY $8034
    JSR $9BA4
    LDX $C20A                           ; workspace
    LDA $9B03,X
    STA $23
    LDA $9B07,X
    STA $24
    JSR $991E
    LDY #$00
    STY $C20C                           ; workspace
    LDA ($23),Y
    STA $C20D                           ; workspace
    LDA ($23),Y
    JSR $9926
    LDX $C20A                           ; workspace
    LDA $C22C,X
    BPL $98F2
    INC $C20C                           ; workspace
    LDY $C20C                           ; workspace
    CPY $C20D                           ; workspace
    BNE $98DA
    JSR $9922
    LDX $8043
    LDA $C228,X
    CMP $C210                           ; workspace
    BEQ $9903
    DEX
    BPL $98F8
    LDA $C22C,X
    BPL $990B
    JMP $9862
    LDA #$00
    STA $C228,X
    LDX $C210                           ; workspace
    INX
    CPX #$60
    BNE $991A
    LDX #$20
    STX $C210                           ; workspace
    RTS
    LDA #$01
    BNE $9937
    LDA #$02
    BNE $9937
    CMP #$00
    BEQ $9937
    CMP #$04
    BCS $9937
    ADC #$20
    PHA
    LDA #$03
    JSR $94E4                           ; MODEM_WAIT_READY
    PLA
    JMP $94E4                           ; MODEM_WAIT_READY

; ============================================================
; PROTO_ERROR_RECOVERY
; ============================================================
PROTO_ERROR_RECOVERY:
    PHA
    TXA
    PHA
    TYA
    PHA
    BIT $8038
    BVS $9947
    JSR $970A                           ; PROTO_DISCONNECT
    BIT $C224                           ; workspace
    BMI $9964
    LDX #$03
    LDA $C22C,X
    BPL $995B
    LDA $C228,X
    CMP $C20F                           ; workspace
    BEQ $9964
    DEX
    BPL $994E
    JSR $9A06
    SEC
    BCS $9965
    CLC
    PLA
    TAY
    PLA
    TAX
    PLA
    RTS

; ============================================================
; PROTO_PROCESS_CMD
; ============================================================
PROTO_PROCESS_CMD:
    TXA
    PHA
    TYA
    PHA
    BIT $8038
    BVS $9977
    JSR $970A                           ; PROTO_DISCONNECT
    LDX $C209                           ; workspace
    LDA $C22C,X
    BMI $9986
    JSR $9A17
    SEC
    ROR $C224                           ; workspace
    LDY $C20B                           ; workspace
    LDA ($21),Y
    INY
    STY $C20B                           ; workspace
    CPY $C217                           ; workspace
    BEQ $9997
    CLC
    BCC $99E7
    PHA
    LDA #$00
    LDX $C209                           ; workspace
    STA $C228,X
    STA $C22C,X
    STA $C224                           ; workspace
    BIT $C216                           ; workspace
    CLC
    BPL $99E6
    LDA #$00
    STA $A2
    STA $A1
    LDA $A2
    CMP $8047
    BCS $99DD
    LDX #$03
    LDA $C22C,X
    BMI $99C5
    DEX
    BPL $99BB
    BMI $99B2
    STX $C209                           ; workspace
    LDA $C228,X
    JSR $99F0
    BEQ $99DD
    JSR $9ABC
    LDX $C209                           ; workspace
    LDA #$00
    STA $C22C,X
    BEQ $99AC
    JSR $9C2D
    LDA #$00
    STA $8038
    SEC
    PLA
    STA $19
    PLA
    TAY
    PLA
    TAX
    LDA $19
    RTS
    STA $19
    LDX $C20F                           ; workspace
    LDY #$03
    CPX $19
    BEQ $9A05
    INX
    CPX #$60
    BNE $9A02
    LDX #$20
    DEY
    BPL $99F7
    RTS
    LDA $A1
    CMP $8048
    BCC $9A16
    JSR $9922
    LDA #$00
    STA $A2
    STA $A1
    RTS
    JSR $9A06
    LDX $C209                           ; workspace
    LDA $C22C,X
    BMI $9A25
    JMP $9AAC
    AND #$40
    BEQ $9A2C
    JMP $9A73
    JSR $9ABC
    LDX $C209                           ; workspace
    LDY $C228,X
    LDX #$03
    LDA $C22C,X
    AND #$40
    BEQ $9A44
    TYA
    CMP $C228,X
    BEQ $9A5E
    DEX
    BPL $9A37
    LDX #$03
    STY $C215                           ; workspace
    LDY $C20F                           ; workspace
    CPY $C215                           ; workspace
    BEQ $9A6B
    INY
    CPY #$60
    BNE $9A5B
    LDY #$20
    DEX
    BPL $9A4F
    LDX $C209                           ; workspace
    LDA #$00
    STA $C228,X
    STA $C22C,X
    BEQ $9AAC
    LDX $C209                           ; workspace
    LDA #$C0
    STA $C22C,X
    LDA $C228,X
    CMP $C20F                           ; workspace
    BNE $9AAC
    LDY $C20F                           ; workspace
    INY
    CPY #$60
    BNE $9A85
    LDY #$20
    STY $C20F                           ; workspace
    LDA $9B03,X
    STA $21
    LDA $9B07,X
    STA $22
    LDA #$03
    STA $C20B                           ; workspace
    LDY #$00
    LDA ($21),Y
    SEC
    SBC #$02
    STA $C217                           ; workspace
    INY
    LDA ($21),Y
    STA $8034
    ASL A
    STA $C216                           ; workspace
    RTS
    LDX $C209                           ; workspace
    INX
    CPX #$04
    BNE $9AB6
    LDX #$00
    STX $C209                           ; workspace
    JMP $9A17
    LDA $C228,X
    STA $C206                           ; workspace
    LDX #$19
    LDY #$20
    JSR $9BA4
    LDA #$40
    STA $C21D                           ; workspace
    LDA #$E6
    STA $C21E                           ; workspace
    LDA $C206                           ; workspace
    JSR $9B10
    JSR $9B0B
    LDA $C21D                           ; workspace
    STA $C207                           ; workspace
    LDA $C21E                           ; workspace
    STA $C208                           ; workspace
    JSR $991E
    LDX #$00
    STX $C20C                           ; workspace
    LDA $C203,X
    JSR $9926
    INC $C20C                           ; workspace
    LDX $C20C                           ; workspace
    CPX #$06
    BNE $9AF0
    JMP $9922
    .byte $34, $C8, $5C, $F0, $C2, $C2, $C3, $C3    ; $9B03 4.\.....
    LDA #$00
    JSR $9B10
    PHA
    STA $C21F                           ; workspace
    TXA
    PHA
    LDX #$07
    CLC
    ROL $C21F                           ; workspace
    ROL $C21E                           ; workspace
    ROL $C21D                           ; workspace
    BCC $9B34
    LDA $C21D                           ; workspace
    EOR #$10
    STA $C21D                           ; workspace
    LDA $C21E                           ; workspace
    EOR #$21
    STA $C21E                           ; workspace
    DEX
    BPL $9B18
    PLA
    TAX
    PLA
    RTS

; ============================================================
; PROTO_FLOW_CONTROL
; ============================================================
PROTO_FLOW_CONTROL:
    JSR $970A                           ; PROTO_DISCONNECT
    JSR $9A17
    LDA $8034
    CMP #$41
    BEQ $9B52
    CMP #$42
    BEQ $9B52
    CMP #$40
    BEQ $9B52
    CLC
    RTS
    JSR $94D5                           ; MODEM_REG_READ_STATUS
    LDA #$00
    STA $C100,Y
    LDA $8034
    CMP #$40
    BEQ $9B50
    CMP #$42
    BEQ $9B74
    LDX #$00
    LDY #$C1
    JSR $907B                           ; PRINT_STATUS_MSG
    JSR $9002                           ; CLEAR_STATUS
    JSR $938B                           ; PROTOCOL_STATE_INIT
    SEC
    RTS
    LDX #$01
    JMP $8F47                           ; MODEM_SEND_CMD

; ============================================================
; PROTO_SEND_PACKET
; ============================================================
PROTO_SEND_PACKET:
    JSR $9C36
    LDX #$03
    LDA #$20
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $94FA                           ; MODEM_REG_READ
    AND #$20
    BNE $9B83

; ============================================================
; PROTO_RECV_PACKET
; ============================================================
PROTO_RECV_PACKET:
    LDA #$20
    STA $C20E                           ; workspace
    STA $C20F                           ; workspace
    STA $C204                           ; workspace
    STA $C205                           ; workspace
    LDA #$06
    STA $C203                           ; workspace
    STA $C220                           ; workspace
    STA $8038
    RTS
    BIT $8011
    BPL $9C0A
    STA $C226                           ; workspace
    TYA
    AND #$3F
    CMP #$20
    BCC $9BC5
    AND #$1F
    STA $C225                           ; workspace
    ASL A
    ADC $C225                           ; workspace
    ADC #$0B
    LDY #$9C
    BCC $9BD3
    INY
    BNE $9BD3
    STA $C225                           ; workspace
    ASL A
    ADC $C225                           ; workspace
    ADC #$14
    LDY #$9C
    BCC $9BD3
    INY
    STA $1B
    STY $1C
    LDY #$00
    LDA ($1B),Y
    CMP #$20
    BEQ $9BE1
    AND #$1F
    ORA #$80
    STA $07C0,X
    INX
    INY
    CPY #$03
    BNE $9BD9
    INX
    LDA $C226                           ; workspace
    LSR A
    LSR A
    LSR A
    LSR A
    JSR $9BFD
    INX
    LDA $C226                           ; workspace
    AND #$0F
    ORA #$B0
    CMP #$BA
    BCC $9C07
    ADC #$06
    AND #$8F
    STA $07C0,X

; --- Protocol command tokens ---
    .byte $60, $41, $43, $4B, $44, $49, $52, $44, $41, $54, $4F, $4B, $20, $45, $52, $52    ; $9C0A `ACKDIRDATOK ERR
    .byte $46, $54, $4C, $43, $4F, $4D, $A0, $40    ; $9C1A FTLCOM.@
    LDA $02A6
    BNE $9C29
    LDY #$42
    STY $DC05
    RTS
    JSR $9C20
    LDA #$46
    LDY #$9C
    BNE $9C3D
    JSR $9C20
    LDA #$31
    LDY #$EA
    SEI
    STA $0314
    STY $0315
    CLI
    RTS
    .byte $20, $7D, $9C    ; $9C46  }.
    LDX #$00
    JSR $94FA                           ; MODEM_REG_READ
    AND #$20
    BEQ $9C55
    JMP $EA31
    LDX #$02
    JMP $8F47                           ; MODEM_SEND_CMD
    JSR $9C7D
    JSR $9C8F
    JMP $9C71
    JSR $9D00
    INC $C221                           ; workspace
    BNE $9C6E
    INC $C222                           ; workspace
    JSR $9C7D
    JSR $FFEA
    LDA $DC0D                           ; CIA1_ICR
    PLA
    TAY
    PLA
    TAX
    PLA
    RTI
    LDA $DC01                           ; CIA1_PRB
    CMP $DC01                           ; CIA1_PRB
    BNE $9C7D
    CMP #$7B
    BEQ $9C8A
    RTS
    LDX #$00
    JMP $8F47                           ; MODEM_SEND_CMD
    JSR $9D54
    BIT $C223                           ; workspace
    BMI $9C98
    RTS
    LDY $C485
    LDA $C486
    CPY #$20
    BNE $9CA5
    LDA $C487
    LDX #$20
    JSR $9BA4
    LDA $C485
    CMP #$20
    BEQ $9CF1
    LDX #$03
    LDA $C22C,X
    BPL $9CBD
    DEX
    BPL $9CB3
    BMI $9CF1
    LDA $1B
    PHA
    LDA $1C
    PHA
    LDA $9B03,X
    STA $1B
    LDA $9B07,X
    STA $1C
    LDA #$80
    STA $C22C,X
    LDA $C485
    STA $C230,X
    LDA $C486
    STA $C228,X
    LDY #$00
    LDA $C484,Y
    STA ($1B),Y
    INY
    CPY $C212                           ; workspace
    BNE $9CE0
    PLA
    STA $1C
    PLA
    STA $1B
    JMP $9E3C
    .byte $93, $0E, $C1, $42, $4F, $52, $54, $45, $44, $0D, $0D, $00    ; $9CF4 ...BORTED...
    JSR $9D54
    BIT $C223                           ; workspace
    BMI $9D09
    RTS
    LDA $C485
    CMP #$20
    BNE $9D40
    LDY #$03
    LDA $C484,Y
    STY $C227                           ; workspace
    LDX #$20
    LDY #$20
    JSR $9BA4
    LDY $C227                           ; workspace
    LDA $C484,Y
    LDX $8043
    CMP $C228,X
    BEQ $9D32
    DEX
    BPL $9D28
    BMI $9D37
    LDA #$00
    STA $C22C,X
    INY
    CPY $C212                           ; workspace
    BNE $9D12
    JMP $9E3C
    LDA $C486
    JSR $99F0
    BNE $9D3D
    LDX $8043
    LDA #$00
    STA $C22C,X
    DEX
    BPL $9D4D
    RTS
    LDA #$00
    STA $C223                           ; workspace
    LDX #$00
    JSR $94FA                           ; MODEM_REG_READ
    TAX
    AND #$40
    BNE $9D85
    TXA
    AND #$20
    BNE $9D6D
    LDX #$02
    JMP $8F47                           ; MODEM_SEND_CMD
    INC $C218                           ; workspace
    BNE $9D7F
    INC $C219                           ; workspace
    LDA $8049
    BEQ $9D7F
    CMP $C219                           ; workspace
    BEQ $9D80
    RTS
    LDX #$03
    JMP $8F47                           ; MODEM_SEND_CMD
    LDA #$00
    STA $A2
    STA $C218                           ; workspace
    STA $C219                           ; workspace
    LDX #$04
    JSR $94FA                           ; MODEM_REG_READ
    BIT $C213                           ; workspace
    BPL $9DA3
    CMP #$01
    BNE $9DA2
    LDA #$00
    STA $C213                           ; workspace
    RTS
    CMP #$01
    BNE $9DAF
    LDA #$93
    JSR $9E50
    JMP $9E41
    CMP #$02
    BNE $9DE9
    LDA $C484
    CMP $C212                           ; workspace
    BEQ $9DBF
    LDA #$8E
    BNE $9E39
    LDA $C21A                           ; workspace
    BEQ $9DC8
    LDA #$83
    BNE $9E39
    LDA $C21B                           ; workspace
    BNE $9DC4
    LDA $C212                           ; workspace
    CMP #$05
    BCS $9DD8
    LDA #$95
    BNE $9E39
    DEC $C212                           ; workspace
    DEC $C212                           ; workspace
    LDA #$A0
    JSR $9E50
    LDA #$FF
    STA $C223                           ; workspace
    RTS
    LDY $C212                           ; workspace
    CPY #$94
    BNE $9DF4
    LDA #$8F
    BNE $9E39
    BIT $C214                           ; workspace
    BPL $9E04
    LDX #$00
    STX $C214                           ; workspace
    SEC
    SBC #$20
    JMP $9E0E
    CMP #$03
    BNE $9E0E
    LDA #$FF
    STA $C214                           ; workspace
    RTS
    STA $C484,Y
    INC $C212                           ; workspace
    STA $C21C                           ; workspace
    LDX #$07
    CLC
    ROL $C21C                           ; workspace
    ROL $C21B                           ; workspace
    ROL $C21A                           ; workspace
    BCC $9E35
    LDA $C21A                           ; workspace
    EOR #$10
    STA $C21A                           ; workspace
    LDA $C21B                           ; workspace
    EOR #$21
    STA $C21B                           ; workspace
    DEX
    BPL $9E19
    RTS
    JSR $9E50
    LDA #$FF
    STA $C213                           ; workspace
    LDA #$00
    STA $C212                           ; workspace
    STA $C214                           ; workspace
    STA $C21A                           ; workspace
    STA $C21B                           ; workspace
    RTS
    BIT $8011
    BPL $9E58
    STA $07E7
    RTS
    .byte $C3, $4F, $4E, $4E, $45, $43, $54, $49, $4E, $47, $2E, $2E, $2E, $0D, $11, $00    ; $9E59 .ONNECTING......

; ============================================================
; PROTO_CONNECT
; ============================================================
PROTO_CONNECT:
    LDX #$00
    JSR $94FA                           ; MODEM_REG_READ
    AND #$20
    BNE $9E89
    LDX #$08
    JSR $94FA                           ; MODEM_REG_READ
    AND #$40
    BNE $9E80
    LDX #$02
    JMP $8F47                           ; MODEM_SEND_CMD
    JSR $FFE4                           ; KERNAL_GETIN
    CMP #$03
    BNE $9E69                           ; PROTO_CONNECT
    BEQ $9EE1
    LDA $8012
    STA $D020                           ; VIC_BORDER
    LDX #$03
    LDA #$D0
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $906E
    JSR $906E
    BIT $8010
    BVC $9EA6
    JSR $96D8
    CLC
    RTS
    LDX #$59
    LDY #$9E
    JSR $90B7                           ; PRINT_STRING
    LDA #$00
    STA $C200                           ; workspace
    STA $C202                           ; workspace
    STA $1F
    STA $20
    STA $C201                           ; workspace
    LDA #$C8
    LDY #$9F
    JSR $9C3D
    LDA $8046
    STA $DC05
    JSR $9FA9
    JSR $9FA9
    LDA #$40
    LDX #$08
    JSR $94F0                           ; MODEM_REG_WRITE
    LDX $20
    CPX #$0A
    BCS $9EE3
    JSR $9F90
    BNE $9ED6
    SEC
    RTS
    JSR $9F90
    BEQ $9EE1
    LDX $1F
    CPX $20
    BNE $9F14
    LDX #$00
    JSR $94FA                           ; MODEM_REG_READ
    TAX
    BPL $9EE3
    LDX $C202                           ; workspace
    BMI $9EE3
    JSR $9FBC
    LDA $8052,X
    INX
    CPX $8051
    BNE $9F09
    LDX #$FF
    STX $C202                           ; workspace
    LDX #$04
    JSR $94F0                           ; MODEM_REG_WRITE
    JMP $9EE3
    LDA $C234,X
    INC $1F
    AND #$7F
    CMP #$20
    BCC $9F3B
    CMP #$41
    BCC $9F3B
    CMP #$5B
    BCS $9F2B
    ORA #$80
    BNE $9F3B
    CMP #$60
    BCC $9F3B
    BEQ $9F39
    CMP #$7B
    BCS $9F39
    AND #$DF
    BNE $9F3B
    LDA #$00
    CMP #$0D
    BEQ $9F43
    CMP #$20
    BCC $9EE3
    LDX $C201                           ; workspace
    BNE $9F4C
    CMP #$3F
    BEQ $9F55
    CMP #$2A
    BNE $9F59
    LDX #$00
    STX $C201                           ; workspace
    SEC
    ROR $C200                           ; workspace
    BIT $8010
    BMI $9F63
    BIT $C200                           ; workspace
    BPL $9F66
    JSR $FFD2                           ; KERNAL_CHROUT
    AND #$7F
    STA $0200,X
    CPX #$4F
    BEQ $9F72
    INC $C201                           ; workspace
    CMP #$0D
    BEQ $9F79
    JMP $9EE3
    LDA #$00
    STA $C200                           ; workspace
    STA $C201                           ; workspace
    LDX #$03
    LDA $0200,X
    CMP $804D,X
    BNE $9F76
    DEX
    BPL $9F83
    CLC
    RTS
    BIT $8010
    BPL $9FA3
    LDX #$08
    JSR $94FA                           ; MODEM_REG_READ
    AND #$40
    BNE $9FA3
    LDX #$02
    JMP $8F47                           ; MODEM_SEND_CMD
    JSR $FFE4                           ; KERNAL_GETIN
    CMP #$03
    RTS
    LDX #$08
    LDA #$10
    JSR $94F0                           ; MODEM_REG_WRITE
    JSR $94FA                           ; MODEM_REG_READ
    AND #$10
    BNE $9FB0
    LDA #$0D
    JMP $94E4                           ; MODEM_WAIT_READY
    LDA #$00
    STA $A2
    LDA $8044
    CMP $A2
    BCS $9FC3
    RTS
    .byte $A2, $00    ; $9FC8 ..
    JSR $94FA                           ; MODEM_REG_READ
    TAY
    AND #$40
    BEQ $9FE1
    LDX #$04
    JSR $94FA                           ; MODEM_REG_READ
    LDX $20
    STA $C234,X
    INC $20
    JMP $EA31
    TYA
    AND #$20
    BNE $9FDE
    LDX #$02
    JMP $8F47                           ; MODEM_SEND_CMD
    .byte $00, $00, $00, $00, $00, $00, $AA, $AA, $AA, $AA, $AA, $AA, $AA, $AA, $AA, $AA    ; $9FEB ................
    .byte $AA, $AA, $AA, $AA, $AA    ; $9FFB .....