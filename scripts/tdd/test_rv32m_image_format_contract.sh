#!/bin/sh
# test_rv32m_image_format_contract.sh — validate image format contract (7.1)
set -eu

BUILDER="scripts/riscv/rv32m_image_builder.py"
TMPDIR="$(mktemp -d tmp/rv32m_format_test.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 7.1 Image Format Contract ==="

# Build a valid image
PAYLOAD="$TMPDIR/payload.bin"
python3 -c "
import sys
# 4608 bits = 576 bytes (64 slots × 72 bits per instruction)
payload = b'\x00' * (4608 // 8)
sys.stdout.buffer.write(payload)
" > "$PAYLOAD"

VALID="$TMPDIR/valid.rv32m"
python3 "$BUILDER" build --payload "$PAYLOAD" --output "$VALID" --entry 0x1000

echo "--- 7.1.1: valid image accepted ---"
python3 "$BUILDER" validate "$VALID" 2>&1 || { echo "FAIL: valid image rejected"; exit 1; }
echo "OK"

echo "--- 7.1.2: info displays metadata ---"
python3 "$BUILDER" info "$VALID" 2>&1 | grep -q "magic:" || { echo "FAIL: no magic in info"; exit 1; }
python3 "$BUILDER" info "$VALID" 2>&1 | grep -q "version:" || { echo "FAIL: no version in info"; exit 1; }
python3 "$BUILDER" info "$VALID" 2>&1 | grep -q "payload_sha256:" || { echo "FAIL: no sha256 in info"; exit 1; }
echo "OK"

echo "--- 7.1.3: negative vectors rejected ---"
for v in bad_magic bad_version bad_length bad_sha; do
  NEG="$TMPDIR/neg_${v}.rv32m"
  python3 "$BUILDER" negative --variant "$v" --output "$NEG"
  if python3 "$BUILDER" validate "$NEG" 2>/dev/null; then
    echo "FAIL: negative vector '$v' was accepted"; exit 1
  fi
  echo "  $v -> correctly rejected"
done
echo "OK"

echo "--- 7.1.4: verify-sha on valid image ---"
python3 "$BUILDER" verify-sha "$VALID" 2>&1 || { echo "FAIL: verify-sha failed on valid"; exit 1; }
echo "OK"

echo ""
echo "ALL 7.1 CHECKS PASSED"
