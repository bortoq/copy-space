#!/bin/sh
set -eu

mkdir -p tmp

build/bin/vmrun --help 2>&1 | rg -n -- "--image|--life|--dump" >/dev/null

TMPDIR="$(mktemp -d tmp/space_host_contract.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

IMG="$TMPDIR/image.bin"
DUMP="$TMPDIR/dump.bin"
build/bin/mkimage_std7_fixed --out "$IMG" >/dev/null
build/bin/vmrun --image "$IMG" --life 1 --dump "$DUMP" >/dev/null

[ -s "$DUMP" ]

echo "OK space minimal host contract"
