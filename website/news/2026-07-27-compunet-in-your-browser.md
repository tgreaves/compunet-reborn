# Compunet in your browser

There is now a Compunet client that needs no emulator, no cartridge and no setup. Go to
[connect.compunet.live](https://connect.compunet.live), sign in, and you are on.

It is the same client in two wrappers. The browser version and the Windows desktop app are built
from one codebase and behave identically — the desktop app comes as an installer that asks where
to put it, or as a portable build that keeps its settings and your editor pages beside the
executable.

Either way you get the authentic 40&times;24 PETSCII screen, the duckshoot, mail, Partyline and
the frame editor.

## Two things worth knowing

**The editor works offline.** Compose pages with no connection at all, and every page you read is
kept, so you can go back through your mail after hanging up. The buffer survives closing the
client.

**There is a 1200 baud mode.** Switch it on and pages paint as they arrive, at the speed Compunet
actually ran at. It is optional, and it is slower on purpose.

## For anyone wanting to build their own client

Two things landed alongside the client.

A **JSON API** does the hard part once, in the server: reaching Compunet used to mean
reimplementing X.25 framing, CRC, sequencing and PETSCII. Now directories arrive as entry lists
and frames as a rendered grid of cells, over WebSocket and REST. It is a second binding over the
same core — the C64 and Amiga wire protocol is untouched by it.

And a **client specification** describes the whole service independently of any platform:
transport, session, commands, the display contract, frame and directory formats, and the
subsystems. It carries the C64 font, the palette and the built-in frames as data, so a client can
be built from the document alone.
