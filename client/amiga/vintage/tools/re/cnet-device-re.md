# cnet.device — receive-engine reverse engineering

Ground-truth RE of `cnet.device` (the Amiga Compunet transport driver) to resolve the
**read/ack demux**: exactly what `io_Command 2` (READ / `serial_read`) and `io_Command
0xb` (ACK / `serial_io_c`) do, and what the client's status bytes (`+0x2c`/`+0x2d`) and
ack char mean.

**Method:** every address below is from the *relocated* image
(`flatten.py ../../devs/cnet.device cnet_flat` → `cnet_flat.bin`, BASE `0x100000`),
disassembled with capstone (m68k, 68000, big-endian) and cross-checked against exec
LVOs and struct offsets. Nothing here is inferred from the Ghidra decompile. One
capstone branch-render bug (`bne.w $fc3f4` @0x101948) was resolved from raw bytes
(`66 00 ff 52` = disp −174 → `0x10189c`).

## Dispatch skeleton (all verified from machine code)

```
RomTag $4AFC @0x100004  (rt_MatchTag→self ✓, NT_DEVICE, RTF_AUTOINIT, v2)
  auto-init @0x100058: dSize $22, vectors $100068, struct $100084, init $1000b0
  vectors: Open $1000d6  Close $100110  Expunge $100134  Null $100000
           BeginIO $1002b0  AbortIO $10032a
  initFunc $1000b0: ExecBase→$103000, seglist→$103008, OpenLibrary dos→DOSBase $103004
  Open $1000d6: single-open; real work @0x1001bc
  open-work $1001bc: AllocMem 4K stack; build Task @$103024 (name "cnet.device");
                     AddTask initialPC = $1003a8
  device task $1003a8: loop { Wait(sig31); Forbid; GetMsg(port $103080); Permit;
                              bsr dispatch $10042c }
  BeginIO $1002b0: io_Command@+$1c, clears io_Error@+$1f=0;
     immediate mask $01C3 = cmds {0,1,6,7,8} → sync dispatch $10042c
     else → clear IOF_QUICK, PutMsg to port $103080 (handled by the task)
  dispatch $10042c: jump table @$1003f0 [io_Command] → handler; epilogue $10043e
     ReplyMsg (-$17a) unless IOF_QUICK
```

Handler jump table `@0x1003f0` (cmd → stub → worker; each stub stores the worker's d0
into `io_Error`+$1f then replies):

| cmd | meaning | stub | worker |
|-----|---------|------|--------|
| 2 | READ (`serial_read` / `serial_io_variant`) | $1004f0 | **$1005e0** |
| 3 | WRITE (`serial_write`) | $1004d8 | $100598 |
| 9 | set read mode (`link_viewer_exit`) | $100520 | $1006e0 |
| 0xb | ACK (`serial_io_c`) | $100508 | **$10073c → $101ae0** |
| 0xc | DIAL | $100550 | (calls `*$103012`+$20) |
| 0xe | STATUS (`modem_read_status`) | $100580 | $100780 (→ `*$103012`+$30, sets io_Actual) |
| 0,1,4,5 | INVALID/RESET/UPDATE/CLEAR | — | $10044c (io_Error=$fd IOERR_NOCMD) |

`*$103012` is a table of low-level serial ops: `+$20` dial, `+$2c` read-bytes,
`+$30` status/avail (returns `$FFFF` on carrier-lost).

## READ worker `$1005e0` (io_Command 2)

Two modes, selected by global flag `$104000` (set by cmd 9 @`$1006e0`: `+$2c==0`→raw(0),
`+$2c==1`→framed(1)):

- **Raw mode (`$104000==0`)**: read `io_Length` raw bytes via `*$103012`+$2c, polling
  `*$103012`+$30 for availability (`$FFFF`→return **9 carrier-lost**; `0`→delay+retry).
  No status bytes. Used for the connect handshake (`serial_io_variant`).
- **Framed mode (`$104000!=0`)**: `$1017fa(io_Data, io_Length, &+$2d, &+$2c, &io_Actual)`.
  This is the framed read the protocol uses.

## The frame primitive `$1017fa` — the demux answer

Signature `$1017fa(buf, len, &outA, &outB, &count)`. A **streaming frame reassembler**
over the de-framed/de-stuffed byte stream at running pointer `$104046` (the `$01/$02`
markers, byte-stuffing and CRC are handled by a lower layer, e.g. `$1016c6`):

- Parses each record header `[len][token][seq]`; **payload_len = len − 5**
  (`0x1018b6`–`0x101904`). Saves token at `$10471e`.
- Copies payload bytes into `buf` (`0x10191a`–`0x101948`), counting in `$10403e`
  until `== payload_len`, then does end-of-frame bookkeeping (`0x10194c`).
- **Ends the call when either** `buf` is full (`count == len`) **or** a frame whose
  **`token & $40` is set** just completed (`0x101974`: `tst $10471a` = saved `token&$40`).
- Outputs on return (`0x10198e`): `*count = bytes delivered`; `*outB = token`
  (`$10471e`, masked to `$3f` only if bit5 set); **`*outA = 1` iff it stopped on a
  `token&$40` frame** (end-of-data), else 0 (initialised to 0 at `0x101896`).

### Client-visible meaning (cross-checked with transport.c)

- `serial_read`: `out_ser_flags(+$2d) = outA` = **end-of-data flag** → explains
  `do{…}while(ser_flags==0)` (login.c) and `g_frame_eof` (frame.c);
  `out_status_hi(+$2c) = outB` = **frame token**; `io_Actual = count`.
- `serial_io_c` (`$101ae0`): reads 1 byte via `$1017fa`, takes **outB (the token)** as
  the ack char, classified `@`($40)/`A`($41)/`B`($42) — all have bit `$40` set. If the
  token is `@/A/B` and not yet EOF, it reads the rest of the frame as the message
  (`text+1`, trims trailing spaces). If the token is **not** `@/A/B`, it **pushes the
  byte back** (`subq #1` on `$104046` and `$10403e`) and forces the ack to `@`, so a data
  frame seen where an ack was expected is not consumed.

## Header layout matches the server exactly

Device `payload_len = len − 5` ⇔ server `x25_protocol.make_data_packet`
`pkt_len = len(payload) + 5`. The `[len][token][seq][payload][crc]` framing and the CRC
table (`protocol-analysis.md`) also match. So transport framing is compatible.

## The one incompatibility this RE exposes (verified both sides)

The Amiga device's **end-of-data + ack signal is a frame whose `token & $40` is set**
(`@`=accepted, `A`=message, `B`=error). The **Reborn server never sends one**: it sends
DAT frames (`token $22`), signals end with an **empty DAT frame** (`token $22`, payload 0),
and carries `RESP_ACK='A'` in the *payload*, not the token. Verified device behaviour on
that empty-DAT EOS: `payload_len=0`, `token=$22` (bit `$40` clear) → it loops for the next
frame and blocks; `outA` never becomes 1, so `while(ser_flags==0)` hangs.

**Resolution (choose one):**
1. **Server Amiga-branch** ends each response to an Amiga client with a **terminal frame,
   token `$40`/`$41`/`$42`** (accepted/message/error, message text in payload), instead of
   the empty-DAT EOS. One change satisfies both `outA` (frame completion) and `outB` (ack).
2. **Client read-path adaptation** (we control the reconstruction): treat an empty DAT
   frame as end-of-data and synthesise the `@` ack, matching the server's existing model.

Either makes an Amiga login work; (1) keeps the client bit-faithful, (2) keeps the server
unchanged for other clients. Decision pending; both are now grounded in the actual code.

## Still to confirm (not yet reversed / not yet runtime-verified)

- The lower de-framing layer that fills `$104046` (`$1016c6`, `$101ba2`→`$1050e4`, and the
  `$100a00` send path) — CRC check, `$01/$02` de-framing, byte de-stuffing, seq/ACK
  windowing. Not needed for the demux answer but completes the picture.
- **Runtime confirmation**: point the original decrunched `Compunet` binary at a
  byte-logging server and watch a real exchange, to confirm the `token&$40` terminal-frame
  model against live bytes before relying on it for the server change.
