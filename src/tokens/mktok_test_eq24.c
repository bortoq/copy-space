// mktok_test_eq24.c
// EQ24 test using 2a library word WORD_EQ24 and fixed operand/result vars.
// Output: 4 bytes at TESTG[0..3]: 0x80 if equal else 0x00
// Expected: 80 00 80 00

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
  fprintf(stderr, "ERROR: image missing required symbol: %s\n", what);
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

  uint64_t WORD_EQ24 = vm_read_uint(&vm, ART + 51*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_A24   = vm_read_uint(&vm, ART + 47*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_B24   = vm_read_uint(&vm, ART + 48*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t VAR_EQ    = vm_read_uint(&vm, ART + 52*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  if (!WORD_EQ24) die_missing("WORD_EQ24 (ART[51])");
  if (!VAR_A24)   die_missing("VAR_A24 (ART[47])");
  if (!VAR_B24)   die_missing("VAR_B24 (ART[48])");
  if (!VAR_EQ)    die_missing("VAR_EQ (ART[52])");

  FILE *f = fopen(out,"wb");
  if (!f) { perror("fopen"); vm_free(&vm); return 1; }

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

#define COPY1(dst_bitaddr, src_bitaddr) \
  do { \
    SETN(1); \
    SETDST((uint64_t)(dst_bitaddr)); \
    SETSRC((uint64_t)(src_bitaddr)); \
    DO_COPY(); \
  } while(0)

  struct pair { uint32_t A, B; } cases[4] = {
    { 0x000000u, 0x000000u },
    { 0x000001u, 0x000000u },
    { 0x123456u, 0x123456u },
    { 0x123456u, 0x123457u },
  };

  for (unsigned i=0; i<4; i++) {
    // Load operands
    SETN(1);
    SET24(VAR_A24, cases[i].A);
    SET24(VAR_B24, cases[i].B);

    // Call library word
    EMIT(WORD_EQ24);

    // Store result byte: clear then set bit0 from VAR_EQ
    uint64_t outb = (uint64_t)TESTG + (uint64_t)i*8u;
    CLRBYTE(outb);
    COPY1(outb + 0u, (uint64_t)VAR_EQ);
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