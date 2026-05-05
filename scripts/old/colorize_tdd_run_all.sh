#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_colorize_tdd"
mkdir -p "$bakdir"

F="scripts/tdd/run_all.sh"
[ -f "$F" ] || { echo "FAIL: missing $F" >&2; exit 1; }

cp -a "$F" "$bakdir/run_all.sh.bak"

cat >"$F" <<'EOF'
#!/bin/sh
set -eu

# colors (only when stderr is a terminal and NO_COLOR not set)
if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RED="$(printf '\033[31m')"
  C_GRN="$(printf '\033[32m')"
  C_YEL="$(printf '\033[33m')"
  C_RST="$(printf '\033[0m')"
else
  C_RED=""; C_GRN=""; C_YEL=""; C_RST=""
fi

fail=0

for t in \
  scripts/tdd/test_vmrep_tools.sh \
  scripts/tdd/test_vmerr_diag.sh \
  scripts/tdd/test_scratch_abi.sh \
  scripts/tdd/test_scratch_artifacts.sh \
  scripts/tdd/test_term0_desc_abi.sh \
  scripts/tdd/test_fail_bundle.sh
do
  printf "\n" >&2
  printf "%s[tdd] RUN %s%s\n" "$C_YEL" "$t" "$C_RST" >&2
  if sh "$t"; then
    printf "%s[tdd] OK  %s%s\n" "$C_GRN" "$t" "$C_RST" >&2
  else
    printf "%s[tdd] FAIL %s%s\n" "$C_RED" "$t" "$C_RST" >&2
    fail=1
  fi
done

exit "$fail"
EOF

chmod +x "$F"
echo "OK: updated $F (backup: $bakdir/run_all.sh.bak)" >&2
echo "Tip: disable colors with NO_COLOR=1 make tdd" >&2
