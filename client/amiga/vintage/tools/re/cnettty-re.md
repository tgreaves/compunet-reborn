# CnetTty ("Scrollback v1.0") — reverse-engineering notes

`CnetTty` is the Amiga Compunet client's **live interactive terminal** — the viewer the
main client hands off to when you follow an `L`-type ("link" / sub-program) directory row.
It is the Partyline / chat / MUD terminal. Its internal title strings identify it as
**"Scrollback v1.0"** by **Zugger, 1989**.

It is a separate executable, `LoadSeg`'d once at start-up (`launch_tty`, `FUN_001026ae`,
stored as `g_tty_seg_bptr` = `DAT_0012016c`) and invoked as a plain subroutine when needed.

## Obtaining a readable image (decrunch)

`vintage/CNETTTY` (4584 bytes) is a **self-decrunching HUNK executable**, but *not*
PowerPacker (so `ppdecrunch.py` does not handle it). It is a 3-hunk wrapper:

| hunk | kind | size | role |
|------|------|------|------|
| 0 | CODE | 620 B  | decruncher stub |
| 1 | DATA | 3904 B | compressed payload |
| 2 | BSS  | 5900 B | scratch the payload unpacks into |

The stub (disassembled @`0x1001c0`) is a **backwards, marker-bit LZ** decompressor: it
consumes the compressed stream from the end as big-endian longwords, refills the bit buffer
with a sentinel via `move.w #$10,ccr; roxr.l #1,d0`, and writes the output backwards from
`dst_end`. Its `a5` parameter table (`lea $1001ac(pc),a5`) gives `comp_len=0xf40` (= the
DATA hunk) and `out_len=0x170c` (= the BSS alloc).

`tools/ttydecrunch.py` is a faithful 1:1 port of that decompressor. Two independent oracles
confirm it: the backwards write pointer lands **exactly** on the buffer start, and the
5900-byte result parses as a clean HUNK executable. Reproduce with:

```
python tools/ttydecrunch.py CNETTTY decrunched/CnetTty
python tools/re/flatten.py decrunched/CnetTty tools/re/cnettty_flat
```

The decrunched program (`decrunched/CnetTty`, 5900 B) is a real **8-hunk** HUNK executable:

| hunk | kind | bytes | notes |
|------|------|-------|-------|
| 0 | CODE | 3436 | all the program logic (entry + 8 functions) |
| 1 | DATA | 356  | NewWindow/IntuiText/gadget structs |
| 2 | BSS  | —    | the scrollback text buffer (`0x1020f2`…) + state |
| 3 | DATA | 512  | more render data |
| 4–7 | CODE | 20/84/192/116 | amiga.lib call glue (`exec`/`dos`/`intuition`/`graphics`) |

`flatten.py` places hunk 0 at `0x100000`; addresses below are in that flattened image.

## Entry ABI — how the client calls it

The client (`download_link`, `FUN_0010b66a`) calls the viewer as a **C stack call**,
returning a WORD in `d0`:

```c
LONG entry(struct Screen *screen, ULONG (*read_cb)(void),
           void (*io_cb)(APTR buf, UWORD len), void (*send_cb)(APTR buf, ULONG len));
```

Verified from the original caller (`0x10b6ec`–`0x10b702`): four longs pushed, caller-cleaned
(`lea $10(a7),a7`), result tested with `tst.w d0`. Inside CnetTty the args live at
`$8/$c/$10/$14(a5)` (see `tty_entry`).

| arg | CnetTty uses it as | client passes | contract |
|-----|--------------------|---------------|----------|
| `screen`  | plants into 3 `NewWindow.Screen` fields, opens its windows on it | `g_screen` | — |
| `read_cb` | **polls** each loop iteration | `modem_read_status` (`FUN_00119a60`) | returns byte-available **count**: `0`=none, `0xffff`=carrier lost, `>0`=N ready |
| `io_cb`   | bulk-reads `min(count,35)` bytes | `serial_io_variant` (`FUN_0011998a`) | `io_cb(buf, len)` reads exactly `len` bytes |
| `send_cb` | sends typed characters | `modem_send_delayed` (`FUN_001198e0`) | `send_cb(buf, len)` |
| **ret `d0`** | `1`=clean exit, `0`=carrier lost | — | client shows *"Carrier lost"* iff `d0==0` |

## What the program does

### `tty_entry` @0x100000
1. Store `ExecBase`; `OpenLibrary` `dos`/`intuition`/`graphics` at v33
   (bases `$102004`/`$10200c`/`$102008`; `$102000`=Exec).
2. `bsr tty_init` (`0x1002ec`).
3. Copy `screen` (`$8(a5)`) into the `NewWindow.Screen` of all three windows.
4. `OpenWindow` ×3 → `$102010` (Receive), `$102014` (Send), `$102018` (Scrollback), drawing
   borders/IntuiText into each ("Send window", "Receive window", "Scrollback v1.0 Zugger'89").
5. `bsr tty_loop($c,$10,$14)` — the terminal loop, with `read_cb`/`io_cb`/`send_cb`.
6. On return: `CloseWindow` ×3, `CloseLibrary` ×3, return the loop's result.

### `tty_loop` @0x1008f2 — the terminal main loop

```
poll:  count = read_cb()                      ; $8(a5) = read_cb
       if count == 0      -> UI/idle (GetMsg on window UserPort)
       if count == 0xffff -> return 0          ; CARRIER LOST
       n = min(count, 35)
       io_cb(buf, n)                           ; $c(a5) = io_cb, bulk read
       for each byte c in buf[0..n):
           if c == 0x02: if ++stx == 3 -> return 1   ; server end-of-session
                         else next byte
           else stx = 0
           if c == 0x0d (CR): close the line, advance + scroll the receive buffer
           elif 0x20 <= c <= 0x7e: store into current line + scrollback buffer
           else: ignore
       goto poll
```

The idle branch (`0x100b30`) `GetMsg`s the interactive window's `UserPort` and dispatches:
- **`IDCMP_VANILLAKEY`** (`0x200000`): local-echo the key, then `send_cb(&c, 1)` — with CR
  turned into the host's line ending. This is the **Send window** input path.
- **`IDCMP_GADGETUP`** (`0x20`): by `GadgetID` — **0 = "Done"** (→ `return 1`), **1 = "Up"**,
  **2 = "Down"** (scroll the receive buffer). Idle with no message does a `dos.Delay(5)`.

### How it knows when to stop  ← (the key question)

There are exactly **three** exit paths out of `tty_loop`, all routed through the common
epilogue at `0x100cfc`:

| trigger | disasm | returns | client effect |
|---------|--------|---------|---------------|
| `read_cb()` returns `0xffff` (socket/carrier closed) | `0x100926` `cmpi.w #$ffff,d1` → `0x10092c` | **0** | *"Carrier lost"* + disconnect |
| **three consecutive `0x02` bytes** from the host | `0x10097e`–`0x10098e` (`stx++; cmpi.w #3; moveq #1`) | **1** | clean end; `link_end` then sends `0x02`×6 |
| **"Done" gadget** (GadgetID 0) | `0x100bb0` `moveq #1,d0` | **1** | clean end |

So the session ends when the **host signals it** (`\x02\x02\x02`), the **line drops**
(`read_cb → 0xffff`), or the **user clicks Done**. Any other received byte resets the STX
counter, so only *consecutive* `0x02`s count — matching the `0x01…`/`0x02…` control framing
the client emits in `link_drain_preamble` / `link_end`.

## Function map (hunk 0)

| addr | name | role |
|------|------|------|
| `0x100000` | `tty_entry` | exported entry; libs + windows + loop + teardown |
| `0x1002ec` | `tty_init` | clear scrollback buffers / gadget state |
| `0x10042c` | render helper | line/column rendering into a window RastPort |
| `0x1004ce` | echo helper | append/echo a typed char in the Send window |
| `0x100618` | render helper | scrollback line render |
| `0x1006f6` | render helper | scrollback line render |
| `0x10077e` | scroll helper | advance/scroll the receive buffer on CR |
| `0x10082a` | scroll render | redraw the scrollback view (Up/Down/CR) |
| `0x1008f2` | `tty_loop` | terminal main loop (above) |

## Client-side integration (the `L` path)

`download_link` (`FUN_0010b66a`): send `"D%02d"`; read + validate the 8-byte link header
(magic `0x01000001`); `link_drain_preamble` (`FUN_0010b602`) — **arm** the viewer
(`link_viewer_arm`, `FUN_001194e8`) then run the `0x01`/`0x02` marker handshake; hand off to
CnetTty; on `d0==0` show *"Carrier lost"*; `link_end` (`FUN_0010b656`) sends `0x02`×6 and
`link_viewer_exit` (`FUN_001194c8`).

Reconstruction fixes made after this analysis (both verified against the original
disassembly and CnetTty's own use of the callback):
- **read callback**: `download_link` now passes `modem_read_status` (the count-poll with the
  `0xffff` carrier sentinel), not `link_read_char` (which returns a byte value and could
  never signal carrier loss — it broke the viewer's read loop).
- **preamble leading call**: now `link_viewer_arm` (`FUN_001194e8`, the mirror of
  `link_viewer_exit`), not a spurious `link_read_char` byte read.
