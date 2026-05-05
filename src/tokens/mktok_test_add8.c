// mktok_test_add8.c
// ADD8 via std7 words: BXOR, BAND, BOR and bit regs BA,BB,BC,BR plus temps T0,T1.
// Writes 8 bytes at TESTG:
//   case0: A0,B0,SUM0,COUT0
//   case1: A1,B1,SUM1,COUT1 (COUT stored at bit0 => 0x80)
//
// Expected:
//   00 00 00 00  ff 01 00 80

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

#define SETBIT(dst_bitaddr, val01) \
  do { \
    write_be(f, LITD, nb); write_be(f, (uint64_t)(dst_bitaddr), nb); \
    write_be(f, LITS, nb); write_be(f, (uint64_t)((val01)?C1:C0), nb); \
    write_be(f, COPY, nb); \
  } while(0)

#define MOVBIT(dst_bitaddr, src_bitaddr) \
  do { \
    write_be(f, LITD, nb); write_be(f, (uint64_t)(dst_bitaddr), nb); \
    write_be(f, LITS, nb); write_be(f, (uint64_t)(src_bitaddr), nb); \
    write_be(f, COPY, nb); \
  } while(0)

#define SETBYTE(byte_base_bitaddr, u8val) \
  do { \
    for (unsigned off=0; off<8; off++) { \
      unsigned bit = ((u8val) >> (7u-off)) & 1u; /* off=0 -> MSB */ \
      SETBIT((uint64_t)(byte_base_bitaddr) + (uint64_t)off, bit); \
    } \
  } while(0)

// Correct full-adder:
// Inputs: BA=A, BB=B, BC=Cin
// Outputs: BR=SUM, BC=Cout
// Temps: T0,T1
#define FULLADD_1BIT() \
  do { \
    /* save Cin */ \
    MOVBIT(T1, BC); \
    /* t = A XOR B */ \
    write_be(f, BXOR, nb); \
    MOVBIT(T0, BR); \
    /* ab = A AND B -> store into BC (Cin already saved) */ \
    write_be(f, BAND, nb); \
    MOVBIT(BC, BR); \
    /* cin_t = Cin & t */ \
    MOVBIT(BA, T1); \
    MOVBIT(BB, T0); \
    write_be(f, BAND, nb); \
    /* cout = ab | cin_t */ \
    MOVBIT(BA, BC); \
    MOVBIT(BB, BR); \
    write_be(f, BOR, nb); \
    MOVBIT(BC, BR); \
    /* sum = t XOR Cin */ \
    MOVBIT(BA, T0); \
    MOVBIT(BB, T1); \
    write_be(f, BXOR, nb); \
  } while(0)

#define ADD8(Abyte_bit, Bbyte_bit, SUMbyte_bit, COUT_bitaddr) \
  do { \
    SETBIT(BC, 0); \
    for (int off = 7; off >= 0; off--) { /* LSB (off=7) -> MSB (off=0) */ \
      uint64_t Abit = (uint64_t)(Abyte_bit)   + (uint64_t)off; \
      uint64_t Bbit = (uint64_t)(Bbyte_bit)   + (uint64_t)off; \
      uint64_t Sbit = (uint64_t)(SUMbyte_bit) + (uint64_t)off; \
      MOVBIT(BA, Abit); \
      MOVBIT(BB, Bbit); \
      FULLADD_1BIT(); \
      MOVBIT(Sbit, BR); \
    } \
    MOVBIT((uint64_t)(COUT_bitaddr), BC); \
  } while(0)

  // TESTG bytes (bitaddrs)
  uint64_t A0  = TESTG + 0u*8u;
  uint64_t B0  = TESTG + 1u*8u;
  uint64_t S0  = TESTG + 2u*8u;
  uint64_t CO0 = TESTG + 3u*8u + 0u; // bit0 => 0x80

  uint64_t A1  = TESTG + 4u*8u;
  uint64_t B1  = TESTG + 5u*8u;
  uint64_t S1  = TESTG + 6u*8u;
  uint64_t CO1 = TESTG + 7u*8u + 0u; // bit0 => 0x80

  // init memory
  SETBYTE(A0, 0x00); SETBYTE(B0, 0x00); SETBYTE(S0, 0x00); SETBYTE(TESTG + 3u*8u, 0x00);
  SETBYTE(A1, 0xFF); SETBYTE(B1, 0x01); SETBYTE(S1, 0x00); SETBYTE(TESTG + 7u*8u, 0x00);

  // run
  ADD8(A0, B0, S0, CO0);
  ADD8(A1, B1, S1, CO1);

  write_be(f, HALT, nb);

#undef SETBIT
#undef MOVBIT
#undef SETBYTE
#undef FULLADD_1BIT
#undef ADD8

  fclose(f);
  fprintf(stderr, "TESTG(byte)=%llu\n", (unsigned long long)(TESTG >> 3));
  vm_free(&vm);
  return 0;
}
