#!/bin/sh
set -eu

TMP_IMAGE="build/std7_c3_addi_proof.bin"
build/bin/mkimage_std7_fixed --out "$TMP_IMAGE" >/dev/null
build/bin/c3_addi_proof --image "$TMP_IMAGE" --case sw >/dev/null
build/bin/c3_addi_proof --image "$TMP_IMAGE" --case lw >/dev/null

echo "OK c3 real mem"
