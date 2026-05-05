#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_ptr_arith_macros"
mkdir -p "$bakdir"

need_file() { [ -f "$1" ] || { echo "FAIL: missing $1" >&2; exit 1; }; }
backup() { cp -a "$1" "$bakdir/$(echo "$1" | tr '/ ' '__')"; }

[ -d src ] && [ -d scripts ] || { echo "FAIL: run from project root" >&2; exit 1; }

F_ADD="src/tokens/mktok_test_add24p_via_prims.c"
F_LT="src/tokens/mktok_test_lt24p_via_prims.c"
need_file "$F_ADD"
need_file "$F_LT"

backup "$F_ADD"
backup "$F_LT"

cat >"$F_ADD" <<'EOF'
/* file: src/tokens/mktok_test_add24p_via_prims.c
 * date: 2026-05-05
 * purpose: todo B — ADD24 via block-pointer primitives + pointer arithmetic macros (AP/BP/RP += 32)
 * layout/output matches mktok_test_add24.c expected by scripts/test_all.sh
 *
 * Expected (same as scripts/test_all.sh):
 * case0: 16x00
 * case1: ffffff00 00000100 00000000 80000000
 * case2: 12345600 01020300 13365900 00000000
 * case3: 80000000 80000000 00000000 80000000
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

  /* core words */
  uint64_t LITN  = vm_read_uint(&vm, ART + 28*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITD  = vm_read_uint(&vm, ART + 29*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITS  = vm_read_uint(&vm, ART + 30*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t COPY  = vm_read_uint(&vm, ART + 31*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t HALT  = vm_read_uint(&vm, ART + 7 *(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t CONST1 = vm_read_uint(&vm, ART + 41*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t CONST0 = vm_read_uint(&vm, ART + 42*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t TESTG  = vm_read_uint(&vm, ART + 43*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* 2a */
  uint64_t WORD_ADD24 = vm_read_uint(&vm, ART + 46*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_A24    = vm_read_uint(&vm, ART + 47*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_B24    = vm_read_uint(&vm, ART + 48*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_SUM24  = vm_read_uint(&vm, ART + 49*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_COUT   = vm_read_uint(&vm, ART + 50*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* 2b pointers */
  uint64_t WORD_LITAP = vm_read_uint(&vm, ART + 55*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LITBP = vm_read_uint(&vm, ART + 56*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LITRP = vm_read_uint(&vm, ART + 57*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_AP     = vm_read_uint(&vm, ART + 58*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_BP     = vm_read_uint(&vm, ART + 59*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_RP     = vm_read_uint(&vm, ART + 60*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* block-pointer primitives */
  uint64_t WORD_LOAD24AP  = vm_read_uint(&vm, ART + 67*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LOAD24BP  = vm_read_uint(&vm, ART + 68*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_STORE24RP = vm_read_uint(&vm, ART + 69*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* checks */
  if (!WORD_ADD24) die_missing("WORD_ADD24 (ART[46])");
  if (!VAR_A24)    die_missing("VAR_A24 (ART[47])");
  if (!VAR_B24)    die_missing("VAR_B24 (ART[48])");
  if (!VAR_SUM24)  die_missing("VAR_SUM24 (ART[49])");
  if (!VAR_COUT)   die_missing("VAR_COUT (ART[50])");
  if (!WORD_LITAP) die_missing("WORD_LITAP (ART[55])");
  if (!WORD_LITBP) die_missing("WORD_LITBP (ART[56])");
  if (!WORD_LITRP) die_missing("WORD_LITRP (ART[57])");
  if (!VAR_AP)     die_missing("VAR_AP (ART[58])");
  if (!VAR_BP)     die_missing("VAR_BP (ART[59])");
  if (!VAR_RP)     die_missing("VAR_RP (ART[60])");
  if (!WORD_LOAD24AP)  die_missing("WORD_LOAD24AP (ART[67])");
  if (!WORD_LOAD24BP)  die_missing("WORD_LOAD24BP (ART[68])");
  if (!WORD_STORE24RP) die_missing("WORD_STORE24RP (ART[69])");

  FILE *f = fopen(out,"wb");
  if (!f) { perror("fopen"); vm_free(&vm); return 1; }

  /* helpers */
#define EMIT(tok) do { write_be(f, (uint64_t)(tok), nb); } while(0)
#define LIT(word, imm) do { EMIT(word); write_be(f, (uint64_t)(imm), nb); } while(0)
#define SETN(n)  do { LIT(LITN, (uint64_t)(n)); } while(0)
#define SETDST(d) do { LIT(LITD, (uint64_t)(d)); } while(0)
#define SETSRC(s) do { LIT(LITS, (uint64_t)(s)); } while(0)
#define DO_COPY() do { EMIT(COPY); } while(0)

#define CLRBYTE(byte_bitaddr) \
  do { \
    SETN(8); \
    SETDST((uint64_t)(byte_bitaddr)); \
    SETSRC((uint64_t)(CONST0)); \
    DO_COPY(); \
  } while(0)

#define SETBIT(dst_bitaddr, val01) \
  do { \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)((val01) ? CONST1 : CONST0)); \
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
    SETBYTE((uint64_t)(base_bitaddr) + 0u*8u, (uint8_t)(((u24) >> 16) & 0xFFu)); \
    SETBYTE((uint64_t)(base_bitaddr) + 1u*8u, (uint8_t)(((u24) >>  8) & 0xFFu)); \
    SETBYTE((uint64_t)(base_bitaddr) + 2u*8u, (uint8_t)(((u24) >>  0) & 0xFFu)); \
  } while(0)

#define COPY24(dst_bitaddr, src_bitaddr) \
  do { \
    SETN(24); \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)(src_bitaddr)); \
    DO_COPY(); \
  } while(0)

#define COPY1(dst_bitaddr, src_bitaddr) \
  do { \
    SETN(1); \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)(src_bitaddr)); \
    DO_COPY(); \
  } while(0)

/* pointer arithmetic macro: ptrvar += 32 (bitaddr) */
#define INC_PTR32(ptrvar_bitaddr) \
  do { \
    /* B24 = 32 */ \
    SETN(1); \
    SET24((uint64_t)VAR_B24, 0x000020u); \
    SETBYTE((uint64_t)VAR_B24 + 3u*8u, 0); /* padding */ \
    /* A24 = ptrvar */ \
    SETN((uint64_t)vm.addr_bits); \
    SETDST((uint64_t)VAR_A24); \
    SETSRC((uint64_t)(ptrvar_bitaddr)); \
    DO_COPY(); \
    /* SUM24 = A24 + B24 */ \
    EMIT(WORD_ADD24); \
    /* ptrvar = SUM24 */ \
    SETN((uint64_t)vm.addr_bits); \
    SETDST((uint64_t)(ptrvar_bitaddr)); \
    SETSRC((uint64_t)VAR_SUM24); \
    DO_COPY(); \
  } while(0)

  /* clear TESTG */
  for (unsigned j=0; j<64; j++) {
    CLRBYTE((uint64_t)TESTG + (uint64_t)j*8u);
  }

  /* arrays layout: A[4], B[4], RES[4], each element is 4 bytes (32 bits) */
  uint64_t testg_byte = (uint64_t)(TESTG >> 3);
  uint64_t op_byte = (testg_byte + 64u + 3u) & ~3ull; /* align 4 */
  uint64_t OPBASE = op_byte << 3;

  uint64_t A_base   = OPBASE;
  uint64_t B_base   = A_base + 4u*4u*8u;
  uint64_t RES_base = B_base + 4u*4u*8u;

  struct case24 { uint32_t A, B; } cases[4] = {
    { 0x000000u, 0x000000u },
    { 0xFFFFFFu, 0x000001u },
    { 0x123456u, 0x010203u },
    { 0x800000u, 0x800000u },
  };

  /* prefill operands and clear RES */
  SETN(1);
  for (unsigned k=0; k<4; k++) {
    uint64_t Aaddr   = A_base   + (uint64_t)k*32u;
    uint64_t Baddr   = B_base   + (uint64_t)k*32u;
    uint64_t RESaddr = RES_base + (uint64_t)k*32u;

    SET24(Aaddr, cases[k].A);
    SET24(Baddr, cases[k].B);
    SET24(RESaddr, 0x000000u);

    /* define padding bytes */
    SETBYTE(Aaddr + 3u*8u, 0);
    SETBYTE(Baddr + 3u*8u, 0);
    SETBYTE(RESaddr + 3u*8u, 0);
  }

  /* set pointers once */
  EMIT(WORD_LITAP); write_be(f, (uint64_t)A_base,   nb);
  EMIT(WORD_LITBP); write_be(f, (uint64_t)B_base,   nb);
  EMIT(WORD_LITRP); write_be(f, (uint64_t)RES_base, nb);

  /* run cases using pointer arithmetic */
  for (unsigned k=0; k<4; k++) {
    uint64_t Aaddr   = A_base   + (uint64_t)k*32u;
    uint64_t Baddr   = B_base   + (uint64_t)k*32u;
    uint64_t RESaddr = RES_base + (uint64_t)k*32u;

    EMIT(WORD_LOAD24AP);
    EMIT(WORD_LOAD24BP);
    EMIT(WORD_ADD24);
    EMIT(WORD_STORE24RP);

    /* export result to TESTG layout (same as mktok_test_add24.c) */
    uint64_t base_out = (uint64_t)TESTG + (uint64_t)k*16u*8u;
    COPY24(base_out + 0u*8u, Aaddr);
    COPY24(base_out + 4u*8u, Baddr);

    /* IMPORTANT: verify STORE24RP by reading SUM from *RP (RESaddr) */
    COPY24(base_out + 8u*8u, RESaddr);

    COPY1 (base_out + 12u*8u + 0u, (uint64_t)VAR_COUT);

    /* advance pointers to next elements */
    if (k + 1u < 4u) {
      INC_PTR32((uint64_t)VAR_AP);
      INC_PTR32((uint64_t)VAR_BP);
      INC_PTR32((uint64_t)VAR_RP);
    }
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
#undef COPY24
#undef COPY1
#undef INC_PTR32

  fclose(f);
  fprintf(stderr, "TESTG(byte)=%llu\n", (unsigned long long)(TESTG >> 3));
  vm_free(&vm);
  return 0;
}
EOF

cat >"$F_LT" <<'EOF'
/* file: src/tokens/mktok_test_lt24p_via_prims.c
 * date: 2026-05-05
 * purpose: todo B — LT24 via block-pointer primitives + pointer arithmetic macros (AP/BP += 32)
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
  uint64_t VAR_AP     = vm_read_uint(&vm, ART + 58*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_BP     = vm_read_uint(&vm, ART + 59*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t WORD_LOAD24AP = vm_read_uint(&vm, ART + 67*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t WORD_LOAD24BP = vm_read_uint(&vm, ART + 68*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t WORD_LT24 = vm_read_uint(&vm, ART + 53*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_LT    = vm_read_uint(&vm, ART + 54*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  /* 2a vars used by INC_PTR32 */
  uint64_t WORD_ADD24 = vm_read_uint(&vm, ART + 46*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_A24    = vm_read_uint(&vm, ART + 47*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_B24    = vm_read_uint(&vm, ART + 48*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_SUM24  = vm_read_uint(&vm, ART + 49*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  if (!WORD_LITAP) die_missing("WORD_LITAP (ART[55])");
  if (!WORD_LITBP) die_missing("WORD_LITBP (ART[56])");
  if (!VAR_AP)     die_missing("VAR_AP (ART[58])");
  if (!VAR_BP)     die_missing("VAR_BP (ART[59])");
  if (!WORD_LOAD24AP) die_missing("WORD_LOAD24AP (ART[67])");
  if (!WORD_LOAD24BP) die_missing("WORD_LOAD24BP (ART[68])");
  if (!WORD_LT24) die_missing("WORD_LT24 (ART[53])");
  if (!VAR_LT)    die_missing("VAR_LT (ART[54])");
  if (!WORD_ADD24) die_missing("WORD_ADD24 (ART[46])");
  if (!VAR_A24) die_missing("VAR_A24 (ART[47])");
  if (!VAR_B24) die_missing("VAR_B24 (ART[48])");
  if (!VAR_SUM24) die_missing("VAR_SUM24 (ART[49])");

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

#define INC_PTR32(ptrvar_bitaddr) \
  do { \
    /* B24 = 32 */ \
    SETN(1); \
    SET24((uint64_t)VAR_B24, 0x000020u); \
    SETBYTE((uint64_t)VAR_B24 + 3u*8u, 0); \
    /* A24 = ptrvar */ \
    SETN((uint64_t)vm.addr_bits); \
    SETDST((uint64_t)VAR_A24); \
    SETSRC((uint64_t)(ptrvar_bitaddr)); \
    DO_COPY(); \
    EMIT(WORD_ADD24); \
    SETN((uint64_t)vm.addr_bits); \
    SETDST((uint64_t)(ptrvar_bitaddr)); \
    SETSRC((uint64_t)VAR_SUM24); \
    DO_COPY(); \
  } while(0)

  /* clear output bytes */
  for (unsigned i=0; i<4; i++) CLRBYTE(TESTG + (uint64_t)i*8u);

  /* arrays layout: A[4], B[4], element is 4 bytes (32 bits), stored right after output area */
  uint64_t testg_byte = (uint64_t)(TESTG >> 3);
  uint64_t op_byte = (testg_byte + 16u + 3u) & ~3ull; /* align to 4 bytes */
  uint64_t OPBASE = op_byte << 3;

  uint64_t A_base = OPBASE;
  uint64_t B_base = A_base + 4u*4u*8u;

  struct pair { uint32_t A,B; } cases[4] = {
    {0x000000u, 0x000000u},
    {0x000001u, 0x000000u},
    {0x123456u, 0x123457u},
    {0xFFFFFFu, 0x000001u},
  };

  SETN(1);
  for (unsigned i=0; i<4; i++) {
    uint64_t Aaddr = A_base + (uint64_t)i*32u;
    uint64_t Baddr = B_base + (uint64_t)i*32u;

    SET24(Aaddr, cases[i].A);
    SET24(Baddr, cases[i].B);
    SETBYTE(Aaddr + 3u*8u, 0);
    SETBYTE(Baddr + 3u*8u, 0);
  }

  /* set pointers once */
  EMIT(WORD_LITAP); write_be(f, (uint64_t)A_base, nb);
  EMIT(WORD_LITBP); write_be(f, (uint64_t)B_base, nb);

  for (unsigned i=0; i<4; i++) {
    /* load operands by pointers + compare */
    EMIT(WORD_LOAD24AP);
    EMIT(WORD_LOAD24BP);
    EMIT(WORD_LT24);

    /* export result bit into output byte bit0 (0x80) */
    COPY1(TESTG + (uint64_t)i*8u + 0u, VAR_LT);

    if (i + 1u < 4u) {
      INC_PTR32((uint64_t)VAR_AP);
      INC_PTR32((uint64_t)VAR_BP);
    }
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
#undef INC_PTR32

  fclose(f);
  fprintf(stderr, "TESTG(byte)=%llu\n", (unsigned long long)(TESTG >> 3));
  vm_free(&vm);
  return 0;
}
EOF

echo "DONE. Backups: $bakdir"
echo "Next: make test && scripts/test_all.sh"
