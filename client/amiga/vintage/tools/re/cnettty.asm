; CnetTty ("Scrollback v1.0", Zugger '89) — full relocated disassembly
; Regenerate: ttydecrunch.py CNETTTY decrunched/CnetTty; flatten.py decrunched/CnetTty cnettty_flat; then disassemble.
; Code hunks placed by flatten.py at 0x100000 (h0), 0x108000 (h4), 0x109000 (h5), 0x10a000 (h6), 0x10b000 (h7).

;===== hunk 0 (program logic, 3436 bytes) =====
100000: 4e55fffa             link.w   a5, #$fffa
100004: 48e72000             movem.l  d2, -(a7)
100008: 3b7c0001fffa         move.w   #$1, -$6(a5)
10000e: 307c0004             movea.w  #$4, a0
100012: 23d000102000         move.l   (a0), $102000.l
100018: 48780021             pea.l    $21.w
10001c: 48790010111e         pea.l    $10111e.l
100022: 4eba0d10             jsr      $100d34(pc)
100026: 504f                 addq.w   #$8, a7
100028: 23c000102004         move.l   d0, $102004.l
10002e: 4a80                 tst.l    d0
100030: 670002ae             beq.w    $1002e0
100034: 48780021             pea.l    $21.w
100038: 48790010112a         pea.l    $10112a.l
10003e: 4eba0cf4             jsr      $100d34(pc)
100042: 504f                 addq.w   #$8, a7
100044: 23c00010200c         move.l   d0, $10200c.l
10004a: 4a80                 tst.l    d0
10004c: 67000286             beq.w    $1002d4
100050: 48780021             pea.l    $21.w
100054: 48790010113c         pea.l    $10113c.l
10005a: 4eba0cd8             jsr      $100d34(pc)
10005e: 504f                 addq.w   #$8, a7
100060: 23c000102008         move.l   d0, $102008.l
100066: 4a80                 tst.l    d0
100068: 6700025e             beq.w    $1002c8
10006c: 6100027e             bsr.w    $1002ec
100070: 23fc0010209000101020 move.l   #$102090, $101020.l
10007a: 206d0008             movea.l  $8(a5), a0
10007e: 23c80010102c         move.l   a0, $10102c.l
100084: 23c80010106c         move.l   a0, $10106c.l
10008a: 23c8001010b8         move.l   a0, $1010b8.l
100090: 48790010100e         pea.l    $10100e.l
100096: 4eba0c8a             jsr      $100d22(pc)
10009a: 584f                 addq.w   #$4, a7
10009c: 23c000102010         move.l   d0, $102010.l
1000a2: 4a80                 tst.l    d0
1000a4: 67000216             beq.w    $1002bc
1000a8: 2240                 movea.l  d0, a1
1000aa: 20690032             movea.l  $32(a1), a0
1000ae: 4878000b             pea.l    $b.w
1000b2: 48780004             pea.l    $4.w
1000b6: 4879001010ca         pea.l    $1010ca.l
1000bc: 2f08                 move.l   a0, -(a7)
1000be: 23c80010201c         move.l   a0, $10201c.l
1000c4: 4eba0c74             jsr      $100d3a(pc)
1000c8: 4fef0010             lea.l    $10(a7), a7
1000cc: 42a7                 clr.l    -(a7)
1000ce: 2f3900102010         move.l   $102010.l, -(a7)
1000d4: 487900102090         pea.l    $102090.l
1000da: 4eba0c3a             jsr      $100d16(pc)
1000de: 4fef000c             lea.l    $c(a7), a7
1000e2: 48780001             pea.l    $1.w
1000e6: 2f390010201c         move.l   $10201c.l, -(a7)
1000ec: 4eba0c5e             jsr      $100d4c(pc)
1000f0: 504f                 addq.w   #$8, a7
1000f2: 48780005             pea.l    $5.w
1000f6: 2f390010201c         move.l   $10201c.l, -(a7)
1000fc: 4eba0c1e             jsr      $100d1c(pc)
100100: 504f                 addq.w   #$8, a7
100102: 48780001             pea.l    $1.w
100106: 2f390010201c         move.l   $10201c.l, -(a7)
10010c: 4eba0c50             jsr      $100d5e(pc)
100110: 504f                 addq.w   #$8, a7
100112: 7000                 moveq    #$0, d0
100114: 33c0001020c4         move.w   d0, $1020c4.l
10011a: 33c0001020c6         move.w   d0, $1020c6.l
100120: 61000360             bsr.w    $100482
100124: 4239001020c8         clr.b    $1020c8.l
10012a: 48790010104e         pea.l    $10104e.l
100130: 4eba0bf0             jsr      $100d22(pc)
100134: 584f                 addq.w   #$4, a7
100136: 23c000102014         move.l   d0, $102014.l
10013c: 4a80                 tst.l    d0
10013e: 67000170             beq.w    $1002b0
100142: 2240                 movea.l  d0, a1
100144: 20690032             movea.l  $32(a1), a0
100148: 4878000b             pea.l    $b.w
10014c: 48780004             pea.l    $4.w
100150: 4879001010de         pea.l    $1010de.l
100156: 2f08                 move.l   a0, -(a7)
100158: 23c800102020         move.l   a0, $102020.l
10015e: 4eba0bda             jsr      $100d3a(pc)
100162: 4fef0010             lea.l    $10(a7), a7
100166: 48780001             pea.l    $1.w
10016a: 2f3900102020         move.l   $102020.l, -(a7)
100170: 4eba0bda             jsr      $100d4c(pc)
100174: 504f                 addq.w   #$8, a7
100176: 48780006             pea.l    $6.w
10017a: 2f3900102020         move.l   $102020.l, -(a7)
100180: 4eba0b9a             jsr      $100d1c(pc)
100184: 504f                 addq.w   #$8, a7
100186: 48780001             pea.l    $1.w
10018a: 2f3900102020         move.l   $102020.l, -(a7)
100190: 4eba0bcc             jsr      $100d5e(pc)
100194: 504f                 addq.w   #$8, a7
100196: 4279001020ee         clr.w    $1020ee.l
10019c: 33fc000b001020f0     move.w   #$b, $1020f0.l
1001a4: 61000528             bsr.w    $1006ce
1001a8: 48790010109a         pea.l    $10109a.l
1001ae: 4eba0b72             jsr      $100d22(pc)
1001b2: 584f                 addq.w   #$4, a7
1001b4: 23c000102018         move.l   d0, $102018.l
1001ba: 4a80                 tst.l    d0
1001bc: 670000e6             beq.w    $1002a4
1001c0: 2240                 movea.l  d0, a1
1001c2: 20690032             movea.l  $32(a1), a0
1001c6: 4878000b             pea.l    $b.w
1001ca: 48780004             pea.l    $4.w
1001ce: 4879001010f2         pea.l    $1010f2.l
1001d4: 2f08                 move.l   a0, -(a7)
1001d6: 23c800102024         move.l   a0, $102024.l
1001dc: 4eba0b5c             jsr      $100d3a(pc)
1001e0: 4fef0010             lea.l    $10(a7), a7
1001e4: 48780001             pea.l    $1.w
1001e8: 2f3900102024         move.l   $102024.l, -(a7)
1001ee: 4eba0b5c             jsr      $100d4c(pc)
1001f2: 504f                 addq.w   #$8, a7
1001f4: 48780002             pea.l    $2.w
1001f8: 2f3900102024         move.l   $102024.l, -(a7)
1001fe: 4eba0b1c             jsr      $100d1c(pc)
100202: 504f                 addq.w   #$8, a7
100204: 48780001             pea.l    $1.w
100208: 2f3900102024         move.l   $102024.l, -(a7)
10020e: 4eba0b4e             jsr      $100d5e(pc)
100212: 504f                 addq.w   #$8, a7
100214: 7001                 moveq    #$1, d0
100216: 7214                 moveq    #$14, d1
100218: 7400                 moveq    #$0, d2
10021a: 33c00010676a         move.w   d0, $10676a.l
100220: 33c000106766         move.w   d0, $106766.l
100226: 33c10010676e         move.w   d1, $10676e.l
10022c: 33c100106768         move.w   d1, $106768.l
100232: 3b42fffe             move.w   d2, -$2(a5)
100236: 33c20010676c         move.w   d2, $10676c.l
10023c: 0c6d0014fffe         cmpi.w   #$14, -$2(a5)
100242: 6430                 bcc.b    $100274
100244: 426dfffc             clr.w    -$4(a5)
100248: 322dfffc             move.w   -$4(a5), d1
10024c: 0c410023             cmpi.w   #$23, d1
100250: 641c                 bcc.b    $10026e
100252: 2001                 move.l   d1, d0
100254: c1fc01f4             muls.w   #$1f4, d0
100258: 2040                 movea.l  d0, a0
10025a: d1fc001020f2         adda.l   #$1020f2, a0
100260: d0edfffe             adda.w   -$2(a5), a0
100264: 10bc0020             move.b   #$20, (a0)
100268: 526dfffc             addq.w   #$1, -$4(a5)
10026c: 60da                 bra.b    $100248
10026e: 526dfffe             addq.w   #$1, -$2(a5)
100272: 60c8                 bra.b    $10023c
100274: 2f3900102014         move.l   $102014.l, -(a7)
10027a: 4eba0a8e             jsr      $100d0a(pc)
10027e: 584f                 addq.w   #$4, a7
100280: 2f2d0014             move.l   $14(a5), -(a7)
100284: 2f2d0010             move.l   $10(a5), -(a7)
100288: 2f2d000c             move.l   $c(a5), -(a7)
10028c: 61000664             bsr.w    $1008f2
100290: 4fef000c             lea.l    $c(a7), a7
100294: 2f3900102018         move.l   $102018.l, -(a7)
10029a: 3b40fffa             move.w   d0, -$6(a5)
10029e: 4eba0ab2             jsr      $100d52(pc)
1002a2: 584f                 addq.w   #$4, a7
1002a4: 2f3900102014         move.l   $102014.l, -(a7)
1002aa: 4eba0aa6             jsr      $100d52(pc)
1002ae: 584f                 addq.w   #$4, a7
1002b0: 2f3900102010         move.l   $102010.l, -(a7)
1002b6: 4eba0a9a             jsr      $100d52(pc)
1002ba: 584f                 addq.w   #$4, a7
1002bc: 2f3900102008         move.l   $102008.l, -(a7)
1002c2: 4eba0aa0             jsr      $100d64(pc)
1002c6: 584f                 addq.w   #$4, a7
1002c8: 2f390010200c         move.l   $10200c.l, -(a7)
1002ce: 4eba0a94             jsr      $100d64(pc)
1002d2: 584f                 addq.w   #$4, a7
1002d4: 2f3900102004         move.l   $102004.l, -(a7)
1002da: 4eba0a88             jsr      $100d64(pc)
1002de: 584f                 addq.w   #$4, a7
1002e0: 302dfffa             move.w   -$6(a5), d0
1002e4: 4cdf0004             movem.l  (a7)+, d2
1002e8: 4e5d                 unlk     a5
1002ea: 4e75                 rts      
1002ec: 4e55fff6             link.w   a5, #$fff6
1002f0: 48e72030             movem.l  d2/a2-a3, -(a7)
1002f4: 426dfffe             clr.w    -$2(a5)
1002f8: 42adfff6             clr.l    -$a(a5)
1002fc: 322dfffe             move.w   -$2(a5), d1
100300: 0c410003             cmpi.w   #$3, d1
100304: 6c000100             bge.w    $100406
100308: 2001                 move.l   d1, d0
10030a: 7434                 moveq    #$34, d2
10030c: c1c2                 muls.w   d2, d0
10030e: 2040                 movea.l  d0, a0
100310: d1fc00102028         adda.l   #$102028, a0
100316: 20adfff6             move.l   -$a(a5), (a0)
10031a: 2001                 move.l   d1, d0
10031c: 48c0                 ext.l    d0
10031e: ed80                 asl.l    #$6, d0
100320: 5e80                 addq.l   #$7, d0
100322: 31400004             move.w   d0, $4(a0)
100326: 31420006             move.w   d2, $6(a0)
10032a: 317c003c0008         move.w   #$3c, $8(a0)
100330: 317c0010000a         move.w   #$10, $a(a0)
100336: 317c0007000c         move.w   #$7, $c(a0)
10033c: 317c0002000e         move.w   #$2, $e(a0)
100342: 317c00010010         move.w   #$1, $10(a0)
100348: 217c001011060012     move.l   #$101106, $12(a0)
100350: 93c9                 suba.l   a1, a1
100352: 21490016             move.l   a1, $16(a0)
100356: 2001                 move.l   d1, d0
100358: c1fc0014             muls.w   #$14, d0
10035c: 2440                 movea.l  d0, a2
10035e: 264a                 movea.l  a2, a3
100360: d7fc00106770         adda.l   #$106770, a3
100366: 214b001a             move.l   a3, $1a(a0)
10036a: 2149001e             move.l   a1, $1e(a0)
10036e: 21490022             move.l   a1, $22(a0)
100372: 31410026             move.w   d1, $26(a0)
100376: 21490028             move.l   a1, $28(a0)
10037a: 2401                 move.l   d1, d2
10037c: 48c2                 ext.l    d2
10037e: e582                 asl.l    #$2, d2
100380: 2642                 movea.l  d2, a3
100382: d7fc0010111a         adda.l   #$10111a, a3
100388: 2153002c             move.l   (a3), $2c(a0)
10038c: 21490030             move.l   a1, $30(a0)
100390: 2640                 movea.l  d0, a3
100392: d7fc00106770         adda.l   #$106770, a3
100398: 16bc0006             move.b   #$6, (a3)
10039c: 2640                 movea.l  d0, a3
10039e: d7fc00106770         adda.l   #$106770, a3
1003a4: 177c00090001         move.b   #$9, $1(a3)
1003aa: 2640                 movea.l  d0, a3
1003ac: d7fc00106770         adda.l   #$106770, a3
1003b2: 422b0002             clr.b    $2(a3)
1003b6: 2640                 movea.l  d0, a3
1003b8: d7fc00106770         adda.l   #$106770, a3
1003be: 377c000e0004         move.w   #$e, $4(a3)
1003c4: 2640                 movea.l  d0, a3
1003c6: d7fc00106770         adda.l   #$106770, a3
1003cc: 377c00040006         move.w   #$4, $6(a3)
1003d2: 2640                 movea.l  d0, a3
1003d4: d7fc00106770         adda.l   #$106770, a3
1003da: 27490008             move.l   a1, $8(a3)
1003de: 2640                 movea.l  d0, a3
1003e0: d7fc00106770         adda.l   #$106770, a3
1003e6: 2749000c             move.l   a1, $c(a3)
1003ea: d5fc00106770         adda.l   #$106770, a2
1003f0: 25490010             move.l   a1, $10(a2)
1003f4: 2b48fffa             move.l   a0, -$6(a5)
1003f8: 526dfffe             addq.w   #$1, -$2(a5)
1003fc: 2b6dfffafff6         move.l   -$6(a5), -$a(a5)
100402: 6000fef8             bra.w    $1002fc
100406: 23fc0010114e0010677c move.l   #$10114e, $10677c.l
100410: 23fc0010115400106790 move.l   #$101154, $106790.l
10041a: 23fc0010115a001067a4 move.l   #$10115a, $1067a4.l
100424: 4cdf0c04             movem.l  (a7)+, d2/a2-a3
100428: 4e5d                 unlk     a5
10042a: 4e75                 rts      
10042c: 4e550000             link.w   a5, #$0
100430: 13ed000b00101000     move.b   $b(a5), $101000.l
100438: 3039001020c6         move.w   $1020c6.l, d0
10043e: 48c0                 ext.l    d0
100440: e780                 asl.l    #$3, d0
100442: 5880                 addq.l   #$4, d0
100444: 3239001020c4         move.w   $1020c4.l, d1
10044a: 48c1                 ext.l    d1
10044c: e781                 asl.l    #$3, d1
10044e: 068100000011         addi.l   #$11, d1
100454: 2f01                 move.l   d1, -(a7)
100456: 2f00                 move.l   d0, -(a7)
100458: 2f390010201c         move.l   $10201c.l, -(a7)
10045e: 4eba08b0             jsr      $100d10(pc)
100462: 4fef000c             lea.l    $c(a7), a7
100466: 48780001             pea.l    $1.w
10046a: 487900101000         pea.l    $101000.l
100470: 2f390010201c         move.l   $10201c.l, -(a7)
100476: 4eba08e0             jsr      $100d58(pc)
10047a: 4fef000c             lea.l    $c(a7), a7
10047e: 4e5d                 unlk     a5
100480: 4e75                 rts      
100482: 48e73000             movem.l  d2-d3, -(a7)
100486: 3039001020c6         move.w   $1020c6.l, d0
10048c: 48c0                 ext.l    d0
10048e: e780                 asl.l    #$3, d0
100490: 2200                 move.l   d0, d1
100492: 5881                 addq.l   #$4, d1
100494: 3439001020c4         move.w   $1020c4.l, d2
10049a: 48c2                 ext.l    d2
10049c: e782                 asl.l    #$3, d2
10049e: 2602                 move.l   d2, d3
1004a0: 06830000000b         addi.l   #$b, d3
1004a6: 06800000000b         addi.l   #$b, d0
1004ac: 068200000012         addi.l   #$12, d2
1004b2: 2f02                 move.l   d2, -(a7)
1004b4: 2f00                 move.l   d0, -(a7)
1004b6: 2f03                 move.l   d3, -(a7)
1004b8: 2f01                 move.l   d1, -(a7)
1004ba: 2f390010201c         move.l   $10201c.l, -(a7)
1004c0: 4eba0884             jsr      $100d46(pc)
1004c4: 4fef0014             lea.l    $14(a7), a7
1004c8: 4cdf000c             movem.l  (a7)+, d2-d3
1004cc: 4e75                 rts      
1004ce: 4e550000             link.w   a5, #$0
1004d2: 102d000b             move.b   $b(a5), d0
1004d6: 024000ff             andi.w   #$ff, d0
1004da: 0c40000c             cmpi.w   #$c, d0
1004de: 6776                 beq.b    $100556
1004e0: 0c400008             cmpi.w   #$8, d0
1004e4: 6740                 beq.b    $100526
1004e6: 0c40000d             cmpi.w   #$d, d0
1004ea: 660000c6             bne.w    $1005b2
1004ee: 0c790004001020c4     cmpi.w   #$4, $1020c4.l
1004f6: 6c28                 bge.b    $100520
1004f8: 48780020             pea.l    $20.w
1004fc: 6100ff2e             bsr.w    $10042c
100500: 584f                 addq.w   #$4, a7
100502: 5279001020c4         addq.w   #$1, $1020c4.l
100508: 4279001020c6         clr.w    $1020c6.l
10050e: 6100ff72             bsr.w    $100482
100512: 13ed000b001020c8     move.b   $b(a5), $1020c8.l
10051a: 7001                 moveq    #$1, d0
10051c: 600000f6             bra.w    $100614
100520: 7000                 moveq    #$0, d0
100522: 600000f0             bra.w    $100614
100526: 4a79001020c6         tst.w    $1020c6.l
10052c: 6722                 beq.b    $100550
10052e: 48780020             pea.l    $20.w
100532: 6100fef8             bsr.w    $10042c
100536: 584f                 addq.w   #$4, a7
100538: 5379001020c6         subq.w   #$1, $1020c6.l
10053e: 6100ff42             bsr.w    $100482
100542: 13ed000b001020c8     move.b   $b(a5), $1020c8.l
10054a: 7001                 moveq    #$1, d0
10054c: 600000c6             bra.w    $100614
100550: 7000                 moveq    #$0, d0
100552: 600000c0             bra.w    $100614
100556: 48780001             pea.l    $1.w
10055a: 2f390010201c         move.l   $10201c.l, -(a7)
100560: 4eba07ba             jsr      $100d1c(pc)
100564: 504f                 addq.w   #$8, a7
100566: 48780032             pea.l    $32.w
10056a: 4878011b             pea.l    $11b.w
10056e: 4878000b             pea.l    $b.w
100572: 48780004             pea.l    $4.w
100576: 2f390010201c         move.l   $10201c.l, -(a7)
10057c: 4eba07c8             jsr      $100d46(pc)
100580: 4fef0014             lea.l    $14(a7), a7
100584: 48780005             pea.l    $5.w
100588: 2f390010201c         move.l   $10201c.l, -(a7)
10058e: 4eba078c             jsr      $100d1c(pc)
100592: 504f                 addq.w   #$8, a7
100594: 7000                 moveq    #$0, d0
100596: 33c0001020c4         move.w   d0, $1020c4.l
10059c: 33c0001020c6         move.w   d0, $1020c6.l
1005a2: 6100fede             bsr.w    $100482
1005a6: 13ed000b001020c8     move.b   $b(a5), $1020c8.l
1005ae: 7001                 moveq    #$1, d0
1005b0: 6062                 bra.b    $100614
1005b2: 0c790022001020c6     cmpi.w   #$22, $1020c6.l
1005ba: 660e                 bne.b    $1005ca
1005bc: 0c790004001020c4     cmpi.w   #$4, $1020c4.l
1005c4: 6604                 bne.b    $1005ca
1005c6: 7000                 moveq    #$0, d0
1005c8: 604a                 bra.b    $100614
1005ca: 122d000b             move.b   $b(a5), d1
1005ce: 0c010020             cmpi.b   #$20, d1
1005d2: 6540                 bcs.b    $100614
1005d4: 0c01007e             cmpi.b   #$7e, d1
1005d8: 623a                 bhi.b    $100614
1005da: 7000                 moveq    #$0, d0
1005dc: 102d000b             move.b   $b(a5), d0
1005e0: 2f00                 move.l   d0, -(a7)
1005e2: 6100fe48             bsr.w    $10042c
1005e6: 584f                 addq.w   #$4, a7
1005e8: 5279001020c6         addq.w   #$1, $1020c6.l
1005ee: 0c790023001020c6     cmpi.w   #$23, $1020c6.l
1005f6: 660c                 bne.b    $100604
1005f8: 4279001020c6         clr.w    $1020c6.l
1005fe: 5279001020c4         addq.w   #$1, $1020c4.l
100604: 6100fe7c             bsr.w    $100482
100608: 13ed000b001020c8     move.b   $b(a5), $1020c8.l
100610: 7001                 moveq    #$1, d0
100612: 4e71                 nop      
100614: 4e5d                 unlk     a5
100616: 4e75                 rts      
100618: 4e55fffc             link.w   a5, #$fffc
10061c: 426dfffe             clr.w    -$2(a5)
100620: 3b790010676afffc     move.w   $10676a.l, -$4(a5)
100628: 302dfffe             move.w   -$2(a5), d0
10062c: 526dfffe             addq.w   #$1, -$2(a5)
100630: 0c400014             cmpi.w   #$14, d0
100634: 6714                 beq.b    $10064a
100636: 526dfffc             addq.w   #$1, -$4(a5)
10063a: 0c6d01f5fffc         cmpi.w   #$1f5, -$4(a5)
100640: 66e6                 bne.b    $100628
100642: 3b7c0001fffc         move.w   #$1, -$4(a5)
100648: 60de                 bra.b    $100628
10064a: 0c6d0001000a         cmpi.w   #$1, $a(a5)
100650: 663a                 bne.b    $10068c
100652: 426dfffe             clr.w    -$2(a5)
100656: 7000                 moveq    #$0, d0
100658: 302dfffe             move.w   -$2(a5), d0
10065c: 0c8000000025         cmpi.l   #$25, d0
100662: 6728                 beq.b    $10068c
100664: 3040                 movea.w  d0, a0
100666: 2248                 movea.l  a0, a1
100668: d3fc00106742         adda.l   #$106742, a1
10066e: 2200                 move.l   d0, d1
100670: c3fc01f4             muls.w   #$1f4, d1
100674: 2041                 movea.l  d1, a0
100676: d1fc001020f2         adda.l   #$1020f2, a0
10067c: d0f90010676a         adda.w   $10676a.l, a0
100682: 1290                 move.b   (a0), (a1)
100684: 5280                 addq.l   #$1, d0
100686: 3b40fffe             move.w   d0, -$2(a5)
10068a: 60ca                 bra.b    $100656
10068c: 4a6d000a             tst.w    $a(a5)
100690: 6638                 bne.b    $1006ca
100692: 426dfffe             clr.w    -$2(a5)
100696: 7000                 moveq    #$0, d0
100698: 302dfffe             move.w   -$2(a5), d0
10069c: 0c8000000025         cmpi.l   #$25, d0
1006a2: 6726                 beq.b    $1006ca
1006a4: 3040                 movea.w  d0, a0
1006a6: 2248                 movea.l  a0, a1
1006a8: d3fc00106742         adda.l   #$106742, a1
1006ae: 2200                 move.l   d0, d1
1006b0: c3fc01f4             muls.w   #$1f4, d1
1006b4: 2041                 movea.l  d1, a0
1006b6: d1fc001020f2         adda.l   #$1020f2, a0
1006bc: d0edfffc             adda.w   -$4(a5), a0
1006c0: 1290                 move.b   (a0), (a1)
1006c2: 5280                 addq.l   #$1, d0
1006c4: 3b40fffe             move.w   d0, -$2(a5)
1006c8: 60cc                 bra.b    $100696
1006ca: 4e5d                 unlk     a5
1006cc: 4e75                 rts      
1006ce: 3039001020f0         move.w   $1020f0.l, d0
1006d4: 48c0                 ext.l    d0
1006d6: 2200                 move.l   d0, d1
1006d8: 5e81                 addq.l   #$7, d1
1006da: 2f01                 move.l   d1, -(a7)
1006dc: 4878000b             pea.l    $b.w
1006e0: 2f00                 move.l   d0, -(a7)
1006e2: 48780004             pea.l    $4.w
1006e6: 2f3900102020         move.l   $102020.l, -(a7)
1006ec: 4eba0658             jsr      $100d46(pc)
1006f0: 4fef0014             lea.l    $14(a7), a7
1006f4: 4e75                 rts      
1006f6: 4e55fffc             link.w   a5, #$fffc
1006fa: 3b790010676afffe     move.w   $10676a.l, -$2(a5)
100702: 426dfffc             clr.w    -$4(a5)
100706: 302dfffc             move.w   -$4(a5), d0
10070a: 526dfffc             addq.w   #$1, -$4(a5)
10070e: 0c400014             cmpi.w   #$14, d0
100712: 675e                 beq.b    $100772
100714: 48780001             pea.l    $1.w
100718: 6100fefe             bsr.w    $100618
10071c: 584f                 addq.w   #$4, a7
10071e: 52790010676a         addq.w   #$1, $10676a.l
100724: 0c7901f50010676a     cmpi.w   #$1f5, $10676a.l
10072c: 6608                 bne.b    $100736
10072e: 33fc00010010676a     move.w   #$1, $10676a.l
100736: 302dfffc             move.w   -$4(a5), d0
10073a: 48c0                 ext.l    d0
10073c: e780                 asl.l    #$3, d0
10073e: 068000000009         addi.l   #$9, d0
100744: 2f00                 move.l   d0, -(a7)
100746: 48780004             pea.l    $4.w
10074a: 2f3900102024         move.l   $102024.l, -(a7)
100750: 4eba05be             jsr      $100d10(pc)
100754: 4fef000c             lea.l    $c(a7), a7
100758: 48780023             pea.l    $23.w
10075c: 487900106742         pea.l    $106742.l
100762: 2f3900102024         move.l   $102024.l, -(a7)
100768: 4eba05ee             jsr      $100d58(pc)
10076c: 4fef000c             lea.l    $c(a7), a7
100770: 6094                 bra.b    $100706
100772: 33edfffe0010676a     move.w   -$2(a5), $10676a.l
10077a: 4e5d                 unlk     a5
10077c: 4e75                 rts      
10077e: 3039001020ee         move.w   $1020ee.l, d0
100784: 48c0                 ext.l    d0
100786: 4a80                 tst.l    d0
100788: 661a                 bne.b    $1007a4
10078a: 3239001020ee         move.w   $1020ee.l, d1
100790: 5280                 addq.l   #$1, d0
100792: 3041                 movea.w  d1, a0
100794: d1fc001020c9         adda.l   #$1020c9, a0
10079a: 10bc0020             move.b   #$20, (a0)
10079e: 33c0001020ee         move.w   d0, $1020ee.l
1007a4: 3039001020f0         move.w   $1020f0.l, d0
1007aa: 48c0                 ext.l    d0
1007ac: 5c80                 addq.l   #$6, d0
1007ae: 2f00                 move.l   d0, -(a7)
1007b0: 48780004             pea.l    $4.w
1007b4: 2f3900102020         move.l   $102020.l, -(a7)
1007ba: 4eba0554             jsr      $100d10(pc)
1007be: 4fef000c             lea.l    $c(a7), a7
1007c2: 3039001020ee         move.w   $1020ee.l, d0
1007c8: 48c0                 ext.l    d0
1007ca: 2f00                 move.l   d0, -(a7)
1007cc: 4879001020c9         pea.l    $1020c9.l
1007d2: 2f3900102020         move.l   $102020.l, -(a7)
1007d8: 4eba057e             jsr      $100d58(pc)
1007dc: 4fef000c             lea.l    $c(a7), a7
1007e0: 4279001020ee         clr.w    $1020ee.l
1007e6: 3039001020f0         move.w   $1020f0.l, d0
1007ec: 48c0                 ext.l    d0
1007ee: 0c800000009b         cmpi.l   #$9b, d0
1007f4: 6e0a                 bgt.b    $100800
1007f6: 5080                 addq.l   #$8, d0
1007f8: 33c0001020f0         move.w   d0, $1020f0.l
1007fe: 6024                 bra.b    $100824
100800: 487800aa             pea.l    $aa.w
100804: 4878011b             pea.l    $11b.w
100808: 4878000b             pea.l    $b.w
10080c: 48780004             pea.l    $4.w
100810: 48780008             pea.l    $8.w
100814: 42a7                 clr.l    -(a7)
100816: 2f3900102020         move.l   $102020.l, -(a7)
10081c: 4eba0510             jsr      $100d2e(pc)
100820: 4fef001c             lea.l    $1c(a7), a7
100824: 6100fea8             bsr.w    $1006ce
100828: 4e75                 rts      
10082a: 4e550000             link.w   a5, #$0
10082e: 7000                 moveq    #$0, d0
100830: 302d000a             move.w   $a(a5), d0
100834: 2f00                 move.l   d0, -(a7)
100836: 6100fde0             bsr.w    $100618
10083a: 584f                 addq.w   #$4, a7
10083c: 0c6d0001000a         cmpi.w   #$1, $a(a5)
100842: 6652                 bne.b    $100896
100844: 487800aa             pea.l    $aa.w
100848: 4878011b             pea.l    $11b.w
10084c: 4878000b             pea.l    $b.w
100850: 48780004             pea.l    $4.w
100854: 4878fff8             pea.l    $fff8.w
100858: 42a7                 clr.l    -(a7)
10085a: 2f3900102024         move.l   $102024.l, -(a7)
100860: 4eba04cc             jsr      $100d2e(pc)
100864: 4fef001c             lea.l    $1c(a7), a7
100868: 48780011             pea.l    $11.w
10086c: 48780004             pea.l    $4.w
100870: 2f3900102024         move.l   $102024.l, -(a7)
100876: 4eba0498             jsr      $100d10(pc)
10087a: 4fef000c             lea.l    $c(a7), a7
10087e: 48780023             pea.l    $23.w
100882: 487900106742         pea.l    $106742.l
100888: 2f3900102024         move.l   $102024.l, -(a7)
10088e: 4eba04c8             jsr      $100d58(pc)
100892: 4fef000c             lea.l    $c(a7), a7
100896: 4a6d000a             tst.w    $a(a5)
10089a: 6652                 bne.b    $1008ee
10089c: 487800aa             pea.l    $aa.w
1008a0: 4878011b             pea.l    $11b.w
1008a4: 4878000b             pea.l    $b.w
1008a8: 48780004             pea.l    $4.w
1008ac: 48780008             pea.l    $8.w
1008b0: 42a7                 clr.l    -(a7)
1008b2: 2f3900102024         move.l   $102024.l, -(a7)
1008b8: 4eba0474             jsr      $100d2e(pc)
1008bc: 4fef001c             lea.l    $1c(a7), a7
1008c0: 487800a9             pea.l    $a9.w
1008c4: 48780004             pea.l    $4.w
1008c8: 2f3900102024         move.l   $102024.l, -(a7)
1008ce: 4eba0440             jsr      $100d10(pc)
1008d2: 4fef000c             lea.l    $c(a7), a7
1008d6: 48780023             pea.l    $23.w
1008da: 487900106742         pea.l    $106742.l
1008e0: 2f3900102024         move.l   $102024.l, -(a7)
1008e6: 4eba0470             jsr      $100d58(pc)
1008ea: 4fef000c             lea.l    $c(a7), a7
1008ee: 4e5d                 unlk     a5
1008f0: 4e75                 rts      
1008f2: 4e55ffb6             link.w   a5, #$ffb6
1008f6: 48e72000             movem.l  d2, -(a7)
1008fa: 7000                 moveq    #$0, d0
1008fc: 3b40fffa             move.w   d0, -$6(a5)
100900: 3b40ffe0             move.w   d0, -$20(a5)
100904: 3b7c0001ffdc         move.w   #$1, -$24(a5)
10090a: 4a6dfffa             tst.w    -$6(a5)
10090e: 660a                 bne.b    $10091a
100910: 206d0008             movea.l  $8(a5), a0
100914: 4e90                 jsr      (a0)
100916: 3b40fffa             move.w   d0, -$6(a5)
10091a: 4a6dfffa             tst.w    -$6(a5)
10091e: 67000210             beq.w    $100b30
100922: 322dfffa             move.w   -$6(a5), d1
100926: 0c41ffff             cmpi.w   #$ffff, d1
10092a: 6606                 bne.b    $100932
10092c: 7000                 moveq    #$0, d0
10092e: 600003cc             bra.w    $100cfc
100932: 426dffdc             clr.w    -$24(a5)
100936: 48c1                 ext.l    d1
100938: 0c8100000023         cmpi.l   #$23, d1
10093e: 6d02                 blt.b    $100942
100940: 7223                 moveq    #$23, d1
100942: 302dfffa             move.w   -$6(a5), d0
100946: 48c0                 ext.l    d0
100948: 3b41fff8             move.w   d1, -$8(a5)
10094c: 48c1                 ext.l    d1
10094e: 9081                 sub.l    d1, d0
100950: 2f01                 move.l   d1, -(a7)
100952: 486dffb7             pea.l    -$49(a5)
100956: 3b40fffa             move.w   d0, -$6(a5)
10095a: 206d000c             movea.l  $c(a5), a0
10095e: 4e90                 jsr      (a0)
100960: 504f                 addq.w   #$8, a7
100962: 426dfff6             clr.w    -$a(a5)
100966: 322dfff6             move.w   -$a(a5), d1
10096a: b26dfff8             cmp.w    -$8(a5), d1
10096e: 6c0001c0             bge.w    $100b30
100972: 103510b7             move.b   -$49(a5, d1.w), d0
100976: 1b40ffdb             move.b   d0, -$25(a5)
10097a: 5500                 subq.b   #$2, d0
10097c: 6614                 bne.b    $100992
10097e: 526dffe0             addq.w   #$1, -$20(a5)
100982: 0c6d0003ffe0         cmpi.w   #$3, -$20(a5)
100988: 6600019e             bne.w    $100b28
10098c: 7001                 moveq    #$1, d0
10098e: 6000036c             bra.w    $100cfc
100992: 426dffe0             clr.w    -$20(a5)
100996: 102dffdb             move.b   -$25(a5), d0
10099a: 0c00000d             cmpi.b   #$d, d0
10099e: 6600009e             bne.w    $100a3e
1009a2: 3b79001020eefffc     move.w   $1020ee.l, -$4(a5)
1009aa: 322dfffc             move.w   -$4(a5), d1
1009ae: 0c410024             cmpi.w   #$24, d1
1009b2: 6c1e                 bge.b    $1009d2
1009b4: 2001                 move.l   d1, d0
1009b6: c1fc01f4             muls.w   #$1f4, d0
1009ba: 2040                 movea.l  d0, a0
1009bc: d1fc001020f2         adda.l   #$1020f2, a0
1009c2: d0f900106768         adda.w   $106768.l, a0
1009c8: 10bc0020             move.b   #$20, (a0)
1009cc: 526dfffc             addq.w   #$1, -$4(a5)
1009d0: 60d8                 bra.b    $1009aa
1009d2: 527900106768         addq.w   #$1, $106768.l
1009d8: 0c7901f500106768     cmpi.w   #$1f5, $106768.l
1009e0: 6608                 bne.b    $1009ea
1009e2: 7001                 moveq    #$1, d0
1009e4: 33c000106768         move.w   d0, $106768.l
1009ea: 303900106768         move.w   $106768.l, d0
1009f0: 48c0                 ext.l    d0
1009f2: 323900106766         move.w   $106766.l, d1
1009f8: 48c1                 ext.l    d1
1009fa: b081                 cmp.l    d1, d0
1009fc: 6632                 bne.b    $100a30
1009fe: 5281                 addq.l   #$1, d1
100a00: 33c100106766         move.w   d1, $106766.l
100a06: 0c4101f5             cmpi.w   #$1f5, d1
100a0a: 6608                 bne.b    $100a14
100a0c: 7001                 moveq    #$1, d0
100a0e: 33c000106766         move.w   d0, $106766.l
100a14: 53790010676c         subq.w   #$1, $10676c.l
100a1a: 4a790010676c         tst.w    $10676c.l
100a20: 6a0e                 bpl.b    $100a30
100a22: 53790010676a         subq.w   #$1, $10676a.l
100a28: 42a7                 clr.l    -(a7)
100a2a: 6100fdfe             bsr.w    $10082a
100a2e: 584f                 addq.w   #$4, a7
100a30: 52790010676e         addq.w   #$1, $10676e.l
100a36: 6100fd46             bsr.w    $10077e
100a3a: 600000ec             bra.w    $100b28
100a3e: 102dffdb             move.b   -$25(a5), d0
100a42: 0c000020             cmpi.b   #$20, d0
100a46: 650000e0             bcs.w    $100b28
100a4a: 0c00007e             cmpi.b   #$7e, d0
100a4e: 620000d8             bhi.w    $100b28
100a52: 3239001020ee         move.w   $1020ee.l, d1
100a58: 0c410023             cmpi.w   #$23, d1
100a5c: 66000096             bne.w    $100af4
100a60: 3b41fffc             move.w   d1, -$4(a5)
100a64: 322dfffc             move.w   -$4(a5), d1
100a68: 0c410024             cmpi.w   #$24, d1
100a6c: 6c1e                 bge.b    $100a8c
100a6e: 2001                 move.l   d1, d0
100a70: c1fc01f4             muls.w   #$1f4, d0
100a74: 2040                 movea.l  d0, a0
100a76: d1fc001020f2         adda.l   #$1020f2, a0
100a7c: d0f900106768         adda.w   $106768.l, a0
100a82: 10bc0020             move.b   #$20, (a0)
100a86: 526dfffc             addq.w   #$1, -$4(a5)
100a8a: 60d8                 bra.b    $100a64
100a8c: 527900106768         addq.w   #$1, $106768.l
100a92: 0c7901f500106768     cmpi.w   #$1f5, $106768.l
100a9a: 6608                 bne.b    $100aa4
100a9c: 7001                 moveq    #$1, d0
100a9e: 33c000106768         move.w   d0, $106768.l
100aa4: 303900106768         move.w   $106768.l, d0
100aaa: 48c0                 ext.l    d0
100aac: 323900106766         move.w   $106766.l, d1
100ab2: 48c1                 ext.l    d1
100ab4: b081                 cmp.l    d1, d0
100ab6: 6632                 bne.b    $100aea
100ab8: 5281                 addq.l   #$1, d1
100aba: 33c100106766         move.w   d1, $106766.l
100ac0: 0c4101f5             cmpi.w   #$1f5, d1
100ac4: 6608                 bne.b    $100ace
100ac6: 7001                 moveq    #$1, d0
100ac8: 33c000106766         move.w   d0, $106766.l
100ace: 53790010676c         subq.w   #$1, $10676c.l
100ad4: 4a790010676c         tst.w    $10676c.l
100ada: 6a0e                 bpl.b    $100aea
100adc: 53790010676a         subq.w   #$1, $10676a.l
100ae2: 42a7                 clr.l    -(a7)
100ae4: 6100fd44             bsr.w    $10082a
100ae8: 584f                 addq.w   #$4, a7
100aea: 52790010676e         addq.w   #$1, $10676e.l
100af0: 6100fc8c             bsr.w    $10077e
100af4: 3079001020ee         movea.w  $1020ee.l, a0
100afa: 2248                 movea.l  a0, a1
100afc: d3fc001020c9         adda.l   #$1020c9, a1
100b02: 102dffdb             move.b   -$25(a5), d0
100b06: 1280                 move.b   d0, (a1)
100b08: 2008                 move.l   a0, d0
100b0a: 2200                 move.l   d0, d1
100b0c: c3fc01f4             muls.w   #$1f4, d1
100b10: 2241                 movea.l  d1, a1
100b12: d3fc001020f2         adda.l   #$1020f2, a1
100b18: d2f900106768         adda.w   $106768.l, a1
100b1e: 12adffdb             move.b   -$25(a5), (a1)
100b22: 5279001020ee         addq.w   #$1, $1020ee.l
100b28: 526dfff6             addq.w   #$1, -$a(a5)
100b2c: 6000fe38             bra.w    $100966
100b30: 207900102010         movea.l  $102010.l, a0
100b36: 2f280056             move.l   $56(a0), -(a7)
100b3a: 4eba01ec             jsr      $100d28(pc)
100b3e: 584f                 addq.w   #$4, a7
100b40: 2b40fff2             move.l   d0, -$e(a5)
100b44: 4a80                 tst.l    d0
100b46: 6700019e             beq.w    $100ce6
100b4a: 426dffdc             clr.w    -$24(a5)
100b4e: 2040                 movea.l  d0, a0
100b50: 2b680014ffe6         move.l   $14(a0), -$1a(a5)
100b56: 7200                 moveq    #$0, d1
100b58: 32280018             move.w   $18(a0), d1
100b5c: 3b68001affde         move.w   $1a(a0), -$22(a5)
100b62: 2b68001cffea         move.l   $1c(a0), -$16(a5)
100b68: 2f00                 move.l   d0, -(a7)
100b6a: 2b41ffe2             move.l   d1, -$1e(a5)
100b6e: 4eba0194             jsr      $100d04(pc)
100b72: 584f                 addq.w   #$4, a7
100b74: 202dffe6             move.l   -$1a(a5), d0
100b78: 0c8000200000         cmpi.l   #$200000, d0
100b7e: 670000be             beq.w    $100c3e
100b82: 0c8000000020         cmpi.l   #$20, d0
100b88: 66a6                 bne.b    $100b30
100b8a: 2b6dffeaffee         move.l   -$16(a5), -$12(a5)
100b90: 206dffee             movea.l  -$12(a5), a0
100b94: 30280026             move.w   $26(a0), d0
100b98: 1b40ffda             move.b   d0, -$26(a5)
100b9c: 024000ff             andi.w   #$ff, d0
100ba0: 0c400002             cmpi.w   #$2, d0
100ba4: 6750                 beq.b    $100bf6
100ba6: 0c400001             cmpi.w   #$1, d0
100baa: 670a                 beq.b    $100bb6
100bac: 4a40                 tst.w    d0
100bae: 6680                 bne.b    $100b30
100bb0: 7001                 moveq    #$1, d0
100bb2: 60000148             bra.w    $100cfc
100bb6: 30390010676c         move.w   $10676c.l, d0
100bbc: 48c0                 ext.l    d0
100bbe: 4a80                 tst.l    d0
100bc0: 6f00ff6e             ble.w    $100b30
100bc4: 5380                 subq.l   #$1, d0
100bc6: 52790010676e         addq.w   #$1, $10676e.l
100bcc: 53790010676a         subq.w   #$1, $10676a.l
100bd2: 33c00010676c         move.w   d0, $10676c.l
100bd8: 4a790010676a         tst.w    $10676a.l
100bde: 6608                 bne.b    $100be8
100be0: 33fc01f40010676a     move.w   #$1f4, $10676a.l
100be8: 48780001             pea.l    $1.w
100bec: 6100fc3c             bsr.w    $10082a
100bf0: 584f                 addq.w   #$4, a7
100bf2: 6000ff3c             bra.w    $100b30
100bf6: 30390010676e         move.w   $10676e.l, d0
100bfc: 48c0                 ext.l    d0
100bfe: 2200                 move.l   d0, d1
100c00: 048100000016         subi.l   #$16, d1
100c06: 4a81                 tst.l    d1
100c08: 6f00ff26             ble.w    $100b30
100c0c: 52790010676c         addq.w   #$1, $10676c.l
100c12: 5380                 subq.l   #$1, d0
100c14: 52790010676a         addq.w   #$1, $10676a.l
100c1a: 33c00010676e         move.w   d0, $10676e.l
100c20: 0c7901f50010676a     cmpi.w   #$1f5, $10676a.l
100c28: 6608                 bne.b    $100c32
100c2a: 33fc00010010676a     move.w   #$1, $10676a.l
100c32: 42a7                 clr.l    -(a7)
100c34: 6100fbf4             bsr.w    $10082a
100c38: 584f                 addq.w   #$4, a7
100c3a: 6000fef4             bra.w    $100b30
100c3e: 202dffe2             move.l   -$1e(a5), d0
100c42: 1b40ffdb             move.b   d0, -$25(a5)
100c46: 0c00000d             cmpi.b   #$d, d0
100c4a: 6668                 bne.b    $100cb4
100c4c: 0c39000d001020c8     cmpi.b   #$d, $1020c8.l
100c54: 661c                 bne.b    $100c72
100c56: 4878000c             pea.l    $c.w
100c5a: 6100f872             bsr.w    $1004ce
100c5e: 584f                 addq.w   #$4, a7
100c60: 48780001             pea.l    $1.w
100c64: 486dffdb             pea.l    -$25(a5)
100c68: 206d0010             movea.l  $10(a5), a0
100c6c: 4e90                 jsr      (a0)
100c6e: 504f                 addq.w   #$8, a7
100c70: 6064                 bra.b    $100cd6
100c72: 7200                 moveq    #$0, d1
100c74: 122dffdb             move.b   -$25(a5), d1
100c78: 2f01                 move.l   d1, -(a7)
100c7a: 6100f852             bsr.w    $1004ce
100c7e: 584f                 addq.w   #$4, a7
100c80: 4a80                 tst.l    d0
100c82: 6712                 beq.b    $100c96
100c84: 48780001             pea.l    $1.w
100c88: 486dffdb             pea.l    -$25(a5)
100c8c: 206d0010             movea.l  $10(a5), a0
100c90: 4e90                 jsr      (a0)
100c92: 504f                 addq.w   #$8, a7
100c94: 6040                 bra.b    $100cd6
100c96: 4878000c             pea.l    $c.w
100c9a: 6100f832             bsr.w    $1004ce
100c9e: 584f                 addq.w   #$4, a7
100ca0: 48780002             pea.l    $2.w
100ca4: 487900101160         pea.l    $101160.l
100caa: 206d0010             movea.l  $10(a5), a0
100cae: 4e90                 jsr      (a0)
100cb0: 504f                 addq.w   #$8, a7
100cb2: 6022                 bra.b    $100cd6
100cb4: 7200                 moveq    #$0, d1
100cb6: 122dffdb             move.b   -$25(a5), d1
100cba: 2f01                 move.l   d1, -(a7)
100cbc: 6100f810             bsr.w    $1004ce
100cc0: 584f                 addq.w   #$4, a7
100cc2: 4a80                 tst.l    d0
100cc4: 6710                 beq.b    $100cd6
100cc6: 48780001             pea.l    $1.w
100cca: 486dffdb             pea.l    -$25(a5)
100cce: 206d0010             movea.l  $10(a5), a0
100cd2: 4e90                 jsr      (a0)
100cd4: 504f                 addq.w   #$8, a7
100cd6: 102dffdb             move.b   -$25(a5), d0
100cda: 024000ff             andi.w   #$ff, d0
100cde: 3b40fffe             move.w   d0, -$2(a5)
100ce2: 6000fe4c             bra.w    $100b30
100ce6: 4a6dffdc             tst.w    -$24(a5)
100cea: 6700fc18             beq.w    $100904
100cee: 48780005             pea.l    $5.w
100cf2: 4eba004c             jsr      $100d40(pc)
100cf6: 584f                 addq.w   #$4, a7
100cf8: 6000fc0a             bra.w    $100904
100cfc: 4cdf0004             movem.l  (a7)+, d2
100d00: 4e5d                 unlk     a5
100d02: 4e75                 rts      
100d04: 4ef900109014         jmp      $109014.l
100d0a: 4ef90010b060         jmp      $10b060.l
100d10: 4ef90010a01c         jmp      $10a01c.l
100d16: 4ef90010b044         jmp      $10b044.l
100d1c: 4ef90010a058         jmp      $10a058.l
100d22: 4ef90010b030         jmp      $10b030.l
100d28: 4ef900109000         jmp      $109000.l
100d2e: 4ef90010a0a0         jmp      $10a0a0.l
100d34: 4ef90010903c         jmp      $10903c.l
100d3a: 4ef90010b014         jmp      $10b014.l
100d40: 4ef900108000         jmp      $108000.l
100d46: 4ef90010a038         jmp      $10a038.l
100d4c: 4ef90010a088         jmp      $10a088.l
100d52: 4ef90010b000         jmp      $10b000.l
100d58: 4ef90010a000         jmp      $10a000.l
100d5e: 4ef90010a070         jmp      $10a070.l
100d64: 4ef900109028         jmp      $109028.l
100d6a: 7061                 moveq    #$61, d0

;===== hunk 4 (amiga.lib glue) @0x108000 =====
108000: 2f0e                 move.l   a6, -(a7)
108002: 2c7900102004         movea.l  $102004.l, a6
108008: 222f0008             move.l   $8(a7), d1
10800c: 4eaeff3a             jsr      -$c6(a6)
108010: 2c5f                 movea.l  (a7)+, a6
108012: 4e75                 rts      

;===== hunk 5 (amiga.lib glue) @0x109000 =====
109000: 2f0e                 move.l   a6, -(a7)
109002: 2c7900102000         movea.l  $102000.l, a6
109008: 206f0008             movea.l  $8(a7), a0
10900c: 4eaefe8c             jsr      -$174(a6)
109010: 2c5f                 movea.l  (a7)+, a6
109012: 4e75                 rts      
109014: 2f0e                 move.l   a6, -(a7)
109016: 2c7900102000         movea.l  $102000.l, a6
10901c: 226f0008             movea.l  $8(a7), a1
109020: 4eaefe86             jsr      -$17a(a6)
109024: 2c5f                 movea.l  (a7)+, a6
109026: 4e75                 rts      
109028: 2f0e                 move.l   a6, -(a7)
10902a: 2c7900102000         movea.l  $102000.l, a6
109030: 226f0008             movea.l  $8(a7), a1
109034: 4eaefe62             jsr      -$19e(a6)
109038: 2c5f                 movea.l  (a7)+, a6
10903a: 4e75                 rts      
10903c: 2f0e                 move.l   a6, -(a7)
10903e: 2c7900102000         movea.l  $102000.l, a6
109044: 226f0008             movea.l  $8(a7), a1
109048: 202f000c             move.l   $c(a7), d0
10904c: 4eaefdd8             jsr      -$228(a6)
109050: 2c5f                 movea.l  (a7)+, a6
109052: 4e75                 rts      

;===== hunk 6 (amiga.lib glue) @0x10a000 =====
10a000: 2f0e                 move.l   a6, -(a7)
10a002: 2c7900102008         movea.l  $102008.l, a6
10a008: 226f0008             movea.l  $8(a7), a1
10a00c: 206f000c             movea.l  $c(a7), a0
10a010: 202f0010             move.l   $10(a7), d0
10a014: 4eaeffc4             jsr      -$3c(a6)
10a018: 2c5f                 movea.l  (a7)+, a6
10a01a: 4e75                 rts      
10a01c: 2f0e                 move.l   a6, -(a7)
10a01e: 2c7900102008         movea.l  $102008.l, a6
10a024: 226f0008             movea.l  $8(a7), a1
10a028: 4cef0003000c         movem.l  $c(a7), d0-d1
10a02e: 4eaeff10             jsr      -$f0(a6)
10a032: 2c5f                 movea.l  (a7)+, a6
10a034: 4e75                 rts      
10a036: 000048e7             ori.b    #$e7, d0
10a03a: 3002                 move.w   d2, d0
10a03c: 2c7900102008         movea.l  $102008.l, a6
10a042: 226f0010             movea.l  $10(a7), a1
10a046: 4cef000f0014         movem.l  $14(a7), d0-d3
10a04c: 4eaefece             jsr      -$132(a6)
10a050: 4cdf400c             movem.l  (a7)+, d2-d3/a6
10a054: 4e75                 rts      
10a056: 00002f0e             ori.b    #$e, d0
10a05a: 2c7900102008         movea.l  $102008.l, a6
10a060: 226f0008             movea.l  $8(a7), a1
10a064: 202f000c             move.l   $c(a7), d0
10a068: 4eaefeaa             jsr      -$156(a6)
10a06c: 2c5f                 movea.l  (a7)+, a6
10a06e: 4e75                 rts      
10a070: 2f0e                 move.l   a6, -(a7)
10a072: 2c7900102008         movea.l  $102008.l, a6
10a078: 226f0008             movea.l  $8(a7), a1
10a07c: 202f000c             move.l   $c(a7), d0
10a080: 4eaefea4             jsr      -$15c(a6)
10a084: 2c5f                 movea.l  (a7)+, a6
10a086: 4e75                 rts      
10a088: 2f0e                 move.l   a6, -(a7)
10a08a: 2c7900102008         movea.l  $102008.l, a6
10a090: 226f0008             movea.l  $8(a7), a1
10a094: 202f000c             move.l   $c(a7), d0
10a098: 4eaefe9e             jsr      -$162(a6)
10a09c: 2c5f                 movea.l  (a7)+, a6
10a09e: 4e75                 rts      
10a0a0: 48e73c02             movem.l  d2-d5/a6, -(a7)
10a0a4: 2c790010             movea.l  $aaaaaaaa.l, a6

;===== hunk 7 (amiga.lib glue) @0x10b000 =====
10b000: 2f0e                 move.l   a6, -(a7)
10b002: 2c790010200c         movea.l  $10200c.l, a6
10b008: 206f0008             movea.l  $8(a7), a0
10b00c: 4eaeffb8             jsr      -$48(a6)
10b010: 2c5f                 movea.l  (a7)+, a6
10b012: 4e75                 rts      
10b014: 2f0e                 move.l   a6, -(a7)
10b016: 2c790010200c         movea.l  $10200c.l, a6
10b01c: 4cef03000008         movem.l  $8(a7), a0-a1
10b022: 4cef00030010         movem.l  $10(a7), d0-d1
10b028: 4eaeff8e             jsr      -$72(a6)
10b02c: 2c5f                 movea.l  (a7)+, a6
10b02e: 4e75                 rts      
10b030: 2f0e                 move.l   a6, -(a7)
10b032: 2c790010200c         movea.l  $10200c.l, a6
10b038: 206f0008             movea.l  $8(a7), a0
10b03c: 4eaeff34             jsr      -$cc(a6)
10b040: 2c5f                 movea.l  (a7)+, a6
10b042: 4e75                 rts      
10b044: 48e70022             movem.l  a2/a6, -(a7)
10b048: 2c790010200c         movea.l  $10200c.l, a6
10b04e: 4cef0700000c         movem.l  $c(a7), a0-a2
10b054: 4eaeff22             jsr      -$de(a6)
10b058: 4cdf4400             movem.l  (a7)+, a2/a6
10b05c: 4e75                 rts      
10b05e: 00002f0e             ori.b    #$e, d0
10b062: 2c790010200c         movea.l  $10200c.l, a6
10b068: 206f0008             movea.l  $8(a7), a0
10b06c: 4eaefec8             jsr      -$138(a6)
10b070: 2c5f                 movea.l  (a7)+, a6
10b072: 4e75                 rts      
