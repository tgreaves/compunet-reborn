# Requirements — what each part of this repository needs to build

One page, so this does not have to be reconstructed from four README sections and a build
failure. Nothing here is required to *run* Compunet Reborn as a user — only to build it, or to
work on it.

| To work on | You need | Check it is there |
|---|---|---|
| Server, website, tools | **Python 3** (3.12+) | `python --version` |
| Web client, Electron app | **Node.js** (20+) and npm | `node --version` |
| C64 client (`.prg`, `.crt`) | **cc65** — `ca65`, `ld65` — and **make** | `ca65 --version` |
| C64 disk image (`.d64`) | **`c1541`**, from VICE | `c1541 -help` |
| Amiga client | **vbcc** (m68k-amigaos) with `vasmm68k_mot`, `vlink` | `$VBCC/bin/vc -v` |
| Amiga ADF / icon steps | **`xdftool`**, from amitools | `xdftool --help` |
| Issues and pull requests | **GitHub CLI** (`gh`) | `gh --version` |

Sources: [cc65](https://cc65.github.io/) · [VICE](https://vice-emu.sourceforge.io/) ·
[vbcc](http://sun.hasenbraten.de/vbcc/) · [amitools](https://github.com/cnvogelg/amitools) ·
[GitHub CLI](https://cli.github.com/)

Each component builds independently — you only need the toolchain for the part you are working
on. A missing toolchain is a component you have not installed, not a build to debug.

---

## Python — server, website, tooling

Production runs `python:3.12-slim` ([server/Dockerfile](server/Dockerfile)), so 3.12 is the
version to match locally.

Server and website each carry their own virtualenv. The interpreter and the venv's script
directory are named differently per platform — `bin/` and `python3` on Linux and macOS,
`Scripts/` and `python` on Windows:

```bash
cd server  && python3 -m venv venv && venv/bin/pip install -r requirements.txt          # Linux/macOS
cd website && python3 -m venv venv && venv/bin/pip install -r requirements.txt
```

```powershell
cd server ; python -m venv venv ; venv\Scripts\pip install -r requirements.txt           # Windows
cd website; python -m venv venv ; venv\Scripts\pip install -r requirements.txt
```

Tests run under `unittest`; there is no pytest in this tree:

```bash
cd server && python -m unittest discover -s tests -q
```

⚠ **On Windows, `python --version` does not tell you whether Python is installed.** Windows
ships alias stubs at `%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe`, so with no interpreter
present the check prints *"Python was not found; run without arguments to install from the
Microsoft Store"* and exits non-zero — an advert, not a "command not found". Anything that
shells out to `python3` reaches the same stub and fails the same puzzling way. Confirm a real
interpreter instead:

```powershell
winget install --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" --version
```

## Running the server locally

```bash
cp server/cfg/users.json.example server/cfg/users.json
./server.sh start        # Linux/macOS
```

It listens on 6400 (C64/Amiga), 6401 (PETSCII terminal), 6403 (admin REST) and 6404 (client API
— Binding B). The server runs without any `.env` — the C64, Amiga, terminal and client-API paths
all work — but the website cannot then talk to it at all; see the shared-key trap below.
`venv/`, `cfg/users.json` and every `.env` are gitignored.

⚠ **There are no accounts until you create `cfg/users.json`.** Only `users.json.example` is
tracked, and it carries the `TEST` and `ADMIN` logins — a server started without it runs
perfectly and rejects every login.

⚠ **`./server.sh` does not work on Windows.** It selects `venv/bin/python3`, which a Windows venv
does not have (`venv/Scripts/python.exe`), falls back to `python3` — the Store stub above — and
the server dies at once. It now reports that correctly (`Server failed to start`, followed by the
tail of `server/logs/compunet-server.log`, and no PID file); until 1.2.2 it printed
`Server started (PID …)` regardless, because it backgrounded the process and recorded the PID
without checking it survived. `./server.sh status` still fails separately on `pgrep`, which Git
Bash does not provide. On Windows, run the server directly and check the ports:

```powershell
cd server ; .\venv\Scripts\python.exe compunet_server.py
Get-NetTCPConnection -State Listen -LocalPort 6400,6401,6403,6404
```

## Running the website locally

The website is a separate Flask app with its own virtualenv and its own dependencies
(`flask`, `requests`, `markdown` — it shares nothing with the server's):

```bash
cd website && python3 -m venv venv && venv/bin/pip install -r requirements.txt
./website.sh start       # Linux/macOS — serves on 6464
```

It reaches the server's admin REST API at `COMPUNET_API_URL`, defaulting to
`http://localhost:6403`, so a server on the same machine needs no configuration for the two to
find each other. `website.sh` carries the *same* two Windows faults as `server.sh` — `venv/bin/python3`
and `pgrep` — so on Windows run `.\venv\Scripts\python.exe app.py` directly.

⚠ **The admin API key fails closed, and the symptom is a working-looking site.**
`_api_check_auth` returns false when `COMPUNET_API_KEY` is empty, *before* comparing anything, so
with no key set every website→server call is a 401. Pages render, `/` and `/register` return 200,
and only the operations that matter — registration, the admin panel, password reset — fail. Set
the same key on both sides.

**One `.env`, at the repository root**, is all a checkout needs — the file `.env.example`
describes. `website/config.py` reads it directly; `compunet_server.py` prefers `server/.env` and
falls back to the root file when that does not exist, which is the normal case outside the
container. (In the container they are the same file: both images flatten to `/app`, and
docker-compose mounts the root `.env` to `/app/.env` for each.)

⚠ **On Windows, write that file without a byte-order mark.** `Out-File -Encoding utf8` and
`Set-Content -Encoding utf8` both emit UTF-8 *with* a BOM in Windows PowerShell 5.1. `server.sh`
and `website.sh` `source` the root `.env`, and bash treats the BOM as part of the first line —
`$'\357\273\277#': command not found`. Python tolerates it only by luck, because the first line
is a comment; a BOM in front of a `KEY=value` line corrupts the key name silently. Write it as
UTF-8 without BOM:

```powershell
[System.IO.File]::WriteAllText("$PWD\.env", $text, (New-Object System.Text.UTF8Encoding($false)))
```

Verify the key rather than trusting a page load — unauthenticated is 401, correct key is 200:

```powershell
Invoke-WebRequest "http://127.0.0.1:6403/api/users" -Headers @{Authorization="Bearer $k"}
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

## gh — issues and pull requests

Issues and pull requests are worked through the GitHub CLI rather than the web interface, so it
is a requirement for development even though nothing builds with it.

```bash
gh auth login          # once per machine
gh issue list
gh pr create
```

⚠ **`gh auth` and `git push` are separate credentials.** The remote is SSH
(`git@github.com:tgreaves/compunet-reborn.git`), so authenticating `gh` does not let you push,
and a working push does not mean `gh` is logged in. Each fails on its own: `gh` with *"You are
not logged into any GitHub hosts"*, push with *"Permission denied (publickey)"* — see the
ssh-agent note under [Deploying](#deploying) for the latter.

⚠ **On Windows, install it per-user.** The winget package installs machine-wide by default,
which needs elevation — from a non-interactive shell the UAC prompt cannot be answered and the
install fails with the unhelpful `exit code: 1602` ("You cancelled the installation"). `--scope
user` unpacks the same release archive without elevation:

```powershell
winget install --id GitHub.cli --scope user --accept-source-agreements --accept-package-agreements
```

It puts `gh` on `PATH` for new shells only — an existing shell keeps the old `PATH` and still
reports `gh` as not found.

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
