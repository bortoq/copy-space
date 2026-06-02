#!/bin/sh
# test_rv32m_loader_integrity.sh — verify image integrity pipeline (7.3)
set -eu

BUILDER="scripts/riscv/rv32m_image_builder.py"
TMPDIR="$(mktemp -d tmp/rv32m_integrity.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 7.3 Loader Integrity Checks ==="

# Create a test payload
python3 -c "import sys; sys.stdout.buffer.write(b'\x00'*(4608//8))" > "$TMPDIR/payload.bin"

# Build image with manifest
python3 "$BUILDER" build --payload "$TMPDIR/payload.bin" \
  --output "$TMPDIR/test.rv32m" --entry 0x1000 \
  --manifest "$TMPDIR/manifest.json" 2>/dev/null

echo "--- 7.3.1: manifest generation ---"
[ -f "$TMPDIR/manifest.json" ] || { echo "FAIL: manifest not created"; exit 1; }
python3 -c "import json; m = json.load(open('$TMPDIR/manifest.json')); print('  format:', m['format']); print('  full_sha256:', m['digests']['full_sha256'][:16]+'...')"
echo "OK"

echo "--- 7.3.2: pre-send SHA verification ---"
python3 "$BUILDER" verify-sha "$TMPDIR/test.rv32m" 2>&1 | grep -q "OK" || { echo "FAIL: pre-send verify"; exit 1; }
echo "OK"

echo "--- 7.3.3: readback verification (self-test: copy == original) ---"
cp "$TMPDIR/test.rv32m" "$TMPDIR/readback.rv32m"
python3 "$BUILDER" verify-readback --original "$TMPDIR/test.rv32m" --readback "$TMPDIR/readback.rv32m" 2>&1 | grep -q "OK" || { echo "FAIL: readback verify"; exit 1; }
echo "OK"

echo "--- 7.3.4: readback mismatch detection ---"
# Modify readback to trigger mismatch
cp "$TMPDIR/test.rv32m" "$TMPDIR/tampered.rv32m"
python3 -c "with open('$TMPDIR/tampered.rv32m','r+b') as f: f.seek(52); f.write(b'\x01')"
if python3 "$BUILDER" verify-readback --original "$TMPDIR/test.rv32m" --readback "$TMPDIR/tampered.rv32m" 2>/dev/null; then
  echo "FAIL: tampered readback was accepted"; exit 1
fi
echo "  tampered image correctly rejected"
echo "OK"

echo ""
echo "ALL INTEGRITY CHECKS PASSED"
