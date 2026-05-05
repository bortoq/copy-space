#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_lt24p_test"
mkdir -p "$bakdir"

[ -d src ] && [ -d scripts ] || { echo "FAIL: run from project root" >&2; exit 1; }

TEST_FILE="src/tokens/mktok_test_lt24p_via_prims.c"
if [ -f "$TEST_FILE" ]; then
  echo "SKIP: $TEST_FILE already exists"
  exit 0
fi

cat >"$TEST_FILE" <<'EOF'
/* file: src/tokens/mktok_test_lt24p_via_prims.c
 * date: 2026-05-05
 * purpose: todo B — LT24 via block-pointer primitives (LOAD24AP/LOAD24BP + LT24)
 *
 * Output 4 bytes at TESTG[0..3]: 0x80 if (A<B) else 0x00
 * Cases:
 *  0: 0 < 0        => 0x00
 *  1: 1 < 0        => 0x00
 *  2: 0x123456 < 0x123457 => 0x80
 *  3: 0xFFFFFF < 0x000001 => 0x00
 */

#include "space.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static int load_image(vm_t *vm, const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { perror("fopen"); return -1; }
  if (fseek(f, 0, SEEK_END) != 0) { perror("fseek"); fclose(f); return -1; }
  long sz = ftell(f);
  if (sz < 0) { perror("ftell"); fclose(f); return -1; }
  rewind(f);
  if ((size_t)sz != vm->space_bytes) { fprintf(stderr,"size mismatch\n"); fclose(f); return -1; }
  if (fread(vm->space, 1, vm->space_bytes, f) != vm->space_bytes) { perror("fread"); fclose(f); return -1; }
  fclose(f);
  return 0;
}

static void write_be(FILE *f, uint64_t v, unsigned nbytes) {
  for (unsigned i=0; i<nbytes; i++) {
    unsigned shift = 8u*(nbytes-1u-i);
    fputc((int)((v >> shift) & 0xFFu), f);
  }
}

static void die_missing(const char *what) {
  fprintf(stderr, "ERROR: image missing required symbol (artifact entry): %s\n", what);
  exit(1);
}

static void usage(const char *a0) {
  fprintf(stderr, "usage: %s --image std.bin --out tok.bin\n", a0);
}

int main(int argc, char **argv) {
  const char *img=NULL, *out=NULL;
  for (int i=1; i<argc; i++) {
    if (!strcmp(argv[i],"--image") && i+1<argc) img=argv[++i];
    else if (!strcmp(argv[i],"--out") && i+1<argc) out=argv[++i];
    else { usage(argv[0]); return 2; }
  }
  if (!img || !out) { usage(argv[0]); return 2; }

  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 1;
  if (load_image(&vm, img) != 0) { vm_free(&vm); return 1; }

  bitaddr_t ART = (vm.workspace_base + 512u + 7u) & ~(bitaddr_t)7u;
  unsigned nb = vm.addr_bits/8u;

  uint64_t LITN  = vm_read_uint(&vm, ART + 28*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITD  = vm_read_uint(&vm, ART + 29*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITS  = vm_read_uint(&vm, ART + 30*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t COPY  = vm_read_uint(&vm, ART + 31*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t HALT  = vm_read_uint(&vm, ART + 7 *(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t C1    = vm_read_uint(&vm, ART + 41*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t C0    = vm_read_uint(&vm, ART + 42*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t TESTG = vm_read_uint(&vm, ART + 43*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t WORD_LITAP = vm_read_uint(&vm, ART + 55*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LITBP = vm_read_uint(&vm, ART + 56*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LOAD24AP = vm_read_uint(&vm, ART + 67*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LOAD24BP = vm_read_uint(&vm, ART + 68*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t WORD_LT24 = vm_read_uint(&vm, ART + 53*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_LT    = vm_read_uint(&vm, ART + 54*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  if (!WORD_LITAP) die_missing("WORD_LITAP (ART[55])");
  if (!WORD_LITBP) die_missing("WORD_LITBP (ART[56])");
  if (!WORD_LOAD24AP) die_missing("WORD_LOAD24AP (ART[67])");
  if (!WORD_LOAD24BP) die_missing("WORD_LOAD24BP (ART[68])");
  if (!WORD_LT24) die_missing("WORD_LT24 (ART[53])");
  if (!VAR_LT)    die_missing("VAR_LT (ART[54])");

  FILE *f = fopen(out,"wb");
  if (!f) { perror("fopen"); vm_free(&vm); return 1; }

#define EMIT(tok) do { write_be(f, (uint64_t)(tok), nb); } while(0)

#define LIT(word, imm) do { EMIT(word); write_be(f, (uint64_t)(imm), nb); } while(0)
#define SETN(n)   do { LIT(LITN, (uint64_t)(n)); } while(0)
#define SETDST(d) do { LIT(LITD, (uint64_t)(d)); } while(0)
#define SETSRC(s) do { LIT(LITS, (uint64_t)(s)); } while(0)
#define DO_COPY() do { EMIT(COPY); } while(0)

#define CLRBYTE(byte_bitaddr) \
  do { \
    SETN(8); \
    SETDST((uint64_t)(byte_bitaddr)); \
    SETSRC((uint64_t)C0); \
    DO_COPY(); \
  } while(0)

#define SETBIT(dst_bitaddr, val01) \
  do { \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)((val01) ? C1 : C0)); \
    DO_COPY(); \
  } while(0)

#define SETBYTE(byte_bitaddr, u8val) \
  do { \
    for (unsigned off=0; off<8; off++) { \
      unsigned bit = ((unsigned)(u8val) >> (7u-off)) & 1u; \
      SETBIT((uint64_t)(byte_bitaddr) + (uint64_t)off, bit); \
    } \
  } while(0)

#define SET24(base_bitaddr, u24) \
  do { \
    SETBYTE((uint64_t)(base_bitaddr) + 0u*8u, (uint8_t)(((u24)>>16)&0xFFu)); \
    SETBYTE((uint64_t)(base_bitaddr) + 1u*8u, (uint8_t)(((u24)>> 8)&0xFFu)); \
    SETBYTE((uint64_t)(base_bitaddr) + 2u*8u, (uint8_t)(((u24)>> 0)&0xFFu)); \
  } while(0)

#define COPY1(dst_bitaddr, src_bitaddr) \
  do { \
    SETN(1); \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)(src_bitaddr)); \
    DO_COPY(); \
  } while(0)

  /* clear output bytes */
  for (unsigned i=0; i<4; i++) CLRBYTE(TESTG + (uint64_t)i*8u);

  /* allocate 32-bit aligned operand blocks near TESTG */
  uint64_t testg_byte = (uint64_t)(TESTG >> 3);
  uint64_t op_byte = (testg_byte + 16u + 3u) & ~3ull; /* align to 4 bytes */
  uint64_t OPBASE = op_byte << 3;
  uint64_t STRIDE = 8u*8u; /* A(4B) + B(4B) */

  struct pair { uint32_t A,B; } cases[4] = {
    {0x000000u, 0x000000u},
    {0x000001u, 0x000000u},
    {0x123456u, 0x123457u},
    {0xFFFFFFu, 0x000001u},
  };

  /* set N=1 for bitwise writes */
  SETN(1);

  for (unsigned i=0; i<4; i++) {
    uint64_t Aaddr = OPBASE + (uint64_t)i*STRIDE + 0u;
    uint64_t Baddr = OPBASE + (uint64_t)i*STRIDE + 4u*8u;

    /* define padding bytes */
    SETBYTE(Aaddr + 3u*8u, 0);
    SETBYTE(Baddr + 3u*8u, 0);

    SET24(Aaddr, cases[i].A);
    SET24(Baddr, cases[i].B);

    /* set pointers */
    EMIT(WORD_LITAP); write_be(f, (uint64_t)Aaddr, nb);
    EMIT(WORD_LITBP); write_be(f, (uint64_t)Baddr, nb);

    /* load operands by pointers + compare */
    EMIT(WORD_LOAD24AP);
    EMIT(WORD_LOAD24BP);
    EMIT(WORD_LT24);

    /* export result bit into output byte bit0 (0x80) */
    COPY1(TESTG + (uint64_t)i*8u + 0u, VAR_LT);
  }

  EMIT(HALT);

#undef EMIT
#undef LIT
#undef SETN
#undef SETDST
#undef SETSRC
#undef DO_COPY
#undef CLRBYTE
#undef SETBIT
#undef SETBYTE
#undef SET24
#undef COPY1

  fclose(f);
  fprintf(stderr, "TESTG(byte)=%llu\n", (unsigned long long)(TESTG >> 3));
  vm_free(&vm);
  return 0;
}
EOF

echo "OK: created $TEST_FILE"
echo "Next: make test && scripts/test_all.sh"
