#!/bin/sh
# test_rv32m_loader_rollback.sh — verify loader rejects invalid images (7.2)
set -eu

BUILDER="scripts/riscv/rv32m_image_builder.py"
LOADER_TOOL="build/bin/rv32m_loader_tool"
TMPDIR="$(mktemp -d tmp/rv32m_loader_rollback.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 7.2 Loader Rollback (negative tests) ==="

# Build a base space image
build/bin/mkimage_std7_fixed --out "$TMPDIR/base.bin" 2>/dev/null

echo "--- Test 1: bad magic ---"
python3 "$BUILDER" negative --variant bad_magic --output "$TMPDIR/bad_magic.rv32m"
if "$LOADER_TOOL" --rv32m "$TMPDIR/bad_magic.rv32m" --space "$TMPDIR/base.bin" --output "$TMPDIR/out.bin" 2>&1; then
  echo "FAIL: bad magic was accepted"; exit 1
fi
echo "OK: rejected"

echo "--- Test 2: bad version ---"
python3 "$BUILDER" negative --variant bad_version --output "$TMPDIR/bad_ver.rv32m"
if "$LOADER_TOOL" --rv32m "$TMPDIR/bad_ver.rv32m" --space "$TMPDIR/base.bin" --output "$TMPDIR/out.bin" 2>&1; then
  echo "FAIL: bad version was accepted"; exit 1
fi
echo "OK: rejected"

echo "--- Test 3: missing file ---"
if "$LOADER_TOOL" --rv32m "/tmp/nonexistent.rv32m" --space "$TMPDIR/base.bin" --output "$TMPDIR/out.bin" 2>&1; then
  echo "FAIL: missing file was accepted"; exit 1
fi
echo "OK: rejected"

echo "ALL rollback checks passed"
