#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_rewrite_bitcpy"
mkdir -p "$bakdir"

backup() {
  f="$1"
  if [ -f "$f" ]; then
    cp -a "$f" "$bakdir/$(echo "$f" | tr '/ ' '__').bak"
  fi
}

backup src/vm/bitcpy.c
backup src/tools/bitcpy_selftest.c
backup scripts/tdd/test_bitcpy_selftest.sh
backup scripts/tdd/run_all.sh

# ---------------- src/vm/bitcpy.c ----------------
cat > src/vm/bitcpy.c <<'C'
/* file: src/vm/bitcpy.c
 * date: 2026-05-05
 * purpose: copy bits MSB-first (bit 0 in byte = 0x80), overlap-safe, bounds-safe (no out-of-range reads)
 *
 * Semantics:
 * - bit positions within a byte: 0..7 correspond to masks 0x80,0x40,...,0x01 (MSB-first)
 * - behaves like memmove for overlapping ranges when src_org == dst_org
 *
 * This implementation is written from scratch for this project.
 */

#include "space.h"
#include <stdint.h>
#include <string.h>

static inline unsigned bit_get_ptr(const uint8_t *p, size_t bitpos) {
  uint8_t byte = p[bitpos >> 3];
  unsigned shift = 7u - (unsigned)(bitpos & 7u);
  return (byte >> shift) & 1u;
}

static inline void bit_set_ptr(uint8_t *p, size_t bitpos, unsigned v) {
  uint8_t *b = &p[bitpos >> 3];
  unsigned shift = 7u - (unsigned)(bitpos & 7u);
  uint8_t mask = (uint8_t)(1u << shift);
  if (v) *b |= mask;
  else   *b &= (uint8_t)~mask;
}

/* Slow but always-correct overlap handler (memmove semantics). */
static void bitcpy_overlap_fallback(size_t n_bits,
                                    const uint8_t *src, size_t src_bit,
                                    uint8_t *dst, size_t dst_bit)
{
  if (dst_bit <= src_bit) {
    for (size_t i = 0; i < n_bits; i++) {
      bit_set_ptr(dst, dst_bit + i, bit_get_ptr(src, src_bit + i));
    }
  } else {
    for (size_t i = n_bits; i-- > 0;) {
      bit_set_ptr(dst, dst_bit + i, bit_get_ptr(src, src_bit + i));
    }
  }
}

void bitcpy(size_t n_bits,
            const void *src_org, size_t src_bit,
            void *dst_org, size_t dst_bit)
{
  if (n_bits == 0) return;
  if (src_org == dst_org && src_bit == dst_bit) return;

  const uint8_t *src0 = (const uint8_t*)src_org;
  uint8_t *dst0 = (uint8_t*)dst_org;

  /* Overlap check (only meaningful for same base buffer). */
  if (src_org == dst_org) {
    size_t src_end = src_bit + n_bits;
    size_t dst_end = dst_bit + n_bits;
    if (src_bit < dst_end && dst_bit < src_end) {
      bitcpy_overlap_fallback(n_bits, src0, src_bit, dst0, dst_bit);
      return;
    }
  }

  /* Fast path: byte-aligned copy. Overlap already excluded or handled above. */
  if (((src_bit | dst_bit | n_bits) & 7u) == 0u) {
    memmove(dst0 + (dst_bit >> 3), src0 + (src_bit >> 3), n_bits >> 3);
    return;
  }

  /* Head: align destination to byte boundary using bitwise copies (<=7 iterations). */
  while (n_bits && ((dst_bit & 7u) != 0u)) {
    bit_set_ptr(dst0, dst_bit, bit_get_ptr(src0, src_bit));
    dst_bit++; src_bit++; n_bits--;
  }

  /* Middle: copy whole bytes into dst (dst is byte-aligned here). */
  while (n_bits >= 8u) {
    size_t sbyte = src_bit >> 3;
    unsigned smod = (unsigned)(src_bit & 7u);

    uint8_t out;
    if (smod == 0u) {
      out = src0[sbyte];
    } else {
      /* Need bits from src0[sbyte] and src0[sbyte+1]. The +1 byte is always within
         the source range for n_bits>=8, but to be bounds-safe we clamp it. */
      size_t last_src_byte = (src_bit + n_bits - 1u) >> 3;
      uint8_t b0 = src0[sbyte];
      uint8_t b1 = (sbyte + 1u <= last_src_byte) ? src0[sbyte + 1u] : 0u;
      out = (uint8_t)((uint8_t)(b0 << smod) | (uint8_t)(b1 >> (8u - smod)));
    }

    dst0[dst_bit >> 3] = out;
    dst_bit += 8u;
    src_bit += 8u;
    n_bits  -= 8u;
  }

  /* Tail: copy remaining bits (<=7). */
  while (n_bits) {
    bit_set_ptr(dst0, dst_bit, bit_get_ptr(src0, src_bit));
    dst_bit++; src_bit++; n_bits--;
  }
}
C

# ---------------- src/tools/bitcpy_selftest.c ----------------
cat > src/tools/bitcpy_selftest.c <<'C'
/* file: src/tools/bitcpy_selftest.c
 * date: 2026-05-05
 * purpose: self-test for bitcpy correctness and bounds safety (including edge-of-buffer cases)
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void bitcpy(size_t n_bits,
            const void *src_org, size_t src_bit,
            void *dst_org, size_t dst_bit);

static unsigned bit_get_ptr(const uint8_t *p, size_t bitpos) {
  uint8_t byte = p[bitpos >> 3];
  unsigned shift = 7u - (unsigned)(bitpos & 7u);
  return (byte >> shift) & 1u;
}
static void bit_set_ptr(uint8_t *p, size_t bitpos, unsigned v) {
  uint8_t *b = &p[bitpos >> 3];
  unsigned shift = 7u - (unsigned)(bitpos & 7u);
  uint8_t mask = (uint8_t)(1u << shift);
  if (v) *b |= mask;
  else   *b &= (uint8_t)~mask;
}

/* Reference implementation (always bit-by-bit, memmove semantics). */
static void ref_bitcpy(size_t n_bits,
                       const uint8_t *src0, size_t src_bit,
                       uint8_t *dst0, size_t dst_bit,
                       int same_buf)
{
  if (n_bits == 0) return;
  if (same_buf) {
    size_t src_end = src_bit + n_bits;
    size_t dst_end = dst_bit + n_bits;
    if (src_bit < dst_end && dst_bit < src_end) {
      /* overlap */
      if (dst_bit <= src_bit) {
        for (size_t i=0;i<n_bits;i++) bit_set_ptr(dst0, dst_bit+i, bit_get_ptr(src0, src_bit+i));
      } else {
        for (size_t i=n_bits;i-- > 0;) bit_set_ptr(dst0, dst_bit+i, bit_get_ptr(src0, src_bit+i));
      }
      return;
    }
  }
  /* no overlap or different buffers */
  for (size_t i=0;i<n_bits;i++) bit_set_ptr(dst0, dst_bit+i, bit_get_ptr(src0, src_bit+i));
}

static uint32_t rnd_u32(uint32_t *st) {
  /* simple LCG */
  *st = (*st * 1664525u) + 1013904223u;
  return *st;
}

static int run_case(const uint8_t *src_init, const uint8_t *dst_init,
                    uint8_t *src, uint8_t *dst,
                    size_t n_bits, size_t src_bit, size_t dst_bit,
                    int same_buf)
{
  memcpy(src, src_init, 64);
  memcpy(dst, dst_init, 64);

  uint8_t ref_dst[64];
  memcpy(ref_dst, dst, 64);

  /* run reference */
  if (same_buf) {
    /* same buffer: use dst as the shared buffer */
    memcpy(ref_dst, dst, 64);
    ref_bitcpy(n_bits, ref_dst, src_bit, ref_dst, dst_bit, 1);
    /* tested impl */
    bitcpy(n_bits, dst, src_bit, dst, dst_bit);
    if (memcmp(dst, ref_dst, 64) != 0) return 0;
    return 1;
  } else {
    ref_bitcpy(n_bits, src, src_bit, ref_dst, dst_bit, 0);
    bitcpy(n_bits, src, src_bit, dst, dst_bit);
    if (memcmp(dst, ref_dst, 64) != 0) return 0;
    return 1;
  }
}

int main(void) {
  uint8_t src_init[64], dst_init[64], src[64], dst[64];

  /* deterministic patterns */
  for (int i=0;i<64;i++) {
    src_init[i] = (uint8_t)(i*37u + 11u);
    dst_init[i] = (uint8_t)(~src_init[i]);
  }

  /* Edge cases near end-of-buffer (bounds safety) */
  {
    size_t bits = 64u*8u;
    if (!run_case(src_init, dst_init, src, dst, 1, bits-1, 0, 0)) {
      fprintf(stderr, "FAIL edge: copy 1 bit from last bit\n"); return 1;
    }
    if (!run_case(src_init, dst_init, src, dst, 8, bits-9, 3, 0)) {
      fprintf(stderr, "FAIL edge: copy 8 bits near end\n"); return 1;
    }
  }

  /* Randomized cases */
  uint32_t st = 1;
  size_t buf_bits = 64u * 8u;

  for (int it=0; it<5000; it++) {
    uint32_t r = rnd_u32(&st);
    size_t n = (size_t)(r % 256u); /* 0..255 bits */
    if (n == 0) n = 1;

    size_t src_bit = (size_t)(rnd_u32(&st) % (buf_bits - n + 1u));
    size_t dst_bit = (size_t)(rnd_u32(&st) % (buf_bits - n + 1u));

    int same = (rnd_u32(&st) & 1u) ? 1 : 0;

    if (!run_case(src_init, dst_init, src, dst, n, src_bit, dst_bit, same)) {
      fprintf(stderr, "FAIL it=%d same=%d n=%zu src_bit=%zu dst_bit=%zu\n", it, same, n, src_bit, dst_bit);
      return 1;
    }
  }

  printf("OK bitcpy_selftest\n");
  return 0;
}
C

# ---------------- scripts/tdd/test_bitcpy_selftest.sh ----------------
cat > scripts/tdd/test_bitcpy_selftest.sh <<'SH'
#!/bin/sh
set -eu
# file: scripts/tdd/test_bitcpy_selftest.sh
# date: 2026-05-05
# purpose: run bitcpy self-test tool

if [ ! -x build/bin/bitcpy_selftest ]; then
  make bins >/dev/null
fi

build/bin/bitcpy_selftest >/dev/null
echo "OK bitcpy selftest"
SH
chmod +x scripts/tdd/test_bitcpy_selftest.sh

# ---------------- add to scripts/tdd/run_all.sh ----------------
if grep -q 'test_bitcpy_selftest.sh' scripts/tdd/run_all.sh; then
  echo "OK: run_all.sh already contains bitcpy selftest" >&2
else
  # insert at the top of the list (after "for t in \")
  tmp="tmp/run_all_${ts}.sh"
  mkdir -p tmp
  awk '
    BEGIN{done=0}
    {
      print
      if (!done && $0 ~ /^for t in[[:space:]]*\\/) {
        print "  scripts/tdd/test_bitcpy_selftest.sh \\"
        done=1
      }
    }
    END{ if(!done) exit 2 }
  ' scripts/tdd/run_all.sh >"$tmp"
  mv "$tmp" scripts/tdd/run_all.sh
  chmod +x scripts/tdd/run_all.sh
  echo "OK: added bitcpy selftest to scripts/tdd/run_all.sh" >&2
fi

echo "DONE: rewrite bitcpy + add selftest (backups in $bakdir)" >&2
echo "Next: make test && make tdd" >&2
