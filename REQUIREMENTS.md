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
| Verifying the Amiga reconstruction | **capstone** (Python m68k disassembler) | `python -c "import capstone"` |
| Running the Amiga client | An emulator (**WinUAE**/FS-UAE) and a Kickstart 2.04+ ROM | — |
| Issues and pull requests | **GitHub CLI** (`gh`) | `gh --version` |

Sources: [cc65](https://cc65.github.io/) · [VICE](https://vice-emu.sourceforge.io/) ·
[vbcc](http://sun.hasenbraten.de/vbcc/) · [amitools](https://github.com/cnvogelg/amitools) ·
[capstone](https://www.capstone-engine.org/) · [GitHub CLI](https://cli.github.com/)

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
cd server  && python -m unittest discover -s tests -q
cd website && python -m unittest discover -s tests -q
```

Each uses its own virtualenv — the website's tests import `app.py`, which needs
Flask. Neither suite touches the network: the server's drives in-process objects
against the tracked fixture tree, and the website's exercises only routes that are
refused before their handler runs.

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

⚠ **`users.json.example` does not satisfy the test suite.** `test_api_binding.py` signs in as
`TEST` / `SECRET`, but the example file ships a different password for `TEST`, so a checkout set
up exactly as documented fails one test for a reason that has nothing to do with the code. Set it
before believing a failure:

```bash
python -c "import hashlib,json; p='server/cfg/users.json'; u=json.load(open(p)); u['TEST']['password']=hashlib.sha256(b'SECRET').hexdigest(); json.dump(u,open(p,'w'),indent=2)"
```

⚠ **There is no content until you seed `data/`.** `server/data/` is *mostly* untracked and starts
almost empty; with no `content/root/root.json` the server invents a single empty root and every
directory listing is bare. The tracked `server/data.example/` is the starting tree — a root with
The Jungle, news, a header frame and the F-key shortcuts. Seed it **without clobbering**:

```bash
cp -rn server/data.example/* server/data/
```

⚠ **`-n` is load-bearing.** `server/data/` is not entirely untracked: `content/courier-header.seq`
and `content/root/partyline/join-partyline/partyline.prg` *are* in git, and the latter is the real
2,514-byte Partyline client. `data.example` carries a 975-byte placeholder of the same name, so a
plain `cp -r` silently replaces the working binary with the stub and leaves a modified tracked
file for someone to commit by accident. Check with `git status server/data/` after seeding.

(`data/content.test/` is the *test* fixture and is tracked deliberately; do not run a dev server
against it, because uploads and mail would write into it.)

⚠ **`./server.sh` does not work on Windows.** It selects `venv/bin/python3`, which a Windows venv
does not have (`venv/Scripts/python.exe`), falls back to `python3` — the Store stub above — and
the server dies at once. It now reports that correctly (`Server failed to start`, followed by the
tail of `server/logs/compunet-server.log`, and no PID file); until 1.3.0 it printed
`Server started (PID …)` regardless, because it backgrounded the process and recorded the PID
without checking it survived. `./server.sh status` still fails separately on `pgrep`, which Git
Bash does not provide.

⚠ **Running the server directly does NOT load `.env` — `server.sh` does.** This is the part that
bites, because nothing fails: the server starts perfectly and serves the **wrong content tree**.
`.env` is where `COMPUNET_CONTENT_DIR` usually points at a working copy rather than
`server/data/content`, so a server launched without it silently serves a different (often nearly
empty) set of directories, and you debug missing content that is really just a different tree. It
also drops `COMPUNET_API_KEY`, so the website cannot talk to the server at all. Load `.env`
first — this is what `server.sh` does on Linux, and the Windows equivalent:

```powershell
$p = (Get-Location).Path
Get-Content "$p\.env" | ForEach-Object {
  $line = $_.Trim()
  if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
    $i = $line.IndexOf('='); Set-Item -Path "env:$($line.Substring(0,$i).Trim())" -Value $line.Substring($i+1).Trim()
  }
}
"content: $env:COMPUNET_CONTENT_DIR"      # confirm it is the tree you meant
Set-Location "$p\server"
.\venv\Scripts\python.exe compunet_server.py
```

That runs in the foreground. To run it detached, with the logs `server.sh` would have written:

```powershell
Start-Process -FilePath "$p\server\venv\Scripts\python.exe" -ArgumentList "compunet_server.py" `
  -RedirectStandardOutput "$p\server\logs\stdout.log" `
  -RedirectStandardError  "$p\server\logs\stderr.log" -WindowStyle Hidden
```

⚠ **Startup output goes to stderr, not stdout** — `stdout.log` stays empty and `stderr.log` holds
the `Compunet server vX.Y.Z ready` banner and the four `... on port` lines. Read the wrong one and
a healthy server looks like it produced nothing. Check it started, then stop it:

```powershell
foreach ($port in 6400,6401,6403,6404) { "$port : $(Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet)" }
Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
  Where-Object { $_.CommandLine -match 'compunet_server' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
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

`npm run typecheck` in `client/web` runs `tsc --noEmit`. **Worth running — `npm run build` does
not typecheck.** esbuild strips types without checking them, so a type error bundles perfectly
happily and only shows up at runtime.

⚠ **On Windows, install Node per-user** and note it does not land on `PATH` for an existing
shell — the same trap as `gh` above:

```powershell
winget install --id OpenJS.NodeJS.LTS --scope user --accept-source-agreements --accept-package-agreements
```

It unpacks to `%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_…\node-v<ver>-win-x64`.
Prepend that to `PATH` for the current session rather than reinstalling when `node` is "not
found".

⚠ **Always `dist:win`, never `pack:win`** ([CLAUDE.md](CLAUDE.md), Client Rules). `pack:win`
writes only `dist/win-unpacked/` and leaves the installer and portable exe at the previous build
— the two artefacts a tester actually picks up.

⚠ **electron-builder vs. Windows symlinks — turn ON Developer Mode.** Its `winCodeSign`
package contains macOS symlinks Windows will not create without privilege, and the extraction
fails hard:

```
ERROR: Cannot create symbolic link : A required privilege is not held by the client.
       ...\winCodeSign\<id>\darwin\10.12\lib\libcrypto.dylib
  • Above command failed, retrying 3 more times
```

**Settings → System → For developers → Developer Mode.** That permits unprivileged symlink
creation and the build then runs start to finish. An elevated shell works too. Nothing else is
needed — signing itself is skipped (`no signing info identified`), so this is purely about
unpacking a tool we do not use.

⚠ **The pre-extract workaround previously recorded here does NOT work on current
electron-builder** and cost an hour before that was clear. It said to unpack the cache to
`winCodeSign-<ver>` with `-xr!darwin`. This version extracts to a **random numeric id per
download** — eight such directories accumulated from failed attempts, each a different number —
so there is no name to pre-populate. Every one of them contained a perfectly good `windows-10`
directory: only the `darwin` symlinks fail, and electron-builder treats that as fatal anyway.

After enabling Developer Mode, clear the debris so the next run starts clean:

```powershell
Remove-Item "$env:LOCALAPPDATA\electron-builder\Cache\winCodeSign\*" -Recurse -Force
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

⚠ **On Windows, `VBCC` must be a Windows-style path with no spaces**, even when building from
Git Bash. The config expands `%VBCC%` inside `vc.exe`, which cannot read a POSIX path like
`/c/Users/You/vbcc` and does not fail when it cannot — it passes the include flag through
**unexpanded**, and the compiler reports:

```
error 1: only one input file allowed
… -I%VBCC%/targets/m68k-amigaos/include failed
```

which names neither the variable nor the path. A space in the home directory breaks it the same
way. Use the 8.3 short name, which points at the same directory:

```bash
export VBCC="C:/Users/TRISTA~1/vbcc"        # not /c/Users/Tristan Greaves/vbcc
export PATH="/c/Users/TRISTA~1/vbcc/bin:$PATH"
cd client/amiga/src && sh build.sh
```

`vc -v` on its own reports **"No config file!"** and is not a usable check — `build.sh` selects
the config with `+kick13`. A successful build ends with `Built compunet-client (<n> bytes)`.

Building the toolchain from scratch — components, versions, download URLs, directory layout —
is documented in
**[client/amiga/vintage/tools/re/toolchain.md](client/amiga/vintage/tools/re/toolchain.md)**,
which is the authority for it.

## capstone — verifying the Amiga reconstruction

[CLAUDE.md](CLAUDE.md) requires every claim about the original client to be checked against a
**relocated** disassembly rather than the Ghidra decompile. `disasm_fn.py` is the tool that
produces one, and it needs `capstone` — which is not a dependency of anything else in the
repository, so a fresh checkout cannot run the one workflow the project rules mandate:

```bash
pip install capstone
```

Without it the tool dies on import with `ModuleNotFoundError: No module named 'capstone'`,
which reads like a broken tool rather than a missing package.

⚠ **Run `flatten.py` first, and give it both arguments.** `compunet_flat.bin` is generated, not
committed, and `disasm_fn.py` resolves every address through it. `flatten.py` takes no defaults:

```bash
cd client/amiga/vintage/tools/re
python flatten.py ../../decrunched/Compunet compunet_flat    # -> compunet_flat.bin + .map
python disasm_fn.py 0x10b174                                 # or a name from symbols.json
python disasm_fn.py --our account                            # original beside our vc -S
```

Run bare, `flatten.py` fails with `IndexError: list index out of range` from `sys.argv[1]` —
easily misread as a corrupt binary. Disassembling the un-relocated hunk bytes instead decodes
garbage, which is the failure the whole tool exists to prevent.

## Running the Amiga client in an emulator

Needed to test client behaviour end to end; not needed to build anything.

- **Kickstart 2.04 or later.** The client itself is built against the 1.3 NDK, but every Amiga
  TCP/IP stack requires 2.04. Note there was never a *Kickstart* 2.1 — AmigaOS 2.1 was a
  software-only release — so a "2.1 or higher" requirement is wrong wherever it appears.
- **WinUAE has `bsdsocket.library` emulation built in** (Host tab), which removes the need to
  install Roadshow, AmiTCP or Miami inside the emulated Amiga. Socket calls are proxied through
  the host, so a server on the same machine is reachable at `127.0.0.1`.
- **The server address comes from a `TCPHOST` file**, not from the client's configuration
  screen — the phone-number field is far too small for a hostname. One line, `host` or
  `host:port`; looked up in the current directory, then `ENV:`, then `S:`. The shipped archive
  presets it to `vme.compunet.live:6400`, so point it at `127.0.0.1:6400` to test locally.

⚠ **The Amiga client is exempt from the client-version hash gate**, unlike the C64 client. The
server identifies it during handshake and logs *"Amiga client detected — skipping hash check +
LINKING"*. So a shipped `dist/*.lha` talks to a development server as-is: no rebuild, and no
`make HASH=…` override of the kind the C64 client needs.

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

⚠ **A user-scope install may never reach `PATH` in a tool-driven shell at all.** Neither Git
Bash nor `Get-Command gh` in PowerShell resolved it here long after installation, so `gh` looks
uninstalled when it is present and working. Find it rather than reinstalling:

```powershell
Get-ChildItem "$env:LOCALAPPDATA" -Filter gh.exe -Recurse -ErrorAction SilentlyContinue |
  Select-Object -First 1 -ExpandProperty FullName
```

It lands under `%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_…\bin\gh.exe`. Invoke it by
full path with PowerShell's call operator — `& $gh issue view 122` — and note that `--jq`
expressions get word-split by PowerShell, so prefer `--json` and pipe through `ConvertFrom-Json`.

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
