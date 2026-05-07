/* file: src/tokens/mktok_test_ptrprims_padding.c
 * date: 2026-05-07
 * purpose: todo B — verify ptrprims 24-bit semantics w.r.t. 32-bit block padding.
 *
 * Checks:
 *  - LOAD24AP reads only 24 bits and ignores padding byte [24..31].
 *  - STORE24RP writes only 24 bits and preserves padding byte [24..31].
 *
 * Layout:
 *  - Put 32-bit block at *AP: 12 34 56 BB  (padding=BB)
 *    Run LOAD24AP -> VAR_A24, then dump VAR_A24 (3 bytes) to TESTG.
 *  - Put 32-bit block at *RP: 00 00 00 AA  (padding=AA)
 *    Set VAR_SUM24 = AB CD EF, run STORE24RP, then dump 4 bytes from *RP to TESTG+3.
 *
 * Expected output at TESTG (7 bytes):
 *   12 34 56  AB CD EF AA
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

  /* 2a */
  uint64_t VAR_A24   = vm_read_uint(&vm, ART + 47*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_SUM24 = vm_read_uint(&vm, ART + 49*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* 2b pointers */
  uint64_t WORD_LITAP = vm_read_uint(&vm, ART + 55*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LITRP = vm_read_uint(&vm, ART + 57*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_AP     = vm_read_uint(&vm, ART + 58*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_RP     = vm_read_uint(&vm, ART + 60*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* ptrprims */
  uint64_t WORD_LOAD24AP  = vm_read_uint(&vm, ART + 67*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_STORE24RP = vm_read_uint(&vm, ART + 69*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  if (!LITN) die_missing("WORD_LITN (ART[28])");
  if (!LITD) die_missing("WORD_LITD (ART[29])");
  if (!LITS) die_missing("WORD_LITS (ART[30])");
  if (!COPY) die_missing("WORD_COPY (ART[31])");
  if (!HALT) die_missing("WORD_HALT (ART[7])");
  if (!C1) die_missing("CONST1 (ART[41])");
  if (!C0) die_missing("CONST0 (ART[42])");
  if (!TESTG) die_missing("TESTG (ART[43])");

  if (!VAR_A24) die_missing("VAR_A24 (ART[47])");
  if (!VAR_SUM24) die_missing("VAR_SUM24 (ART[49])");

  if (!WORD_LITAP) die_missing("WORD_LITAP (ART[55])");
  if (!WORD_LITRP) die_missing("WORD_LITRP (ART[57])");
  if (!VAR_AP)     die_missing("VAR_AP (ART[58])");
  if (!VAR_RP)     die_missing("VAR_RP (ART[60])");

  if (!WORD_LOAD24AP) die_missing("WORD_LOAD24AP (ART[67])");
  if (!WORD_STORE24RP) die_missing("WORD_STORE24RP (ART[69])");

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

  /* Use scratch area relative to TESTG, keep it aligned and far from output bytes. */
  const uint64_t A_base   = (uint64_t)TESTG + 256u*8u; /* 256 bytes after TESTG */
  const uint64_t RES_base = (uint64_t)TESTG + 320u*8u; /* 320 bytes after TESTG */

  /* Setup *AP block: 12 34 56 BB (padding=BB) */
  SETBYTE(A_base + 0u*8u, 0x12u);
  SETBYTE(A_base + 1u*8u, 0x34u);
  SETBYTE(A_base + 2u*8u, 0x56u);
  SETBYTE(A_base + 3u*8u, 0xBBu);

  /* VAR_AP = A_base */
  EMIT(WORD_LITAP);
  write_be(f, (uint64_t)A_base, nb);

  /* LOAD24AP -> VAR_A24; dump VAR_A24 (24 bits => 3 bytes) to TESTG[0..2] */
  EMIT(WORD_LOAD24AP);
  COPY_BITS(24u, (uint64_t)TESTG + 0u, (uint64_t)VAR_A24);

  /* Setup *RP block padding to AA, clear data bytes */
  SETBYTE(RES_base + 0u*8u, 0x00u);
  SETBYTE(RES_base + 1u*8u, 0x00u);
  SETBYTE(RES_base + 2u*8u, 0x00u);
  SETBYTE(RES_base + 3u*8u, 0xAAu);

  /* VAR_SUM24 = AB CD EF */
  SET24((uint64_t)VAR_SUM24, 0xABCDEFu);

  /* VAR_RP = RES_base; STORE24RP; dump 32 bits from *RP (4 bytes) to TESTG[3..6] */
  EMIT(WORD_LITRP);
  write_be(f, (uint64_t)RES_base, nb);

  EMIT(WORD_STORE24RP);

  COPY_BITS(32u, (uint64_t)TESTG + 24u, (uint64_t)RES_base);

  EMIT(HALT);

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
