# Amiga client — protocol analysis (in progress)

Comparing the Amiga client's wire protocol against [docs/PROTOCOL.md](../../../../../docs/PROTOCOL.md)
(the C64/server X.25-derived protocol). **This is the critical unknown** for Reborn:
does the Amiga client speak the same application-layer protocol the server implements?

## Status: PARTIAL — matching tokens, framing layer not yet confirmed

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
