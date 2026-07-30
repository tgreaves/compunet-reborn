#!/bin/sh
# package.sh — build the reconstructed Amiga Compunet client and package it for
# emulation two ways:
#   1. a host-directory hard-drive layout  (emulation/hdd/)  — mount as DH0: in FS-UAE
#   2. a bootable ADF disk image           (emulation/CompunetReborn.adf) — DF0:/DF1:
#
# Stage 1 goal: get the client to boot and show its UI (screen, window, PETSCII
# rendering) in the emulator. Connecting to a Reborn server (Stage 2) additionally
# needs a serial->TCP bridge — see RUNNING.md.
#
# Requires: the vbcc KS1.3 toolchain (VBCC, see ../vintage/tools/re/toolchain.md) and
# amitools' xdftool (pip install amitools). Run from client/amiga/emulation/.
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/../src"
VINTAGE="$HERE/../vintage"
HDD="$HERE/hdd"
ADF="$HERE/CompunetReborn.adf"
XDFTOOL="${XDFTOOL:-$VINTAGE/tools/re/.venv/bin/xdftool}"

# 1. Build the client -------------------------------------------------------
echo "== building client =="
( cd "$SRC" && VBCC="${VBCC:-/tmp/vbcc}" ./build.sh )
BIN="$SRC/compunet-client"
[ -f "$BIN" ] || { echo "build produced no compunet-client"; exit 1; }

# 2. Assemble the host-directory HD layout ---------------------------------
echo "== assembling hdd/ layout =="
rm -rf "$HDD"
mkdir -p "$HDD/devs/cnet_modems" "$HDD/s" "$HDD/l" "$HDD/libs"

cp "$BIN"                       "$HDD/Compunet"
cp "$VINTAGE/devs/cnet.device"  "$HDD/devs/cnet.device"
cp "$VINTAGE/cnet-configuration" "$HDD/cnet-configuration"
# ⚠ DECRUNCHED, not the crunched originals in $VINTAGE — matching make_hdd.sh, which has
# always done this and documents why: the crunched PowerPacker stub for CnetEditor gurus at
# CreateProc time, and the decrunched CnetTty avoids running a self-decruncher at LoadSeg.
# This script used to copy the crunched pair, which mattered more than it looked: make_lha.py
# packages whatever is in hdd/, so running package.sh then make_lha.py shipped a CnetEditor
# that gurus (14,476 bytes) in place of the working one every release has carried (33,124) —
# same filename, no error. Fall back to crunched only if a decrunched copy is missing.
if [ -f "$VINTAGE/decrunched/CnetEditor" ]; then
    cp "$VINTAGE/decrunched/CnetEditor" "$HDD/CnetEditor"
else
    cp "$VINTAGE/CnetEditor"            "$HDD/CnetEditor" 2>/dev/null || true
fi
if [ -f "$VINTAGE/decrunched/CnetTty" ]; then
    cp "$VINTAGE/decrunched/CnetTty"    "$HDD/CnetTty"
else
    cp "$VINTAGE/CNETTTY"               "$HDD/CnetTty"    2>/dev/null || true
fi
cp "$VINTAGE"/devs/cnet_modems/* "$HDD/devs/cnet_modems/" 2>/dev/null || true

# Minimal startup-sequence: assign DEVS: locally then run the client.
cat > "$HDD/s/startup-sequence" <<'SEQ'
; Compunet Reborn (Amiga) — Stage 1 launch
Assign DEVS: SYS:devs
echo "Starting Compunet..."
Compunet
SEQ

echo "   hdd/ ready ($(find "$HDD" -type f | wc -l | tr -d ' ') files)"

# 3. Build the ADF ----------------------------------------------------------
echo "== building ADF =="
"$XDFTOOL" "$ADF" format "CompunetReborn" + \
    makedir devs + \
    makedir devs/cnet_modems + \
    makedir s + \
    write "$BIN" Compunet + \
    write "$VINTAGE/devs/cnet.device" devs/cnet.device + \
    write "$VINTAGE/cnet-configuration" cnet-configuration + \
    write "$HDD/s/startup-sequence" s/startup-sequence
# add modem scripts individually (xdftool has no glob)
for m in "$VINTAGE"/devs/cnet_modems/*; do
    "$XDFTOOL" "$ADF" write "$m" "devs/cnet_modems/$(basename "$m")"
done
echo "   $ADF ($(wc -c < "$ADF") bytes)"

echo
echo "Done."
echo "  FS-UAE : mount emulation/hdd as a directory hard drive (DH0:)"
echo "  vAmiga : insert emulation/CompunetReborn.adf in DF0: (needs a 1.3 Workbench to boot from, or set as non-boot data disk)"
echo "  See emulation/RUNNING.md."
