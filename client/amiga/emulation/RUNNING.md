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

## Easiest path — the self-booting disk

If you have a Workbench 1.3 ADF, [`make_boot_adf.sh`](make_boot_adf.sh) builds a
**single self-booting floppy** — `CompunetReborn-boot.adf` — that cherry-picks only
the minimal boot pieces from your Workbench (shell, serial.device, a few C: commands;
everything else is Kickstart 1.3 ROM) and launches the client on boot.

```
cd client/amiga/emulation
WB="/path/to/Workbench 1.3.adf" ./make_boot_adf.sh
```

Then in FS-UAE or vAmiga: **A500 + Kickstart 1.3**, put `CompunetReborn-boot.adf` in
**DF0:**, and boot. It runs `Compunet` automatically (OFS disk, standard 1.3
bootblock). No Workbench disk, no hard-drive setup needed. ~18% full, so there's room.

> The disk embeds pieces of *your* licensed Workbench for *your* testing; it is not
> committed to the repo (it's git-ignored, like the other generated images).

## Stage 1 — launch the UI (no server)

This validates the reconstruction's UI, data blob, font, and PETSCII rendering — the
bulk of the work — without needing a server. The self-booting disk above is the
quickest way in; the manual HD/ADF routes below are alternatives.

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

**Decision: no serial→TCP bridge.** We will *not* use a virtual-modem / tcpser
serial redirect. Instead, native TCP/IP will be added to the client via
`bsdsocket.library` (AmiTCP / Roadshow / Miami) as a proper transport, at a later
stage. This keeps the Amiga client architecturally parallel to the C64 (swap only
the transport) without a modem-emulation kludge.

What that entails when we get to it:

1. **New transport module.** The transport seam is `open_transport` (`connect.c`),
   `serial_read`/`serial_write` (`transport.c`), and the dial/handshake in `modem.c`.
   A bsdsocket transport replaces exactly these: `OpenLibrary("bsdsocket.library")`
   + `connect()` in place of `OpenDevice("cnet.device")`, and `recv`/`send` in place
   of the serial IO. The modem dial + `C CNET` handshake + carrier polling are
   **dropped** (a socket connect has no dial). Everything above — `serial_io_c` ack
   handling, the frame parser, the command layer — is unchanged.
2. **Runtime requirement.** The emulated Amiga must have a TCP/IP stack installed
   (AmiTCP/Roadshow) providing `bsdsocket.library`, plus emulator networking enabled.
3. **Server-side detection.** The Amiga sends a *different* identification handshake
   than the C64 (`C CNET\r` ×2 + a 14-byte zero field, vs the C64's hash/`ADP`/`RUN`).
   The Reborn server must recognise it and treat the client as PETSCII-capable (it is
   — see `frame_control.c`). This is a **documented, not-yet-made server change**.

Until the bsdsocket transport lands, there is **no connection path** — Stage 1
(launch + UI) is the current target. Hitting "Connect" will fail at the dial (no
modem), which is expected.

## Troubleshooting

- **"Can't open cnet.device"** — `DEVS:` isn't mapped to our `devs/`. The bundled
  `s/startup-sequence` does `Assign DEVS: SYS:devs`; if you run `Compunet` by hand,
  do that Assign first (or copy `cnet.device` into your Workbench `DEVS:`).
- **Nothing renders / garbage** — check Kickstart is **1.3** and the screen opened;
  the font is built at startup from the embedded C64 charset (`build_font`).
- **Immediate crash** — most likely a struct-offset or data-blob wiring issue that
  only shows at runtime; capture the Guru/address and we can trace it against
  `recon_annotated.c`.
