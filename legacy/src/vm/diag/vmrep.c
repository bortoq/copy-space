/* file: src/vm/diag/vmrep.c
 * date: 2026-05-04
 * purpose: vmrep implementation (was embedded in space.c)
 */
#include "vmrep.h"
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <stdio.h>

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

void vmrep_tick_begin(size_t slots_cap) {
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

void vmrep_note_copy(uint64_t dst, uint64_t n) {
  if (!vmrep.enabled) return;
  if (n == 0) return;
  vmrep.tick_bits_sum += n;
  if (vmrep.iv_n < vmrep.iv_cap) {
    vmrep.iv[vmrep.iv_n++] = (vmrep_iv_t){ .lo = dst, .hi = dst + n };
  }
}

void vmrep_tick_end(void) {
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
/* ===================================================================== */
