#!/bin/sh
# build.sh — compile + link the reconstructed Amiga Compunet client with vbcc.
#
# Requires the vbcc KS1.3 toolchain (see ../vintage/tools/re/toolchain.md). Set
# VBCC to its root (default /tmp/vbcc). Produces ./compunet-client, an Amiga HUNK
# executable (magic 0x000003f3).
#
# This proves the whole reconstruction links into one program. The UI/DOS/modem
# glue below the application layer is currently linkable stubs (stubs.c) pending
# reconstruction; the 53 census application functions are real (see
# ../vintage/tools/re/coverage-census.md).
#
# SAS/C note: the sources target standard Amiga includes, so an SMakefile for real
# SAS/C is a drop-in; vbcc is the modern-host proxy for the compile/verify loop.
set -e

VBCC="${VBCC:-/tmp/vbcc}"
export VBCC
PATH="$VBCC/bin:$PATH"
export PATH

MODS="startup globals transport connect login frame frame_control frame_gfx navigate directory transfer mail resources config launch modem dosio stubs"

OBJS=""
for f in $MODS; do
    echo "  CC   $f.c"
    vc +kick13 -c -I. "$f.c" -o "$f.o"
    OBJS="$OBJS $f.o"
done

echo "  LINK compunet-client"
vc +kick13 -o compunet-client $OBJS -lamiga

echo "Built compunet-client ($(wc -c < compunet-client) bytes)"
