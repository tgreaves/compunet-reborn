# A native Amiga client

Compunet shipped an Amiga client in 1989. That original binary has been recovered,
reverse-engineered and reconstructed — and it now connects to Compunet Reborn over TCP/IP.

It is the real thing rather than a lookalike: the recovered code was mapped function by function,
its OS calls resolved, and its PETSCII frame handling decoded, before being reconstructed as
recompilable C. Only the transport was changed. Where it used to drive a modem through
`cnet.device`, it now speaks to us over a bsdsocket TCP/IP stack.

Everything the C64 client offers is there — directories and the duckshoot, frames, mail,
telesoftware, Partyline — because it speaks exactly the same protocol.

## What you need

- Workbench / Kickstart **2.1 or higher**
- A bsdsocket TCP/IP stack: Roadshow, AmiTCP, Miami and others all work
- A real Amiga or an emulator

Download `compunet-reborn-amiga.lha` from the
[Connect](/connect) page, un-archive it, and double-click the **Compunet** icon. The bundled
`TCPHOST` file already points at the live service, so there is nothing to configure unless you
are connecting somewhere else.
