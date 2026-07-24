# Amiga client — connect & login flow

Traced from disassembly (some functions are not in `recon.c` because Ghidra's
auto-analysis only seeded hunk starts; these mid-hunk functions are reached via
indirect calls and were disassembled directly with capstone).

## do_connect  @ 0x10343c

The connection entry point (docs cited ~0x10343c). Pseudocode:

```
do_connect():
    if connected_flag ($3108.a4) and $3118.a4 != 0:   # already connected
        ... (falls through to already-connected handling)
    status = open_transport()          # jsr 0x10381a -> 0x1192b6
    saved_status = status              # -7(a5)
    switch (status):
        case 0:  goto open_logon_window
        case 10: print "Modem error"          ($5fe.a4)   -> return 0
        case 1:  print <modem msg $5f4.a4>                -> return 0
        default: print "Can't open cnet.device" ($60a.a4) -> return 0
  open_logon_window:
    if (open_window() == 0):           # bsr 0x1030c6
        cleanup (jsr 0x1037fc)
        print "Can't open logon window" ($622.a4) -> return 0
    ... proceed to logon UI (user ID / password entry) ...
```

Key facts:
- **`open_transport` (0x1192b6, via thunk 0x10381a)** returns a status byte:
  `0`=ok, `10`=Modem error (no carrier / dial failed), `1`=other modem msg,
  else = can't open cnet.device. So carrier/dial result is surfaced as a small
  integer code here, right after the device open.
- Only on status 0 does it open the **logon window** and proceed to user
  ID/password entry. "*** No Such User ***" (validate_login, 0x10e0fc, ref at
  0x10e330) is the server's rejection shown later in the login exchange.

## open_transport  @ 0x1192b6  (device/port setup)

Standard Amiga device bring-up:
- Calls a create-port/IO helper (`0x119b36`) three times, storing results at
  `$60a8`, `$60ac`, `$60b0(a4)` — the message port(s) and the two IORequests
  (these are `g_device_port`, `g_read_req`, `g_write_req` — see function-map.md).
- Reads `mp_SigBit` (port offset `0xf`) and builds signal masks (`1<<sigbit`)
  stored at `$60be(a4)` etc. — the masks used by `serial_read`/`serial_write` when
  they `Wait()` for IO completion.
- On any allocation failure returns 1 (→ caller shows the error).

## "Immediately after the modem connects"

1. `open_transport` opens `cnet.device` (which itself dials via the modem script and
   waits for CONNECT — see cnet.device RE), creates ports + IORequests, computes
   signal masks. Returns status 0 on success.
2. `do_connect` opens the logon window.
3. The client then runs the logon UI and the login packet exchange (token `0x43`
   COM — see protocol-analysis.md) and handles "No Such User".

Note: the actual dial/CONNECT handshake is inside `cnet.device` (modem scripts),
consistent with the CRC/framing also living in the device.
