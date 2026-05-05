#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_add_demo_db"
mkdir -p "$bakdir"

F="scripts/demo_db.sh"
if [ -f "$F" ]; then
  cp -a "$F" "$bakdir/demo_db.sh.bak"
fi

cat >"$F" <<'EOF'
#!/bin/sh
set -eu

# file: scripts/demo_db.sh
# date: 2026-05-05
# purpose: quick partner-facing demo (DB/analytics): pack + permute (+ optional bulkcopy + optional tdd)

# defaults (can be overridden by env)
: "${COPYSPACE_REPORT:=1}"
: "${COPYSPACE_REPORT_FROM:=1000}"
: "${COPYSPACE_REPORT_LEN:=5000}"

echo "[demo] build tools (make bins)" >&2
make bins >/dev/null

echo "[demo] PACK (compaction-like):" >&2
: "${COPIES:=64}"
: "${CHUNK_BYTES:=64}"
: "${SRC_STRIDE_BYTES:=4096}"
scripts/bench_pack_csv.sh

echo "[demo] PERMUTE (reorder-like):" >&2
: "${MODE:=random}"
: "${SEED:=1}"
scripts/bench_permute_csv.sh

if [ "${DEMO_BULKCOPY:-1}" = "1" ]; then
  echo "[demo] BULKCOPY (bulk movement):" >&2
  : "${LEN_BYTES:=65536}"
  : "${LIFE:=20000}"
  scripts/bench_bulkcopy_csv.sh
fi

if [ "${DEMO_TDD:-0}" = "1" ]; then
  echo "[demo] TDD (includes TERM0 descriptor ABI):" >&2
  make tdd >/dev/null
  echo "[demo] TDD OK" >&2
fi
EOF

chmod +x "$F"
echo "OK: wrote $F (backup in $bakdir if existed)" >&2
echo "Run: scripts/demo_db.sh" >&2
echo "Optional: DEMO_TDD=1 scripts/demo_db.sh" >&2
