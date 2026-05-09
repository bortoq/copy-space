#!/bin/sh
set -eu

# Run mkimage_std7_fixed and write machine-readable meta file.
#
# usage:
#   scripts/mkimage_meta.sh --out out/img.bin --pool-cells 32768 --meta tmp/mkimage.meta [--log tmp/mkimage.log]
#
# meta keys written (bytes):
#   ART_BYTE, WORDS_BASE_BYTE, STEP_BYTE, WORD_EQ24P_BYTE, OFFTAB_BYTE
#   TESTSCR_BASE_BYTE, TESTSCR_SIZE_BYTE, TESTSCR_END_BYTE
# plus *_BIT (bitaddr) versions.

BIN_DIR="${BIN_DIR:-build/bin}"
MKIMAGE="${MKIMAGE:-$BIN_DIR/mkimage_std7_fixed}"

OUT=""
POOL=""
META=""
LOG=""

while [ $# -gt 0 ]; do
  case "$1" in
    --out) shift; OUT="${1:-}";;
    --pool-cells) shift; POOL="${1:-}";;
    --meta) shift; META="${1:-}";;
    --log) shift; LOG="${1:-}";;
    *) echo "ERROR: unknown arg: $1" >&2; exit 2;;
  esac
  shift
done

test -n "$OUT"  || { echo "ERROR: --out required" >&2; exit 2; }
test -n "$POOL" || { echo "ERROR: --pool-cells required" >&2; exit 2; }
test -n "$META" || { echo "ERROR: --meta required" >&2; exit 2; }

test -x "$MKIMAGE" || { echo "ERROR: mkimage not found/executable: $MKIMAGE" >&2; exit 1; }

META_DIR=$(dirname "$META")
mkdir -p "$META_DIR"
mkdir -p "$(dirname "$OUT")"

if [ -z "$LOG" ]; then
  LOG="${META}.log"
fi
mkdir -p "$(dirname "$LOG")"

# mkimage пишет в stderr => ловим туда
"$MKIMAGE" --out "$OUT" --pool-cells "$POOL" > /dev/null 2> "$LOG"

get1 () {
  key="$1"
  # accept both "... KEY(byte)=123" and "... KEY(bytes)=123"
  v="$(sed -n "s/.*${key}(byte[s]*)=\\([0-9][0-9]*\\).*/\\1/p" "$LOG" | head -n1)"
  test -n "$v" || { echo "ERROR: cannot parse ${key}(byte)=... from $LOG" >&2; exit 1; }
  echo "$v"
}

ART_BYTE="$(get1 ART)"
WORDS_BASE_BYTE="$(get1 WORDS_BASE)"
STEP_BYTE="$(get1 STEP)"
WORD_EQ24P_BYTE="$(get1 WORD_EQ24P)"
OFFTAB_BYTE="$(get1 OFFTAB)"
TESTSCR_BASE_BYTE="$(get1 TESTSCR_BASE)"
TESTSCR_SIZE_BYTE="$(get1 TESTSCR_SIZE)"

TESTSCR_END_BYTE=$((TESTSCR_BASE_BYTE + TESTSCR_SIZE_BYTE))

# bitaddrs
ART_BIT=$((ART_BYTE * 8))
WORDS_BASE_BIT=$((WORDS_BASE_BYTE * 8))
STEP_BIT=$((STEP_BYTE * 8))
WORD_EQ24P_BIT=$((WORD_EQ24P_BYTE * 8))
OFFTAB_BIT=$((OFFTAB_BYTE * 8))
TESTSCR_BASE_BIT=$((TESTSCR_BASE_BYTE * 8))
TESTSCR_END_BIT=$((TESTSCR_END_BYTE * 8))

cat > "$META" <<EOF
OUT_PATH=$OUT
POOL_CELLS=$POOL

ART_BYTE=$ART_BYTE
WORDS_BASE_BYTE=$WORDS_BASE_BYTE
STEP_BYTE=$STEP_BYTE
WORD_EQ24P_BYTE=$WORD_EQ24P_BYTE
OFFTAB_BYTE=$OFFTAB_BYTE
TESTSCR_BASE_BYTE=$TESTSCR_BASE_BYTE
TESTSCR_SIZE_BYTE=$TESTSCR_SIZE_BYTE
TESTSCR_END_BYTE=$TESTSCR_END_BYTE

ART_BIT=$ART_BIT
WORDS_BASE_BIT=$WORDS_BASE_BIT
STEP_BIT=$STEP_BIT
WORD_EQ24P_BIT=$WORD_EQ24P_BIT
OFFTAB_BIT=$OFFTAB_BIT
TESTSCR_BASE_BIT=$TESTSCR_BASE_BIT
TESTSCR_END_BIT=$TESTSCR_END_BIT
EOF

echo "[mkimage_meta] wrote $META (log: $LOG)" >&2