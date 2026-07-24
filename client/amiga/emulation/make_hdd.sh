#!/bin/sh
# make_hdd.sh — build a host-directory hard-drive layout for the reconstructed Amiga
# Compunet client, ready to mount as a Directory HD (DHx:) in Amiga Forever / FS-UAE /
# WinUAE for FAST iteration testing (no ADF rebuild, no Workbench disk needed).
#
#   cd client/amiga/emulation
#   VBCC=/path/to/vbcc ./make_hdd.sh
#
# Then in the emulator add a Directory hard drive pointing at:
#   client/amiga/emulation/hdd        device e.g. DH0:
# Boot a Workbench (KS1.3 or 2.04) and run:  DH0:  then  Compunet
# (Or make DH0: bootable in the emulator's HD settings — the startup-sequence runs it.)
#
# Contains ONLY our reconstructed client + the vintage device/editor/modem files that
# shipped on the original disk — no Cloanto Workbench content, so it is safe to keep in
# the working tree. Rebuilds the client first so the layout is always current.
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/../src"
VINTAGE="$HERE/../vintage"
HDD="$HERE/hdd"

echo "== building client =="
( cd "$SRC" && VBCC="${VBCC:-/tmp/vbcc}" ./build.sh >/dev/null )
[ -f "$SRC/compunet-client" ] || { echo "build produced no compunet-client"; exit 1; }

echo "== building nettest (TCP/IP connectivity smoke test) =="
( cd "$SRC" && VB="${VBCC:-/tmp/vbcc}" && export VBCC="$VB" && PATH="$VB/bin:$PATH" \
  && vc +kick13 -c -I. net.c     -o net.o     >/dev/null 2>&1 \
  && vc +kick13 -c -I. nettest.c -o nettest.o >/dev/null 2>&1 \
  && vc +kick13 -o nettest net.o nettest.o -lamiga >/dev/null 2>&1 \
  && rm -f net.o nettest.o )
[ -f "$SRC/nettest" ] || { echo "build produced no nettest"; exit 1; }

echo "== assembling $HDD =="
# Preserve a TCPHOST address across the wipe (rm -rf below would otherwise delete it,
# defeating the "keep existing" seed check).
SAVED_TCPHOST=""
[ -f "$HDD/TCPHOST" ] && SAVED_TCPHOST=$(cat "$HDD/TCPHOST")
rm -rf "$HDD"
mkdir -p "$HDD/devs/cnet_modems" "$HDD/s"

cp "$SRC/compunet-client"          "$HDD/Compunet"
cp "$SRC/nettest"                  "$HDD/nettest"
cp "$VINTAGE/devs/cnet.device"     "$HDD/devs/cnet.device"
cp "$VINTAGE/cnet-configuration"   "$HDD/cnet-configuration"

# TCPHOST address for nettest and the client. Restore a preserved one, else seed a
# placeholder. (nettest and Compunet both read this file for the server address.)
if [ -n "$SAVED_TCPHOST" ]; then
    printf '%s\n' "$SAVED_TCPHOST" > "$HDD/TCPHOST"
elif [ ! -f "$HDD/TCPHOST" ]; then
    printf 'CHANGE-ME:6400\n' > "$HDD/TCPHOST"
fi

# CnetEditor: use the DECRUNCHED copy (the crunched PowerPacker stub gurus at CreateProc
# time; the boot disk uses the decrunched form too). Fall back to crunched only if absent.
if [ -f "$VINTAGE/decrunched/CnetEditor" ]; then
    cp "$VINTAGE/decrunched/CnetEditor" "$HDD/CnetEditor"
else
    cp "$VINTAGE/CnetEditor"            "$HDD/CnetEditor"
fi
# CnetTty ("Scrollback v1.0"): prefer the DECRUNCHED copy (vintage/decrunched/CnetTty,
# produced by tools/ttydecrunch.py) so no self-decruncher runs at LoadSeg. Fall back to the
# crunched CNETTTY wrapper if the decrunched copy is absent.
if [ -f "$VINTAGE/decrunched/CnetTty" ]; then
    cp "$VINTAGE/decrunched/CnetTty" "$HDD/CnetTty"
elif [ -f "$VINTAGE/CNETTTY" ]; then
    cp "$VINTAGE/CNETTTY"            "$HDD/CnetTty"
fi
cp "$VINTAGE"/devs/cnet_modems/* "$HDD/devs/cnet_modems/" 2>/dev/null || true

# startup-sequence: Kickstart auto-assigns DEVS:/L:/LIBS: to the boot volume, but a mounted
# Directory HD is NOT the boot volume, so cnet.device won't be found via DEVS: unless we
# assign it. Assign DEVS: to this drive's devs/ then run the client.
cat > "$HDD/s/startup-sequence" <<'SEQ'
Assign DEVS: SYS:devs
Compunet
SEQ

echo "== hdd/ ready =="
echo "  client: $(wc -c < "$SRC/compunet-client" | tr -d ' ') bytes"

# Distribution LHA: build the "Compunet" drawer + icons from the freshly-staged files
# (see make_lha.py — produces a public build for the live server and a -dev build for the
# local server). Both archives are dropped into hdd/ so either can be mounted and
# test-extracted on the Amiga. Regenerated on every HDD build. Needs python.
# Pick a working python: verify it actually runs (skips the Windows Store alias stub, which
# is on PATH as python3 but only prints an install message).
PY=""
for _cand in python3 python; do
    if command -v "$_cand" >/dev/null 2>&1 && "$_cand" -c "import sys" >/dev/null 2>&1; then
        PY="$_cand"; break
    fi
done
if [ -n "$PY" ]; then
    echo "== building distribution LHA =="
    ( cd "$HERE" && "$PY" make_lha.py )
    rm -f "$HDD"/CompunetReborn-Amiga-*.lha
    cp "$HERE"/../dist/CompunetReborn-Amiga-*.lha "$HDD/" 2>/dev/null || true
else
    echo "(python not found — skipping distribution LHA)"
fi

echo "  files:"
( cd "$HDD" && find . -type f | sort | sed 's/^/    /' )

# Optional: sync to Google Drive so the Windows PC running WinUAE picks it up (both
# machines run Google Drive; this corp Mac can only push outbound, so cloud is the relay).
# This is SPECIFIC TO tristan's dev Mac and is a silent no-op anywhere else: it fires only
# when that exact Google Drive account folder exists. Override with GDRIVE_HDD=/path.
GDRIVE_HDD="${GDRIVE_HDD:-$HOME/Library/CloudStorage/GoogleDrive-tristan@extricate.org/My Drive/Coding/CompunetHDD}"
GDRIVE_ACCOUNT_ROOT="$HOME/Library/CloudStorage/GoogleDrive-tristan@extricate.org"
if [ -n "${GDRIVE_HDD_OVERRIDE:-}" ] || [ -d "$GDRIVE_ACCOUNT_ROOT" ]; then
    mkdir -p "$GDRIVE_HDD"
    rsync -a --delete "$HDD/" "$GDRIVE_HDD/"
    echo
    echo "Synced to Google Drive: $GDRIVE_HDD"
    echo "  -> on the Windows PC, point WinUAE's directory-HD at the same CompunetHDD folder."
else
    echo
    echo "Mount $HDD as a Directory HD in the emulator, then run: Compunet"
fi
