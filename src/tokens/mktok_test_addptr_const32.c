/* file: src/tokens/mktok_test_addptr_const32.c
 * date: 2026-05-07
 * purpose: todo B — explicit derived ADD_PTR_CONST32 for block pointers, without new ART.
 *
 * We implement:
 *   ptr += (k * 32)  via existing 2a ADD24 over 24-bit bitaddr.
 *
 * Output 9 bytes at TESTG:
 *   [0..2] start AP
 *   [3..5] AP after +0x20  (k=1)
 *   [6..8] AP after +0xE0  (k=7)  (cumulative: start + 0x100)
 *
 * With start=0x00FFE0:
 *   0x00FFE0, 0x010000, 0x0100E0
 */

#include "space.h"
#include <stdio.h>
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

  if (vm.addr_bits != 24u) {
    fprintf(stderr, "ERROR: this test assumes addr_bits=24 (got %u)\n", vm.addr_bits);
    vm_free(&vm);
    return 1;
  }

  bitaddr_t ART = (vm.workspace_base + 512u + 7u) & ~(bitaddr_t)7u;
  unsigned nb = vm.addr_bits/8u;

  /* core */
  uint64_t LITN  = vm_read_uint(&vm, ART + 28*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITD  = vm_read_uint(&vm, ART + 29*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITS  = vm_read_uint(&vm, ART + 30*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t COPY  = vm_read_uint(&vm, ART + 31*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t HALT  = vm_read_uint(&vm, ART + 7 *(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t C1    = vm_read_uint(&vm, ART + 41*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t C0    = vm_read_uint(&vm, ART + 42*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t TESTG = vm_read_uint(&vm, ART + 43*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* 2b pointer */
  uint64_t WORD_LITAP = vm_read_uint(&vm, ART + 55*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_AP     = vm_read_uint(&vm, ART + 58*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* 2a for implementing derived pointer arithmetic */
  uint64_t WORD_ADD24 = vm_read_uint(&vm, ART + 46*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_A24    = vm_read_uint(&vm, ART + 47*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_B24    = vm_read_uint(&vm, ART + 48*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_SUM24  = vm_read_uint(&vm, ART + 49*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  if (!LITN) die_missing("WORD_LITN (ART[28])");
  if (!LITD) die_missing("WORD_LITD (ART[29])");
  if (!LITS) die_missing("WORD_LITS (ART[30])");
  if (!COPY) die_missing("WORD_COPY (ART[31])");
  if (!HALT) die_missing("WORD_HALT (ART[7])");
  if (!C1) die_missing("CONST1 (ART[41])");
  if (!C0) die_missing("CONST0 (ART[42])");
  if (!TESTG) die_missing("TESTG (ART[43])");

  if (!WORD_LITAP) die_missing("WORD_LITAP (ART[55])");
  if (!VAR_AP)     die_missing("VAR_AP (ART[58])");

  if (!WORD_ADD24) die_missing("WORD_ADD24 (ART[46])");
  if (!VAR_A24)    die_missing("VAR_A24 (ART[47])");
  if (!VAR_B24)    die_missing("VAR_B24 (ART[48])");
  if (!VAR_SUM24)  die_missing("VAR_SUM24 (ART[49])");

  /* report TESTG byte offset for bash harness */
  fprintf(stderr, "TESTG(byte)=%u\n", (unsigned)(TESTG / 8u));

  FILE *f = fopen(out,"wb");
  if (!f) { perror("fopen"); vm_free(&vm); return 1; }

#define EMIT(tok) do { write_be(f, (uint64_t)(tok), nb); } while(0)
#define LIT(word, imm) do { EMIT(word); write_be(f, (uint64_t)(imm), nb); } while(0)

#define SETN(n)    do { LIT(LITN,  (uint64_t)(n)); } while(0)
#define SETDST(d)  do { LIT(LITD,  (uint64_t)(d)); } while(0)
#define SETSRC(s)  do { LIT(LITS,  (uint64_t)(s)); } while(0)
#define DO_COPY()  do { EMIT(COPY); } while(0)

#define COPY_BITS(n, dst, src) \
  do { \
    SETN((n)); \
    SETDST((uint64_t)(dst)); \
    SETSRC((uint64_t)(src)); \
    DO_COPY(); \
  } while(0)

#define SETBIT(dst_bitaddr, val01) \
  do { \
    SETN(1u); \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)((val01) ? C1 : C0)); \
    DO_COPY(); \
  } while(0)

#define CLRBYTE(byte_bitaddr) \
  do { \
    SETN(8u); \
    SETDST((uint64_t)(byte_bitaddr)); \
    SETSRC((uint64_t)C0); \
    DO_COPY(); \
  } while(0)

#define SETBYTE(byte_bitaddr, u8val) \
  do { \
    CLRBYTE((byte_bitaddr)); \
    for (unsigned off=0; off<8u; off++) { \
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

#define ADD_PTR_CONST32(ptrvar_bitaddr, k_u32) \
  do { \
    uint32_t delta = ((uint32_t)(k_u32) << 5); /* k blocks => k*32 bits */ \
    COPY_BITS(24u, (uint64_t)VAR_A24, (uint64_t)(ptrvar_bitaddr)); \
    SET24((uint64_t)VAR_B24, delta); \
    EMIT(WORD_ADD24); \
    COPY_BITS(24u, (uint64_t)(ptrvar_bitaddr), (uint64_t)VAR_SUM24); \
  } while(0)

  const uint64_t AP0 = 0x00FFE0u;

  /* VAR_AP = AP0 */
  EMIT(WORD_LITAP);
  write_be(f, AP0, nb);

  /* dump start */
  COPY_BITS(24u, (uint64_t)TESTG + 0u,  (uint64_t)VAR_AP);

  /* +1 block (0x20) */
  ADD_PTR_CONST32((uint64_t)VAR_AP, 1u);
  COPY_BITS(24u, (uint64_t)TESTG + 24u, (uint64_t)VAR_AP);

  /* +7 blocks (0xE0) */
  ADD_PTR_CONST32((uint64_t)VAR_AP, 7u);
  COPY_BITS(24u, (uint64_t)TESTG + 48u, (uint64_t)VAR_AP);

  EMIT(HALT);

#undef ADD_PTR_CONST32
#undef SET24
#undef SETBYTE
#undef CLRBYTE
#undef SETBIT
#undef COPY_BITS
#undef DO_COPY
#undef SETSRC
#undef SETDST
#undef SETN
#undef LIT
#undef EMIT

  fclose(f);
  vm_free(&vm);
  return 0;
}
