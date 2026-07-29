# Requirements — what each part of this repository needs to build

One page, so this does not have to be reconstructed from four README sections and a build
failure. Nothing here is required to *run* Compunet Reborn as a user — only to build it.

| To build | You need | Check it is there |
|---|---|---|
| Server, website, tools | **Python 3** (3.12+) | `python --version` |
| Web client, Electron app | **Node.js** (20+) and npm | `node --version` |
| C64 client (`.prg`, `.crt`) | **cc65** — `ca65`, `ld65` — and **make** | `ca65 --version` |
| C64 disk image (`.d64`) | **`c1541`**, from VICE | `c1541 -help` |
| Amiga client | **vbcc** (m68k-amigaos) with `vasmm68k_mot`, `vlink` | `$VBCC/bin/vc -v` |
| Amiga ADF / icon steps | **`xdftool`**, from amitools | `xdftool --help` |

Sources: [cc65](https://cc65.github.io/) · [VICE](https://vice-emu.sourceforge.io/) ·
[vbcc](http://sun.hasenbraten.de/vbcc/) · [amitools](https://github.com/cnvogelg/amitools)

Each component builds independently — you only need the toolchain for the part you are working
on. A missing toolchain is a component you have not installed, not a build to debug.

---

## Python — server, website, tooling

Server and website each carry their own virtualenv:

```bash
cd server  && python3 -m venv venv && venv/Scripts/pip install -r requirements.txt
cd website && python3 -m venv venv && venv/Scripts/pip install -r requirements.txt
```

Tests run under `unittest`; there is no pytest in this tree:

```bash
cd server && python -m unittest discover -s tests -q
```

## Node.js — web client and Electron app

```bash
cd client/web      && npm install && npm run build     # the bundle
cd client/electron && npm install && npm run dist:win  # the desktop app
```

⚠ **Always `dist:win`, never `pack:win`** ([CLAUDE.md](CLAUDE.md), Client Rules). `pack:win`
writes only `dist/win-unpacked/` and leaves the installer and portable exe at the previous build
— the two artefacts a tester actually picks up.

⚠ **electron-builder vs. Windows symlinks.** Its `winCodeSign` package contains macOS symlinks
Windows cannot create, and the download fails. Pre-extract the cache without them:

```
7z x winCodeSign-<ver>.7z -o"%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\winCodeSign-<ver>" -xr!darwin
```

⚠ **Close the app before packaging.** A running `Compunet Reborn.exe` — especially the portable
build launched from `dist/` — holds a file lock, and the portable target then hangs indefinitely
with nothing in the log to say why:

```powershell
Get-Process | Where-Object { $_.ProcessName -like '*Compunet*' }
```

## cc65 and VICE — C64 client

```bash
cd client/c64/src && make          # -> ../compunet-reborn.prg
```

⚠ **A rebuild changes a hash the server checks.** The build embeds a hash of `compunet.s`, and
the server verifies it against `server/cfg/client_version.txt`. Source, binaries and that file
must be committed together, or the server rejects the client. See CLAUDE.md, Client Rules 1–3.

⚠ **On Windows the hash is computed over CRLF bytes.** `gen_version.py` hashes the working-tree
file, and Git checks `compunet.s` out with CRLF line endings, so a Windows build produces a
*different* hash from the committed one — `0053DF` against the `800CAD` that the shipped `.prg`
and the server both expect from the LF blob. **Do not rebuild the C64 client on Windows without
resolving this first**: publishing that hash locks out every existing client. (Nothing is wrong
in the tree today — the shipped binary and `client_version.txt` agree.)

## vbcc — Amiga client

```bash
cd client/amiga/src && VBCC=/path/to/vbcc sh build.sh     # -> compunet-client
```

⚠ **`VBCC` must be set.** `build.sh` defaults it to `/tmp/vbcc` and prepends `$VBCC/bin` to
`PATH` itself, so pointing that variable at your installation is the whole configuration — vbcc
does not need to be on `PATH` otherwise.

Building the toolchain from scratch — components, versions, download URLs, directory layout —
is documented in
**[client/amiga/vintage/tools/re/toolchain.md](client/amiga/vintage/tools/re/toolchain.md)**,
which is the authority for it.

---

## Deploying

Neither deployment host needs any of the above: both build inside Docker.

```bash
ssh -A tmg@<host>
cd ~/src/compunet-reborn && git fetch origin && git reset --hard origin/<branch>
cd ~/docker && docker compose up -d --build compunet-server compunet-web
```

`docker.lan` is the dev host; production is `nexus.extricate.org`.

⚠ **`git push` and the `ssh -A` hops need an SSH agent**, and it does not survive a reboot. If
push reports *"Permission denied (publickey)"*, check that first:

```bash
eval $(ssh-agent -a ~/.ssh/agent.sock) && ssh-add ~/.ssh/id_ed25519
export SSH_AUTH_SOCK=~/.ssh/agent.sock
```
