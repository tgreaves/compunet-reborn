#!/bin/sh
# make_boot_adf.sh — build a SELF-BOOTING Compunet floppy (CompunetReborn-boot.adf).
#
# A fresh 880K DOS disk with a 1.3 bootblock, the minimal AmigaDOS boot pieces pulled
# from a user-provided Workbench 1.3 ADF, and our reconstructed client set up to launch
# on boot. Kickstart 1.3 supplies dos/exec/intuition/graphics from ROM, so only the
# shell/boot machinery + serial.device come from Workbench — the disk stays small.
#
# Usage:
#   WB=/path/to/Workbench1.3.adf ./make_boot_adf.sh
# (defaults to the Amiga Forever WB 1.3.3 image under ~/Documents/FS-UAE/Floppies)
#
# Requires: the built client (../src/compunet-client) and amitools xdftool.
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/../src"
VINTAGE="$HERE/../vintage"
XDFTOOL="${XDFTOOL:-$VINTAGE/tools/re/.venv/bin/xdftool}"
OUT="$HERE/CompunetReborn-boot.adf"
WB="${WB:-/Users/greavet/Documents/FS-UAE/Floppies/Workbench v1.3.3 rev 34.34 (1990)(Commodore)(Disk 1 of 2)(Workbench)[Cloanto Amiga Forever Edition].adf}"

[ -f "$WB" ] || { echo "Workbench ADF not found: $WB (set WB=...)"; exit 1; }
[ -f "$SRC/compunet-client" ] || { echo "client not built — run ../src/build.sh first"; exit 1; }

# 1. Extract the minimal boot set from the user's Workbench disk -------------
# Only what a CLI boot + our client's LoadSeg/serial path needs. Everything else
# (dos/exec/intuition/graphics) is in Kickstart 1.3 ROM.
WBX="$HERE/.wbextract"
rm -rf "$WBX"; mkdir -p "$WBX/c" "$WBX/l" "$WBX/devs" "$WBX/s"
echo "== extracting boot pieces from Workbench =="
for f in c/SetPatch c/Resident c/Assign c/Echo c/Wait c/Run c/Execute c/MakeDir c/Mount; do
    "$XDFTOOL" "$WB" read "$f" "$WBX/$f" 2>/dev/null || echo "   (skip $f)"
done
"$XDFTOOL" "$WB" read l/Shell-Seg        "$WBX/l/Shell-Seg"        2>/dev/null || true
"$XDFTOOL" "$WB" read l/Newcon-Handler   "$WBX/l/Newcon-Handler"   2>/dev/null || true
"$XDFTOOL" "$WB" read l/Disk-Validator   "$WBX/l/Disk-Validator"   2>/dev/null || true
"$XDFTOOL" "$WB" read devs/serial.device "$WBX/devs/serial.device" 2>/dev/null || true

# 2. Build the client -------------------------------------------------------
echo "== building client =="
( cd "$SRC" && VBCC="${VBCC:-/tmp/vbcc}" ./build.sh >/dev/null )

# 3. startup-sequence: minimal boot -> map DEVS: -> run Compunet -------------
# Minimal boot: Kickstart 1.3 auto-assigns C:/S:/L:/DEVS:/LIBS: to the boot disk's
# dirs, so cnet.device (in devs/) is found without an explicit Assign, and we need
# neither a resident shell nor `mount newcon:` (which aborted the script when its
# MountList was absent — returncode 10 >= default failat). Just patch ROM and run.
cat > "$WBX/s/startup-sequence" <<'SEQ'
c:SetPatch >NIL:
echo "Compunet Reborn - starting..."
Compunet
SEQ

# 4. Assemble the bootable ADF ---------------------------------------------
echo "== building $OUT =="
rm -f "$OUT"
"$XDFTOOL" "$OUT" format "CompunetReborn" + \
    makedir c + makedir l + makedir s + makedir devs + makedir devs/cnet_modems

# Workbench boot pieces
for f in "$WBX"/c/*;    do "$XDFTOOL" "$OUT" write "$f" "c/$(basename "$f")";    done
for f in "$WBX"/l/*;    do "$XDFTOOL" "$OUT" write "$f" "l/$(basename "$f")";    done
"$XDFTOOL" "$OUT" write "$WBX/devs/serial.device" devs/serial.device
"$XDFTOOL" "$OUT" write "$WBX/s/startup-sequence" s/startup-sequence

# Our client + its runtime files
"$XDFTOOL" "$OUT" write "$SRC/compunet-client"          Compunet
"$XDFTOOL" "$OUT" write "$VINTAGE/devs/cnet.device"     devs/cnet.device
"$XDFTOOL" "$OUT" write "$VINTAGE/cnet-configuration"   cnet-configuration
# CnetEditor: prefer the DECRUNCHED copy (vintage/decrunched/) so no PowerPacker
# self-decruncher runs at CreateProc time. The crunched vintage/CnetEditor is a
# 2-hunk self-decrunching wrapper (524B stub + 33636B compressed payload); the
# decrunched form is the real 24-hunk program. Fall back to the crunched one only
# if the decrunched copy is missing.
if [ -f "$VINTAGE/decrunched/CnetEditor" ]; then
    "$XDFTOOL" "$OUT" write "$VINTAGE/decrunched/CnetEditor" CnetEditor
elif [ -f "$VINTAGE/CnetEditor" ]; then
    "$XDFTOOL" "$OUT" write "$VINTAGE/CnetEditor" CnetEditor
fi
# CnetTty ("Scrollback v1.0"): prefer the DECRUNCHED copy. The crunched vintage/CNETTTY is
# a 3-hunk self-decrunching wrapper (620B stub + 3904B compressed payload, a non-PowerPacker
# marker-bit LZ); the decrunched form is the real 8-hunk program (tools/ttydecrunch.py).
if [ -f "$VINTAGE/decrunched/CnetTty" ]; then
    "$XDFTOOL" "$OUT" write "$VINTAGE/decrunched/CnetTty" CnetTty
elif [ -f "$VINTAGE/CNETTTY" ]; then
    "$XDFTOOL" "$OUT" write "$VINTAGE/CNETTTY"            CnetTty
fi
for m in "$VINTAGE"/devs/cnet_modems/*; do
    "$XDFTOOL" "$OUT" write "$m" "devs/cnet_modems/$(basename "$m")"
done

# Install the 1.3 DOS bootblock so it self-boots
"$XDFTOOL" "$OUT" boot install

rm -rf "$WBX"

echo
echo "Built $OUT"
"$XDFTOOL" "$OUT" info 2>/dev/null | grep -E "free|used" || true
echo "Boot it in FS-UAE/vAmiga (A500, Kickstart 1.3) in DF0: — it launches Compunet."
