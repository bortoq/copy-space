#!/bin/sh
set -eu

OUT_DIR="out"
TMP_DIR="tmp"

IMG="$OUT_DIR/img_fixed_pool_big.bin"
META="$TMP_DIR/mkimage_big.meta"

mkdir -p "$OUT_DIR" "$TMP_DIR"

# генерим image + meta
scripts/mkimage_meta.sh --out "$IMG" --pool-cells 32768 --meta "$META" >/dev/null 2>&1

# shellcheck disable=SC1090
. "$META"

# проверки, что ключи есть и числа ненулевые/корректные
test -n "${TESTSCR_BASE_BYTE:-}"
test -n "${TESTSCR_SIZE_BYTE:-}"
test -n "${TESTSCR_END_BYTE:-}"

# простые sanity checks
test "$TESTSCR_SIZE_BYTE" -gt 0
test "$TESTSCR_END_BYTE" -gt "$TESTSCR_BASE_BYTE"
