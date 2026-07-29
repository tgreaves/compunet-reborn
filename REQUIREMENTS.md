# Requirements — what each part of this repository needs to build

One page, so you do not have to reconstruct this from four README sections and a build failure.

**Read the "Status on this machine" column first.** Not every toolchain is installed here, and a
missing one is not a bug to debug — it is a component you cannot build until you install it.

| You want to build | You need | Status on this machine |
|---|---|---|
| Server, website, tools | Python 3 | ✅ **3.12.5**, on `PATH` |
| Web client, Electron app | Node.js + npm | ✅ **node 24.18.0 / npm 11.16.0**, on `PATH` |
| Amiga client | vbcc (m68k) + vasm | ⚠️ installed at `C:\Users\trist\vbcc`, **not on `PATH`** — see below |
| C64 client (`.prg`) | cc65 (`ca65`, `ld65`) + `make` | ❌ **not installed** |
| C64 disk image (`.d64`) | `c1541` from VICE | ❌ **not installed** |
| Amiga disk/icon steps | `xdftool` from amitools | ❌ not installed |

---

## Python — server, website, tooling

Already present and on `PATH`. Both the server and the website use their own virtualenvs:

```bash
cd server  && python3 -m venv venv && venv/Scripts/pip install -r requirements.txt
cd website && python3 -m venv venv && venv/Scripts/pip install -r requirements.txt
```

Run the tests with the interpreter directly — there is no pytest in this tree:

```bash
cd server && python -m unittest discover -s tests -q
```

## Node.js — web client and Electron

Already present and on `PATH`; `npm` needs no path prefix.

```bash
cd client/web      && npm install && npm run build     # bundle only
cd client/electron && npm install && npm run dist:win  # the desktop app
```

⚠ **Always `dist:win`, never `pack:win`** — see [CLAUDE.md](CLAUDE.md), Client Rules. `pack:win`
leaves the installer and portable exe at the previous build.

⚠ **`winCodeSign` and symlinks.** electron-builder downloads a `winCodeSign` package containing
macOS symlinks that Windows cannot create, and the download then fails. If you hit it, pre-extract
the cache excluding the darwin directory:

```
7z x winCodeSign-<ver>.7z -o"%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\winCodeSign-<ver>" -xr!darwin
```

⚠ **Close the app before packaging.** A running `Compunet Reborn.exe` (especially the portable
build, launched from `dist/`) holds a file lock, and the portable target hangs indefinitely
without saying why. Check first:

```powershell
Get-Process | Where-Object { $_.ProcessName -like '*Compunet*' }
```

## vbcc — Amiga client

Installed at `C:\Users\trist\vbcc` (contains `bin/vc.exe`, `vasmm68k_mot.exe`, `vlink.exe`) but
**not on `PATH`**. `client/amiga/src/build.sh` defaults `VBCC` to `/tmp/vbcc`, so it must be told
where the toolchain is — it prepends `$VBCC/bin` to `PATH` itself:

```bash
cd client/amiga/src && VBCC=/c/Users/trist/vbcc sh build.sh     # -> compunet-client
```

Setting it up from scratch — components, versions, download URLs and the directory layout — is
documented in **[client/amiga/vintage/tools/re/toolchain.md](client/amiga/vintage/tools/re/toolchain.md)**.
That file is the authority; this page only records where it ended up here.

## cc65 and VICE — C64 client

**Neither is installed on this machine**, so `client/c64/` cannot currently be built or packaged
here. `make` is absent too, and `client/c64/src/Makefile` needs it.

- **cc65** — <https://cc65.github.io/> — provides `ca65` (assembler) and `ld65` (linker)
- **VICE** — <https://vice-emu.sourceforge.io/> — provides `c1541` for the `.d64`, and `x64sc`
  for testing

Once installed and on `PATH`:

```bash
cd client/c64/src && make          # -> ../compunet-reborn.prg
```

⚠ **Rebuilding the C64 client changes a hash the server checks.** The build embeds a hash of
`compunet.s` and the server verifies it against `server/cfg/client_version.txt`; source, binaries
and that file must be committed together. See [CLAUDE.md](CLAUDE.md), Client Rules 1–3.

⚠ **On Windows, the hash is computed over CRLF line endings.** `gen_version.py` hashes the
working-tree bytes, so a build here yields a *different* hash from the committed one — the tree's
`compunet.s` is CRLF (`0053DF`) while the committed blob is LF (`800CAD`, which is what the
shipped `.prg` and the server both expect). **Do not rebuild the C64 client on Windows without
resolving this**, or you will lock out every existing client. Nothing is wrong today: the shipped
binary and `client_version.txt` agree.

## Toolchains not needed for day-to-day work

`xdftool` (from [amitools](https://github.com/cnvogelg/amitools)) is only required for the Amiga
ADF and icon steps, not for compiling the client.

---

## Deployment hosts

Neither host needs a toolchain — both build inside Docker:

```bash
ssh -A tmg@<host>
cd ~/src/compunet-reborn && git fetch origin && git reset --hard origin/<branch>
cd ~/docker && docker compose up -d --build compunet-server compunet-web
```

`docker.lan` is the dev host; production is `nexus.extricate.org`. `git push` and the `ssh -A`
hops both need an SSH agent:

```bash
eval $(ssh-agent -a ~/.ssh/agent.sock) && ssh-add ~/.ssh/id_ed25519
export SSH_AUTH_SOCK=~/.ssh/agent.sock
```

The agent does not survive a reboot — if `git push` reports *"Permission denied (publickey)"*,
that is the first thing to check.
