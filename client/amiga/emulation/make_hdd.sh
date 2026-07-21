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
rm -rf "$HDD"
mkdir -p "$HDD/devs/cnet_modems" "$HDD/s"

cp "$SRC/compunet-client"          "$HDD/Compunet"
cp "$SRC/nettest"                  "$HDD/nettest"
cp "$VINTAGE/devs/cnet.device"     "$HDD/devs/cnet.device"
cp "$VINTAGE/cnet-configuration"   "$HDD/cnet-configuration"

# Seed a TCPHOST placeholder for the connectivity test (nettest reads it). Preserve
# an existing one so a real address you set isn't clobbered on rebuild.
if [ ! -f "$HDD/TCPHOST" ]; then
    printf 'CHANGE-ME:6400\n' > "$HDD/TCPHOST"
fi

# CnetEditor: use the DECRUNCHED copy (the crunched PowerPacker stub gurus at CreateProc
# time; the boot disk uses the decrunched form too). Fall back to crunched only if absent.
if [ -f "$VINTAGE/decrunched/CnetEditor" ]; then
    cp "$VINTAGE/decrunched/CnetEditor" "$HDD/CnetEditor"
else
    cp "$VINTAGE/CnetEditor"            "$HDD/CnetEditor"
fi
[ -f "$VINTAGE/CNETTTY" ] && cp "$VINTAGE/CNETTTY" "$HDD/CnetTty"
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
echo "  files:"
( cd "$HDD" && find . -type f | sort | sed 's/^/    /' )
echo
echo "Mount $HDD as a Directory HD in the emulator, then run: Compunet"
