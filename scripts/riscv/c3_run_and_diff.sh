#!/bin/sh
set -eu

CASE=""
REF_TRACE=""
MODE="native"
TRACE_MODE="full"
OUTDIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --case) CASE="${2:-}"; shift 2 ;;
    --ref-trace) REF_TRACE="${2:-}"; shift 2 ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --trace-mode) TRACE_MODE="${2:-}"; shift 2 ;;
    --outdir) OUTDIR="${2:-}"; shift 2 ;;
    *) echo "usage: $0 --case <name> --ref-trace <path> [--mode native|scaffold] [--trace-mode full|compact] [--outdir dir]" >&2; exit 2 ;;
  esac
done

[ -n "$CASE" ] || { echo "ERROR: --case required" >&2; exit 2; }
[ -n "$REF_TRACE" ] || { echo "ERROR: --ref-trace required" >&2; exit 2; }
[ -f "$REF_TRACE" ] || { echo "ERROR: no such ref trace: $REF_TRACE" >&2; exit 2; }

if [ -z "$OUTDIR" ]; then
  ts="$(date +%Y%m%d_%H%M%S)"
  OUTDIR="tmp/c3_repro/${CASE}/${ts}"
fi
mkdir -p "$OUTDIR"

C3_TRACE="$OUTDIR/c3_trace.json"
cp "$REF_TRACE" "$OUTDIR/ref_trace.json"

# Capture runtime artifact for native path (trace truth source anchor).
if [ "$MODE" = "native" ]; then
  rt="$OUTDIR/runtime"
  mkdir -p "$rt"
  if [ "$CASE" = "mvp5" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_exec_mvp5_native_stub.f0 --dump-testg 37 --keep --tmpdir "$rt" >/dev/null
  fi
  if [ "$CASE" = "mem_sw_lw" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_mem_sw_lw_native.f0 --dump-testg 24 --keep --tmpdir "$rt" >/dev/null
  fi
  if [ "$CASE" = "branch_matrix" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_branch_matrix.f0 --dump-testg 29 --keep --tmpdir "$rt" >/dev/null
  fi
  if [ "$CASE" = "mem_subword" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_mem_subword.f0 --dump-testg 36 --keep --tmpdir "$rt" >/dev/null
  fi
  if [ "$CASE" = "m_fastpath" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_fastpath.f0 --dump-testg 52 --keep --tmpdir "$rt" >/dev/null
  fi
  if [ "$CASE" = "m_mul4" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_mul4.f0 --dump-testg 52 --keep --tmpdir "$rt" >/dev/null
  fi
  if [ "$CASE" = "m_div4" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_div4.f0 --dump-testg 52 --keep --tmpdir "$rt" >/dev/null
  fi
  if [ "$CASE" = "m_div_corner" ]; then
    LIFE_COMPILE=20000000 LIFE_RUN=20000000 scripts/forth0/run_f0.sh --in src/forth0/tests/test_c3_m_div_corner.f0 --dump-testg 52 --keep --tmpdir "$rt" >/dev/null
  fi
fi

python3 scripts/riscv/c3_emit_trace.py --case "$CASE" --mode "$MODE" --trace-mode "$TRACE_MODE" --out "$C3_TRACE" >/dev/null

set +e
python3 scripts/riscv/c3_trace_diff.py --c3-trace "$C3_TRACE" --ref-trace "$REF_TRACE" >"$OUTDIR/diff.stdout.log" 2>"$OUTDIR/diff.stderr.log"
rc=$?
set -e

cat > "$OUTDIR/meta.json" <<META
{
  "case": "$CASE",
  "mode": "$MODE",
  "trace_mode": "$TRACE_MODE",
  "diff_rc": $rc,
  "c3_trace": "c3_trace.json",
  "ref_trace": "ref_trace.json"
}
META

if [ "$rc" -ne 0 ]; then
  : > "$OUTDIR/stop_dump.bin"
  cp "$OUTDIR/diff.stderr.log" "$OUTDIR/diff.txt"
  echo "FAIL c3_run_and_diff: mismatch; repro bundle at $OUTDIR" >&2
  exit 1
fi

echo "OK c3_run_and_diff case=$CASE mode=$MODE trace_mode=$TRACE_MODE outdir=$OUTDIR"
