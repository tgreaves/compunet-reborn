# Amiga client — protocol analysis (in progress)

Comparing the Amiga client's wire protocol against [docs/PROTOCOL.md](../../../../../docs/PROTOCOL.md)
(the C64/server X.25-derived protocol). **This is the critical unknown** for Reborn:
does the Amiga client speak the same application-layer protocol the server implements?

## Status: TRANSPORT confirmed; APPLICATION COMMANDS still open

The X.25 framing engine in `cnet.device` was disassembled and matches
`docs/PROTOCOL.md` field-for-field (see "Framing engine" below). Combined with the
matching tokens (`0x22`=DAT, `0x43`=COM) and the byte-identical CRC-CCITT table, the
**transport / framing layer matches** the Reborn server.

**Scope caution — not yet a full "same protocol" claim.** What is confirmed:
- **Transport** (framing, CRC, sequence, tokens): matches. ✓
- **Identification handshake**: differs from C64 but is detectable — see
  [identification-and-commands.md](identification-and-commands.md). ✓

What is **NOT** yet confirmed:
- **Application-layer commands** — the byte sequences the Amiga sends for user
  actions (show text frame, DIR, GOTO, login, upload/download). These ride inside
  DAT/COM frames but their contents may differ from the C64 command set the Reborn
  server expects. Must be decoded from the client's command senders and compared to
  PROTOCOL.md before claiming a Reborn Amiga client can drive the existing server.

So: a drop-in TCP `cnet.device` handles the transport, but whether the unmodified
`Compunet` client can then talk to the Reborn server depends on the application
command match — still to verify.

## Framing engine (cnet.device) — confirmed field-by-field

Disassembled the frame-send routine (CRC table at flat `0x1030a8`, referenced from
4 CRC sites; send framing around `0x100a00-0x100b20`). It builds exactly the
PROTOCOL.md wire format `$01 [len][token][seq][payload][CRC_hi][CRC_lo]`:

| PROTOCOL.md field | cnet.device evidence |
|-------------------|----------------------|
| `$01` start marker | `move.b #$1,(a0)` @0x100a1e |
| sequence, range `$20-$5F`, wraps | @0x100a00: inc seq; `cmpi.b #$5f`; if above, reload `#$20` — exact range/wrap |
| token / length bytes | emitted into the frame buffer (`moveq #$6/#$20` stores) |
| CRC-CCITT over frame | table-driven loop @0x100ab2 using `table[idx*2]` at `0x1030a8`; table verified canonical (poly 0x1021, MSB-first) |
| `[CRC_hi][CRC_lo]` appended | @0x100af2: split 16-bit CRC to two bytes, send each via send-byte `0x10094a` |

Send-byte primitive: `0x10094a`. Frame is assembled in a BSS work buffer
(`$104042`/`$10404a` running pointers, buffer base ~`$10451a`).

Consequence: framing/CRC/sequencing live **entirely in `cnet.device`**, not the
client. The client hands the device (token, data); the device produces the wire
frame. This is the transport seam — a TCP `cnet.device` reimplementation that does
the same framing to the Reborn server leaves the `Compunet` client unmodified.

---

## (earlier notes) PARTIAL — matching tokens, framing layer not yet confirmed

### Positive evidence (matches PROTOCOL.md)

The serial-write routine (`serial_write` = `FUN_0011956a`) is called with a **token**
as its 4th argument, and the observed values match the documented protocol tokens:

| Amiga call | Token | PROTOCOL.md meaning |
|------------|-------|---------------------|
| `serial_write(data+0x16, len, 1, 0x22)` | `0x22` | **DAT** (data transfer) ✓ |
| `serial_write(str, len, 1, 0x43)` | `0x43` | **COM** — matches the login-packet token `$43` in PROTOCOL.md ✓ |

`FUN_00108254` sends a DAT packet from a packet struct: data at `+0x16`, length at
`+0x12`, token `0x22`. Multiple senders use token `0x43` (COM) for login/command.

These token values are distinctive and align with the server. Encouraging.

### CRC lives in cnet.device — seam is lower than the client (important)

**`cnet.device` contains the canonical CRC-CCITT table** (poly `0x1021`, MSB-first) at
file offset `0x333c` — verified byte-for-byte against the standard table
(`0000 1021 2042 3063 4084 50a5 60c6 70e7 …`). This is the **same CRC** the server
and C64 ROM use.

Consequence: the CRC (and very likely the `$01…$02` framing/sequencing) is computed
**inside `cnet.device`, not in the `Compunet` client**. The client hands
`cnet.device` a token + data buffer (via `serial_write`), and the device wraps it in
the X.25 frame with CRC.

This **revises the transport-seam model** in `docs/amiga-client.md`, which described
`cnet.device` as a pure serial passthrough with framing in the client. The CRC table
in the device shows framing is (at least partly) in the device. The RE of
`cnet.device` needs revisiting — the earlier disassembly saw the serial-wrapper
skeleton but missed the framing/CRC layer.

Implication for Reborn: the transport swap boundary may be **at the `cnet.device`
level** (replace the device with one that speaks TCP + does the same framing/CRC),
rather than only swapping the client's serial read/write. Either works, but the
device-level swap matches the original architecture and keeps the client unmodified.
- **X.25 markers (`$01`/`$02`) and the length/seq/CRC wrapper** have not been located
  in the client yet. The `serial_write` args are (data, length, ?, token) — it is not
  yet confirmed where (or whether) the `$01 [len][token][seq][payload][CRC] $02`
  wrapper is assembled. It may be built in a layer above, or handled below.
- The 3rd `serial_write` arg (`param_3`, always `1` in observed calls) and the
  IORequest offsets `0x2c/0x2d/0x1f/0x20` are used as in/out parameter slots; their
  exact meaning (io_Actual, status, unit flags) needs pinning before conclusions.

### Next

- **Re-RE `cnet.device`** around the CRC table (`0x333c`): find the framing routine
  that emits `$01 [len][token][seq][payload][CRC] $02`, confirm sequence handling and
  ACK ($20) logic. This is where the protocol match is proven or disproven.
- Confirm the client→device interface: token values (`0x22` DAT, `0x43` COM already
  seen) and how data buffers are passed.
- Compare the device's frame construction against PROTOCOL.md field-by-field.

### Summary so far

- **Tokens match** (`0x22`=DAT, `0x43`=COM). ✓
- **CRC matches** (canonical CRC-CCITT table in `cnet.device`). ✓
- Full frame construction to be read out of `cnet.device` to complete the match.
- Transport seam is likely **at the device**, not the client — revises
  `docs/amiga-client.md`.
