#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
SPACE_C="src/vm/space.c"

if [[ ! -f "Makefile" ]]; then
  echo "ERROR: run from repo root (Makefile not found)" >&2
  exit 1
fi
if [[ ! -f "$SPACE_C" ]]; then
  echo "ERROR: $SPACE_C not found" >&2
  exit 1
fi

ts="$(date +%Y%m%d_%H%M%S)"
bak="${SPACE_C}.bak.${ts}"
cp -a "$SPACE_C" "$bak"
echo "backup: $bak"

python3 - <<'PY'
import re, sys
from pathlib import Path

path = Path("src/vm/space.c")
text = path.read_text(encoding="utf-8", errors="replace")

if "VMREP_BEGIN" in text:
    print("INFO: VM report patch already applied (VMREP_BEGIN found). Nothing to do.")
    sys.exit(0)

# ---------- helpers ----------
def find_matching_brace(s, open_brace_index):
    assert s[open_brace_index] == "{"
    depth = 0
    i = open_brace_index
    n = len(s)
    in_str = False
    in_chr = False
    in_sl_comment = False
    in_ml_comment = False
    esc = False
    while i < n:
        c = s[i]
        nxt = s[i+1] if i+1 < n else ""
        if in_sl_comment:
            if c == "\n":
                in_sl_comment = False
            i += 1
            continue
        if in_ml_comment:
            if c == "*" and nxt == "/":
                in_ml_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            i += 1
            continue

        if c == "/" and nxt == "/":
            in_sl_comment = True
            i += 2
            continue
        if c == "/" and nxt == "*":
            in_ml_comment = True
            i += 2
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_chr = True
            i += 1
            continue

        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("no matching brace found")

def split_args(argstr):
    # split top-level commas
    out = []
    cur = []
    depth_par = 0
    depth_br = 0
    depth_sq = 0
    in_str = False
    in_chr = False
    esc = False
    for c in argstr:
        if in_str:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if in_chr:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            continue
        if c == '"':
            in_str = True
            cur.append(c)
            continue
        if c == "'":
            in_chr = True
            cur.append(c)
            continue
        if c == "(":
            depth_par += 1
        elif c == ")":
            depth_par -= 1
        elif c == "{":
            depth_br += 1
        elif c == "}":
            depth_br -= 1
        elif c == "[":
            depth_sq += 1
        elif c == "]":
            depth_sq -= 1

        if c == "," and depth_par == 0 and depth_br == 0 and depth_sq == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
    tail = "".join(cur).strip()
    if tail:
        out.append(tail)
    return out

# ---------- insert report module code after includes ----------
lines = text.splitlines(True)
inc_end = 0
for i, ln in enumerate(lines):
    if ln.lstrip().startswith("#include"):
        inc_end = i + 1

report_block = r'''
/* ===================== VM REPORT (auto-injected) ===================== */
/* VMREP_BEGIN
 * Enable via env:
 *   COPYSPACE_REPORT=1
 *   COPYSPACE_REPORT_MODE=lat|thr   (default: lat)
 *   COPYSPACE_REPORT_FROM=<tick>    (thr only; default: 0)
 *   COPYSPACE_REPORT_LEN=<ticks>    (thr only; default: 0 => disabled)
 * Optional:
 *   COPYSPACE_REPORT_HZ=<clock_hz>  (to print Gb/s)
 *   COPYSPACE_REPORT_DSTMIN=<bitaddr>, COPYSPACE_REPORT_DSTMAX=<bitaddr> (filter dst range)
 *
 * Report goes to stderr.
 */
#include <inttypes.h>

typedef struct { uint32_t lo, hi; } vmrep_iv_t;

static struct {
  int      inited;
  int      enabled;
  int      mode_thr;          /* 0=lat, 1=thr (still prints latency totals too) */

  uint64_t ticks_total;
  uint64_t bits_sum_total;
  uint64_t bits_uniq_total;

  uint64_t thr_from;
  uint64_t thr_len;
  uint64_t thr_ticks;
  uint64_t thr_bits_sum;
  uint64_t thr_bits_uniq;

  uint64_t hz;               /* optional */
  int      have_dst_filter;
  uint32_t dstmin, dstmax;   /* [dstmin, dstmax) in bits */

  /* per-tick */
  uint64_t tick_bits_sum;
  vmrep_iv_t iv[PROCESSOR_N];
  size_t   iv_n;
} vmrep;

static uint64_t vmrep_parse_u64(const char* s, uint64_t defv) {
  if (!s || !*s) return defv;
  char* end = NULL;
  uint64_t v = strtoull(s, &end, 0);
  return (end && end != s) ? v : defv;
}
static uint32_t vmrep_parse_u32(const char* s, uint32_t defv) {
  if (!s || !*s) return defv;
  char* end = NULL;
  unsigned long v = strtoul(s, &end, 0);
  return (end && end != s) ? (uint32_t)v : defv;
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

static uint64_t vmrep_count_uniq_dst(vmrep_iv_t* iv, size_t n) {
  if (n == 0) return 0;
  qsort(iv, n, sizeof(iv[0]), vmrep_cmp_iv);

  uint64_t total = 0;
  uint32_t cur_lo = iv[0].lo;
  uint32_t cur_hi = iv[0].hi;

  for (size_t i = 1; i < n; i++) {
    uint32_t lo = iv[i].lo, hi = iv[i].hi;
    if (lo <= cur_hi) {
      if (hi > cur_hi) cur_hi = hi;
    } else {
      total += (uint64_t)(cur_hi - cur_lo);
      cur_lo = lo;
      cur_hi = hi;
    }
  }
  total += (uint64_t)(cur_hi - cur_lo);
  return total;
}

static void vmrep_finalize(void) {
  if (!vmrep.enabled) return;

  double avg_sum  = vmrep.ticks_total ? (double)vmrep.bits_sum_total  / (double)vmrep.ticks_total : 0.0;
  double avg_uniq = vmrep.ticks_total ? (double)vmrep.bits_uniq_total / (double)vmrep.ticks_total : 0.0;

  fprintf(stderr, "\n[vmrep] REPORT latency\n");
  fprintf(stderr, "[vmrep] ticks_total=%" PRIu64 "\n", vmrep.ticks_total);
  fprintf(stderr, "[vmrep] bits_sum_total=%" PRIu64 "\n", vmrep.bits_sum_total);
  fprintf(stderr, "[vmrep] bits_uniq_dst_total=%" PRIu64 "\n", vmrep.bits_uniq_total);
  fprintf(stderr, "[vmrep] avg_bits_sum_per_tick=%.3f\n", avg_sum);
  fprintf(stderr, "[vmrep] avg_bits_uniq_dst_per_tick=%.3f\n", avg_uniq);

  if (vmrep.hz) {
    double gbps_sum  = avg_sum  * (double)vmrep.hz / 1e9;
    double gbps_uniq = avg_uniq * (double)vmrep.hz / 1e9;
    fprintf(stderr, "[vmrep] clock_hz=%" PRIu64 "\n", vmrep.hz);
    fprintf(stderr, "[vmrep] est_sum_Gb/s=%.3f\n", gbps_sum);
    fprintf(stderr, "[vmrep] est_uniq_Gb/s=%.3f\n", gbps_uniq);
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
  fprintf(stderr, "[vmrep] VMREP_END\n");
}

static void vmrep_lazy_init(void) {
  if (vmrep.inited) return;
  vmrep.inited = 1;

  const char* en = getenv("COPYSPACE_REPORT");
  vmrep.enabled = (en && *en);

  if (!vmrep.enabled) return;

  const char* mode = getenv("COPYSPACE_REPORT_MODE");
  vmrep.mode_thr = (mode && strcmp(mode, "thr") == 0);

  vmrep.thr_from = vmrep_parse_u64(getenv("COPYSPACE_REPORT_FROM"), 0);
  vmrep.thr_len  = vmrep_parse_u64(getenv("COPYSPACE_REPORT_LEN"),  0);
  vmrep.hz       = vmrep_parse_u64(getenv("COPYSPACE_REPORT_HZ"),   0);

  const char* dmin = getenv("COPYSPACE_REPORT_DSTMIN");
  const char* dmax = getenv("COPYSPACE_REPORT_DSTMAX");
  if ((dmin && *dmin) || (dmax && *dmax)) {
    vmrep.have_dst_filter = 1;
    vmrep.dstmin = vmrep_parse_u32(dmin, 0);
    vmrep.dstmax = vmrep_parse_u32(dmax, 0xFFFFFFFFu);
    if (vmrep.dstmax < vmrep.dstmin) {
      uint32_t tmp = vmrep.dstmin;
      vmrep.dstmin = vmrep.dstmax;
      vmrep.dstmax = tmp;
    }
  }

  atexit(vmrep_finalize);
}

static inline void vmrep_tick_begin(void) {
  vmrep_lazy_init();
  if (!vmrep.enabled) return;
  vmrep.tick_bits_sum = 0;
  vmrep.iv_n = 0;
}

static inline void vmrep_note_copy(uint32_t dst, uint32_t n) {
  if (!vmrep.enabled) return;
  if (n == 0) return;

  uint32_t lo = dst;
  uint32_t hi = dst + n;

  if (vmrep.have_dst_filter) {
    if (hi <= vmrep.dstmin || lo >= vmrep.dstmax) return;
    if (lo < vmrep.dstmin) lo = vmrep.dstmin;
    if (hi > vmrep.dstmax) hi = vmrep.dstmax;
    if (hi <= lo) return;
    n = hi - lo;
  }

  vmrep.tick_bits_sum += n;
  if (vmrep.iv_n < PROCESSOR_N) {
    vmrep.iv[vmrep.iv_n++] = (vmrep_iv_t){ .lo = lo, .hi = hi };
  }
}

static inline void vmrep_tick_end(void) {
  if (!vmrep.enabled) return;

  uint64_t uniq = vmrep_count_uniq_dst(vmrep.iv, vmrep.iv_n);

  vmrep.ticks_total++;
  vmrep.bits_sum_total  += vmrep.tick_bits_sum;
  vmrep.bits_uniq_total += uniq;

  if (vmrep.thr_len) {
    uint64_t t = vmrep.ticks_total - 1; /* 0-based tick index */
    if (t >= vmrep.thr_from && vmrep.thr_ticks < vmrep.thr_len) {
      vmrep.thr_ticks++;
      vmrep.thr_bits_sum  += vmrep.tick_bits_sum;
      vmrep.thr_bits_uniq += uniq;
    }
  }
}
/* VMREP_END */
/* ===================================================================== */
'''

lines.insert(inc_end, report_block + "\n")
text = "".join(lines)

# ---------- find the processor loop (for ... PROCESSOR_N ...) containing bitcpy ----------
loop_re = re.compile(r'for\s*\([^)]*\bPROCESSOR_N\b[^)]*\)\s*\{', re.M)
m_loop = None
loop_open = None
loop_close = None

for m in loop_re.finditer(text):
    open_idx = m.end() - 1  # '{'
    close_idx = find_matching_brace(text, open_idx)
    body = text[open_idx+1:close_idx]
    if "bitcpy" in body:
        m_loop = m
        loop_open = open_idx
        loop_close = close_idx
        break

if m_loop is None:
    print("ERROR: could not find a 'for(...PROCESSOR_N...) { ... bitcpy(...) ... }' loop to patch.", file=sys.stderr)
    print("       Please paste the tick-execution function from src/vm/space.c and I will generate an exact patch.", file=sys.stderr)
    sys.exit(2)

body = text[loop_open+1:loop_close]

# avoid double injection
if "vmrep_tick_begin" in body or "vmrep_note_copy" in body:
    print("ERROR: loop already seems patched, but VMREP_BEGIN was not found. Aborting to avoid corruption.", file=sys.stderr)
    sys.exit(3)

# indent for inserted lines (use indentation of the first non-empty line inside loop or fallback)
indent_match = re.search(r'\n([ \t]*)\S', body)
indent = indent_match.group(1) if indent_match else "  "

# ---------- inject vmrep_note_copy before each bitcpy(...) inside this loop body ----------
def inject_notes(loop_body):
    out = []
    i = 0
    while True:
        j = loop_body.find("bitcpy", i)
        if j < 0:
            out.append(loop_body[i:])
            break

        # ensure it's a call "bitcpy("
        k = j + len("bitcpy")
        while k < len(loop_body) and loop_body[k].isspace():
            k += 1
        if k >= len(loop_body) or loop_body[k] != "(":
            out.append(loop_body[i:k])
            i = k
            continue

        # find statement start (line start) for indentation
        stmt_line_start = loop_body.rfind("\n", 0, j) + 1
        stmt_indent = re.match(r'[ \t]*', loop_body[stmt_line_start:j]).group(0)

        # find matching paren for args
        p0 = k
        depth = 0
        p = p0
        while p < len(loop_body):
            c = loop_body[p]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    p1 = p
                    break
            p += 1
        else:
            raise ValueError("cannot find closing ')' for bitcpy call")

        args_str = loop_body[p0+1:p1]
        args = split_args(args_str)
        if len(args) < 4:
            raise ValueError(f"bitcpy call has <4 args: {args_str!r}")

        dst_expr = args[1]
        n_expr = args[-1]

        note = f"{stmt_indent}vmrep_note_copy((uint32_t)({dst_expr}), (uint32_t)({n_expr}));\n"

        out.append(loop_body[i:stmt_line_start])
        out.append(note)
        out.append(loop_body[stmt_line_start:p1+1])  # include "bitcpy(...)" without semicolon yet
        i = p1 + 1

    return "".join(out)

new_body = inject_notes(body)

# inject tick_begin at start and tick_end at end of loop body
new_body = f"\n{indent}vmrep_tick_begin();\n" + new_body
new_body = new_body.rstrip() + f"\n{indent}vmrep_tick_end();\n"

text = text[:loop_open+1] + new_body + text[loop_close:]

path.write_text(text, encoding="utf-8")
print("OK: patched src/vm/space.c with VM report hooks.")
PY

echo "Done. Now rebuild and run a test with env COPYSPACE_REPORT=1."