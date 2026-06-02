#!/bin/sh
# test_rv32m_loader_reproducibility.sh — verify deterministic builds (7.3)
set -eu

BUILDER="scripts/riscv/rv32m_image_builder.py"
TMPDIR="$(mktemp -d tmp/rv32m_repro.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== 7.3 Loader Reproducibility ==="

python3 -c "import sys; sys.stdout.buffer.write(b'\x00'*(4608//8))" > "$TMPDIR/payload.bin"

echo "--- 7.3.1: 3/3 identical builds ---"
for i in 1 2 3; do
  python3 "$BUILDER" build --payload "$TMPDIR/payload.bin" \
    --output "$TMPDIR/build_${i}.rv32m" --entry 0x1000 2>/dev/null
done

# Check all three are identical
if cmp -s "$TMPDIR/build_1.rv32m" "$TMPDIR/build_2.rv32m" && \
   cmp -s "$TMPDIR/build_2.rv32m" "$TMPDIR/build_3.rv32m"; then
  echo "OK: 3/3 builds identical"
else
  echo "FAIL: builds differ"; exit 1
fi

echo "--- 7.3.2: manifest reproducibility ---"
for i in 1 2 3; do
  python3 "$BUILDER" build --payload "$TMPDIR/payload.bin" \
    --output "$TMPDIR/mbuild_${i}.rv32m" --entry 0x1000 \
    --manifest "$TMPDIR/manifest_${i}.json" 2>/dev/null
done
# Manifests will differ by build_time, but digests should match
DIGEST1=$(python3 -c "import json; print(json.load(open('$TMPDIR/manifest_1.json'))['digests']['full_sha256'])")
DIGEST2=$(python3 -c "import json; print(json.load(open('$TMPDIR/manifest_2.json'))['digests']['full_sha256'])")
if [ "$DIGEST1" = "$DIGEST2" ]; then
  echo "OK: manifest digests match across builds"
else
  echo "FAIL: manifest digests differ"
  echo "  $DIGEST1 vs $DIGEST2"
  exit 1
fi

echo ""
echo "ALL REPRODUCIBILITY CHECKS PASSED"
