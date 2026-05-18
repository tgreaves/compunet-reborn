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
    .byte 60 81 5E FE C3 C2 CD 38 30                ; $8000 `.^....80
    .byte 7C 80 A4 80 00 00 00 00 80 04 01 06 00 E0 04 E0; $8009 |...............
    .byte 00 E0 40 30 3A 00 00 00 00 00 00 00 00 00 00 00; $8019 ..@0:...........
    .byte 00 00 00 00 00 00 00 00 00                ; $8029 .........
    .byte 53 0D 43 00 02 A0 00 09 08 14 08 11 07 36 34 31; $8032 S\nC..........641
    .byte 32 03 14 3E 1A 00 03 24 01 FF FF 2A 43 4F 4E 1D; $8042 2..>...$...*CON.
    .byte 43 20 43 4E 45 54 0D 33 32 32 35 30 30 2F 31 30; $8052 C CNET\n322500/10
    .byte 30 0D 41 44 50 0D 4E 4F 0D 52 55 4E 0D 00 ; $8062 0\nADP\nNO\nRUN\n.
    .byte 00 00 00 00 00 00 00 00 00 00                   ; $8070 ..........

; --- Version strings ---
    .byte 0D 20 43 4F 4D 50 55 4E 45 54 20 54 45 52 4D 49; $807A \n COMPUNET TERMI
    .byte 4E 41 4C 20 31 2E 32 32 0D 00 20 53 45 50 54 45; $808A NAL 1.22\n. SEPTE
    .byte 4D 42 45 52 20 31 39 38 34 20 41 52 49 41 44 4E; $809A MBER 1984 ARIADN
    .byte 45 20 53 4F 46 54 57 41 52 45 20 4C 54 44 2E 0D; $80AA E SOFTWARE LTD.\n
    .byte 0D 00                                     ; $80BA \n.
    .byte 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00; $80BC ................
    .byte 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00; $80CC ................
    .byte 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00; $80DC ................
    .byte 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00; $80EC ................
    .byte 00 00 00 00                               ; $80FC ....
    .byte 4C A0 81 4C 55 83 4C 30 8D 4C C1 94 4C D5 94 4C; $8100 L..LU.L0.L..L..L
    .byte EF 8E 4C 47 8F 4C C9 93 4C D0 93 4C C8 90 4C DF; $8110 ..LG.L..L..L..L.
    .byte 90 4C D0 89 4C E2 89 4C BE 8A 4C EB 8A 4C E4 85; $8120 .L..L..L..L..L..
    .byte 4C 9B 84 4C 46 84 4C 77 84 4C 00 85 4C 9E 86 4C; $8130 L..LF.Lw.L..L..L
    .byte B7 90 4C 93 90 4C 7B 90 4C FB 8F 4C 02 90 4C 1E; $8140 ..L..L{.L..L..L.
    .byte 90 4C 8B 93 4C A8 94 4C 71 91 4C B2 91 4C CD 92; $8150 .L..L..Lq.L..L..

; ============================================================
; COLD_START
; ============================================================
COLD_START:
; Initialize C64 hardware and BASIC, then install command extensions
    20 84 FF      JSR $FF84 ; KERNAL_IOINIT
    20 87 FF      JSR $FF87 ; KERNAL_RAMTAS
    20 8A FF      JSR $FF8A ; KERNAL_RESTOR
    20 81 FF      JSR $FF81 ; KERNAL_CINT
    58            CLI 
    A9 01         LDA #$01
    8D 21 D0      STA $D021 ; VIC_BGCOL0 = white
    20 53 E4      JSR $E453 ; BASIC_RUNC
    20 BF E3      JSR $E3BF ; BASIC_MAIN
    20 22 E4      JSR $E422 ; BASIC_LINKPRG
; Copy 5-byte patch to $E000 (BASIC warm start vector area)
; This redirects BASIC's command input to our parser at $81BC
    A2 04         LDX #$04
    BD B7 81      LDA $81B7,X
    9D 00 E0      STA $E000,X
    CA            DEX 
    10 F7         BPL $817D
; Copy ROM to RAM at $8000-$9FFF (so it can be banked out later)
    A0 00         LDY #$00
    84 1D         STY $1D
    A9 80         LDA #$80
    85 1E         STA $1E
    B1 1D         LDA ($1D),Y
    91 1D         STA ($1D),Y
    C8            INY 
    D0 F9         BNE $818E
    E6 1E         INC $1E
    A5 1E         LDA $1E
    C9 A0         CMP #$A0
    D0 F1         BNE $818E
; Initialize terminal state
    20 35 83      JSR $8335

; ============================================================
; MAIN_INIT
; Called after COLD_START completes initialization.
; Prints version string, installs BASIC extension vector,
; then drops into BASIC READY prompt.
; User types CONNECT, EDITOR, CNLOAD, CNSAVE, or HELP.
; ============================================================
MAIN_INIT:
; Print " COMPUNET TERMINAL 1.22" version string
    A2 7A         LDX #$7A
    A0 80         LDY #$80
    20 B7 90      JSR $90B7 ; PRINT_STRING
; Install our command parser at $0302/$0303 (BASIC IGONE vector)
    A2 BC         LDX #$BC
    A0 81         LDY #$81
    8E 02 03      STX $0302
    8C 03 03      STY $0303
; Reset stack and enter BASIC
    A2 FB         LDX #$FB
    9A            TXS 
    4C 74 A4      JMP $A474 ; BASIC_READY

; --- BASIC stub bytes ---
; These 5 bytes are copied to $E000 to patch BASIC's warm start
; They form a JMP to the command parser at $81BC
    .byte 00 F6 F1 0E 00                            ; $81B7 .....

; ============================================================
; BASIC_CMD_PARSER - Intercepts BASIC input to handle custom commands
; Commands: EDITOR, CONNECT, CNLOAD, CNSAVE, HELP
; ============================================================
    20 60 A5      JSR $A560
    86 7A         STX $7A
    84 7B         STY $7B
    20 73 00      JSR $0073
    AA            TAX 
    F0 F3         BEQ $81BC
    A2 FF         LDX #$FF
    86 3A         STX $3A
    B0 03         BCS $81D2
    4C 9C A4      JMP $A49C
; Compare input buffer against command table at $8249
    A6 7A         LDX $7A
    A0 00         LDY #$00
    84 1A         STY $1A
    BD 00 02      LDA $0200,X
    38            SEC 
    F9 49 82      SBC $8249,Y
    D0 04         BNE $81E5
    E8            INX 
    C8            INY 
    D0 F3         BNE $81D8
    C9 80         CMP #$80
    F0 01         BEQ $81EA
    18            CLC 
    A5 1A         LDA $1A
    B0 12         BCS $8200
    88            DEY 
    A6 7A         LDX $7A
    E6 1A         INC $1A
    C9 05         CMP #$05
    F0 40         BEQ $8237
    C8            INY 
    B9 49 82      LDA $8249,Y
    10 FA         BPL $81F7
    C8            INY 
    D0 D8         BNE $81D8
; Command matched - save screen state and dispatch
    AE 20 D0      LDX $D020 ; VIC_BORDER
    8E 51 C1      STX $C151 ; workspace
    AE 21 D0      LDX $D021 ; VIC_BGCOL0
    8E 52 C1      STX $C152 ; workspace
    AE 86 02      LDX $0286
    8E 53 C1      STX $C153 ; workspace
    A2 36         LDX #$36
    86 01         STX $01
    20 3E 82      JSR $823E
; Restore screen state after command returns
    AD 51 C1      LDA $C151 ; workspace
    8D 20 D0      STA $D020 ; VIC_BORDER
    AD 52 C1      LDA $C152 ; workspace
    8D 21 D0      STA $D021 ; VIC_BGCOL0
    AD 53 C1      LDA $C153 ; workspace
    8D 86 02      STA $0286
    A2 37         LDX #$37
    86 01         STX $01
    A9 09         LDA #$09
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 74 A4      JMP $A474 ; BASIC_READY
; SYNTAX ERROR handler
    A2 FF         LDX #$FF
    A0 01         LDY #$01
    4C 86 A4      JMP $A486
; Dispatch via address table at $8269 (RTS trick)
    0A            ASL A
    A8            TAY 
    B9 6A 82      LDA $826A,Y
    48            PHA 
    B9 69 82      LDA $8269,Y
    48            PHA 
    60            RTS 

; --- BASIC Command Strings (high bit set on last char) ---
; 0: EDITOR  1: CONNECT  2: CNLOAD  3: CNSAVE  4: HELP
    .byte 45 44 49 54 4F D2 43 4F 4E 4E 45 43 D4 43 4E    ; $8249 EDITO.CONNEC.CN
    4C 4F 41      JMP $414F
    .byte C4 43 4E 53 41 56 C5                            ; $825B .CNSAV.
    48            PHA 
    45 4C         EOR $4C
    D0 4F         BNE $82B6
    46 C6         LSR $C6
    4C 83 2F      JMP $2F83
    .byte 8D AB 82 A8 82 74 82 9D 82                      ; $826C .....t...
    A2 7A         LDX #$7A
    A0 80         LDY #$80
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A2 94         LDX #$94
    A0 80         LDY #$80
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A2 06         LDX #$06
    A0 00         LDY #$00
    20 6A 90      JSR $906A
    B9 49 82      LDA $8249,Y
    08            PHP 
    29 7F         AND #$7F
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    C8            INY 
    28            PLP 
    10 F3         BPL $828A
    20 6E 90      JSR $906E
    CA            DEX 
    D0 EA         BNE $8287
    60            RTS 
    A2 83         LDX #$83
    A0 A4         LDY #$A4
    8E 02 03      STX $0302
    8C 03 03      STY $0303
    60            RTS 
    38            SEC 
    B0 01         BCS $82AD
    18            CLC 
    66 19         ROR $19
    20 AD 92      JSR $92AD
    B0 0F         BCS $82C3
    A9 08         LDA #$08
    48            PHA 
    24 19         BIT $19
    10 0B         BPL $82C6
    A9 07         LDA #$07
    A2 2E         LDX #$2E
    A0 83         LDY #$83
    D0 09         BNE $82CC
    A9 01         LDA #$01
    48            PHA 
    A9 04         LDA #$04
    A2 31         LDX #$31
    A0 83         LDY #$83
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    68            PLA 
    AA            TAX 
    A0 01         LDY #$01
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    A2 F0         LDX #$F0
    A0 9F         LDY #$9F
    86 1D         STX $1D
    84 1E         STY $1E
    24 19         BIT $19
    10 12         BPL $82F4
    A9 1D         LDA #$1D
    AE 36 80      LDX $8036
    AC 37 80      LDY $8037
    20 D8 FF      JSR $FFD8 ; KERNAL_SAVE
    20 5F 93      JSR $935F
    D0 25         BNE $8317
    F0 37         BEQ $832B
    20 35 83      JSR $8335
    A9 00         LDA #$00
    20 D5 FF      JSR $FFD5 ; KERNAL_LOAD
    90 06         BCC $8304
    20 5F 93      JSR $935F
    4C 0F 83      JMP $830F
    8E 36 80      STX $8036
    8C 37 80      STY $8037
    20 5F 93      JSR $935F
    F0 1C         BEQ $832B
    20 35 83      JSR $8335
    2C 56 C1      BIT $C156 ; workspace
    30 14         BMI $832B
    20 6E 90      JSR $906E
    A2 53         LDX #$53
    A0 93         LDY #$93
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A2 00         LDX #$00
    A0 02         LDY #$02
    20 B7 90      JSR $90B7 ; PRINT_STRING
    20 6E 90      JSR $906E
    4C E0 92      JMP $92E0
    .byte 40 30 3A 43 4E 45 54                            ; $832E @0:CNET
    A9 00         LDA #$00
    8D F0 9F      STA $9FF0
    A9 30         LDA #$30
    8D 00 A0      STA $A000
    8D 01 A0      STA $A001
    A2 02         LDX #$02
    A0 A0         LDY #$A0
    8E 36 80      STX $8036
    8C 37 80      STY $8037
    60            RTS 
    .byte A9 FF 8D 4B 80 8D                               ; $834D ...K..
    4C 80 20      JMP $2080
    .byte DC 89                                           ; $8356 ..
    AD 4B 80      LDA $804B
    85 1D         STA $1D
    AD 4C 80      LDA $804C
    85 1E         STA $1E
    A0 00         LDY #$00
    A2 01         LDX #$01
    06 1E         ASL $1E
    26 1D         ROL $1D
    90 16         BCC $8382
    E0 0E         CPX #$0E
    D0 07         BNE $8377
    20 4B 87      JSR $874B
    A2 0E         LDX #$0E
    B0 0B         BCS $8382
    8A            TXA 
    99 75 C1      STA $C175,Y
    BD FD 83      LDA $83FD,X
    99 66 C1      STA $C166,Y
    C8            INY 
    E8            INX 
    E0 0F         CPX #$0F
    D0 DF         BNE $8366
    8C 65 C1      STY $C165 ; workspace
    A2 AA         LDX #$AA
    A0 83         LDY #$83
    20 C9 93      JSR $93C9 ; PROTOCOL_RESET
    A9 01         LDA #$01
    8D 33 80      STA $8033
    A9 08         LDA #$08
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A2 65         LDX #$65
    A0 C1         LDY #$C1
    20 D0 93      JSR $93D0 ; PROTOCOL_CLEANUP
    B0 F2         BCS $8396
    20 0C 84      JSR $840C
    4C 96 83      JMP $8396

; --- Duckshoot menu text ---
    .byte 20 48 45 4C 50 20 20 45 44 49 54 20 20 4C 41 53; $83AA  HELP  EDIT  LAS
    .byte 54 20 20 4E 45 58 54 20 20 4E 45 57 20 20 20 43; $83BA T  NEXT  NEW   C
    .byte 4F 50 59 20 45 52 41 53 45 20 20 47 45 54 20 20; $83CA OPY ERASE  GET  
    .byte 20 50 55 54 20 20 53 54 4F 52 45 20 50 52 49 4E; $83DA  PUT  STORE PRIN
    .byte 54 20 20 46 52 45 45 20 20 44 4F 53 20 20 52 45; $83EA T  FREE  DOS  RE
    .byte 54 55 52 4E 00 06 0C 12 18 1E             ; $83FA TURN......
    .byte 24 2A 30 36 3C 42 4E                            ; $8404 $*06<BN
    48            PHA 
    AE 33 80      LDX $8033
    BD 74 C1      LDA $C174,X
    0A            ASL A
    AA            TAX 
    BD 1C 84      LDA $841C,X
    48            PHA 
    BD 1B 84      LDA $841B,X
    48            PHA 
    60            RTS 
    .byte 38 84 5F 87 45 84 76 84 94 84 CA 84 D3 84 FF 84 ; $841D 8._.E.v.........
    .byte 40                                              ; $842D @
    85 7F         STA $7F
    85 DD         STA $DD
    85 9B         STA $9B
    89            .byte $89
    .byte 5A 87 9D                                        ; $8435 Z..
    86 A2         STX $A2
    89            .byte $89
    A0 95         LDY #$95
    20 E2 89      JSR $89E2 ; FRAME_BUF_WRITE
    20 FB 8F      JSR $8FFB ; WAIT_KEYPRESS
    4C DC 89      JMP $89DC

; ============================================================
; KEYBOARD_SCAN
; ============================================================
KEYBOARD_SCAN:
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    EC 15 80      CPX $8015
    D0 06         BNE $8457
    CC 16 80      CPY $8016
    D0 01         BNE $8457
    60            RTS 
    86 1D         STX $1D
    84 1E         STY $1E
    A5 1D         LDA $1D
    D0 02         BNE $8461
    C6 1E         DEC $1E
    C6 1D         DEC $1D
    20 B6 8C      JSR $8CB6
    C9 00         CMP #$00
    D0 F1         BNE $845B
    A5 1D         LDA $1D
    8D 19 80      STA $8019
    A5 1E         LDA $1E
    8D 1A 80      STA $801A
    4C DC 89      JMP $89DC

; ============================================================
; KEY_DISPATCH
; ============================================================
KEY_DISPATCH:
    20 AB 8C      JSR $8CAB
    20 C5 8C      JSR $8CC5
    A6 1D         LDX $1D
    A4 1E         LDY $1E
    EC 17 80      CPX $8017
    D0 06         BNE $848C
    CC 18 80      CPY $8018
    D0 01         BNE $848C
    60            RTS 
    8E 19 80      STX $8019
    8C 1A 80      STY $801A
    4C DC 89      JMP $89DC
    20 9B 84      JSR $849B ; INPUT_HANDLER
    4C DC 89      JMP $89DC

; ============================================================
; INPUT_HANDLER
; ============================================================
INPUT_HANDLER:
    18            CLC 
    AD 17 80      LDA $8017
    8D 19 80      STA $8019
    85 1D         STA $1D
    69 04         ADC #$04
    AA            TAX 
    AD 18 80      LDA $8018
    8D 1A 80      STA $801A
    85 1E         STA $1E
    69 00         ADC #$00
    90 06         BCC $84B9
    20 40 8C      JSR $8C40
    4C 9B 84      JMP $849B ; INPUT_HANDLER
    8E 17 80      STX $8017
    8D 18 80      STA $8018
    20 05 8C      JSR $8C05
    8A            TXA 
    20 C0 8B      JSR $8BC0
    A9 00         LDA #$00
    4C C0 8B      JMP $8BC0
    20 9B 84      JSR $849B ; INPUT_HANDLER
    20 BE 8A      JSR $8ABE ; DISK_LOAD
    4C DC 89      JMP $89DC
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    20 70 8C      JSR $8C70
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    EC 17 80      CPX $8017
    D0 05         BNE $84ED
    CC 18 80      CPY $8018
    F0 03         BEQ $84F0
    4C DC 89      JMP $89DC
    EC 15 80      CPX $8015
    D0 05         BNE $84FA
    CC 16 80      CPY $8016
    F0 03         BEQ $84FD
    4C 46 84      JMP $8446 ; KEYBOARD_SCAN
    4C 95 84      JMP $8495

; ============================================================
; COMMAND_EXEC
; ============================================================
COMMAND_EXEC:
    A2 3D         LDX #$3D
    A0 85         LDY #$85
    20 93 90      JSR $9093 ; CURSOR_HOME
    A9 52         LDA #$52
    A2 53         LDX #$53
    20 71 91      JSR $9171 ; FILE_UPLOAD
    B0 66         BCS $8576
    20 95 84      JSR $8495
    A9 8C         LDA #$8C
    8D 40 C1      STA $C140 ; workspace
    A9 8A         LDA #$8A
    8D 41 C1      STA $C141 ; workspace
    A2 08         LDX #$08
    20 C6 FF      JSR $FFC6 ; KERNAL_CHKIN
    B0 13         BCS $8537
    20 F0 89      JSR $89F0
    B0 0E         BCS $8537
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    20 BE 8A      JSR $8ABE ; DISK_LOAD
    AD 5D C1      LDA $C15D ; workspace
    F0 DC         BEQ $8510
    4C CD 92      JMP $92CD ; FRAME_STORE
    20 E7 FF      JSR $FFE7
    4C D4 84      JMP $84D4
    .byte 47 45 54 00                                     ; $853D GET.
    A2 7C         LDX #$7C
    A0 85         LDY #$85
    20 93 90      JSR $9093 ; CURSOR_HOME
    A9 57         LDA #$57
    A2 53         LDX #$53
    20 71 91      JSR $9171 ; FILE_UPLOAD
    B0 25         BCS $8576
    20 AB 8C      JSR $8CAB
    A2 08         LDX #$08
    20 C9 FF      JSR $FFC9 ; KERNAL_CHKOUT
    B0 1B         BCS $8576
    20 D4 85      JSR $85D4
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    B0 13         BCS $8576
    E6 1D         INC $1D
    D0 02         BNE $8569
    E6 1E         INC $1E
    20 B6 8C      JSR $8CB6
    C9 00         CMP #$00
    D0 EE         BNE $855E
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    4C CD 92      JMP $92CD ; FRAME_STORE
    20 E7 FF      JSR $FFE7
    4C DC 89      JMP $89DC
    .byte 50 55 54 00                                     ; $857C PUT.
    A2 CE         LDX #$CE
    A0 85         LDY #$85
    20 93 90      JSR $9093 ; CURSOR_HOME
    A9 57         LDA #$57
    A2 53         LDX #$53
    20 71 91      JSR $9171 ; FILE_UPLOAD
    B0 E6         BCS $8576
    AE 15 80      LDX $8015
    AC 16 80      LDY $8016
    86 1D         STX $1D
    84 1E         STY $1E
    A2 08         LDX #$08
    20 C9 FF      JSR $FFC9 ; KERNAL_CHKOUT
    B0 D5         BCS $8576
    20 D4 85      JSR $85D4
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    B0 CD         BCS $8576
    E6 1D         INC $1D
    D0 02         BNE $85AF
    E6 1E         INC $1E
    20 B6 8C      JSR $8CB6
    C9 00         CMP #$00
    D0 EE         BNE $85A4
    A6 1D         LDX $1D
    EC 17 80      CPX $8017
    D0 07         BNE $85C4
    A6 1E         LDX $1E
    EC 18 80      CPX $8018
    F0 AC         BEQ $8570
    20 D4 85      JSR $85D4
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    B0 AA         BCS $8576
    90 D6         BCC $85A4
    53            .byte $53
    .byte 54 4F 52 45 00                                  ; $85CF TORE.
    A9 00         LDA #$00
    2C 56 C1      BIT $C156 ; workspace
    10 02         BPL $85DD
    A9 01         LDA #$01
    60            RTS 
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A

; ============================================================
; SCREEN_DRAW
; ============================================================
SCREEN_DRAW:
    86 1D         STX $1D
    84 1E         STY $1E
    A9 81         LDA #$81
    8D 40 C1      STA $C140 ; workspace
    A9 8A         LDA #$8A
    8D 41 C1      STA $C141 ; workspace
    20 7E 8A      JSR $8A7E
    20 7E 8A      JSR $8A7E
    20 7E 8A      JSR $8A7E
    A9 00         LDA #$00
    8D 5F C1      STA $C15F ; workspace
    20 4B 8A      JSR $8A4B
    8D 5E C1      STA $C15E ; workspace
    A9 04         LDA #$04
    AA            TAX 
    A0 00         LDY #$00
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    A9 00         LDA #$00
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    20 C0 FF      JSR $FFC0 ; KERNAL_OPEN
    A2 04         LDX #$04
    20 C9 FF      JSR $FFC9 ; KERNAL_CHKOUT
    B0 5A         BCS $8677
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    C9 03         CMP #$03
    F0 50         BEQ $8674
    20 4B 8A      JSR $8A4B
    C9 00         CMP #$00
    F0 49         BEQ $8674
    C9 0D         CMP #$0D
    D0 08         BNE $8637
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    B0 43         BCS $8677
    4C 1D 86      JMP $861D
    48            PHA 
    A2 14         LDX #$14
    20 6A 90      JSR $906A
    B0 38         BCS $8677
    CA            DEX 
    D0 F8         BNE $863A
    2C 5E C1      BIT $C15E ; workspace
    30 07         BMI $864E
    A9 11         LDA #$11
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    B0 29         BCS $8677
    68            PLA 
    D0 12         BNE $8663
    20 4B 8A      JSR $8A4B
    C9 00         CMP #$00
    F0 1C         BEQ $8674
    C9 0D         CMP #$0D
    D0 07         BNE $8663
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    B0 16         BCS $8677
    90 BA         BCC $861D
    A2 0F         LDX #$0F
    DD F5 8B      CMP $8BF5,X
    F0 E7         BEQ $8651
    CA            DEX 
    10 F8         BPL $8665
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    B0 05         BCS $8677
    90 DD         BCC $8651
    20 6E 90      JSR $906E
    08            PHP 
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    A9 04         LDA #$04
    20 C3 FF      JSR $FFC3 ; KERNAL_CLOSE
    28            PLP 
    90 20         BCC $86A3
    A2 90         LDX #$90
    A0 86         LDY #$86
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG
    20 02 90      JSR $9002 ; CLEAR_STATUS
    4C 8B 93      JMP $938B ; PROTOCOL_STATE_INIT
    .byte 50 52 49 4E 54 45 52                            ; $8690 PRINTER
    20 45 52      JSR $5245
    52            .byte $52
    .byte 4F 52 00                                        ; $869B OR.

; ============================================================
; FILE_OPS
; ============================================================
FILE_OPS:
    20 4B 87      JSR $874B
    90 01         BCC $86A4
    60            RTS 
    AD 13 80      LDA $8013
    8D 21 D0      STA $D021 ; VIC_BGCOL0
    AD 14 80      LDA $8014
    8D 86 02      STA $0286
    A2 2A         LDX #$2A
    A0 87         LDY #$87
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A6 7A         LDX $7A
    A4 7B         LDY $7B
    8E 61 C1      STX $C161 ; workspace
    8C 62 C1      STY $C162 ; workspace
    A9 40         LDA #$40
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A2 26         LDX #$26
    A9 00         LDA #$00
    A8            TAY 
    18            CLC 
    20 C8 90      JSR $90C8 ; SETUP_INPUT_PARAMS
    A2 00         LDX #$00
    A0 02         LDY #$02
    86 7A         STX $7A
    84 7B         STY $7B
    E8            INX 
    20 DF 90      JSR $90DF ; INPUT_LINE
    90 0D         BCC $86EA
    AE 61 C1      LDX $C161 ; workspace
    AC 62 C1      LDY $C162 ; workspace
    86 7A         STX $7A
    84 7B         STY $7B
    4C DC 89      JMP $89DC
    20 6E 90      JSR $906E
    A9 00         LDA #$00
    A4 1A         LDY $1A
    99 01 02      STA $0201,Y
    AE 14 03      LDX $0314
    AC 15 03      LDY $0315
    8E 63 C1      STX $C163 ; workspace
    8C 64 C1      STY $C164 ; workspace
    A2 31         LDX #$31
    A0 EA         LDY #$EA
    78            SEI 
    8E 14 03      STX $0314
    8C 15 03      STY $0315
    58            CLI 
    A2 37         LDX #$37
    86 01         STX $01
    A9 40         LDA #$40
    20 10 CD      JSR $CD10
    A2 36         LDX #$36
    86 01         STX $01
    AE 63 C1      LDX $C163 ; workspace
    AC 64 C1      LDY $C164 ; workspace
    78            SEI 
    8E 14 03      STX $0314
    8C 15 03      STY $0315
    58            CLI 
    4C C1 86      JMP $86C1
    .byte 93                                              ; $872A .
    0E 92 11      ASL $1192
    C9 4E         CMP #$4E
    50 55         BVC $8787
    54            .byte $54
    20 C4 CF      JSR $CFC4
    D3            .byte $D3
    20 43 4F      JSR $4F43
    4D 4D 41      EOR $414D
    4E 44 53      LSR $5344
    20 4F 52      JSR $524F
    20 D3 D4      JSR $D4D3
    CF            .byte $CF
    .byte D0 0D 0D 00                                     ; $8747 ....
    A2 02         LDX #$02
    B5 7C         LDA $7C,X
    DD DE CC      CMP $CCDE,X
    D0 05         BNE $8759
    CA            DEX 
    10 F6         BPL $874D
    18            CLC 
    60            RTS 
    38            SEC 
    60            RTS 
    .byte 68 68                                           ; $875B hh
    4C 62 90      JMP $9062
    A9 09         LDA #$09
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 02         LDA #$02
    8D 86 02      STA $0286
    A2 19         LDX #$19
    B5 D9         LDA $D9,X
    09 80         ORA #$80
    95 D9         STA $D9,X
    CA            DEX 
    10 F7         BPL $876C
    18            CLC 
    6E 5B C1      ROR $C15B ; workspace
    A2 9B         LDX #$9B
    A0 88         LDY #$88
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG
    20 66 90      JSR $9066
    A9 00         LDA #$00
    85 D4         STA $D4
    85 D8         STA $D8
    20 26 8C      JSR $8C26
    A5 D6         LDA $D6
    C9 18         CMP #$18
    D0 05         BNE $8797
    A9 91         LDA #$91
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A4 D3         LDY $D3
    B1 D1         LDA ($D1),Y
    8D 57 C1      STA $C157 ; workspace
    20 24 EA      JSR $EA24
    B1 F3         LDA ($F3),Y
    2C 5B C1      BIT $C15B ; workspace
    10 03         BPL $87AB
    AD 86 02      LDA $0286
    8D 58 C1      STA $C158 ; workspace
    A9 FF         LDA #$FF
    8D 59 C1      STA $C159 ; workspace
    8D 5A C1      STA $C15A ; workspace
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    D0 2A         BNE $87E5
    EE 59 C1      INC $C159 ; workspace
    D0 F6         BNE $87B6
    EE 5A C1      INC $C15A ; workspace
    D0 F1         BNE $87B6
    A9 E0         LDA #$E0
    8D 5A C1      STA $C15A ; workspace
    A4 D3         LDY $D3
    B1 D1         LDA ($D1),Y
    49 80         EOR #$80
    91 D1         STA ($D1),Y
    AE 86 02      LDX $0286
    8A            TXA 
    51 F3         EOR ($F3),Y
    29 0F         AND #$0F
    D0 03         BNE $87DF
    AE 58 C1      LDX $C158 ; workspace
    8A            TXA 
    91 F3         STA ($F3),Y
    4C B6 87      JMP $87B6
    48            PHA 
    AD 57 C1      LDA $C157 ; workspace
    A4 D3         LDY $D3
    91 D1         STA ($D1),Y
    AD 58 C1      LDA $C158 ; workspace
    91 F3         STA ($F3),Y
    68            PLA 
    C9 03         CMP #$03
    D0 73         BNE $886A
    20 8B 93      JSR $938B ; PROTOCOL_STATE_INIT
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    20 70 8C      JSR $8C70
    AE 17 80      LDX $8017
    AC 18 80      LDY $8018
    20 EB 8A      JSR $8AEB ; DISK_SAVE
    AE 17 80      LDX $8017
    AC 18 80      LDY $8018
    86 1F         STX $1F
    84 20         STY $20
    A5 1D         LDA $1D
    D0 02         BNE $881C
    C6 1E         DEC $1E
    C6 1D         DEC $1D
    A5 1D         LDA $1D
    8D 17 80      STA $8017
    A5 1E         LDA $1E
    8D 18 80      STA $8018
    EC 19 80      CPX $8019
    D0 05         BNE $8832
    CC 1A 80      CPY $801A
    F0 37         BEQ $8869
    A0 00         LDY #$00
    A2 34         LDX #$34
    78            SEI 
    86 01         STX $01
    B1 1F         LDA ($1F),Y
    A2 36         LDX #$36
    86 01         STX $01
    58            CLI 
    91 1D         STA ($1D),Y
    A5 1D         LDA $1D
    D0 02         BNE $8848
    C6 1E         DEC $1E
    C6 1D         DEC $1D
    A5 1F         LDA $1F
    D0 02         BNE $8850
    C6 20         DEC $20
    C6 1F         DEC $1F
    A6 1F         LDX $1F
    EC 19 80      CPX $8019
    D0 DB         BNE $8834
    A6 20         LDX $20
    EC 1A 80      CPX $801A
    D0 D4         BNE $8834
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    20 EB 8A      JSR $8AEB ; DISK_SAVE
    60            RTS 
    C9 83         CMP #$83
    D0 03         BNE $8871
    4C DC 89      JMP $89DC
    C9 85         CMP #$85
    90 1A         BCC $888F
    C9 8D         CMP #$8D
    90 2F         BCC $88A8
    C9 93         CMP #$93
    D0 06         BNE $8883
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 79 87      JMP $8779
    C9 94         CMP #$94
    D0 08         BNE $888F
    A9 20         LDA #$20
    A0 27         LDY #$27
    91 D1         STA ($D1),Y
    A9 94         LDA #$94
    C9 A0         CMP #$A0
    D0 02         BNE $8895
    A9 20         LDA #$20
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 83 87      JMP $8783
    .byte 53 54 4F 50                                     ; $889B STOP
    20 54 4F      JSR $4F54
    20 45 58      JSR $5845
    49 54         EOR #$54
    00            BRK 
    38            SEC 
    E9 85         SBC #$85
    0A            ASL A
    AA            TAX 
    20 B3 88      JSR $88B3
    4C 83 87      JMP $8783
    BD BD 88      LDA $88BD,X
    48            PHA 
    BD BC 88      LDA $88BC,X
    48            PHA 
    60            RTS 
    .byte BA 88 F0 88 DE 88 CB 88 BA 88 3D 89 E7 88 D1 88 ; $88BC ..........=.....
    .byte EE 21 D0                                        ; $88CC .!.
    4C D5 88      JMP $88D5
    .byte EE                                              ; $88D2 .
    20 D0 20      JSR $20D0
    8B            .byte $8B
    .byte 93                                              ; $88D7 .
    A2 9B         LDX #$9B
    A0 88         LDY #$88
    4C 7B 90      JMP $907B ; PRINT_STATUS_MSG
    AD 8A 02      LDA $028A
    49 80         EOR #$80
    8D 8A 02      STA $028A
    60            RTS 
    AD 5B C1      LDA $C15B ; workspace
    49 80         EOR #$80
    8D 5B C1      STA $C15B ; workspace
    60            RTS 
    .byte A6 D6 F0                                        ; $88F1 ...
    48            PHA 
    A5 D1         LDA $D1
    85 1D         STA $1D
    38            SEC 
    E9 28         SBC #$28
    85 D1         STA $D1
    85 1F         STA $1F
    A5 D2         LDA $D2
    85 1E         STA $1E
    E9 00         SBC #$00
    85 D2         STA $D2
    85 20         STA $20
    C6 D6         DEC $D6
    20 83 89      JSR $8983
    A0 27         LDY #$27
    B1 1D         LDA ($1D),Y
    91 1F         STA ($1F),Y
    B1 21         LDA ($21),Y
    91 23         STA ($23),Y
    88            DEY 
    10 F5         BPL $8911
    E8            INX 
    E0 18         CPX #$18
    F0 13         BEQ $8934
    18            CLC 
    A5 1D         LDA $1D
    85 1F         STA $1F
    69 28         ADC #$28
    85 1D         STA $1D
    A5 1E         LDA $1E
    85 20         STA $20
    90 DC         BCC $890C
    E6 1E         INC $1E
    B0 D8         BCS $890C
    A9 20         LDA #$20
    A0 27         LDY #$27
    91 1D         STA ($1D),Y
    88            DEY 
    10 FB         BPL $8938
    60            RTS 
    A9 98         LDA #$98
    85 1D         STA $1D
    A9 07         LDA #$07
    85 1E         STA $1E
    A9 70         LDA #$70
    85 1F         STA $1F
    A9 07         LDA #$07
    85 20         STA $20
    A2 17         LDX #$17
    E4 D6         CPX $D6
    D0 0A         BNE $895E
    A9 20         LDA #$20
    A0 27         LDY #$27
    91 1D         STA ($1D),Y
    88            DEY 
    10 FB         BPL $8958
    60            RTS 
    20 83 89      JSR $8983
    A0 27         LDY #$27
    B1 1F         LDA ($1F),Y
    91 1D         STA ($1D),Y
    B1 23         LDA ($23),Y
    91 21         STA ($21),Y
    88            DEY 
    10 F5         BPL $8963
    A5 1F         LDA $1F
    85 1D         STA $1D
    38            SEC 
    E9 28         SBC #$28
    85 1F         STA $1F
    A5 20         LDA $20
    85 1E         STA $1E
    E9 00         SBC #$00
    85 20         STA $20
    CA            DEX 
    4C 50 89      JMP $8950
    A5 1D         LDA $1D
    85 21         STA $21
    A5 1F         LDA $1F
    85 23         STA $23
    A5 1E         LDA $1E
    29 03         AND #$03
    09 D8         ORA #$D8
    85 22         STA $22
    A5 20         LDA $20
    29 03         AND #$03
    09 D8         ORA #$D8
    85 24         STA $24
    60            RTS 
    A2 CF         LDX #$CF
    A0 89         LDY #$89
    20 93 90      JSR $9093 ; CURSOR_HOME
    38            SEC 
    A9 00         LDA #$00
    ED 17 80      SBC $8017
    AA            TAX 
    A9 00         LDA #$00
    ED 18 80      SBC $8018
    A0 37         LDY #$37
    84 01         STY $01
    20 CD BD      JSR $BDCD
    A0 36         LDY #$36
    84 01         STY $01
    A2 C4         LDX #$C4
    A0 89         LDY #$89
    20 B7 90      JSR $90B7 ; PRINT_STRING
    4C 02 90      JMP $9002 ; CLEAR_STATUS
    20 43 48      JSR $4843
    41 52         EOR ($52,X)
    53            .byte $53
    20 46 52      JSR $5246
    45 45         EOR $45
    00            BRK 

; ============================================================
; FRAME_BUF_READ
; ============================================================
FRAME_BUF_READ:
    A9 AD         LDA #$AD
    8D 40 C1      STA $C140 ; workspace
    A9 8A         LDA #$8A
    8D 41 C1      STA $C141 ; workspace
    D0 14         BNE $89F0
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A

; ============================================================
; FRAME_BUF_WRITE
; ============================================================
FRAME_BUF_WRITE:
    86 1D         STX $1D
    84 1E         STY $1E
    A9 81         LDA #$81
    8D 40 C1      STA $C140 ; workspace
    A9 8A         LDA #$8A
    8D 41 C1      STA $C141 ; workspace
    A9 00         LDA #$00
    8D 5D C1      STA $C15D ; workspace
    20 7E 8A      JSR $8A7E
    B0 41         BCS $8A3B
    8D 35 80      STA $8035
    20 50 90      JSR $9050
    20 7E 8A      JSR $8A7E
    B0 36         BCS $8A3B
    8D 20 D0      STA $D020 ; VIC_BORDER
    20 8B 93      JSR $938B ; PROTOCOL_STATE_INIT
    20 7E 8A      JSR $8A7E
    B0 2B         BCS $8A3B
    8D 21 D0      STA $D021 ; VIC_BGCOL0
    A9 00         LDA #$00
    8D 5F C1      STA $C15F ; workspace
    20 4B 8A      JSR $8A4B
    B0 1E         BCS $8A3B
    C9 00         CMP #$00
    F0 16         BEQ $8A37
    C9 0D         CMP #$0D
    D0 0C         BNE $8A31
    20 26 8C      JSR $8C26
    90 05         BCC $8A2F
    A9 91         LDA #$91
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 0D         LDA #$0D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 18 8A      JMP $8A18
    20 26 8C      JSR $8C26
    18            CLC 
    A9 00         LDA #$00
    85 D4         STA $D4
    60            RTS 
    .byte A0 00 91 D1 E6 D1 D0 02 E6 D2 60                ; $8A40 ..........`
    AD 5F C1      LDA $C15F ; workspace
    F0 08         BEQ $8A58
    CE 5F C1      DEC $C15F ; workspace
    AD 60 C1      LDA $C160 ; workspace
    18            CLC 
    60            RTS 
    20 7E 8A      JSR $8A7E
    B0 20         BCS $8A7D
    C9 06         CMP #$06
    D0 04         BNE $8A65
    A9 20         LDA #$20
    D0 09         BNE $8A6E
    C9 07         CMP #$07
    D0 13         BNE $8A7C
    20 7E 8A      JSR $8A7E
    B0 0F         BCS $8A7D
    8D 60 C1      STA $C160 ; workspace
    20 7E 8A      JSR $8A7E
    B0 07         BCS $8A7D
    8D 5F C1      STA $C15F ; workspace
    AD 60 C1      LDA $C160 ; workspace
    18            CLC 
    60            RTS 
    6C 40 C1      JMP ($C140)
    20 B6 8C      JSR $8CB6
    E6 1D         INC $1D
    D0 02         BNE $8A8A
    E6 1E         INC $1E
    18            CLC 
    60            RTS 
    AE 5D C1      LDX $C15D ; workspace
    F0 03         BEQ $8A94
    A9 00         LDA #$00
    60            RTS 
    A2 08         LDX #$08
    20 C6 FF      JSR $FFC6 ; KERNAL_CHKIN
    B0 11         BCS $8AAC
    20 CF FF      JSR $FFCF ; KERNAL_CHRIN
    B0 0C         BCS $8AAC
    C9 01         CMP #$01
    D0 02         BNE $8AA6
    A9 00         LDA #$00
    A6 90         LDX $90
    8E 5D C1      STX $C15D ; workspace
    18            CLC 
    60            RTS 
    .byte 2C 5D C1 10 04                                  ; $8AAD ,]...
    A9 00         LDA #$00
    18            CLC 
    60            RTS 
    20 CC 96      JSR $96CC
    6E 5D C1      ROR $C15D ; workspace
    18            CLC 
    60            RTS 

; ============================================================
; DISK_LOAD
; ============================================================
DISK_LOAD:
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    20 70 8C      JSR $8C70
    AE 17 80      LDX $8017
    AC 18 80      LDY $8018
    20 EB 8A      JSR $8AEB ; DISK_SAVE
    AE 17 80      LDX $8017
    AC 18 80      LDY $8018
    8E 19 80      STX $8019
    8C 1A 80      STY $801A
    A4 1E         LDY $1E
    A6 1D         LDX $1D
    D0 01         BNE $8AE3
    88            DEY 
    CA            DEX 
    8E 17 80      STX $8017
    8C 18 80      STY $8018
    60            RTS 

; ============================================================
; DISK_SAVE
; ============================================================
DISK_SAVE:
    86 1D         STX $1D
    84 1E         STY $1E
    20 05 8C      JSR $8C05
    86 19         STX $19
    A9 00         LDA #$00
    85 1A         STA $1A
    A9 FF         LDA #$FF
    8D 58 C1      STA $C158 ; workspace
    20 66 90      JSR $9066
    20 24 EA      JSR $EA24
    A9 12         LDA #$12
    8D 5C C1      STA $C15C ; workspace
    A0 00         LDY #$00
    B1 D1         LDA ($D1),Y
    C9 20         CMP #$20
    D0 07         BNE $8B17
    C8            INY 
    C0 28         CPY #$28
    D0 F5         BNE $8B0A
    F0 52         BEQ $8B69
    C0 00         CPY #$00
    F0 0C         BEQ $8B27
    84 D3         STY $D3
    A9 20         LDA #$20
    20 7D 8B      JSR $8B7D
    A4 D3         LDY $D3
    88            DEY 
    84 1A         STY $1A
    A4 D3         LDY $D3
    B1 D1         LDA ($D1),Y
    48            PHA 
    C9 20         CMP #$20
    F0 15         BEQ $8B45
    B1 F3         LDA ($F3),Y
    29 0F         AND #$0F
    CD 58 C1      CMP $C158 ; workspace
    F0 0A         BEQ $8B43
    8D 58 C1      STA $C158 ; workspace
    A8            TAY 
    B9 F5 8B      LDA $8BF5,Y
    20 7D 8B      JSR $8B7D
    68            PLA 
    48            PHA 
    4D 5C C1      EOR $C15C ; workspace
    10 0E         BPL $8B58
    AD 5C C1      LDA $C15C ; workspace
    20 7D 8B      JSR $8B7D
    AD 5C C1      LDA $C15C ; workspace
    49 80         EOR #$80
    8D 5C C1      STA $C15C ; workspace
    68            PLA 
    20 A8 94      JSR $94A8 ; MODEM_STATUS_CHECK
    20 7D 8B      JSR $8B7D
    A4 D3         LDY $D3
    C0 27         CPY #$27
    F0 04         BEQ $8B69
    E6 D3         INC $D3
    D0 BE         BNE $8B27
    20 6E 90      JSR $906E
    20 7D 8B      JSR $8B7D
    A5 D6         LDA $D6
    C9 18         CMP #$18
    F0 03         BEQ $8B78
    4C 00 8B      JMP $8B00
    A9 00         LDA #$00
    4C C0 8B      JMP $8BC0
    C5 19         CMP $19
    D0 03         BNE $8B84
    E6 1A         INC $1A
    60            RTS 
    A6 19         LDX $19
    85 19         STA $19
    C9 0D         CMP #$0D
    D0 09         BNE $8B95
    E0 20         CPX #$20
    D0 05         BNE $8B95
    2C 5C C1      BIT $C15C ; workspace
    10 26         BPL $8BBB
    8A            TXA 
    A6 1A         LDX $1A
    E0 02         CPX #$02
    B0 08         BCS $8BA4
    20 C0 8B      JSR $8BC0
    CA            DEX 
    10 FA         BPL $8B9C
    30 17         BMI $8BBB
    C9 20         CMP #$20
    D0 04         BNE $8BAC
    A9 06         LDA #$06
    D0 07         BNE $8BB3
    AA            TAX 
    A9 07         LDA #$07
    20 C0 8B      JSR $8BC0
    8A            TXA 
    20 C0 8B      JSR $8BC0
    A5 1A         LDA $1A
    20 C0 8B      JSR $8BC0
    A9 00         LDA #$00
    85 1A         STA $1A
    60            RTS 
    A0 00         LDY #$00
    91 1D         STA ($1D),Y
    E6 1D         INC $1D
    F0 01         BEQ $8BC9
    60            RTS 
    E6 1E         INC $1E
    F0 01         BEQ $8BCE
    60            RTS 
    48            PHA 
    8A            TXA 
    48            PHA 
    20 40 8C      JSR $8C40
    20 B6 8C      JSR $8CB6
    A0 00         LDY #$00
    91 1F         STA ($1F),Y
    E6 1F         INC $1F
    D0 02         BNE $8BE1
    E6 20         INC $20
    E6 1D         INC $1D
    D0 EF         BNE $8BD4
    E6 1E         INC $1E
    D0 EB         BNE $8BD4
    A5 1F         LDA $1F
    85 1D         STA $1D
    A5 20         LDA $20
    85 1E         STA $1E
    68            PLA 
    AA            TAX 
    68            PLA 
    60            RTS 
    .byte 90 05 1C 9F 9C 1E 1F 9E 81 95 96 97 98 99 9A 9B ; $8BF5 ................
    A9 00         LDA #$00
    20 C0 8B      JSR $8BC0
    AD 20 D0      LDA $D020 ; VIC_BORDER
    09 F0         ORA #$F0
    20 C0 8B      JSR $8BC0
    AD 21 D0      LDA $D021 ; VIC_BGCOL0
    09 F0         ORA #$F0
    20 C0 8B      JSR $8BC0
    A2 0E         LDX #$0E
    AD 18 D0      LDA $D018 ; VIC_MEMSETUP
    29 02         AND #$02
    D0 02         BNE $8C25
    A2 8E         LDX #$8E
    60            RTS 
    A5 D3         LDA $D3
    C9 28         CMP #$28
    F0 02         BEQ $8C2E
    18            CLC 
    60            RTS 
    38            SEC 
    20 F0 FF      JSR $FFF0
    A0 00         LDY #$00
    B5 D9         LDA $D9,X
    09 80         ORA #$80
    95 D9         STA $D9,X
    18            CLC 
    20 F0 FF      JSR $FFF0
    38            SEC 
    60            RTS 
    AE 15 80      LDX $8015
    AC 16 80      LDY $8016
    20 70 8C      JSR $8C70
    AE 19 80      LDX $8019
    AC 1A 80      LDY $801A
    EC 15 80      CPX $8015
    D0 05         BNE $8C59
    CC 16 80      CPY $8016
    F0 16         BEQ $8C6F
    38            SEC 
    8A            TXA 
    E5 1D         SBC $1D
    AA            TAX 
    98            TYA 
    E5 1E         SBC $1E
    A8            TAY 
    18            CLC 
    8A            TXA 
    65 1F         ADC $1F
    8D 19 80      STA $8019
    98            TYA 
    65 20         ADC $20
    8D 1A 80      STA $801A
    60            RTS 
    86 1D         STX $1D
    86 1F         STX $1F
    84 1E         STY $1E
    84 20         STY $20
    20 C5 8C      JSR $8CC5
    20 B6 8C      JSR $8CB6
    A0 00         LDY #$00
    91 1F         STA ($1F),Y
    D0 0E         BNE $8C92
    A5 1D         LDA $1D
    CD 17 80      CMP $8017
    D0 07         BNE $8C92
    A5 1E         LDA $1E
    CD 18 80      CMP $8018
    F0 0E         BEQ $8CA0
    E6 1D         INC $1D
    D0 02         BNE $8C98
    E6 1E         INC $1E
    E6 1F         INC $1F
    D0 DF         BNE $8C7B
    E6 20         INC $20
    D0 DB         BNE $8C7B
    A5 1F         LDA $1F
    8D 17 80      STA $8017
    A5 20         LDA $20
    8D 18 80      STA $8018
    60            RTS 
    AD 19 80      LDA $8019
    85 1D         STA $1D
    AD 1A 80      LDA $801A
    85 1E         STA $1E
    60            RTS 
    A0 34         LDY #$34
    78            SEI 
    84 01         STY $01
    A0 00         LDY #$00
    B1 1D         LDA ($1D),Y
    A0 36         LDY #$36
    84 01         STY $01
    58            CLI 
    60            RTS 
    A0 34         LDY #$34
    78            SEI 
    84 01         STY $01
    A0 00         LDY #$00
    E6 1D         INC $1D
    D0 02         BNE $8CD2
    E6 1E         INC $1E
    B1 1D         LDA ($1D),Y
    D0 F6         BNE $8CCC
    A0 36         LDY #$36
    84 01         STY $01
    58            CLI 
    60            RTS 
    .byte 0E CD 4F 44 45 4D                               ; $8CDC ..ODEM
    20 46 41      JSR $4146
    55 4C         EOR $4C,X
    54            .byte $54
    .byte 0D 00 93 0E                                     ; $8CE8 ....
    08            PHP 
    11 C9         ORA ($C9),Y
    4E 50 55      LSR $5550
    54            .byte $54
    20 50 48      JSR $4850
    4F            .byte $4F
    .byte 4E 45                                           ; $8CF7 NE
    20 4E 55      JSR $554E
    4D 42 45      EOR $4542
    52            .byte $52
    .byte 00                                              ; $8D00 .
    20 4F 52      JSR $524F
    20 D2 C5      JSR $C5D2
    D4            .byte $D4
    .byte D5 D2 CE 2E 00 0D 11 CE 55 4D 42 45 52 3F       ; $8D08 ........UMBER?
    20 20 00      JSR $0020
    11 C4         ORA ($C4),Y
    49 41         EOR #$41
    4C 4C 49      JMP $494C
    .byte 4E 47                                           ; $8D20 NG
    20 00 50      JSR $5000
    4C 45 41      JMP $4145
    .byte 53 45                                           ; $8D28 SE
    20 57 41      JSR $4157
    49 54         EOR #$54
    00            BRK 

; ============================================================
; FRAME_RENDER
; ============================================================
FRAME_RENDER:
    BA            TSX 
    8E 54 C1      STX $C154 ; workspace
    A2 03         LDX #$03
    A9 20         LDA #$20
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    C9 20         CMP #$20
    D0 09         BNE $8D4B
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    F0 0B         BEQ $8D52
    C9 20         CMP #$20
    F0 F7         BEQ $8D42
    A2 DC         LDX #$DC
    A0 8C         LDY #$8C
    4C B7 90      JMP $90B7 ; PRINT_STRING
    20 50 90      JSR $9050
    AD 13 80      LDA $8013
    8D 21 D0      STA $D021 ; VIC_BGCOL0
    AD 14 80      LDA $8014
    8D 86 02      STA $0286
    A2 EA         LDX #$EA
    A0 8C         LDY #$8C
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A0 01         LDY #$01
    AD F0 9F      LDA $9FF0
    F0 09         BEQ $8D78
    A2 01         LDX #$01
    A0 8D         LDY #$8D
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A0 00         LDY #$00
    A2 10         LDX #$10
    A9 2D         LDA #$2D
    38            SEC 
    20 C8 90      JSR $90C8 ; SETUP_INPUT_PARAMS
    A2 0D         LDX #$0D
    A0 8D         LDY #$8D
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A2 00         LDX #$00
    A0 02         LDY #$02
    20 DF 90      JSR $90DF ; INPUT_LINE
    90 01         BCC $8D91
    60            RTS 
    20 6E 90      JSR $906E
    A6 1A         LDX $1A
    F0 0C         BEQ $8DA4
    8E F0 9F      STX $9FF0
    BD FF 01      LDA $01FF,X
    9D F0 9F      STA $9FF0,X
    CA            DEX 
    D0 F7         BNE $8D9B
    A2 19         LDX #$19
    A0 8D         LDY #$8D
    20 B7 90      JSR $90B7 ; PRINT_STRING
    20 C0 96      JSR $96C0 ; PROTO_DISPATCH_TABLE
    20 C6 96      JSR $96C6
    A0 03         LDY #$03
    A2 08         LDX #$08
    A9 10         LDA #$10
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 10         AND #$10
    F0 0A         BEQ $8DCB
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    C9 03         CMP #$03
    D0 F2         BNE $8DBA
    4C C0 96      JMP $96C0 ; PROTO_DISPATCH_TABLE
    88            DEY 
    D0 E7         BNE $8DB5
    A0 00         LDY #$00
    B9 F1 9F      LDA $9FF1,Y
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    C9 2D         CMP #$2D
    D0 10         BNE $8DEA
    A2 08         LDX #$08
    A9 10         LDA #$10
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 10         AND #$10
    D0 F9         BNE $8DE1
    F0 12         BEQ $8DFC
    29 0F         AND #$0F
    D0 02         BNE $8DF0
    A9 0A         LDA #$0A
    09 A0         ORA #$A0
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 20         AND #$20
    D0 F9         BNE $8DF5
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    C9 03         CMP #$03
    F0 19         BEQ $8E1C
    C8            INY 
    CC F0 9F      CPY $9FF0
    D0 C7         BNE $8DD0
    A2 03         LDX #$03
    A9 90         LDA #$90
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    A2 08         LDX #$08
    A9 40         LDA #$40
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 D5 96      JSR $96D5
    90 03         BCC $8E1F
    4C C0 96      JMP $96C0 ; PROTO_DISPATCH_TABLE
    A2 24         LDX #$24
    A0 8D         LDY #$8D
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG
    18            CLC 
    6E 55 C1      ROR $C155 ; workspace
    20 D2 96      JSR $96D2
    90 06         BCC $8E35
    20 C0 96      JSR $96C0 ; PROTO_DISPATCH_TABLE
    4C 62 90      JMP $9062
    20 50 90      JSR $9050
    A2 07         LDX #$07
    A0 95         LDY #$95
    20 E2 89      JSR $89E2 ; FRAME_BUF_WRITE
    A9 02         LDA #$02
    8D 86 02      STA $0286
    A9 5A         LDA #$5A
    8D 00 C1      STA $C100 ; workspace
    A2 10         LDX #$10
    A0 12         LDY #$12
    18            CLC 
    20 F0 FF      JSR $FFF0
    A2 08         LDX #$08
    A0 01         LDY #$01
    A9 00         LDA #$00
    18            CLC 
    20 C8 90      JSR $90C8 ; SETUP_INPUT_PARAMS
    A2 01         LDX #$01
    A0 C1         LDY #$C1
    20 DF 90      JSR $90DF ; INPUT_LINE
    B0 D4         BCS $8E38
    A4 1A         LDY $1A
    A9 20         LDA #$20
    99 01 C1      STA $C101,Y
    C8            INY 
    C0 08         CPY #$08
    90 F8         BCC $8E68
    A2 12         LDX #$12
    A0 0D         LDY #$0D
    18            CLC 
    20 F0 FF      JSR $FFF0
    A2 00         LDX #$00
    A9 5F         LDA #$5F
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 02 90      JSR $9002 ; CLEAR_STATUS
    C9 0D         CMP #$0D
    F0 18         BEQ $8EA3
    E0 06         CPX #$06
    F0 EB         BEQ $8E7A
    9D 09 C1      STA $C109,X
    C9 30         CMP #$30
    90 E4         BCC $8E7A
    C9 5B         CMP #$5B
    B0 E0         BCS $8E7A
    E8            INX 
    A9 2A         LDA #$2A
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 7A 8E      JMP $8E7A
    20 6A 90      JSR $906A
    A9 20         LDA #$20
    9D 09 C1      STA $C109,X
    E8            INX 
    E0 06         CPX #$06
    90 F8         BCC $8EA8
    A2 37         LDX #$37
    86 01         STX $01
    A2 09         LDX #$09
    BD 39 80      LDA $8039,X
    9D 0F C1      STA $C10F,X
    CA            DEX 
    10 F7         BPL $8EB6
    A2 36         LDX #$36
    86 01         STX $01
    AD 00 A0      LDA $A000
    8D 19 C1      STA $C119 ; workspace
    AD 01 A0      LDA $A001
    8D 1A C1      STA $C11A ; workspace
    A2 24         LDX #$24
    A0 8D         LDY #$8D
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG
    A9 43         LDA #$43
    8D 34 80      STA $8034
    A0 1B         LDY #$1B
    20 C1 94      JSR $94C1 ; MODEM_REG_WRITE_WAIT
    20 D2 96      JSR $96D2
    90 03         BCC $8EE8
    4C 38 8E      JMP $8E38
    20 D0 89      JSR $89D0 ; FRAME_BUF_READ
    38            SEC 
    6E 55 C1      ROR $C155 ; workspace

; ============================================================
; MODEM_INIT_DOWNLOAD
; ============================================================
MODEM_INIT_DOWNLOAD:
    20 CC 96      JSR $96CC
    20 CC 96      JSR $96CC
    20 CC 96      JSR $96CC
    85 1F         STA $1F
    20 CC 96      JSR $96CC
    85 20         STA $20
    B0 37         BCS $8F38
    A2 3F         LDX #$3F
    A0 8F         LDY #$8F
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG
    20 CC 96      JSR $96CC
    85 1D         STA $1D
    20 CC 96      JSR $96CC
    85 1E         STA $1E
    20 CC 96      JSR $96CC
    20 CC 96      JSR $96CC
    A0 00         LDY #$00
    20 CC 96      JSR $96CC
    91 1D         STA ($1D),Y
    B0 08         BCS $8F29
    E6 1D         INC $1D
    D0 F5         BNE $8F1A
    E6 1E         INC $1E
    D0 F1         BNE $8F1A
    2C 55 C1      BIT $C155 ; workspace
    10 0A         BPL $8F38
    A6 1D         LDX $1D
    A4 1E         LDY $1E
    8E 36 80      STX $8036
    8C 37 80      STY $8037
    18            CLC 
    6E 55 C1      ROR $C155 ; workspace
    6C 1F 00      JMP ($001F)
    4C 49 4E      JMP $4E49
    .byte 4B 49 4E 47 00                                  ; $8F42 KING.

; ============================================================
; MODEM_SEND_CMD
; ============================================================
MODEM_SEND_CMD:
    E0 00         CPX #$00
    F0 33         BEQ $8F7E
    8E 50 C1      STX $C150 ; workspace
    AE 54 C1      LDX $C154 ; workspace
    9A            TXS 
    20 C0 96      JSR $96C0 ; PROTO_DISPATCH_TABLE
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    20 F2 8F      JSR $8FF2
    AD 51 C1      LDA $C151 ; workspace
    8D 20 D0      STA $D020 ; VIC_BORDER
    AC 50 C1      LDY $C150 ; workspace
    BE AF 8F      LDX $8FAF,Y
    B9 B4 8F      LDA $8FB4,Y
    A8            TAY 
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG
    20 02 90      JSR $9002 ; CLEAR_STATUS
    AD 53 C1      LDA $C153 ; workspace
    8D 86 02      STA $0286
    A2 DA         LDX #$DA
    A0 8F         LDY #$8F
    4C B7 90      JMP $90B7 ; PRINT_STRING
    AE 54 C1      LDX $C154 ; workspace
    9A            TXS 
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    AD 14 80      LDA $8014
    8D 86 02      STA $0286
    A2 F4         LDX #$F4
    A0 9C         LDY #$9C
    20 B7 90      JSR $90B7 ; PRINT_STRING
    AD 01 DC      LDA $DC01 ; CIA1_PRB
    CD 01 DC      CMP $DC01 ; CIA1_PRB
    D0 F8         BNE $8F92
    C9 FF         CMP #$FF
    D0 F4         BNE $8F92
    A9 00         LDA #$00
    85 C6         STA $C6
    2C 10 80      BIT $8010
    10 03         BPL $8FAA
    20 D8 96      JSR $96D8
    20 F2 8F      JSR $8FF2
    4C C0 96      JMP $96C0 ; PROTO_DISPATCH_TABLE
    .byte 00 BA BB D4 D7 C1 8F 8F 8F 8F                   ; $8FB0 ..........

; --- Status messages ---
    .byte 20 44 49 53 43 4F 4E 4E 45 43 54 45 44 20 2D 20; $8FBA  DISCONNECTED - 
    .byte 42 41 44 20 4C 49 4E 45 3F 00 57 52 00 52 57 00; $8FCA BAD LINE?.WR.RW.
    .byte 93 0E 43 4F 4E 4E 45 43 54 20 41 47 41 49 4E 20; $8FDA ..CONNECT AGAIN 
    .byte 50 4C 45 41 53 45 0D 00 2C 55 C1 10 03 20 3A 83; $8FEA PLEASE\n.,U... :.
    .byte 60 A2                                     ; $8FFA `.
    .byte 10                                              ; $8FFC .
    A0 90         LDY #$90
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG

; ============================================================
; CLEAR_STATUS
; ============================================================
CLEAR_STATUS:
    A9 00         LDA #$00
    85 C6         STA $C6
    86 19         STX $19
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    F0 FB         BEQ $9008
    A6 19         LDX $19
    60            RTS 
    .byte 50 52 45 53 53                                  ; $9010 PRESS
    20 41 4E      JSR $4E41
    59 20 4B      EOR $4B20,Y
    45 59         EOR $59
    00            BRK 

; ============================================================
; STATUS_LINE
; ============================================================
STATUS_LINE:
    A2 01         LDX #$01
    A0 01         LDY #$01
    A9 00         LDA #$00
    18            CLC 
    20 C8 90      JSR $90C8 ; SETUP_INPUT_PARAMS
    A2 00         LDX #$00
    A0 02         LDY #$02
    20 DF 90      JSR $90DF ; INPUT_LINE
    B0 0D         BCS $903E
    AD 00 02      LDA $0200
    29 DF         AND #$DF
    C9 59         CMP #$59
    F0 13         BEQ $904D
    C9 4E         CMP #$4E
    F0 0F         BEQ $904D
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    C0 00         CPY #$00
    F0 D7         BEQ $901E ; STATUS_LINE
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    4C 1E 90      JMP $901E ; STATUS_LINE
    C9 59         CMP #$59
    60            RTS 
    20 62 90      JSR $9062
    20 8B 93      JSR $938B ; PROTOCOL_STATE_INIT
    20 76 90      JSR $9076
    A9 00         LDA #$00
    8D 15 D0      STA $D015
    A9 0E         LDA #$0E
    D0 16         BNE $9078
    A9 93         LDA #$93
    D0 12         BNE $9078
    A9 13         LDA #$13
    D0 0E         BNE $9078
    A9 20         LDA #$20
    D0 0A         BNE $9078
    A9 0D         LDA #$0D
    D0 06         BNE $9078
    A9 12         LDA #$12
    D0 02         BNE $9078
    A9 92         LDA #$92
    4C D2 FF      JMP $FFD2 ; KERNAL_CHROUT

; ============================================================
; PRINT_STATUS_MSG
; ============================================================
PRINT_STATUS_MSG:
    86 1B         STX $1B
    84 1C         STY $1C
    20 B4 93      JSR $93B4
    AD 86 02      LDA $0286
    48            PHA 
    20 97 90      JSR $9097
    20 76 90      JSR $9076
    68            PLA 
    8D 86 02      STA $0286
    4C BF 93      JMP $93BF

; ============================================================
; CURSOR_HOME
; ============================================================
CURSOR_HOME:
    86 1B         STX $1B
    84 1C         STY $1C
    20 8B 93      JSR $938B ; PROTOCOL_STATE_INIT
    20 AF 90      JSR $90AF
    20 72 90      JSR $9072
    AD 21 D0      LDA $D021 ; VIC_BGCOL0
    29 0F         AND #$0F
    AA            TAX 
    BD A4 93      LDA $93A4,X
    8D 86 02      STA $0286
    4C BB 90      JMP $90BB
    A2 18         LDX #$18
    A0 00         LDY #$00
    18            CLC 
    4C F0 FF      JMP $FFF0

; ============================================================
; PRINT_STRING
; ============================================================
PRINT_STRING:
    86 1B         STX $1B
    84 1C         STY $1C
    A0 00         LDY #$00
    B1 1B         LDA ($1B),Y
    F0 06         BEQ $90C7
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    C8            INY 
    D0 F6         BNE $90BD
    60            RTS 

; ============================================================
; SETUP_INPUT_PARAMS
; ============================================================
SETUP_INPUT_PARAMS:
    8E 43 C1      STX $C143 ; workspace
    8C 44 C1      STY $C144 ; workspace
    8D 46 C1      STA $C146 ; workspace
    AA            TAX 
    A9 00         LDA #$00
    6A            ROR A
    E0 00         CPX #$00
    F0 02         BEQ $90DB
    09 40         ORA #$40
    8D 45 C1      STA $C145 ; workspace
    60            RTS 

; ============================================================
; INPUT_LINE
; ============================================================
INPUT_LINE:
    86 1D         STX $1D
    84 1E         STY $1E
    A0 00         LDY #$00
    84 1A         STY $1A
    84 C6         STY $C6
    A9 00         LDA #$00
    85 D4         STA $D4
    A9 5F         LDA #$5F
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    F0 FB         BEQ $90F7
    A4 1A         LDY $1A
    C9 03         CMP #$03
    D0 05         BNE $9107
    20 6A 90      JSR $906A
    38            SEC 
    60            RTS 
    CC 44 C1      CPY $C144 ; workspace
    90 04         BCC $9110
    C9 0D         CMP #$0D
    F0 5C         BEQ $916C
    C0 00         CPY #$00
    F0 14         BEQ $9128
    C9 14         CMP #$14
    D0 10         BNE $9128
    20 6A 90      JSR $906A
    A9 9D         LDA #$9D
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    C6 1A         DEC $1A
    4C E9 90      JMP $90E9
    CC 43 C1      CPY $C143 ; workspace
    F0 CA         BEQ $90F7
    2C 45 C1      BIT $C145 ; workspace
    50 07         BVC $9139
    CD 46 C1      CMP $C146 ; workspace
    F0 2B         BEQ $9162
    D0 02         BNE $913B
    10 0A         BPL $9145
    C9 30         CMP #$30
    90 B8         BCC $90F7
    C9 3A         CMP #$3A
    B0 B4         BCS $90F7
    90 1D         BCC $9162
    C9 22         CMP #$22
    F0 AE         BEQ $90F7
    C9 20         CMP #$20
    90 AA         BCC $90F7
    C9 60         CMP #$60
    90 11         BCC $9162
    AA            TAX 
    AD 18 D0      LDA $D018 ; VIC_MEMSETUP
    29 02         AND #$02
    F0 9E         BEQ $90F7
    8A            TXA 
    C9 A0         CMP #$A0
    90 99         BCC $90F7
    C9 E0         CMP #$E0
    B0 95         BCS $90F7
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    91 1D         STA ($1D),Y
    E6 1A         INC $1A
    4C E9 90      JMP $90E9
    20 6A 90      JSR $906A
    18            CLC 
    60            RTS 

; ============================================================
; FILE_UPLOAD
; ============================================================
FILE_UPLOAD:
    8D 47 C1      STA $C147 ; workspace
    8E 32 80      STX $8032
    A2 56         LDX #$56
    A0 92         LDY #$92
    20 B7 90      JSR $90B7 ; PRINT_STRING
    20 AD 92      JSR $92AD
    A0 00         LDY #$00
    B0 01         BCS $9186
    C8            INY 
    A9 00         LDA #$00
    A2 10         LDX #$10
    18            CLC 
    20 C8 90      JSR $90C8 ; SETUP_INPUT_PARAMS
    AD 18 D0      LDA $D018 ; VIC_MEMSETUP
    48            PHA 
    A2 1E         LDX #$1E
    A0 80         LDY #$80
    20 DF 90      JSR $90DF ; INPUT_LINE
    84 19         STY $19
    68            PLA 
    8D 18 D0      STA $D018 ; VIC_MEMSETUP
    08            PHP 
    A9 08         LDA #$08
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    28            PLP 
    90 03         BCC $91AB
    4C 4C 92      JMP $924C
    2C 56 C1      BIT $C156 ; workspace
    10 4A         BPL $91FA
    30 0D         BMI $91BF

; ============================================================
; FILE_DOWNLOAD
; ============================================================
FILE_DOWNLOAD:
    8D 47 C1      STA $C147 ; workspace
    8E 32 80      STX $8032
    84 19         STY $19
    20 AD 92      JSR $92AD
    90 3B         BCC $91FA
    A5 19         LDA $19
    A2 1E         LDX #$1E
    A0 80         LDY #$80
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    AD 32 80      LDA $8032
    C9 50         CMP #$50
    F0 28         BEQ $91F7
    A0 00         LDY #$00
    AD 47 C1      LDA $C147 ; workspace
    C9 57         CMP #$57
    D0 01         BNE $91D9
    C8            INY 
    A2 01         LDX #$01
    A9 08         LDA #$08
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    A2 6D         LDX #$6D
    A0 92         LDY #$92
    20 93 90      JSR $9093 ; CURSOR_HOME
    20 90 92      JSR $9290
    20 C0 FF      JSR $FFC0 ; KERNAL_OPEN
    20 A2 92      JSR $92A2
    90 5E         BCC $9250
    A9 08         LDA #$08
    20 C3 FF      JSR $FFC3 ; KERNAL_CLOSE
    38            SEC 
    B0 56         BCS $9250
    A4 19         LDY $19
    AD 47 C1      LDA $C147 ; workspace
    99 21 80      STA $8021,Y
    AD 32 80      LDA $8032
    99 1F 80      STA $801F,Y
    A9 2C         LDA #$2C
    99 1E 80      STA $801E,Y
    99 20 80      STA $8020,Y
    98            TYA 
    18            CLC 
    69 06         ADC #$06
    8D 48 C1      STA $C148 ; workspace
    A2 1C         LDX #$1C
    A0 80         LDY #$80
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    A9 08         LDA #$08
    AA            TAX 
    A8            TAY 
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    20 C0 FF      JSR $FFC0 ; KERNAL_OPEN
    20 E8 92      JSR $92E8
    90 23         BCC $9250
    10 21         BPL $9250
    A2 64         LDX #$64
    A0 92         LDY #$92
    20 93 90      JSR $9093 ; CURSOR_HOME
    20 1E 90      JSR $901E ; STATUS_LINE
    D0 11         BNE $924C
    20 AD 92      JSR $92AD
    B0 10         BCS $9250
    A2 1B         LDX #$1B
    A0 80         LDY #$80
    EE 48 C1      INC $C148 ; workspace
    AD 48 C1      LDA $C148 ; workspace
    D0 CF         BNE $921B
    20 E0 92      JSR $92E0
    38            SEC 
    08            PHP 
    20 76 90      JSR $9076
    28            PLP 
    60            RTS 
    .byte 09                                              ; $9256 .
    20 46 49      JSR $4946
    4C 45 20      JMP $2045
    .byte 4E 41                                           ; $925D NA
    4D 45 3F      EOR $3F45
    20 00 52      JSR $5200
    45 50         EOR $50
    4C 41 43      JMP $4341
    .byte 45 3F                                           ; $926A E?
    20 00 C9      JSR $C900
    0D D0 04      ORA $04D0
    38            SEC 
    66 19         ROR $19
    60            RTS 
    .byte 24 19 10 13                                     ; $9276 $...
    18            CLC 
    66 19         ROR $19
    48            PHA 
    8A            TXA 
    48            PHA 
    98            TYA 
    48            PHA 
    20 8B 93      JSR $938B ; PROTOCOL_STATE_INIT
    20 AF 90      JSR $90AF
    68            PLA 
    A8            TAY 
    68            PLA 
    AA            TAX 
    68            PLA 
    4C CA F1      JMP $F1CA
    A2 6E         LDX #$6E
    A0 92         LDY #$92
    8E 26 03      STX $0326
    8C 27 03      STY $0327
    18            CLC 
    66 19         ROR $19
    A9 80         LDA #$80
    4C 90 FF      JMP $FF90
    A2 CA         LDX #$CA
    A0 F1         LDY #$F1
    8E 26 03      STX $0326
    8C 27 03      STY $0327
    60            RTS 
    A9 00         LDA #$00
    20 BD FF      JSR $FFBD ; KERNAL_SETNAM
    A9 0F         LDA #$0F
    A8            TAY 
    A2 08         LDX #$08
    20 BA FF      JSR $FFBA ; KERNAL_SETLFS
    20 C0 FF      JSR $FFC0 ; KERNAL_OPEN
    A2 0F         LDX #$0F
    20 C9 FF      JSR $FFC9 ; KERNAL_CHKOUT
    08            PHP 
    6E 56 C1      ROR $C156 ; workspace
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    28            PLP 
    B0 14         BCS $92E0
    60            RTS 

; ============================================================
; FRAME_STORE
; ============================================================
FRAME_STORE:
    20 90 92      JSR $9290
    A9 08         LDA #$08
    20 C3 FF      JSR $FFC3 ; KERNAL_CLOSE
    90 03         BCC $92DA
    20 E7 FF      JSR $FFE7
    20 A2 92      JSR $92A2
    20 E8 92      JSR $92E8
    08            PHP 
    A9 0F         LDA #$0F
    20 C3 FF      JSR $FFC3 ; KERNAL_CLOSE
    28            PLP 
    60            RTS 
    20 5F 93      JSR $935F
    08            PHP 
    A2 00         LDX #$00
    28            PLP 
    F0 15         BEQ $9306
    A2 A0         LDX #$A0
    C9 32         CMP #$32
    F0 0F         BEQ $9306
    A2 80         LDX #$80
    C9 36         CMP #$36
    D0 09         BNE $9306
    AC 01 02      LDY $0201
    C0 33         CPY #$33
    D0 02         BNE $9306
    A2 C0         LDX #$C0
    8E 49 C1      STX $C149 ; workspace
    A9 20         LDA #$20
    2C 49 C1      BIT $C149 ; workspace
    10 29         BPL $9339
    70 27         BVS $9339
    D0 17         BNE $932B
    A2 00         LDX #$00
    BD 00 02      LDA $0200,X
    E8            INX 
    C9 2C         CMP #$2C
    D0 F8         BNE $9316
    BD 00 02      LDA $0200,X
    E8            INX 
    C9 2C         CMP #$2C
    D0 F8         BNE $931E
    A9 00         LDA #$00
    9D FF 01      STA $01FF,X
    A2 53         LDX #$53
    A0 93         LDY #$93
    20 93 90      JSR $9093 ; CURSOR_HOME
    A2 00         LDX #$00
    A0 02         LDY #$02
    20 B7 90      JSR $90B7 ; PRINT_STRING
    0E 49 C1      ASL $C149 ; workspace
    90 14         BCC $9352
    A9 08         LDA #$08
    20 C3 FF      JSR $FFC3 ; KERNAL_CLOSE
    20 E0 92      JSR $92E0
    AD 49 C1      LDA $C149 ; workspace
    30 06         BMI $9351
    20 02 90      JSR $9002 ; CLEAR_STATUS
    AD 49 C1      LDA $C149 ; workspace
    38            SEC 
    60            RTS 
    .byte 44 49 53 4B                                     ; $9353 DISK
    20 45 52      JSR $5245
    52            .byte $52
    .byte 4F 52                                           ; $935B OR
    20 00 2C      JSR $2C00
    56 C1         LSR $C1,X
    10 03         BPL $9367
    A9 00         LDA #$00
    60            RTS 
    A2 0F         LDX #$0F
    20 C6 FF      JSR $FFC6 ; KERNAL_CHKIN
    A2 00         LDX #$00
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    C9 0D         CMP #$0D
    F0 06         BEQ $937B
    9D 00 02      STA $0200,X
    E8            INX 
    D0 F3         BNE $936E
    A9 00         LDA #$00
    9D 00 02      STA $0200,X
    85 90         STA $90
    20 CC FF      JSR $FFCC ; KERNAL_CLRCHN
    AD 00 02      LDA $0200
    C9 30         CMP #$30
    60            RTS 

; ============================================================
; PROTOCOL_STATE_INIT
; ============================================================
PROTOCOL_STATE_INIT:
    AD 21 D0      LDA $D021 ; VIC_BGCOL0
    29 0F         AND #$0F
    AA            TAX 
    BD A4 93      LDA $93A4,X
    AA            TAX 
    A0 27         LDY #$27
    A9 A0         LDA #$A0
    99 C0 07      STA $07C0,Y
    8A            TXA 
    99 C0 DB      STA $DBC0,Y
    88            DEY 
    10 F4         BPL $9397
    60            RTS 
    .byte 01 00 01 00 01 01 01 00 00 01 00 01 01 00 01 00 ; $93A4 ................
    38            SEC 
    20 F0 FF      JSR $FFF0
    8E 4A C1      STX $C14A ; workspace
    8C 4B C1      STY $C14B ; workspace
    60            RTS 
    18            CLC 
    AE 4A C1      LDX $C14A ; workspace
    AC 4B C1      LDY $C14B ; workspace
    4C F0 FF      JMP $FFF0

; ============================================================
; PROTOCOL_RESET
; ============================================================
PROTOCOL_RESET:
    8E 4E C1      STX $C14E ; workspace
    8C 4F C1      STY $C14F ; workspace
    60            RTS 

; ============================================================
; PROTOCOL_CLEANUP
; ============================================================
PROTOCOL_CLEANUP:
    86 1D         STX $1D
    84 1E         STY $1E
    AE 4E C1      LDX $C14E ; workspace
    AC 4F C1      LDY $C14F ; workspace
    86 1F         STX $1F
    84 20         STY $20
    A0 00         LDY #$00
    B1 1D         LDA ($1D),Y
    8D 4C C1      STA $C14C ; workspace
    A2 00         LDX #$00
    20 36 94      JSR $9436
    20 02 90      JSR $9002 ; CLEAR_STATUS
    C9 1D         CMP #$1D
    D0 1D         BNE $940E
    A2 01         LDX #$01
    20 36 94      JSR $9436
    20 9B 94      JSR $949B
    E8            INX 
    E0 06         CPX #$06
    D0 F5         BNE $93F3
    AC 33 80      LDY $8033
    CC 4C C1      CPY $C14C ; workspace
    D0 02         BNE $9408
    A0 00         LDY #$00
    C8            INY 
    8C 33 80      STY $8033
    D0 D7         BNE $93E5
    C9 9D         CMP #$9D
    D0 19         BNE $942B
    AC 33 80      LDY $8033
    88            DEY 
    D0 03         BNE $941B
    AC 4C C1      LDY $C14C ; workspace
    8C 33 80      STY $8033
    A2 05         LDX #$05
    20 36 94      JSR $9436
    20 9B 94      JSR $949B
    CA            DEX 
    D0 F7         BNE $9420
    F0 BA         BEQ $93E5
    C9 0D         CMP #$0D
    D0 05         BNE $9434
    AD 33 80      LDA $8033
    18            CLC 
    60            RTS 
    38            SEC 
    60            RTS 
    8A            TXA 
    48            PHA 
    86 1A         STX $1A
    AD 21 D0      LDA $D021 ; VIC_BGCOL0
    29 0F         AND #$0F
    AA            TAX 
    BD A4 93      LDA $93A4,X
    8D 42 C1      STA $C142 ; workspace
    AD 33 80      LDA $8033
    38            SEC 
    E9 03         SBC #$03
    F0 02         BEQ $9450
    B0 06         BCS $9456
    18            CLC 
    6D 4C C1      ADC $C14C ; workspace
    F0 FA         BEQ $9450
    85 19         STA $19
    A2 00         LDX #$00
    A4 19         LDY $19
    B1 1D         LDA ($1D),Y
    18            CLC 
    65 1A         ADC $1A
    A8            TAY 
    B1 1F         LDA ($1F),Y
    29 3F         AND #$3F
    E0 12         CPX #$12
    90 04         BCC $946E
    E0 18         CPX #$18
    90 02         BCC $9470
    09 80         ORA #$80
    9D C0 07      STA $07C0,X
    AD 42 C1      LDA $C142 ; workspace
    9D C0 DB      STA $DBC0,X
    E8            INX 
    E0 28         CPX #$28
    F0 1A         BEQ $9498
    E6 1A         INC $1A
    A5 1A         LDA $1A
    C9 06         CMP #$06
    D0 D4         BNE $945A
    A9 00         LDA #$00
    85 1A         STA $1A
    A4 19         LDY $19
    CC 4C C1      CPY $C14C ; workspace
    D0 02         BNE $9493
    A0 00         LDY #$00
    C8            INY 
    84 19         STY $19
    D0 C2         BNE $945A
    68            PLA 
    AA            TAX 
    60            RTS 
    AD 11 D0      LDA $D011 ; VIC_CTRL1
    0A            ASL A
    B0 FA         BCS $949B
    AD 11 D0      LDA $D011 ; VIC_CTRL1
    0A            ASL A
    90 FA         BCC $94A1
    60            RTS 

; ============================================================
; MODEM_STATUS_CHECK
; ============================================================
MODEM_STATUS_CHECK:
    29 7F         AND #$7F
    C9 20         CMP #$20
    B0 04         BCS $94B2
    09 40         ORA #$40
    D0 0E         BNE $94C0
    C9 40         CMP #$40
    90 0A         BCC $94C0
    C9 60         CMP #$60
    B0 04         BCS $94BE
    09 80         ORA #$80
    D0 02         BNE $94C0
    49 C0         EOR #$C0
    60            RTS 

; ============================================================
; MODEM_REG_WRITE_WAIT
; ============================================================
MODEM_REG_WRITE_WAIT:
    8C 4D C1      STY $C14D ; workspace
    A0 00         LDY #$00
    B9 00 C1      LDA $C100,Y
    C8            INY 
    CC 4D C1      CPY $C14D ; workspace
    08            PHP 
    20 C9 96      JSR $96C9
    28            PLP 
    90 F2         BCC $94C6
    60            RTS 

; ============================================================
; MODEM_REG_READ_STATUS
; ============================================================
MODEM_REG_READ_STATUS:
    A0 00         LDY #$00
    20 CC 96      JSR $96CC
    99 00 C1      STA $C100,Y
    C8            INY 
    90 F7         BCC $94D7
    AD 34 80      LDA $8034
    60            RTS 

; ============================================================
; MODEM_WAIT_READY
; ============================================================
MODEM_WAIT_READY:
    48            PHA 
    A2 00         LDX #$00
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    AA            TAX 
    10 FA         BPL $94E7
    68            PLA 
    A2 04         LDX #$04

; ============================================================
; MODEM_REG_WRITE
; ============================================================
MODEM_REG_WRITE:
    08            PHP 
    78            SEI 
    8E 00 DE      STX $DE00 ; MODEM_REG_SELECT
    8D 01 DE      STA $DE01 ; MODEM_DATA
    28            PLP 
    60            RTS 

; ============================================================
; MODEM_REG_READ
; ============================================================
MODEM_REG_READ:
    08            PHP 
    78            SEI 
    8E 00 DE      STX $DE00 ; MODEM_REG_SELECT
    AD 01 DE      LDA $DE01 ; MODEM_DATA
    AD 01 DE      LDA $DE01 ; MODEM_DATA
    28            PLP 
    60            RTS 
    .byte 00 F4 FF 8E 07 0D 0C                            ; $9507 .......
    20 20 90      JSR $9020
    B0 07         BCS $951A
    C0 21         CPY #$21
    AE 9B 0D      LDX $0D9B

; --- Login screen layout and help text ---
    .byte 20 20 90 DD 43 4F 4D 50 55 4E 45 54 20 53 59 53; $9518   ..COMPUNET SYS
    .byte 54 45 4D 20 4C 4F 47 4F 4E 2E 06 0B DD 9B 0D 20; $9528 TEM LOGON.....\n 
    .byte 20 90 DD 06 21 DD 9B 0D 20 20 90 DD 1F 45 4E 54; $9538  ...!..\n  ...ENT
    .byte 45 52 20 55 53 45 52 20 49 44 3A 06 13 90 DD 9B; $9548 ER USER ID:.....
    .byte 0D 20 20 90 DD 06 21 DD 9B 0D 20 20 90 DD 1F 50; $9558 \n  ...!..\n  ...P
    .byte 41 53 53 57 4F 52 44 3A 06 18 90 DD 9B 0D 20 20; $9568 ASSWORD:.....\n  
    .byte 90 DD 06 21 DD 9B 0D 20 20 90 AD 07 C0 21 BD 9B; $9578 ...!..\n  ....!..
    .byte 0D 00 F6 FC 0E 0D 06 02 1F C5 44 49 54 20 CB 45; $9588 \n....\n....DIT .E
    .byte 59 53 07 0D 03 06 02 D3 D4 CF D0 20 CB C5 D9 06; $9598 YS.\n....... ....
    .byte 07 46 33 2F 34 0D 06 02 95 53 54 4F 50 20 45 44; $95A8 .F3/4\n...STOP ED
    .byte 49 54 2C 06 05 C4 45 4C 45 54 45 2F C9 4E 53 45; $95B8 IT,...ELETE/.NSE
    .byte 52 54 0D 06 02 53 54 4F 52 45 20 46 52 41 4D 45; $95C8 RT\n..STORE FRAME
    .byte 06 04 4C 49 4E 45 20 41 42 4F 56 45 20 43 55 52; $95D8 ..LINE ABOVE CUR
    .byte 53 4F 52 0D 0D 06 02 1F D2 D5 CE 20 CB C5 D9 06; $95E8 SOR\n\n...... ....
    .byte 08 46 35 0D 06 02 95 52 45 53 54 4F 52 45 06 08; $95F8 .F5\n...RESTORE..
    .byte CF 4E 2F CF 46 46 20 41 55 54 4F 2D 52 45 50 45; $9608 .N/.FF AUTO-REPE
    .byte 41 54 0D 06 02 4F 52 49 47 49 4E 41 4C 0D 06 12; $9618 AT\n..ORIGINAL\n..
    .byte 1F 46 36 0D 06 02 D3 C8 C9 C6 D4 2D C3 3D 06 07; $9628 .F6\n.......-.=..
    .byte 95 CF 4E 2F CF 46 46 20 43 4F 4C 4F 55 52 0D 06; $9638 ..N/.FF COLOUR\n.
    .byte 02 43 48 41 4E 47 45 20 43 41 53 45 06 04 4F 56; $9648 .CHANGE CASE..OV
    .byte 45 52 57 52 49 54 45 0D 0D 06 12 1F 46 37 2F 38; $9658 ERWRITE\n\n...F7/8
    .byte 0D 06 12 95 D3 43 52 45 45 4E 2F C2 4F 52 44 45; $9668 \n....CREEN/.ORDE
    .byte 52 0D 06 12 43 4F 4C 4F 55 52 20 43 48 41 4E 47; $9678 R\n..COLOUR CHANG
    .byte 45 07 0D 02 06 02 1F D3 45 45 20 C8 CF D7 20 D4; $9688 E.\n.....EE ... .
    .byte CF 20 C5 C4 C9 D4 0D 06 02 46 4F 52 20 46 55 4C; $9698 . ....\n..FOR FUL
    .byte 4C 45 52 20 44 45 54 41 49 4C 53 00 00 00 00 00; $96A8 LER DETAILS.....
    .byte 00 00 00 00 00 00 00 00                   ; $96B8 ........

; ============================================================
; PROTO_DISPATCH_TABLE
; ============================================================
PROTO_DISPATCH_TABLE:
    4C 79 9B      JMP $9B79 ; PROTO_SEND_PACKET
    4C 8A 9B      JMP $9B8A ; PROTO_RECV_PACKET
    4C DB 96      JMP $96DB ; PROTO_INIT_REGS
    4C AD 97      JMP $97AD ; PROTO_RECV_FRAME
    4C 6B 99      JMP $996B ; PROTO_PROCESS_CMD
    4C 3A 99      JMP $993A ; PROTO_ERROR_RECOVERY
    4C 3B 9B      JMP $9B3B ; PROTO_FLOW_CONTROL
    4C 69 9E      JMP $9E69 ; PROTO_CONNECT
    4C 00 C8      JMP $C800

; ============================================================
; PROTO_INIT_REGS
; ============================================================
PROTO_INIT_REGS:
    A2 02         LDX #$02
    A9 40         LDA #$40
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    A2 06         LDX #$06
    A9 05         LDA #$05
    4C F0 94      JMP $94F0 ; MODEM_REG_WRITE

; ============================================================
; PROTO_START_SESSION
; ============================================================
PROTO_START_SESSION:
    2C 38 80      BIT $8038
    50 05         BVC $96F3
    A2 04         LDX #$04
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    AD 0E C2      LDA $C20E ; workspace
    8D 10 C2      STA $C210 ; workspace
    8D 11 C2      STA $C211 ; workspace
    A9 80         LDA #$80
    8D 38 80      STA $8038
    AE 43 80      LDX $8043
    A9 63         LDA #$63
    A0 9C         LDY #$9C
    D0 15         BNE $971F

; ============================================================
; PROTO_DISCONNECT
; ============================================================
PROTO_DISCONNECT:
    2C 38 80      BIT $8038
    10 05         BPL $9714
    A2 05         LDX #$05
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    A9 40         LDA #$40
    8D 38 80      STA $8038
    A2 03         LDX #$03
    A9 5A         LDA #$5A
    A0 9C         LDY #$9C
    8E 0A C2      STX $C20A ; workspace
    48            PHA 
    BD 03 9B      LDA $9B03,X
    85 23         STA $23
    BD 07 9B      LDA $9B07,X
    85 24         STA $24
    68            PLA 
    20 3D 9C      JSR $9C3D
    AE 46 80      LDX $8046
    8E 05 DC      STX $DC05
    20 3C 9E      JSR $9E3C
    A9 00         LDA #$00
    8D 09 C2      STA $C209 ; workspace
    85 A2         STA $A2
    85 A1         STA $A1
    8D 18 C2      STA $C218 ; workspace
    8D 19 C2      STA $C219 ; workspace
    8D 24 C2      STA $C224 ; workspace
    A2 0B         LDX #$0B
    9D 28 C2      STA $C228,X
    CA            DEX 
    10 FA         BPL $974E
    A9 34         LDA #$34
    85 21         STA $21
    A9 C2         LDA #$C2
    85 22         STA $22
    A9 03         LDA #$03
    8D 0B C2      STA $C20B ; workspace
    60            RTS 
    A0 01         LDY #$01
    B1 21         LDA ($21),Y
    09 40         ORA #$40
    91 21         STA ($21),Y
    AD 0B C2      LDA $C20B ; workspace
    18            CLC 
    69 02         ADC #$02
    88            DEY 
    91 21         STA ($21),Y
    A0 00         LDY #$00
    8C 1D C2      STY $C21D ; workspace
    8C 1E C2      STY $C21E ; workspace
    B1 21         LDA ($21),Y
    20 10 9B      JSR $9B10
    C8            INY 
    CC 0B C2      CPY $C20B ; workspace
    D0 F5         BNE $977B
    20 0B 9B      JSR $9B0B
    AD 1D C2      LDA $C21D ; workspace
    91 21         STA ($21),Y
    C8            INY 
    AD 1E C2      LDA $C21E ; workspace
    91 21         STA ($21),Y
    AE 09 C2      LDX $C209 ; workspace
    A9 80         LDA #$80
    9D 2C C2      STA $C22C,X
    20 F5 98      JSR $98F5
    AE 43 80      LDX $8043
    BD 2C C2      LDA $C22C,X
    30 F5         BMI $979C
    CA            DEX 
    10 F8         BPL $97A2
    4C 2D 9C      JMP $9C2D

; ============================================================
; PROTO_RECV_FRAME
; ============================================================
PROTO_RECV_FRAME:
    85 19         STA $19
    48            PHA 
    8A            TXA 
    48            PHA 
    98            TYA 
    48            PHA 
    08            PHP 
    A5 19         LDA $19
    48            PHA 
    2C 38 80      BIT $8038
    30 03         BMI $97C0
    20 E9 96      JSR $96E9 ; PROTO_START_SESSION
    AE 09 C2      LDX $C209 ; workspace
    BD 2C C2      LDA $C22C,X
    10 22         BPL $97EA
    EC 43 80      CPX $8043
    D0 02         BNE $97CF
    A2 FF         LDX #$FF
    E8            INX 
    8E 09 C2      STX $C209 ; workspace
    BD 03 9B      LDA $9B03,X
    85 21         STA $21
    BD 07 9B      LDA $9B07,X
    85 22         STA $22
    A9 03         LDA #$03
    8D 0B C2      STA $C20B ; workspace
    BD 28 C2      LDA $C228,X
    F0 03         BEQ $97EA
    20 F5 98      JSR $98F5
    AD 0B C2      LDA $C20B ; workspace
    C9 03         CMP #$03
    D0 33         BNE $9824
    A0 00         LDY #$00
    8C 1D C2      STY $C21D ; workspace
    8C 1E C2      STY $C21E ; workspace
    AD 45 80      LDA $8045
    91 21         STA ($21),Y
    20 10 9B      JSR $9B10
    C8            INY 
    AD 34 80      LDA $8034
    91 21         STA ($21),Y
    20 10 9B      JSR $9B10
    C8            INY 
    AD 0E C2      LDA $C20E ; workspace
    AE 09 C2      LDX $C209 ; workspace
    9D 28 C2      STA $C228,X
    AA            TAX 
    E8            INX 
    E0 60         CPX #$60
    D0 02         BNE $981C
    A2 20         LDX #$20
    8E 0E C2      STX $C20E ; workspace
    91 21         STA ($21),Y
    20 10 9B      JSR $9B10
    AC 0B C2      LDY $C20B ; workspace
    68            PLA 
    91 21         STA ($21),Y
    20 10 9B      JSR $9B10
    C8            INY 
    8C 0B C2      STY $C20B ; workspace
    C8            INY 
    C8            INY 
    CC 45 80      CPY $8045
    D0 19         BNE $9851
    20 0B 9B      JSR $9B0B
    AD 1D C2      LDA $C21D ; workspace
    AC 0B C2      LDY $C20B ; workspace
    91 21         STA ($21),Y
    C8            INY 
    AD 1E C2      LDA $C21E ; workspace
    91 21         STA ($21),Y
    AE 09 C2      LDX $C209 ; workspace
    A9 80         LDA #$80
    9D 2C C2      STA $C22C,X
    28            PLP 
    90 08         BCC $985C
    20 62 97      JSR $9762
    A9 00         LDA #$00
    8D 38 80      STA $8038
    68            PLA 
    A8            TAY 
    68            PLA 
    AA            TAX 
    68            PLA 
    60            RTS 
    AE 43 80      LDX $8043
    BD 28 C2      LDA $C228,X
    CD 11 C2      CMP $C211 ; workspace
    D0 10         BNE $987D
    AC 11 C2      LDY $C211 ; workspace
    C8            INY 
    C0 60         CPY #$60
    D0 02         BNE $9877
    A0 20         LDY #$20
    8C 11 C2      STY $C211 ; workspace
    4C 8B 98      JMP $988B
    CA            DEX 
    10 E5         BPL $9865
    AE 0A C2      LDX $C20A ; workspace
    EC 43 80      CPX $8043
    D0 02         BNE $988A
    A2 FF         LDX #$FF
    E8            INX 
    8E 0A C2      STX $C20A ; workspace
    BD 2C C2      LDA $C22C,X
    10 62         BPL $98F5
    BD 28 C2      LDA $C228,X
    CD 20 C2      CMP $C220 ; workspace
    D0 1A         BNE $98B5
    A9 00         LDA #$00
    8D 21 C2      STA $C221 ; workspace
    8D 22 C2      STA $C222 ; workspace
    AD 4A 80      LDA $804A
    F0 0A         BEQ $98B2
    BC 2C C2      LDY $C22C,X
    10 48         BPL $98F5
    CD 22 C2      CMP $C222 ; workspace
    D0 F6         BNE $98A8
    BD 28 C2      LDA $C228,X
    8D 20 C2      STA $C220 ; workspace
    A2 19         LDX #$19
    AC 34 80      LDY $8034
    20 A4 9B      JSR $9BA4
    AE 0A C2      LDX $C20A ; workspace
    BD 03 9B      LDA $9B03,X
    85 23         STA $23
    BD 07 9B      LDA $9B07,X
    85 24         STA $24
    20 1E 99      JSR $991E
    A0 00         LDY #$00
    8C 0C C2      STY $C20C ; workspace
    B1 23         LDA ($23),Y
    8D 0D C2      STA $C20D ; workspace
    B1 23         LDA ($23),Y
    20 26 99      JSR $9926
    AE 0A C2      LDX $C20A ; workspace
    BD 2C C2      LDA $C22C,X
    10 0B         BPL $98F2
    EE 0C C2      INC $C20C ; workspace
    AC 0C C2      LDY $C20C ; workspace
    CC 0D C2      CPY $C20D ; workspace
    D0 E8         BNE $98DA
    20 22 99      JSR $9922
    AE 43 80      LDX $8043
    BD 28 C2      LDA $C228,X
    CD 10 C2      CMP $C210 ; workspace
    F0 03         BEQ $9903
    CA            DEX 
    10 F5         BPL $98F8
    BD 2C C2      LDA $C22C,X
    10 03         BPL $990B
    4C 62 98      JMP $9862
    A9 00         LDA #$00
    9D 28 C2      STA $C228,X
    AE 10 C2      LDX $C210 ; workspace
    E8            INX 
    E0 60         CPX #$60
    D0 02         BNE $991A
    A2 20         LDX #$20
    8E 10 C2      STX $C210 ; workspace
    60            RTS 
    A9 01         LDA #$01
    D0 15         BNE $9937
    A9 02         LDA #$02
    D0 11         BNE $9937
    C9 00         CMP #$00
    F0 0D         BEQ $9937
    C9 04         CMP #$04
    B0 09         BCS $9937
    69 20         ADC #$20
    48            PHA 
    A9 03         LDA #$03
    20 E4 94      JSR $94E4 ; MODEM_WAIT_READY
    68            PLA 
    4C E4 94      JMP $94E4 ; MODEM_WAIT_READY

; ============================================================
; PROTO_ERROR_RECOVERY
; ============================================================
PROTO_ERROR_RECOVERY:
    48            PHA 
    8A            TXA 
    48            PHA 
    98            TYA 
    48            PHA 
    2C 38 80      BIT $8038
    70 03         BVS $9947
    20 0A 97      JSR $970A ; PROTO_DISCONNECT
    2C 24 C2      BIT $C224 ; workspace
    30 18         BMI $9964
    A2 03         LDX #$03
    BD 2C C2      LDA $C22C,X
    10 08         BPL $995B
    BD 28 C2      LDA $C228,X
    CD 0F C2      CMP $C20F ; workspace
    F0 09         BEQ $9964
    CA            DEX 
    10 F0         BPL $994E
    20 06 9A      JSR $9A06
    38            SEC 
    B0 01         BCS $9965
    18            CLC 
    68            PLA 
    A8            TAY 
    68            PLA 
    AA            TAX 
    68            PLA 
    60            RTS 

; ============================================================
; PROTO_PROCESS_CMD
; ============================================================
PROTO_PROCESS_CMD:
    8A            TXA 
    48            PHA 
    98            TYA 
    48            PHA 
    2C 38 80      BIT $8038
    70 03         BVS $9977
    20 0A 97      JSR $970A ; PROTO_DISCONNECT
    AE 09 C2      LDX $C209 ; workspace
    BD 2C C2      LDA $C22C,X
    30 07         BMI $9986
    20 17 9A      JSR $9A17
    38            SEC 
    6E 24 C2      ROR $C224 ; workspace
    AC 0B C2      LDY $C20B ; workspace
    B1 21         LDA ($21),Y
    C8            INY 
    8C 0B C2      STY $C20B ; workspace
    CC 17 C2      CPY $C217 ; workspace
    F0 03         BEQ $9997
    18            CLC 
    90 50         BCC $99E7
    48            PHA 
    A9 00         LDA #$00
    AE 09 C2      LDX $C209 ; workspace
    9D 28 C2      STA $C228,X
    9D 2C C2      STA $C22C,X
    8D 24 C2      STA $C224 ; workspace
    2C 16 C2      BIT $C216 ; workspace
    18            CLC 
    10 3A         BPL $99E6
    A9 00         LDA #$00
    85 A2         STA $A2
    85 A1         STA $A1
    A5 A2         LDA $A2
    CD 47 80      CMP $8047
    B0 24         BCS $99DD
    A2 03         LDX #$03
    BD 2C C2      LDA $C22C,X
    30 05         BMI $99C5
    CA            DEX 
    10 F8         BPL $99BB
    30 ED         BMI $99B2
    8E 09 C2      STX $C209 ; workspace
    BD 28 C2      LDA $C228,X
    20 F0 99      JSR $99F0
    F0 0D         BEQ $99DD
    20 BC 9A      JSR $9ABC
    AE 09 C2      LDX $C209 ; workspace
    A9 00         LDA #$00
    9D 2C C2      STA $C22C,X
    F0 CF         BEQ $99AC
    20 2D 9C      JSR $9C2D
    A9 00         LDA #$00
    8D 38 80      STA $8038
    38            SEC 
    68            PLA 
    85 19         STA $19
    68            PLA 
    A8            TAY 
    68            PLA 
    AA            TAX 
    A5 19         LDA $19
    60            RTS 
    85 19         STA $19
    AE 0F C2      LDX $C20F ; workspace
    A0 03         LDY #$03
    E4 19         CPX $19
    F0 0A         BEQ $9A05
    E8            INX 
    E0 60         CPX #$60
    D0 02         BNE $9A02
    A2 20         LDX #$20
    88            DEY 
    10 F2         BPL $99F7
    60            RTS 
    A5 A1         LDA $A1
    CD 48 80      CMP $8048
    90 09         BCC $9A16
    20 22 99      JSR $9922
    A9 00         LDA #$00
    85 A2         STA $A2
    85 A1         STA $A1
    60            RTS 
    20 06 9A      JSR $9A06
    AE 09 C2      LDX $C209 ; workspace
    BD 2C C2      LDA $C22C,X
    30 03         BMI $9A25
    4C AC 9A      JMP $9AAC
    29 40         AND #$40
    F0 03         BEQ $9A2C
    4C 73 9A      JMP $9A73
    20 BC 9A      JSR $9ABC
    AE 09 C2      LDX $C209 ; workspace
    BC 28 C2      LDY $C228,X
    A2 03         LDX #$03
    BD 2C C2      LDA $C22C,X
    29 40         AND #$40
    F0 06         BEQ $9A44
    98            TYA 
    DD 28 C2      CMP $C228,X
    F0 1A         BEQ $9A5E
    CA            DEX 
    10 F0         BPL $9A37
    A2 03         LDX #$03
    8C 15 C2      STY $C215 ; workspace
    AC 0F C2      LDY $C20F ; workspace
    CC 15 C2      CPY $C215 ; workspace
    F0 17         BEQ $9A6B
    C8            INY 
    C0 60         CPY #$60
    D0 02         BNE $9A5B
    A0 20         LDY #$20
    CA            DEX 
    10 F1         BPL $9A4F
    AE 09 C2      LDX $C209 ; workspace
    A9 00         LDA #$00
    9D 28 C2      STA $C228,X
    9D 2C C2      STA $C22C,X
    F0 41         BEQ $9AAC
    AE 09 C2      LDX $C209 ; workspace
    A9 C0         LDA #$C0
    9D 2C C2      STA $C22C,X
    BD 28 C2      LDA $C228,X
    CD 0F C2      CMP $C20F ; workspace
    D0 31         BNE $9AAC
    AC 0F C2      LDY $C20F ; workspace
    C8            INY 
    C0 60         CPY #$60
    D0 02         BNE $9A85
    A0 20         LDY #$20
    8C 0F C2      STY $C20F ; workspace
    BD 03 9B      LDA $9B03,X
    85 21         STA $21
    BD 07 9B      LDA $9B07,X
    85 22         STA $22
    A9 03         LDA #$03
    8D 0B C2      STA $C20B ; workspace
    A0 00         LDY #$00
    B1 21         LDA ($21),Y
    38            SEC 
    E9 02         SBC #$02
    8D 17 C2      STA $C217 ; workspace
    C8            INY 
    B1 21         LDA ($21),Y
    8D 34 80      STA $8034
    0A            ASL A
    8D 16 C2      STA $C216 ; workspace
    60            RTS 
    AE 09 C2      LDX $C209 ; workspace
    E8            INX 
    E0 04         CPX #$04
    D0 02         BNE $9AB6
    A2 00         LDX #$00
    8E 09 C2      STX $C209 ; workspace
    4C 17 9A      JMP $9A17
    BD 28 C2      LDA $C228,X
    8D 06 C2      STA $C206 ; workspace
    A2 19         LDX #$19
    A0 20         LDY #$20
    20 A4 9B      JSR $9BA4
    A9 40         LDA #$40
    8D 1D C2      STA $C21D ; workspace
    A9 E6         LDA #$E6
    8D 1E C2      STA $C21E ; workspace
    AD 06 C2      LDA $C206 ; workspace
    20 10 9B      JSR $9B10
    20 0B 9B      JSR $9B0B
    AD 1D C2      LDA $C21D ; workspace
    8D 07 C2      STA $C207 ; workspace
    AD 1E C2      LDA $C21E ; workspace
    8D 08 C2      STA $C208 ; workspace
    20 1E 99      JSR $991E
    A2 00         LDX #$00
    8E 0C C2      STX $C20C ; workspace
    BD 03 C2      LDA $C203,X
    20 26 99      JSR $9926
    EE 0C C2      INC $C20C ; workspace
    AE 0C C2      LDX $C20C ; workspace
    E0 06         CPX #$06
    D0 F0         BNE $9AF0
    4C 22 99      JMP $9922
    .byte 34 C8 5C F0 C2 C2 C3 C3                         ; $9B03 4.\.....
    A9 00         LDA #$00
    20 10 9B      JSR $9B10
    48            PHA 
    8D 1F C2      STA $C21F ; workspace
    8A            TXA 
    48            PHA 
    A2 07         LDX #$07
    18            CLC 
    2E 1F C2      ROL $C21F ; workspace
    2E 1E C2      ROL $C21E ; workspace
    2E 1D C2      ROL $C21D ; workspace
    90 10         BCC $9B34
    AD 1D C2      LDA $C21D ; workspace
    49 10         EOR #$10
    8D 1D C2      STA $C21D ; workspace
    AD 1E C2      LDA $C21E ; workspace
    49 21         EOR #$21
    8D 1E C2      STA $C21E ; workspace
    CA            DEX 
    10 E1         BPL $9B18
    68            PLA 
    AA            TAX 
    68            PLA 
    60            RTS 

; ============================================================
; PROTO_FLOW_CONTROL
; ============================================================
PROTO_FLOW_CONTROL:
    20 0A 97      JSR $970A ; PROTO_DISCONNECT
    20 17 9A      JSR $9A17
    AD 34 80      LDA $8034
    C9 41         CMP #$41
    F0 0A         BEQ $9B52
    C9 42         CMP #$42
    F0 06         BEQ $9B52
    C9 40         CMP #$40
    F0 02         BEQ $9B52
    18            CLC 
    60            RTS 
    20 D5 94      JSR $94D5 ; MODEM_REG_READ_STATUS
    A9 00         LDA #$00
    99 00 C1      STA $C100,Y
    AD 34 80      LDA $8034
    C9 40         CMP #$40
    F0 EF         BEQ $9B50
    C9 42         CMP #$42
    F0 0F         BEQ $9B74
    A2 00         LDX #$00
    A0 C1         LDY #$C1
    20 7B 90      JSR $907B ; PRINT_STATUS_MSG
    20 02 90      JSR $9002 ; CLEAR_STATUS
    20 8B 93      JSR $938B ; PROTOCOL_STATE_INIT
    38            SEC 
    60            RTS 
    A2 01         LDX #$01
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD

; ============================================================
; PROTO_SEND_PACKET
; ============================================================
PROTO_SEND_PACKET:
    20 36 9C      JSR $9C36
    A2 03         LDX #$03
    A9 20         LDA #$20
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 20         AND #$20
    D0 F9         BNE $9B83

; ============================================================
; PROTO_RECV_PACKET
; ============================================================
PROTO_RECV_PACKET:
    A9 20         LDA #$20
    8D 0E C2      STA $C20E ; workspace
    8D 0F C2      STA $C20F ; workspace
    8D 04 C2      STA $C204 ; workspace
    8D 05 C2      STA $C205 ; workspace
    A9 06         LDA #$06
    8D 03 C2      STA $C203 ; workspace
    8D 20 C2      STA $C220 ; workspace
    8D 38 80      STA $8038
    60            RTS 
    2C 11 80      BIT $8011
    10 61         BPL $9C0A
    8D 26 C2      STA $C226 ; workspace
    98            TYA 
    29 3F         AND #$3F
    C9 20         CMP #$20
    90 12         BCC $9BC5
    29 1F         AND #$1F
    8D 25 C2      STA $C225 ; workspace
    0A            ASL A
    6D 25 C2      ADC $C225 ; workspace
    69 0B         ADC #$0B
    A0 9C         LDY #$9C
    90 11         BCC $9BD3
    C8            INY 
    D0 0E         BNE $9BD3
    8D 25 C2      STA $C225 ; workspace
    0A            ASL A
    6D 25 C2      ADC $C225 ; workspace
    69 14         ADC #$14
    A0 9C         LDY #$9C
    90 01         BCC $9BD3
    C8            INY 
    85 1B         STA $1B
    84 1C         STY $1C
    A0 00         LDY #$00
    B1 1B         LDA ($1B),Y
    C9 20         CMP #$20
    F0 02         BEQ $9BE1
    29 1F         AND #$1F
    09 80         ORA #$80
    9D C0 07      STA $07C0,X
    E8            INX 
    C8            INY 
    C0 03         CPY #$03
    D0 ED         BNE $9BD9
    E8            INX 
    AD 26 C2      LDA $C226 ; workspace
    4A            LSR A
    4A            LSR A
    4A            LSR A
    4A            LSR A
    20 FD 9B      JSR $9BFD
    E8            INX 
    AD 26 C2      LDA $C226 ; workspace
    29 0F         AND #$0F
    09 B0         ORA #$B0
    C9 BA         CMP #$BA
    90 04         BCC $9C07
    69 06         ADC #$06
    29 8F         AND #$8F
    9D C0 07      STA $07C0,X

; --- Protocol command tokens ---
    .byte 60 41 43 4B 44 49 52 44 41 54 4F 4B 20 45 52 52; $9C0A `ACKDIRDATOK ERR
    .byte 46 54 4C 43 4F 4D A0 40                   ; $9C1A FTLCOM.@
    AD A6 02      LDA $02A6
    D0 02         BNE $9C29
    A0 42         LDY #$42
    8C 05 DC      STY $DC05
    60            RTS 
    20 20 9C      JSR $9C20
    A9 46         LDA #$46
    A0 9C         LDY #$9C
    D0 07         BNE $9C3D
    20 20 9C      JSR $9C20
    A9 31         LDA #$31
    A0 EA         LDY #$EA
    78            SEI 
    8D 14 03      STA $0314
    8C 15 03      STY $0315
    58            CLI 
    60            RTS 
    .byte 20 7D 9C                                        ; $9C46  }.
    A2 00         LDX #$00
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 20         AND #$20
    F0 03         BEQ $9C55
    4C 31 EA      JMP $EA31
    A2 02         LDX #$02
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    20 7D 9C      JSR $9C7D
    20 8F 9C      JSR $9C8F
    4C 71 9C      JMP $9C71
    20 00 9D      JSR $9D00
    EE 21 C2      INC $C221 ; workspace
    D0 03         BNE $9C6E
    EE 22 C2      INC $C222 ; workspace
    20 7D 9C      JSR $9C7D
    20 EA FF      JSR $FFEA
    AD 0D DC      LDA $DC0D ; CIA1_ICR
    68            PLA 
    A8            TAY 
    68            PLA 
    AA            TAX 
    68            PLA 
    40            RTI 
    AD 01 DC      LDA $DC01 ; CIA1_PRB
    CD 01 DC      CMP $DC01 ; CIA1_PRB
    D0 F8         BNE $9C7D
    C9 7B         CMP #$7B
    F0 01         BEQ $9C8A
    60            RTS 
    A2 00         LDX #$00
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    20 54 9D      JSR $9D54
    2C 23 C2      BIT $C223 ; workspace
    30 01         BMI $9C98
    60            RTS 
    AC 85 C4      LDY $C485
    AD 86 C4      LDA $C486
    C0 20         CPY #$20
    D0 03         BNE $9CA5
    AD 87 C4      LDA $C487
    A2 20         LDX #$20
    20 A4 9B      JSR $9BA4
    AD 85 C4      LDA $C485
    C9 20         CMP #$20
    F0 40         BEQ $9CF1
    A2 03         LDX #$03
    BD 2C C2      LDA $C22C,X
    10 05         BPL $9CBD
    CA            DEX 
    10 F8         BPL $9CB3
    30 34         BMI $9CF1
    A5 1B         LDA $1B
    48            PHA 
    A5 1C         LDA $1C
    48            PHA 
    BD 03 9B      LDA $9B03,X
    85 1B         STA $1B
    BD 07 9B      LDA $9B07,X
    85 1C         STA $1C
    A9 80         LDA #$80
    9D 2C C2      STA $C22C,X
    AD 85 C4      LDA $C485
    9D 30 C2      STA $C230,X
    AD 86 C4      LDA $C486
    9D 28 C2      STA $C228,X
    A0 00         LDY #$00
    B9 84 C4      LDA $C484,Y
    91 1B         STA ($1B),Y
    C8            INY 
    CC 12 C2      CPY $C212 ; workspace
    D0 F5         BNE $9CE0
    68            PLA 
    85 1C         STA $1C
    68            PLA 
    85 1B         STA $1B
    4C 3C 9E      JMP $9E3C
    .byte 93 0E C1 42 4F 52 54 45 44 0D 0D 00             ; $9CF4 ...BORTED...
    20 54 9D      JSR $9D54
    2C 23 C2      BIT $C223 ; workspace
    30 01         BMI $9D09
    60            RTS 
    AD 85 C4      LDA $C485
    C9 20         CMP #$20
    D0 30         BNE $9D40
    A0 03         LDY #$03
    B9 84 C4      LDA $C484,Y
    8C 27 C2      STY $C227 ; workspace
    A2 20         LDX #$20
    A0 20         LDY #$20
    20 A4 9B      JSR $9BA4
    AC 27 C2      LDY $C227 ; workspace
    B9 84 C4      LDA $C484,Y
    AE 43 80      LDX $8043
    DD 28 C2      CMP $C228,X
    F0 05         BEQ $9D32
    CA            DEX 
    10 F8         BPL $9D28
    30 05         BMI $9D37
    A9 00         LDA #$00
    9D 2C C2      STA $C22C,X
    C8            INY 
    CC 12 C2      CPY $C212 ; workspace
    D0 D5         BNE $9D12
    4C 3C 9E      JMP $9E3C
    AD 86 C4      LDA $C486
    20 F0 99      JSR $99F0
    D0 F5         BNE $9D3D
    AE 43 80      LDX $8043
    A9 00         LDA #$00
    9D 2C C2      STA $C22C,X
    CA            DEX 
    10 FA         BPL $9D4D
    60            RTS 
    A9 00         LDA #$00
    8D 23 C2      STA $C223 ; workspace
    A2 00         LDX #$00
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    AA            TAX 
    29 40         AND #$40
    D0 22         BNE $9D85
    8A            TXA 
    29 20         AND #$20
    D0 05         BNE $9D6D
    A2 02         LDX #$02
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    EE 18 C2      INC $C218 ; workspace
    D0 0D         BNE $9D7F
    EE 19 C2      INC $C219 ; workspace
    AD 49 80      LDA $8049
    F0 05         BEQ $9D7F
    CD 19 C2      CMP $C219 ; workspace
    F0 01         BEQ $9D80
    60            RTS 
    A2 03         LDX #$03
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    A9 00         LDA #$00
    85 A2         STA $A2
    8D 18 C2      STA $C218 ; workspace
    8D 19 C2      STA $C219 ; workspace
    A2 04         LDX #$04
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    2C 13 C2      BIT $C213 ; workspace
    10 0A         BPL $9DA3
    C9 01         CMP #$01
    D0 05         BNE $9DA2
    A9 00         LDA #$00
    8D 13 C2      STA $C213 ; workspace
    60            RTS 
    C9 01         CMP #$01
    D0 08         BNE $9DAF
    A9 93         LDA #$93
    20 50 9E      JSR $9E50
    4C 41 9E      JMP $9E41
    C9 02         CMP #$02
    D0 36         BNE $9DE9
    AD 84 C4      LDA $C484
    CD 12 C2      CMP $C212 ; workspace
    F0 04         BEQ $9DBF
    A9 8E         LDA #$8E
    D0 7A         BNE $9E39
    AD 1A C2      LDA $C21A ; workspace
    F0 04         BEQ $9DC8
    A9 83         LDA #$83
    D0 71         BNE $9E39
    AD 1B C2      LDA $C21B ; workspace
    D0 F7         BNE $9DC4
    AD 12 C2      LDA $C212 ; workspace
    C9 05         CMP #$05
    B0 04         BCS $9DD8
    A9 95         LDA #$95
    D0 61         BNE $9E39
    CE 12 C2      DEC $C212 ; workspace
    CE 12 C2      DEC $C212 ; workspace
    A9 A0         LDA #$A0
    20 50 9E      JSR $9E50
    A9 FF         LDA #$FF
    8D 23 C2      STA $C223 ; workspace
    60            RTS 
    AC 12 C2      LDY $C212 ; workspace
    C0 94         CPY #$94
    D0 04         BNE $9DF4
    A9 8F         LDA #$8F
    D0 45         BNE $9E39
    2C 14 C2      BIT $C214 ; workspace
    10 0B         BPL $9E04
    A2 00         LDX #$00
    8E 14 C2      STX $C214 ; workspace
    38            SEC 
    E9 20         SBC #$20
    4C 0E 9E      JMP $9E0E
    C9 03         CMP #$03
    D0 06         BNE $9E0E
    A9 FF         LDA #$FF
    8D 14 C2      STA $C214 ; workspace
    60            RTS 
    99 84 C4      STA $C484,Y
    EE 12 C2      INC $C212 ; workspace
    8D 1C C2      STA $C21C ; workspace
    A2 07         LDX #$07
    18            CLC 
    2E 1C C2      ROL $C21C ; workspace
    2E 1B C2      ROL $C21B ; workspace
    2E 1A C2      ROL $C21A ; workspace
    90 10         BCC $9E35
    AD 1A C2      LDA $C21A ; workspace
    49 10         EOR #$10
    8D 1A C2      STA $C21A ; workspace
    AD 1B C2      LDA $C21B ; workspace
    49 21         EOR #$21
    8D 1B C2      STA $C21B ; workspace
    CA            DEX 
    10 E1         BPL $9E19
    60            RTS 
    20 50 9E      JSR $9E50
    A9 FF         LDA #$FF
    8D 13 C2      STA $C213 ; workspace
    A9 00         LDA #$00
    8D 12 C2      STA $C212 ; workspace
    8D 14 C2      STA $C214 ; workspace
    8D 1A C2      STA $C21A ; workspace
    8D 1B C2      STA $C21B ; workspace
    60            RTS 
    2C 11 80      BIT $8011
    10 03         BPL $9E58
    8D E7 07      STA $07E7
    60            RTS 
    .byte C3 4F 4E 4E 45 43 54 49 4E 47 2E 2E 2E 0D 11 00 ; $9E59 .ONNECTING......

; ============================================================
; PROTO_CONNECT
; ============================================================
PROTO_CONNECT:
    A2 00         LDX #$00
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 20         AND #$20
    D0 17         BNE $9E89
    A2 08         LDX #$08
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 40         AND #$40
    D0 05         BNE $9E80
    A2 02         LDX #$02
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    C9 03         CMP #$03
    D0 E2         BNE $9E69 ; PROTO_CONNECT
    F0 58         BEQ $9EE1
    AD 12 80      LDA $8012
    8D 20 D0      STA $D020 ; VIC_BORDER
    A2 03         LDX #$03
    A9 D0         LDA #$D0
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 6E 90      JSR $906E
    20 6E 90      JSR $906E
    2C 10 80      BIT $8010
    50 05         BVC $9EA6
    20 D8 96      JSR $96D8
    18            CLC 
    60            RTS 
    A2 59         LDX #$59
    A0 9E         LDY #$9E
    20 B7 90      JSR $90B7 ; PRINT_STRING
    A9 00         LDA #$00
    8D 00 C2      STA $C200 ; workspace
    8D 02 C2      STA $C202 ; workspace
    85 1F         STA $1F
    85 20         STA $20
    8D 01 C2      STA $C201 ; workspace
    A9 C8         LDA #$C8
    A0 9F         LDY #$9F
    20 3D 9C      JSR $9C3D
    AD 46 80      LDA $8046
    8D 05 DC      STA $DC05
    20 A9 9F      JSR $9FA9
    20 A9 9F      JSR $9FA9
    A9 40         LDA #$40
    A2 08         LDX #$08
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    A6 20         LDX $20
    E0 0A         CPX #$0A
    B0 07         BCS $9EE3
    20 90 9F      JSR $9F90
    D0 F5         BNE $9ED6
    38            SEC 
    60            RTS 
    20 90 9F      JSR $9F90
    F0 F9         BEQ $9EE1
    A6 1F         LDX $1F
    E4 20         CPX $20
    D0 26         BNE $9F14
    A2 00         LDX #$00
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    AA            TAX 
    10 ED         BPL $9EE3
    AE 02 C2      LDX $C202 ; workspace
    30 E8         BMI $9EE3
    20 BC 9F      JSR $9FBC
    BD 52 80      LDA $8052,X
    E8            INX 
    EC 51 80      CPX $8051
    D0 02         BNE $9F09
    A2 FF         LDX #$FF
    8E 02 C2      STX $C202 ; workspace
    A2 04         LDX #$04
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    4C E3 9E      JMP $9EE3
    BD 34 C2      LDA $C234,X
    E6 1F         INC $1F
    29 7F         AND #$7F
    C9 20         CMP #$20
    90 1C         BCC $9F3B
    C9 41         CMP #$41
    90 18         BCC $9F3B
    C9 5B         CMP #$5B
    B0 04         BCS $9F2B
    09 80         ORA #$80
    D0 10         BNE $9F3B
    C9 60         CMP #$60
    90 0C         BCC $9F3B
    F0 08         BEQ $9F39
    C9 7B         CMP #$7B
    B0 04         BCS $9F39
    29 DF         AND #$DF
    D0 02         BNE $9F3B
    A9 00         LDA #$00
    C9 0D         CMP #$0D
    F0 04         BEQ $9F43
    C9 20         CMP #$20
    90 A0         BCC $9EE3
    AE 01 C2      LDX $C201 ; workspace
    D0 04         BNE $9F4C
    C9 3F         CMP #$3F
    F0 09         BEQ $9F55
    C9 2A         CMP #$2A
    D0 09         BNE $9F59
    A2 00         LDX #$00
    8E 01 C2      STX $C201 ; workspace
    38            SEC 
    6E 00 C2      ROR $C200 ; workspace
    2C 10 80      BIT $8010
    30 05         BMI $9F63
    2C 00 C2      BIT $C200 ; workspace
    10 03         BPL $9F66
    20 D2 FF      JSR $FFD2 ; KERNAL_CHROUT
    29 7F         AND #$7F
    9D 00 02      STA $0200,X
    E0 4F         CPX #$4F
    F0 03         BEQ $9F72
    EE 01 C2      INC $C201 ; workspace
    C9 0D         CMP #$0D
    F0 03         BEQ $9F79
    4C E3 9E      JMP $9EE3
    A9 00         LDA #$00
    8D 00 C2      STA $C200 ; workspace
    8D 01 C2      STA $C201 ; workspace
    A2 03         LDX #$03
    BD 00 02      LDA $0200,X
    DD 4D 80      CMP $804D,X
    D0 EB         BNE $9F76
    CA            DEX 
    10 F5         BPL $9F83
    18            CLC 
    60            RTS 
    2C 10 80      BIT $8010
    10 0E         BPL $9FA3
    A2 08         LDX #$08
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 40         AND #$40
    D0 05         BNE $9FA3
    A2 02         LDX #$02
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    20 E4 FF      JSR $FFE4 ; KERNAL_GETIN
    C9 03         CMP #$03
    60            RTS 
    A2 08         LDX #$08
    A9 10         LDA #$10
    20 F0 94      JSR $94F0 ; MODEM_REG_WRITE
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    29 10         AND #$10
    D0 F9         BNE $9FB0
    A9 0D         LDA #$0D
    4C E4 94      JMP $94E4 ; MODEM_WAIT_READY
    A9 00         LDA #$00
    85 A2         STA $A2
    AD 44 80      LDA $8044
    C5 A2         CMP $A2
    B0 FC         BCS $9FC3
    60            RTS 
    .byte A2 00                                           ; $9FC8 ..
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    A8            TAY 
    29 40         AND #$40
    F0 0F         BEQ $9FE1
    A2 04         LDX #$04
    20 FA 94      JSR $94FA ; MODEM_REG_READ
    A6 20         LDX $20
    9D 34 C2      STA $C234,X
    E6 20         INC $20
    4C 31 EA      JMP $EA31
    98            TYA 
    29 20         AND #$20
    D0 F8         BNE $9FDE
    A2 02         LDX #$02
    4C 47 8F      JMP $8F47 ; MODEM_SEND_CMD
    .byte 00 00 00 00 00 00 AA AA AA AA AA AA AA AA AA AA ; $9FEB ................
    .byte AA AA AA AA AA                                  ; $9FFB .....
