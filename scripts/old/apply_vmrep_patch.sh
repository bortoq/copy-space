#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f Makefile ]]; then
  echo "ERROR: run from repo root (Makefile not found)" >&2
  exit 1
fi

F="src/vm/space.c"
if [[ ! -f "$F" ]]; then
  echo "ERROR: $F not found" >&2
  exit 1
fi

ts="$(date +%Y%m%d_%H%M%S)"
bak="${F}.bak.${ts}"
cp -a "$F" "$bak"
echo "backup: $bak"

python3 - <<'PY'
from pathlib import Path
import re, sys

p = Path("src/vm/space.c")
s = p.read_text(encoding="utf-8", errors="replace")

if "VMREP_BEGIN" in s:
    print("INFO: VMREP already applied (VMREP_BEGIN found).")
    sys.exit(0)

# ---------- insert VMREP block after includes ----------
lines = s.splitlines(True)
ins_at = 0
for i, ln in enumerate(lines):
    if ln.lstrip().startswith("#include"):
        ins_at = i + 1

vmrep_block = r'''
/* ===================== VM REPORT (auto-injected) ===================== */
/* VMREP_BEGIN
 * Enable:
 *   COPYSPACE_REPORT=1
 *
 * Modes:
 *   COPYSPACE_REPORT_MODE=lat            (default)
 *   COPYSPACE_REPORT_MODE=thr            (steady-state window)
 *     COPYSPACE_REPORT_FROM=<tick0>      (0-based, default 0)
 *     COPYSPACE_REPORT_LEN=<count>       (default 0 = disabled)
 *
 * Optional:
 *   COPYSPACE_REPORT_HZ=<clock_hz>       (to print Gb/s)
 *
 * Output: stderr at exit.
 */
#include <inttypes.h>

typedef struct { uint64_t lo, hi; } vmrep_iv_t;

static struct {
  int inited;
  int enabled;

  uint64_t ticks_total;
  uint64_t bits_sum_total;
  uint64_t bits_uniq_dst_total;

  uint64_t thr_from;
  uint64_t thr_len;
  uint64_t thr_ticks;
  uint64_t thr_bits_sum;
  uint64_t thr_bits_uniq;

  uint64_t hz;

  /* per-tick */
  uint64_t tick_bits_sum;
  vmrep_iv_t* iv;
  size_t iv_cap;
  size_t iv_n;
} vmrep;

static uint64_t vmrep_parse_u64(const char* s, uint64_t defv) {
  if (!s || !*s) return defv;
  char* end = NULL;
  uint64_t v = strtoull(s, &end, 0);
  return (end && end != s) ? v : defv;
}

static int vmrep_cmp_iv(const void* a, const void* b) {
  const vmrep_iv_t* x = (const vmrep_iv_t*)a;
  const vmrep_iv_t* y = (const vmrep_iv_t*)b;
  if (x->lo < y->lo) return -1;
  if (x->lo > y->lo) return  1;
  if (x->hi < y->hi) return -1;
  if (x->hi > y->hi) return  1;
  return 0;
}

static uint64_t vmrep_count_uniq(vmrep_iv_t* iv, size_t n) {
  if (n == 0) return 0;
  qsort(iv, n, sizeof(iv[0]), vmrep_cmp_iv);
  uint64_t total = 0;
  uint64_t cur_lo = iv[0].lo;
  uint64_t cur_hi = iv[0].hi;

  for (size_t i = 1; i < n; i++) {
    uint64_t lo = iv[i].lo, hi = iv[i].hi;
    if (lo <= cur_hi) {
      if (hi > cur_hi) cur_hi = hi;
    } else {
      total += (cur_hi - cur_lo);
      cur_lo = lo;
      cur_hi = hi;
    }
  }
  total += (cur_hi - cur_lo);
  return total;
}

static void vmrep_finalize(void) {
  if (!vmrep.enabled) return;

  double avg_sum  = vmrep.ticks_total ? (double)vmrep.bits_sum_total / (double)vmrep.ticks_total : 0.0;
  double avg_uniq = vmrep.ticks_total ? (double)vmrep.bits_uniq_dst_total / (double)vmrep.ticks_total : 0.0;

  fprintf(stderr, "\n[vmrep] REPORT latency\n");
  fprintf(stderr, "[vmrep] ticks_total=%" PRIu64 "\n", vmrep.ticks_total);
  fprintf(stderr, "[vmrep] bits_sum_total=%" PRIu64 "\n", vmrep.bits_sum_total);
  fprintf(stderr, "[vmrep] bits_uniq_dst_total=%" PRIu64 "\n", vmrep.bits_uniq_dst_total);
  fprintf(stderr, "[vmrep] avg_bits_sum_per_tick=%.3f\n", avg_sum);
  fprintf(stderr, "[vmrep] avg_bits_uniq_dst_per_tick=%.3f\n", avg_uniq);

  if (vmrep.hz) {
    fprintf(stderr, "[vmrep] clock_hz=%" PRIu64 "\n", vmrep.hz);
    fprintf(stderr, "[vmrep] est_sum_Gb/s=%.3f\n", avg_sum * (double)vmrep.hz / 1e9);
    fprintf(stderr, "[vmrep] est_uniq_Gb/s=%.3f\n", avg_uniq * (double)vmrep.hz / 1e9);
  }

  if (vmrep.thr_len && vmrep.thr_ticks) {
    double thr_avg_sum  = (double)vmrep.thr_bits_sum  / (double)vmrep.thr_ticks;
    double thr_avg_uniq = (double)vmrep.thr_bits_uniq / (double)vmrep.thr_ticks;
    fprintf(stderr, "[vmrep] REPORT throughput\n");
    fprintf(stderr, "[vmrep] thr_from=%" PRIu64 " thr_len=%" PRIu64 " thr_ticks=%" PRIu64 "\n",
            vmrep.thr_from, vmrep.thr_len, vmrep.thr_ticks);
    fprintf(stderr, "[vmrep] thr_avg_bits_sum_per_tick=%.3f\n", thr_avg_sum);
    fprintf(stderr, "[vmrep] thr_avg_bits_uniq_dst_per_tick=%.3f\n", thr_avg_uniq);
    if (vmrep.hz) {
      fprintf(stderr, "[vmrep] thr_est_sum_Gb/s=%.3f\n", thr_avg_sum * (double)vmrep.hz / 1e9);
      fprintf(stderr, "[vmrep] thr_est_uniq_Gb/s=%.3f\n", thr_avg_uniq * (double)vmrep.hz / 1e9);
    }
  }

  free(vmrep.iv);
  vmrep.iv = NULL;
  vmrep.iv_cap = vmrep.iv_n = 0;

  fprintf(stderr, "[vmrep] VMREP_END\n");
}

static void vmrep_lazy_init(void) {
  if (vmrep.inited) return;
  vmrep.inited = 1;

  const char* en = getenv("COPYSPACE_REPORT");
  vmrep.enabled = (en && *en);
  if (!vmrep.enabled) return;

  vmrep.thr_from = vmrep_parse_u64(getenv("COPYSPACE_REPORT_FROM"), 0);
  vmrep.thr_len  = vmrep_parse_u64(getenv("COPYSPACE_REPORT_LEN"),  0);
  vmrep.hz       = vmrep_parse_u64(getenv("COPYSPACE_REPORT_HZ"),   0);

  atexit(vmrep_finalize);
}

static inline void vmrep_tick_begin(size_t slots_cap) {
  vmrep_lazy_init();
  if (!vmrep.enabled) return;

  if (slots_cap > vmrep.iv_cap) {
    vmrep_iv_t* nv = (vmrep_iv_t*)realloc(vmrep.iv, slots_cap * sizeof(vmrep_iv_t));
    if (!nv) return; /* disable silently on OOM */
    vmrep.iv = nv;
    vmrep.iv_cap = slots_cap;
  }

  vmrep.tick_bits_sum = 0;
  vmrep.iv_n = 0;
}

static inline void vmrep_note_copy(uint64_t dst, uint64_t n) {
  if (!vmrep.enabled) return;
  if (n == 0) return;
  vmrep.tick_bits_sum += n;
  if (vmrep.iv_n < vmrep.iv_cap) {
    vmrep.iv[vmrep.iv_n++] = (vmrep_iv_t){ .lo = dst, .hi = dst + n };
  }
}

static inline void vmrep_tick_end(void) {
  if (!vmrep.enabled) return;

  uint64_t uniq = vmrep_count_uniq(vmrep.iv, vmrep.iv_n);

  uint64_t tick_index = vmrep.ticks_total; /* 0-based */
  vmrep.ticks_total++;
  vmrep.bits_sum_total += vmrep.tick_bits_sum;
  vmrep.bits_uniq_dst_total += uniq;

  if (vmrep.thr_len) {
    if (tick_index >= vmrep.thr_from && vmrep.thr_ticks < vmrep.thr_len) {
      vmrep.thr_ticks++;
      vmrep.thr_bits_sum  += vmrep.tick_bits_sum;
      vmrep.thr_bits_uniq += uniq;
    }
  }
}
/* VMREP_END */
/* ===================================================================== */
'''

lines.insert(ins_at, vmrep_block + "\n")
s = "".join(lines)

# ---------- patch vm_tick() ----------
# Insert tick_begin() before the slot loop, note_copy() before bitcpy, tick_end() after loop.
if "vm_rc_t vm_tick" not in s:
    print("ERROR: vm_tick not found", file=sys.stderr)
    sys.exit(2)

# Add vmrep_tick_begin before 'for (unsigned i = 0; i < vm->processor_n; i++) {'
slot_for_pat = r'(\n\s*/\*\s*3\)\s*fetch-execute slots\s*\*/\s*\n)(\s*for\s*\(\s*unsigned\s+i\s*=\s*0\s*;\s*i\s*<\s*vm->processor_n\s*;\s*i\+\+\s*\)\s*\{)'
m = re.search(slot_for_pat, s)
if not m:
    # fallback: find the for-loop line directly
    m = re.search(r'\n(\s*)for\s*\(\s*unsigned\s+i\s*=\s*0\s*;\s*i\s*<\s*vm->processor_n\s*;\s*i\+\+\s*\)\s*\{', s)
    if not m:
        print("ERROR: slot loop not found in vm_tick", file=sys.stderr)
        sys.exit(3)
    indent = m.group(1)
    insert_pos = m.start()
    s = s[:insert_pos] + f"\n{indent}vmrep_tick_begin(vm->processor_n);\n" + s[insert_pos:]
else:
    insert_pos = m.end(1)
    # indent from the for line
    indent_m = re.search(r'\n(\s*)for\s*\(', s[insert_pos:])
    indent = indent_m.group(1) if indent_m else "  "
    s = s[:insert_pos] + f"{indent}vmrep_tick_begin(vm->processor_n);\n" + s[insert_pos:]

# Insert vmrep_note_copy(dst,n) just before bitcpy(...) inside vm_tick loop
# We match the specific line 'bitcpy((size_t)n, ... (size_t)dst);'
if "vmrep_note_copy" in s:
    pass
else:
    # Insert before the first occurrence of 'bitcpy((size_t)n,'
    s2 = re.sub(
        r'(\n\s*)bitcpy\s*\(\s*\(size_t\)\s*n\s*,',
        r'\1vmrep_note_copy((uint64_t)dst, (uint64_t)n);\n\1bitcpy((size_t)n,',
        s,
        count=1
    )
    if s2 == s:
        print("ERROR: could not find bitcpy((size_t)n, ...) call to hook", file=sys.stderr)
        sys.exit(4)
    s = s2

# Insert vmrep_tick_end() before 'return VM_OK;' in vm_tick
s2 = re.sub(
    r'(\n\s*)return\s+VM_OK\s*;\s*\n\}',
    r'\1vmrep_tick_end();\n\1return VM_OK;\n}',
    s,
    count=1
)
if s2 == s:
    print("ERROR: could not insert vmrep_tick_end() before return VM_OK in vm_tick", file=sys.stderr)
    sys.exit(5)
s = s2

p.write_text(s, encoding="utf-8")
print("OK: VMREP injected and vm_tick patched.")
PY

echo "OK. Rebuild."
echo "Example:"
echo "  COPYSPACE_REPORT=1 make test-all"
echo "  COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=2000 COPYSPACE_REPORT_LEN=5000 make test-all"