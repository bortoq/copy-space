// mktok_test_add24.c
// ADD24 test using 2a library word WORD_ADD24 and fixed operand/result vars.
// Uses only: LITN/LITD/LITS/COPY + WORD_ADD24 + HALT.
// Writes the same 64-byte layout in TESTG as the previous unrolled test.
//
// Expected (same as scripts/test_all.sh):
// case0: 16x00
// case1: ffffff00 00000100 00000000 80000000
// case2: 12345600 01020300 13365900 00000000
// case3: 80000000 80000000 00000000 80000000

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
  fprintf(stderr, "ERROR: image missing required symbol (artifact entry 0): %s\n", what);
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

  uint64_t LITN = vm_read_uint(&vm, ART + 28*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITD = vm_read_uint(&vm, ART + 29*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t LITS = vm_read_uint(&vm, ART + 30*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t COPY = vm_read_uint(&vm, ART + 31*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t HALT = vm_read_uint(&vm, ART + 7 *(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t CONST1= vm_read_uint(&vm, ART + 41*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t CONST0= vm_read_uint(&vm, ART + 42*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t TESTG = vm_read_uint(&vm, ART + 43*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  // New 2a entries
  uint64_t WORD_ADD24 = vm_read_uint(&vm, ART + 46*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_A24    = vm_read_uint(&vm, ART + 47*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_B24    = vm_read_uint(&vm, ART + 48*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_SUM24  = vm_read_uint(&vm, ART + 49*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_COUT   = vm_read_uint(&vm, ART + 50*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  if (!WORD_ADD24) die_missing("WORD_ADD24 (ART[46])");
  if (!VAR_A24)    die_missing("VAR_A24 (ART[47])");
  if (!VAR_B24)    die_missing("VAR_B24 (ART[48])");
  if (!VAR_SUM24)  die_missing("VAR_SUM24 (ART[49])");
  if (!VAR_COUT)   die_missing("VAR_COUT (ART[50])");

  FILE *f = fopen(out,"wb");
  if (!f) { perror("fopen"); vm_free(&vm); return 1; }

  // Emit helpers
#define EMIT(tok) do { write_be(f, (uint64_t)(tok), nb); } while(0)
#define LIT(word, imm) do { EMIT(word); write_be(f, (uint64_t)(imm), nb); } while(0)

  // Set VAR_N = n
#define SETN(n) do { LIT(LITN, (uint64_t)(n)); } while(0)

  // Set VAR_DST = dst, VAR_SRC = src
#define SETDST(dst) do { LIT(LITD, (uint64_t)(dst)); } while(0)
#define SETSRC(src) do { LIT(LITS, (uint64_t)(src)); } while(0)

  // COPY using current VAR_N/VAR_DST/VAR_SRC
#define DO_COPY() do { EMIT(COPY); } while(0)

  // Clear one byte at byte_bitaddr using CONST0 (8 bits)
#define CLRBYTE(byte_bitaddr) \
  do { \
    SETN(8); \
    SETDST((uint64_t)(byte_bitaddr)); \
    SETSRC((uint64_t)(CONST0)); \
    DO_COPY(); \
  } while(0)

  // Set a single bit at dst_bitaddr to 0/1 using CONST0/CONST1 (requires N=1)
#define SETBIT(dst_bitaddr, val01) \
  do { \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)((val01) ? CONST1 : CONST0)); \
    DO_COPY(); \
  } while(0)

  // Set a byte value bitwise (requires N=1)
#define SETBYTE(byte_bitaddr, u8val) \
  do { \
    for (unsigned off=0; off<8; off++) { \
      unsigned bit = ((unsigned)(u8val) >> (7u-off)) & 1u; \
      SETBIT((uint64_t)(byte_bitaddr) + (uint64_t)off, bit); \
    } \
  } while(0)

  // Set 24-bit big-endian at base_bitaddr (requires N=1)
#define SET24(base_bitaddr, u24) \
  do { \
    SETBYTE((uint64_t)(base_bitaddr) + 0u*8u, (uint8_t)(((u24) >> 16) & 0xFFu)); \
    SETBYTE((uint64_t)(base_bitaddr) + 1u*8u, (uint8_t)(((u24) >>  8) & 0xFFu)); \
    SETBYTE((uint64_t)(base_bitaddr) + 2u*8u, (uint8_t)(((u24) >>  0) & 0xFFu)); \
  } while(0)

  // Copy 24 bits: dst <- src
#define COPY24(dst_bitaddr, src_bitaddr) \
  do { \
    SETN(24); \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)(src_bitaddr)); \
    DO_COPY(); \
  } while(0)

  // Copy 1 bit: dst <- src
#define COPY1(dst_bitaddr, src_bitaddr) \
  do { \
    SETN(1); \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)(src_bitaddr)); \
    DO_COPY(); \
  } while(0)

  // Clear 64 bytes at TESTG
  for (unsigned j=0; j<64; j++) {
    CLRBYTE((uint64_t)TESTG + (uint64_t)j*8u);
  }

  // Each case occupies 16 bytes at TESTG.
  // Layout inside case:
  // +0..2 : A (24 bits)
  // +4..6 : B
  // +8..10: SUM
  // +12   : COUT in bit0 (0x80)
  struct case24 { uint32_t A, B; } cases[4] = {
    { 0x000000u, 0x000000u },
    { 0xFFFFFFu, 0x000001u },
    { 0x123456u, 0x010203u },
    { 0x800000u, 0x800000u },
  };

  // Compute each case using WORD_ADD24 and export results to TESTG layout.
  for (unsigned k=0; k<4; k++) {
    uint64_t base = (uint64_t)TESTG + (uint64_t)k*16u*8u;

    // Load operands into VAR_A24/VAR_B24 (bitwise)
    SETN(1);
    SET24(VAR_A24, cases[k].A);
    SET24(VAR_B24, cases[k].B);

    // Copy operands into output layout (so expected dump matches)
    COPY24(base + 0u*8u, VAR_A24);
    COPY24(base + 4u*8u, VAR_B24);

    // Call library word
    EMIT(WORD_ADD24);

    // Export SUM
    COPY24(base + 8u*8u, (uint64_t)VAR_SUM24);

    // Export COUT into byte12 bit0 (0x80)
    // (byte already cleared)
    COPY1(base + 12u*8u + 0u, (uint64_t)VAR_COUT);
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

  fclose(f);
  fprintf(stderr, "TESTG(byte)=%llu\n", (unsigned long long)(TESTG >> 3));
  vm_free(&vm);
  return 0;
}