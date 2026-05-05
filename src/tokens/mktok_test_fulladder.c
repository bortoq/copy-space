// mktok_test_fulladder.c
// Full-adder truth table using existing words: BXOR, BAND, BOR and bit regs BA,BB,BC,BR,T0,T1.
// Writes 8 bytes at TESTG:
//   bit0 (0x80) = SUM
//   bit1 (0x40) = COUT
//
// Order of cases: A,B,Cin = 000,001,010,011,100,101,110,111

#include "space.h"
#include <stdlib.h>
#include <string.h>

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

static void usage(const char *a0) {
  fprintf(stderr, "usage: %s --image std7.bin --out tok.bin\n", a0);
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

  uint64_t BAND = vm_read_uint(&vm, ART + 40*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t BOR  = vm_read_uint(&vm, ART + 44*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t BXOR = vm_read_uint(&vm, ART + 45*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t HALT = vm_read_uint(&vm, ART + 7 *(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t BA   = vm_read_uint(&vm, ART + 33*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t BB   = vm_read_uint(&vm, ART + 34*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t BC   = vm_read_uint(&vm, ART + 35*(bitaddr_t)vm.addr_bits, vm.addr_bits); // carry in/out
  uint64_t BR   = vm_read_uint(&vm, ART + 36*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t T0   = vm_read_uint(&vm, ART + 37*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t T1   = vm_read_uint(&vm, ART + 38*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t C1   = vm_read_uint(&vm, ART + 41*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t C0   = vm_read_uint(&vm, ART + 42*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  uint64_t TESTG= vm_read_uint(&vm, ART + 43*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  FILE *f = fopen(out,"wb");
  if (!f) { perror("fopen"); vm_free(&vm); return 1; }

  // VAR_N = 1 once
  write_be(f, LITN, nb); write_be(f, 1u, nb);

  // Helpers: set a bit-reg from const0/const1
#define SETREG(reg_addr, val) \
  do { \
    write_be(f, LITD, nb); write_be(f, (reg_addr), nb); \
    write_be(f, LITS, nb); write_be(f, (val)?(C1):(C0), nb); \
    write_be(f, COPY, nb); \
  } while(0)

  // Move src bit -> dst bit (1 bit)
#define MOV(dst_addr, src_addr) \
  do { \
    write_be(f, LITD, nb); write_be(f, (dst_addr), nb); \
    write_be(f, LITS, nb); write_be(f, (src_addr), nb); \
    write_be(f, COPY, nb); \
  } while(0)

  // Store SUM (BR) to dest bit0, and COUT (BC) to dest bit1 (bit address +1)
#define STORE_RESULT(byte_base_bitaddr) \
  do { \
    /* SUM -> bit0 */ \
    write_be(f, LITD, nb); write_be(f, (uint64_t)((byte_base_bitaddr) + 0), nb); \
    write_be(f, LITS, nb); write_be(f, BR, nb); \
    write_be(f, COPY, nb); \
    /* COUT -> bit1 */ \
    write_be(f, LITD, nb); write_be(f, (uint64_t)((byte_base_bitaddr) + 1), nb); \
    write_be(f, LITS, nb); write_be(f, BC, nb); \
    write_be(f, COPY, nb); \
  } while(0)

  // Full adder macro:
  // t = A XOR B -> T0
  // ab = A AND B -> T1
  // sum = t XOR Cin -> BR
  // cin_t = Cin AND t -> T0
  // cout = ab OR cin_t -> BC
#define FULLADD_AND_STORE(dest_byte_bitaddr) \
  do { \
    /* t = A XOR B */ \
    write_be(f, BXOR, nb); \
    MOV(T0, BR); \
    /* ab = A AND B */ \
    write_be(f, BAND, nb); \
    MOV(T1, BR); \
    /* sum = t XOR Cin */ \
    MOV(BA, T0); \
    MOV(BB, BC); \
    write_be(f, BXOR, nb); \
    /* store SUM now (BR) */ \
    write_be(f, LITD, nb); write_be(f, (uint64_t)((dest_byte_bitaddr) + 0), nb); \
    write_be(f, LITS, nb); write_be(f, BR, nb); \
    write_be(f, COPY, nb); \
    /* cin_t = Cin AND t */ \
    MOV(BA, BC); \
    MOV(BB, T0); \
    write_be(f, BAND, nb); \
    MOV(T0, BR); \
    /* cout = ab OR cin_t */ \
    MOV(BA, T1); \
    MOV(BB, T0); \
    write_be(f, BOR, nb); \
    MOV(BC, BR); \
    /* store COUT */ \
    write_be(f, LITD, nb); write_be(f, (uint64_t)((dest_byte_bitaddr) + 1), nb); \
    write_be(f, LITS, nb); write_be(f, BC, nb); \
    write_be(f, COPY, nb); \
  } while(0)

  // Run 8 cases, store into TESTG bytes 0..7
  for (unsigned a=0; a<=1; a++) {
    for (unsigned b=0; b<=1; b++) {
      for (unsigned c=0; c<=1; c++) {
        unsigned idx = (a<<2) | (b<<1) | c; // 0..7
        uint64_t dst_byte_bit = TESTG + (uint64_t)idx * 8u;
        SETREG(BA, a);
        SETREG(BB, b);
        SETREG(BC, c);
        FULLADD_AND_STORE(dst_byte_bit);
      }
    }
  }

  write_be(f, HALT, nb);

#undef SETREG
#undef MOV
#undef STORE_RESULT
#undef FULLADD_AND_STORE

  fclose(f);
  fprintf(stderr, "TESTG(byte)=%llu\n", (unsigned long long)(TESTG >> 3));
  vm_free(&vm);
  return 0;
}