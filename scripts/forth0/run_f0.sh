#!/bin/sh
set -eu

LIFE_COMPILE="${LIFE_COMPILE:-20000000}"
LIFE_RUN="${LIFE_RUN:-20000000}"

usage() {
  echo "usage: $0 --in prog.f0 [--dump-testg N] [--expect-hex HEX] [--keep]" >&2
  exit 2
}

IN=""
DUMP_N=64
EXPECT_HEX=""
KEEP=0

while [ $# -gt 0 ]; do
  case "$1" in
    --in) IN="${2:-}"; shift 2;;
    --dump-testg) DUMP_N="${2:-}"; shift 2;;
    --expect-hex) EXPECT_HEX="${2:-}"; shift 2;;
    --keep) KEEP=1; shift 1;;
    *) usage;;
  esac
done

[ -n "$IN" ] || usage
[ -f "$IN" ] || { echo "ERROR: no such file: $IN" >&2; exit 1; }

need_bin() { [ -x "$1" ] || { echo "ERROR: missing binary: $1 (run: make bins)" >&2; exit 1; }; }
need_bin build/bin/mkimage_std7_fixed
need_bin build/bin/forth0c
need_bin build/bin/vmrun
need_bin build/bin/vmprep_forth0

dump_or_xxd() {
  f="$1"
  if command -v hexdump >/dev/null 2>&1; then
    hexdump -Cv "$f"
  else
    xxd "$f"
  fi
}

hex_to_bin() { # $1=hexstring $2=outfile
  python3 - "$1" "$2" <<'PY'
import sys
hexs = sys.argv[1].replace(" ", "").replace("\n", "")
out  = sys.argv[2]
open(out, "wb").write(bytes.fromhex(hexs))
PY
}

tmp="tmp/f0run"
rm -rf "$tmp"
mkdir -p "$tmp"

std7="$tmp/std7.bin"
tok="$tmp/prog.tok"
compiled="$tmp/compiled.bin"
after="$tmp/after.bin"
testg_off="$tmp/testg.byte"
testg_bin="$tmp/testg.bin"

build/bin/mkimage_std7_fixed --out "$std7" >/dev/null 2>"$tmp/mkimage.stderr"

build/bin/forth0c --image "$std7" --in "$IN" --out "$tok" \
  1>/dev/null 2>"$tmp/forth0c.stderr"

awk -F= '/^TESTG\(byte\)=/{print $2}' "$tmp/forth0c.stderr" >"$testg_off"
B="$(cat "$testg_off" || true)"
[ -n "$B" ] || { echo "ERROR: cannot parse TESTG(byte) from $tmp/forth0c.stderr" >&2; exit 1; }

build/bin/vmrun --image "$std7" --life "$LIFE_COMPILE" --dump "$compiled" \
  < "$tok" >/dev/null 2>"$tmp/compile.stderr"

build/bin/vmprep_forth0 --image "$compiled" >/dev/null 2>"$tmp/prep.stderr"

build/bin/vmrun --image "$compiled" --life "$LIFE_RUN" --dump "$after" \
  < /dev/null >/dev/null 2>"$tmp/run.stderr"

dd if="$after" bs=1 skip="$B" count="$DUMP_N" status=none > "$testg_bin"

echo "[f0run] IN=$IN"
echo "[f0run] TESTG(byte)=$B dump_n=$DUMP_N"

if [ -n "$EXPECT_HEX" ]; then
  exp="$tmp/expected.bin"
  hex_to_bin "$EXPECT_HEX" "$exp"
  if cmp -s "$testg_bin" "$exp"; then
    echo "[f0run] OK (matches --expect-hex)"
  else
    echo "[f0run] FAIL (mismatch vs --expect-hex)" >&2
    echo "--- got ---" >&2
    dump_or_xxd "$testg_bin" >&2
    echo "--- expected ---" >&2
    dump_or_xxd "$exp" >&2
    [ "$KEEP" -eq 0 ] || echo "[f0run] kept tmp dir: $tmp" >&2
    exit 1
  fi
else
  dump_or_xxd "$testg_bin"
fi

if [ "$KEEP" -eq 0 ]; then
  rm -rf "$tmp"
else
  echo "[f0run] kept tmp dir: $tmp" >&2
fi
