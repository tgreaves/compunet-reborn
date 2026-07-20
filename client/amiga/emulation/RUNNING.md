# Running the reconstructed Amiga client on a Mac

Two packages are built by [`package.sh`](package.sh):

- **`hdd/`** — a host-directory hard-drive layout (mount as a directory HD in FS-UAE).
- **`CompunetReborn.adf`** — an 880K floppy image (drop into a drive in any emulator).

```
cd client/amiga/emulation
VBCC=/path/to/vbcc ./package.sh      # rebuilds the client + both packages
```

## What you need (once)

1. **An emulator.** Two good Mac choices:
   - **vAmiga** (Apple-Silicon native, great accuracy) — best for a quick "does it come up?" look with the ADF.
   - **FS-UAE** (mature, host-folder HD + serial→TCP) — best for the dev loop and for Stage 2.
2. **A Kickstart 1.3 ROM and a Workbench 1.3 disk.** These are Cloanto's IP — the
   usual legal Mac source is **Amiga Forever**. This repo can't ship them. The client
   targets the 1989 KS1.2/1.3 era, so use **1.3** (A500). It may also run on 2.0+.

> The client is **not** a self-booting disk — it has no ROM/Workbench on it. You boot
> an emulated 1.3 Workbench, then run `Compunet` from our disk/HD.

## Stage 1 — launch the UI (no server)

This validates the reconstruction's UI, data blob, font, and PETSCII rendering — the
bulk of the work — without needing a server.

### FS-UAE (recommended)
1. New config: **Amiga Model = A500**, **Kickstart = 1.3**.
2. Add a **Workbench 1.3** floppy in DF0: (to boot AmigaDOS).
3. Add a **Directory hard drive** pointing at `client/amiga/emulation/hdd`, device `DH0:`.
4. Boot. At the Workbench CLI/shell:
   ```
   DH0:
   Compunet
   ```
   (Or just double-click `Compunet` if you booted to Workbench.)
5. **Expected:** the Compunet screen/window opens and renders. Menus (Goto, Dir,
   Vote, Mail, …) are present. Selecting **Connect** will try to dial and — with no
   modem bridge — report "No answer"/"Failed to connect". That's the correct Stage-1
   result: the UI and command wiring work; only the transport isn't bridged yet.

### vAmiga
1. Set Kickstart 1.3 (Settings → ROM).
2. Boot a Workbench 1.3 ADF in DF0:.
3. Insert `CompunetReborn.adf` in DF1:.
4. In a shell: `DF1:` then `Compunet`.

### Fast iteration
With the FS-UAE **directory HD**, re-running `package.sh` refreshes `hdd/Compunet`
in place — just reset the emulated Amiga and re-run `Compunet`, no image rebuild.

## Stage 2 — connect to a Reborn server (later)

The binary does `OpenDevice("cnet.device")`, and `cnet.device` dials a **modem** over
the stock `serial.device`. To reach a Reborn server over TCP you need the same bridge
the C64 side uses:

1. **Serial → TCP.** In FS-UAE set the serial port to a TCP endpoint:
   ```
   serial_port = tcp://<host>:<port>
   ```
   pointed at a **virtual modem** (e.g. `tcpser`) that answers the AT dial with
   `CONNECT` and then pipes bytes to the Reborn server's socket. (vAmiga's serial
   redirection is weaker; prefer FS-UAE for this.)
2. **Server-side detection.** The Amiga sends a *different* identification handshake
   than the C64 (`C CNET\r` ×2 + a 14-byte zero field, vs the C64's hash/`ADP`/`RUN`).
   The Reborn server must recognise it and, if it wants correct rendering, treat the
   client as PETSCII-capable (it is — see `frame_control.c`). This is a **documented,
   not-yet-made server change**; until then a live login won't complete.
3. **Config.** The bundled `cnet-configuration` selects `linnet_1200` (1275 split
   baud) and user `NEW-USER`. Point the modem script / virtual modem at your bridge.

So Stage 2 is a two-sided task (emulator serial bridge **and** a small server change),
not just "run the exe". Stage 1 is independent and worth confirming first.

## Troubleshooting

- **"Can't open cnet.device"** — `DEVS:` isn't mapped to our `devs/`. The bundled
  `s/startup-sequence` does `Assign DEVS: SYS:devs`; if you run `Compunet` by hand,
  do that Assign first (or copy `cnet.device` into your Workbench `DEVS:`).
- **Nothing renders / garbage** — check Kickstart is **1.3** and the screen opened;
  the font is built at startup from the embedded C64 charset (`build_font`).
- **Immediate crash** — most likely a struct-offset or data-blob wiring issue that
  only shows at runtime; capture the Guru/address and we can trace it against
  `recon_annotated.c`.
