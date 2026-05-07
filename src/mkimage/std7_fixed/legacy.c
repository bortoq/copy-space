/* file: src/mkimage/std7_fixed/legacy.c
 * date: 2026-05-04
 * purpose: legacy monolithic mkimage for std7_fixed (to be split)
 */

// mkimage_std7_fixed.c
// std7_fixed + 2a words (ADD24/EQ24/LT24) + start of 2b (pointer ABI):
//   WORD_LITAP/WORD_LITBP/WORD_LITRP, VAR_AP/VAR_BP/VAR_RP, OFFTAB, WORD_EQ24P.
//
// Property preserved: word pages live in a fixed region near end of space,
// changing POOL_CELLS does NOT change word page addresses.

#include "layout.h"
#include "devices.h"
#include "addrs.h"
#include "artifacts.h"
#include "space.h"
#include "words.h"
#include "report.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>

static bitaddr_t align8(bitaddr_t x) { return (x + 7u) & ~(bitaddr_t)7u; }
static bitaddr_t align64(bitaddr_t x){ return (x + 63u) & ~(bitaddr_t)63u; }
// static bitaddr_t align_pow2(bitaddr_t x, bitaddr_t p2){ return (x + (p2-1)) & ~(p2-1); }

static int save_space(const vm_t *vm, const char *path) {
  FILE *f = fopen(path, "wb");
  if (!f) { perror("fopen"); return -1; }
  if (fwrite(vm->space, 1, vm->space_bytes, f) != vm->space_bytes) { perror("fwrite"); fclose(f); return -1; }
  fclose(f);
  return 0;
}
/* extracted to words_all.c */


static void usage(const char *a0) {
  fprintf(stderr, "usage: %s [--out PATH] [--pool-cells N]\n", a0);
}

int std7_fixed_legacy_main(int argc, char **argv) {
  const char *out_path = "space_forth0_compiler_std7_fixed_halt.bin";
  unsigned pool_cells = 32768;

  for (int i=1; i<argc; i++) {
    if (!strcmp(argv[i],"--out") && i+1<argc) out_path = argv[++i];
    else if (!strcmp(argv[i],"--pool-cells") && i+1<argc) pool_cells = (unsigned)strtoul(argv[++i], NULL, 0);
    else { usage(argv[0]); return 2; }
  }

  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 1;
  memset(vm.space, 0, vm.space_bytes);

  if (vm.addr_bits > 32) {
    fprintf(stderr, "This build assumes ADDR_BITS<=32 (got %u)\n", vm.addr_bits);
    vm_free(&vm);
    return 1;
  }

  bitaddr_t W = vm.workspace_base;
  bitaddr_t CONST1 = W;
  bitaddr_t CONST0 = W + 256;
  size_t cbyte = (size_t)(CONST1 >> 3);
  memset(&vm.space[cbyte], 0xFF, 32);
  memset(&vm.space[cbyte + 32], 0x00, 32);

  bitaddr_t ART = align8(W + 512u);

  // std7 was 46 entries (0..45), +2a added up to 54, now we extend to 62
  const unsigned ART_N = ART_COUNT; // 0..64    // d'b
  bitaddr_t P = align8(ART + (bitaddr_t)ART_N*(bitaddr_t)vm.addr_bits);

  // interpreter vars
  bitaddr_t VAR_IP   = P; P = align8(VAR_IP   + vm.addr_bits);
  bitaddr_t VAR_CODE = P; P = align8(VAR_CODE + vm.addr_bits);
  bitaddr_t VAR_NEXT = P; P = align8(VAR_NEXT + vm.addr_bits);

  // COPY regs
  bitaddr_t VAR_N   = P; P = align8(VAR_N   + vm.addr_bits);
  bitaddr_t VAR_DST = P; P = align8(VAR_DST + vm.addr_bits);
  bitaddr_t VAR_SRC = P; P = align8(VAR_SRC + vm.addr_bits);

  // loop / got flags
  bitaddr_t VAR_LOOP= P; P = align8(VAR_LOOP + vm.addr_bits);
  bitaddr_t VAR_FLAG= P; P = align8(VAR_FLAG + 1);
  bitaddr_t VAR_Z   = P; P = align8(VAR_Z + 1);

  // bit regs (public)
  bitaddr_t BA = P++;
  bitaddr_t BB = P++;
  bitaddr_t BC = P++;
  bitaddr_t BR = P++;
  bitaddr_t T0 = P++;
  bitaddr_t T1 = P++;

  // hidden temps for BXOR inlining
  bitaddr_t X0 = P++;
  bitaddr_t X1 = P++;
  P = align8(P);

  // token compiler vars
  bitaddr_t VAR_FREE          = P; P = align8(VAR_FREE + vm.addr_bits);
  bitaddr_t VAR_CUR           = P; P = align8(VAR_CUR + vm.addr_bits);
  bitaddr_t VAR_NEXTFREE      = P; P = align8(VAR_NEXTFREE + vm.addr_bits);
  bitaddr_t VAR_PREV_NEXT_FLD = P; P = align8(VAR_PREV_NEXT_FLD + vm.addr_bits);
  bitaddr_t VAR_TOKEN         = P; P = align8(VAR_TOKEN + vm.addr_bits);

  // 2a fixed operands/results
  bitaddr_t VAR_A24   = align8(P); P = align8(VAR_A24   + 24u);
  bitaddr_t VAR_B24   = align8(P); P = align8(VAR_B24   + 24u);
  bitaddr_t VAR_SUM24 = align8(P); P = align8(VAR_SUM24 + 24u);
  bitaddr_t VAR_COUT  = P++;
  bitaddr_t VAR_EQ    = P++;
  bitaddr_t VAR_LT    = P++;
  P = align8(P);

  // NEW 2b pointer regs
  bitaddr_t VAR_AP = P; P = align8(VAR_AP + vm.addr_bits);
  bitaddr_t VAR_BP = P; P = align8(VAR_BP + vm.addr_bits);
  bitaddr_t VAR_RP = P; P = align8(VAR_RP + vm.addr_bits);

  // NEW OFFTAB (32 bytes): OFFTAB[i] = i<<3, so top5 bits encode offset 0..31 (MSB-first)
  bitaddr_t OFFTAB = align8(P);
  size_t off_byte = (size_t)(OFFTAB >> 3);
  for (unsigned i=0; i<32; i++) vm.space[off_byte + i] = (uint8_t)(i << 3);
  P = align8(OFFTAB + 256u);

  // test region
  bitaddr_t TESTG = align8(P + 256); P = align8(TESTG + 64);

  // cells
  bitaddr_t CELLS_BASE = align64(P + 1024);
  bitaddr_t HEAD_CELL = CELLS_BASE + 0*64;
  bitaddr_t HALT_CELL = CELLS_BASE + 1*64;
  bitaddr_t POOL_BASE = CELLS_BASE + 2*64;

  // choose bsel so STEP >= processor_bits
  unsigned bsel=0;
  while (((bitaddr_t)1u<<bsel) < (bitaddr_t)vm.processor_bits) bsel++;
  if (bsel >= vm.addr_bits) { fprintf(stderr,"cannot choose bsel\n"); vm_free(&vm); return 1; }
  bitaddr_t STEP = (bitaddr_t)1u << bsel;

  // Fixed words/compiler region at end of space
  std7_layout_t L;
  if (std7_fixed_compute_layout(&vm, STEP, bsel, POOL_BASE, pool_cells, &L, stderr) != 0) {
    vm_free(&vm);
    return 1;
  }

  /* keep legacy variable names below */
  bitaddr_t WORDS_BASE = L.words_base;
  bitaddr_t TESTSCR_BASE = L.testscr_base;
  // size_t TESTSCR_SIZE_BYTES = L.testscr_size_bytes;  // d'b
  // bitaddr_t TESTSCR_SIZE_BITS = L.testscr_size_bits; // d'b
  // bitaddr_t pool_end = L.pool_end;   // d'b

  // Word pages (stable)
  bitaddr_t NEXT_IMG     = WORDS_BASE + 0*STEP;
  bitaddr_t WORD_NOP     = WORDS_BASE + 1*STEP;
  bitaddr_t WORD_SETUP   = WORDS_BASE + 2*STEP;
  bitaddr_t WORD_INREQ   = WORDS_BASE + 3*STEP;
  bitaddr_t WORD_OUTREQ  = WORDS_BASE + 4*STEP;
  bitaddr_t WORD_HALT    = WORDS_BASE + 5*STEP;
  bitaddr_t WORD_SAVEIP  = WORDS_BASE + 6*STEP;
  bitaddr_t WORD_JMP     = WORDS_BASE + 7*STEP;
  bitaddr_t WORD_SETOLEN = WORDS_BASE + 8*STEP;
  bitaddr_t WORD_IFGOT0  = WORDS_BASE + 9*STEP;

  bitaddr_t WORD_LITN    = WORDS_BASE + 10*STEP;
  bitaddr_t WORD_LITD    = WORDS_BASE + 11*STEP;
  bitaddr_t WORD_LITS    = WORDS_BASE + 12*STEP;
  bitaddr_t WORD_COPY    = WORDS_BASE + 13*STEP;
  bitaddr_t WORD_LITIP   = WORDS_BASE + 14*STEP;

  bitaddr_t WORD_BNOT    = WORDS_BASE + 15*STEP;
  bitaddr_t WORD_BAND    = WORDS_BASE + 16*STEP;
  bitaddr_t WORD_BOR     = WORDS_BASE + 17*STEP;
  bitaddr_t WORD_BXOR    = WORDS_BASE + 18*STEP;

  // Pad so DO/END alignment remains stable
  (void)(WORDS_BASE + 19*STEP);

  // Token compiler pages (stable)
  bitaddr_t DO_BASE      = WORDS_BASE + 20*STEP;
  bitaddr_t END_BASE     = DO_BASE + STEP;
  bitaddr_t BRANCH_IMG   = WORDS_BASE + 22*STEP;

  // NEW: pointer literal loaders (2b convenience)
  bitaddr_t WORD_LITAP   = WORDS_BASE + 23*STEP;
  bitaddr_t WORD_LITBP   = WORDS_BASE + 24*STEP;
  bitaddr_t WORD_LITRP   = WORDS_BASE + 25*STEP;
  /* 2b block-pointer primitives (appended ABI) */
  bitaddr_t WORD_LOAD24AP  = WORDS_BASE + 26*STEP;
  bitaddr_t WORD_LOAD24BP  = WORDS_BASE + 27*STEP;
  bitaddr_t WORD_STORE24RP = WORDS_BASE + 28*STEP;

  // 2a library words pages (stable)
  bitaddr_t WORD_ADD24   = WORDS_BASE + 32*STEP; // 24 pages: 32..55
  bitaddr_t WORD_EQ24    = WORDS_BASE + 56*STEP; // 24 pages: 56..79
  bitaddr_t WORD_LT24    = WORDS_BASE + 80*STEP; // 24 pages: 80..103

  // NEW 2b word EQ24P uses free block 104..127 (24 pages)
  bitaddr_t WORD_EQ24P   = WORDS_BASE + 104*STEP;

  // build core word pages
  write_next_page(&vm, NEXT_IMG, VAR_IP, VAR_CODE, VAR_NEXT, CONST1);

  write_word_nop(&vm, WORD_NOP, NEXT_IMG);
  write_word_setup_echo(&vm, WORD_SETUP, NEXT_IMG, CONST1);
  write_word_inreq(&vm, WORD_INREQ, NEXT_IMG, CONST1);
  write_word_outreq(&vm, WORD_OUTREQ, NEXT_IMG, CONST1);
  write_word_halt(&vm, WORD_HALT, NEXT_IMG, CONST1);

  write_word_saveip(&vm, WORD_SAVEIP, NEXT_IMG, VAR_IP, VAR_LOOP);
  write_word_jmp(&vm, WORD_JMP, NEXT_IMG, VAR_IP, VAR_LOOP);
  write_word_setolen(&vm, WORD_SETOLEN, NEXT_IMG);
  write_word_ifgot0(&vm, WORD_IFGOT0, NEXT_IMG, VAR_IP, VAR_FLAG, VAR_Z, CONST1, CONST0, bsel);

  write_word_lit_generic(&vm, WORD_LITN, NEXT_IMG, VAR_IP, VAR_N,   CONST1);
  write_word_lit_generic(&vm, WORD_LITD, NEXT_IMG, VAR_IP, VAR_DST, CONST1);
  write_word_lit_generic(&vm, WORD_LITS, NEXT_IMG, VAR_IP, VAR_SRC, CONST1);
  write_word_copy(&vm, WORD_COPY, NEXT_IMG, VAR_N, VAR_DST, VAR_SRC);
  write_word_litip(&vm, WORD_LITIP, NEXT_IMG, VAR_IP, VAR_SRC, CONST1);

  // NEW pointer literal loaders
  write_word_lit_generic(&vm, WORD_LITAP, NEXT_IMG, VAR_IP, VAR_AP, CONST1);
  write_word_lit_generic(&vm, WORD_LITBP, NEXT_IMG, VAR_IP, VAR_BP, CONST1);
  write_word_lit_generic(&vm, WORD_LITRP, NEXT_IMG, VAR_IP, VAR_RP, CONST1);
  write_word_load24ap(&vm, WORD_LOAD24AP, NEXT_IMG, VAR_A24, VAR_AP);
  write_word_load24bp(&vm, WORD_LOAD24BP, NEXT_IMG, VAR_B24, VAR_BP);
  write_word_store24rp(&vm, WORD_STORE24RP, NEXT_IMG, VAR_RP, VAR_SUM24);

  write_word_bnot(&vm, WORD_BNOT, NEXT_IMG, BA, BR, CONST1, CONST0);
  write_word_band(&vm, WORD_BAND, NEXT_IMG, BA, BB, BR, CONST0);
  write_word_bor(&vm, WORD_BOR, NEXT_IMG, BA, BB, BR, CONST1, CONST0);
  write_word_bxor(&vm, WORD_BXOR, NEXT_IMG, BA, BB, BR, X0, X1, CONST1, CONST0);

  // static cells
  write_cell(&vm, HEAD_CELL, WORD_NOP, HALT_CELL);
  write_cell(&vm, HALT_CELL, WORD_HALT, HALT_CELL);

  // init freelist
  for (unsigned i=0; i<pool_cells; i++) {
    bitaddr_t cell = POOL_BASE + (bitaddr_t)i*64u;
    bitaddr_t next = (i+1u<pool_cells) ? (cell+64u) : cell;
    vm_write_uint(&vm, cell + 0, vm.addr_bits, (uint64_t)next);
  }
  vm_write_uint(&vm, VAR_FREE, vm.addr_bits, (uint64_t)POOL_BASE);
  vm_write_uint(&vm, VAR_PREV_NEXT_FLD, vm.addr_bits, (uint64_t)(HEAD_CELL + 32u));

  // token compiler pages
  write_page_do(&vm, DO_BASE, BRANCH_IMG, VAR_FREE, VAR_CUR, VAR_NEXTFREE, VAR_PREV_NEXT_FLD, VAR_TOKEN, CONST1);
  write_page_end(&vm, END_BASE, HALT_CELL, VAR_PREV_NEXT_FLD, CONST1);
  write_page_branch(&vm, BRANCH_IMG, DO_BASE, bsel);

  // build 2a microcode pages (same mapping as before)
  for (unsigned i=0; i<24; i++) {
    unsigned byte_index = 2u - (i / 8u);
    unsigned bit_in_byte = 7u - (i % 8u);

    bitaddr_t Abit = VAR_A24   + (bitaddr_t)byte_index*8u + (bitaddr_t)bit_in_byte;
    bitaddr_t Bbit = VAR_B24   + (bitaddr_t)byte_index*8u + (bitaddr_t)bit_in_byte;
    bitaddr_t Sbit = VAR_SUM24 + (bitaddr_t)byte_index*8u + (bitaddr_t)bit_in_byte;

    bitaddr_t img = WORD_ADD24 + (bitaddr_t)i*STEP;
    bitaddr_t nxt = (i+1u<24) ? (img + STEP) : NEXT_IMG;

    write_word_add24_micro(&vm, img, nxt, Abit, Bbit, Sbit,
                           (i==0), (i==23), VAR_COUT,
                           BA, BB, BC, BR, T0, T1, X0, X1, CONST1, CONST0);
  }

  for (unsigned i=0; i<24; i++) {
    unsigned byte_index = (i / 8u);
    unsigned bit_in_byte = (i % 8u);

    bitaddr_t Abit = VAR_A24 + (bitaddr_t)byte_index*8u + (bitaddr_t)bit_in_byte;
    bitaddr_t Bbit = VAR_B24 + (bitaddr_t)byte_index*8u + (bitaddr_t)bit_in_byte;

    bitaddr_t img = WORD_EQ24 + (bitaddr_t)i*STEP;
    bitaddr_t nxt = (i+1u<24) ? (img + STEP) : NEXT_IMG;

    write_word_eq24_micro(&vm, img, nxt, Abit, Bbit,
                          (i==0), (i==23), VAR_EQ,
                          BA, BB, BR, T0, T1, X0, X1, CONST1, CONST0);
  }

  for (unsigned i=0; i<24; i++) {
    unsigned byte_index = (i / 8u);
    unsigned bit_in_byte = (i % 8u);

    bitaddr_t Abit = VAR_A24 + (bitaddr_t)byte_index*8u + (bitaddr_t)bit_in_byte;
    bitaddr_t Bbit = VAR_B24 + (bitaddr_t)byte_index*8u + (bitaddr_t)bit_in_byte;

    bitaddr_t img = WORD_LT24 + (bitaddr_t)i*STEP;
    bitaddr_t nxt = (i+1u<24) ? (img + STEP) : NEXT_IMG;

    write_word_lt24_micro(&vm, img, nxt, Abit, Bbit,
                          (i==0), (i==23), VAR_LT,
                          BA, BB, BR, T0, BC, T1, X0, X1, CONST1, CONST0);
  }

  // NEW: build EQ24P micro-pages (MSB->LSB offsets 0..23)
  for (unsigned i=0; i<24; i++) {
    unsigned off5 = i; // MSB bit is offset 0 within 24-bit slice
    bitaddr_t img = WORD_EQ24P + (bitaddr_t)i*STEP;
    bitaddr_t nxt = (i+1u<24) ? (img + STEP) : NEXT_IMG;

    write_word_eq24p_micro(&vm, img, nxt, off5,
                           (i==0), (i==23),
                           VAR_AP, VAR_BP, OFFTAB,
                           BA, BB, BR, T0, T1,
                           X0, X1, CONST1, CONST0,
                           VAR_EQ);
  }

  // artifact: keep previous indices unchanged, append new at the end
  /* devices/bus: build TERM0 structures after pool (byte-aligned) */
  bitaddr_t pool_end_bits = POOL_BASE + (bitaddr_t)pool_cells * 64u;
  bitaddr_t BUS_GUARD_BITS = (bitaddr_t)64u * 8u;
  bitaddr_t BUS_SIZE_BITS  = (bitaddr_t)256u * 8u;
  bitaddr_t BUS_BASE = (pool_end_bits + BUS_GUARD_BITS + 7u) & ~(bitaddr_t)7u;
  if (BUS_BASE + BUS_SIZE_BITS + BUS_GUARD_BITS > TESTSCR_BASE) {
    fprintf(stderr, "mkimage: BUS overlaps scratch\n");
    return 1;
  }
  std7_devices_t DEV = {0};
  if (std7_fixed_build_devices(&vm, BUS_BASE, &DEV) != 0) {
    fprintf(stderr, "mkimage: std7_fixed_build_devices failed\n");
    return 1;
  }

  std7_addrs_t A = {0}; // d'b {{

  A.head_cell   = HEAD_CELL;
  A.next_img    = NEXT_IMG;
  A.var_ip      = VAR_IP;

  A.word_setup  = WORD_SETUP;
  A.word_inreq  = WORD_INREQ;
  A.word_outreq = WORD_OUTREQ;
  A.word_halt   = WORD_HALT;

  A.var_loop     = VAR_LOOP;
  A.word_saveip  = WORD_SAVEIP;
  A.word_jmp     = WORD_JMP;
  A.word_setolen = WORD_SETOLEN;
  A.word_ifgot0  = WORD_IFGOT0;

  A.var_n    = VAR_N;
  A.var_dst  = VAR_DST;
  A.var_src  = VAR_SRC;

  A.word_litn  = WORD_LITN;
  A.word_litd  = WORD_LITD;
  A.word_lits  = WORD_LITS;
  A.word_copy  = WORD_COPY;
  A.word_litip = WORD_LITIP;

  A.ba = BA; A.bb = BB; A.bc = BC; A.br = BR; A.t0 = T0; A.t1 = T1;

  A.word_bnot = WORD_BNOT;
  A.word_band = WORD_BAND;

  A.const1 = CONST1;
  A.const0 = CONST0;

  /* policy */
  A.testscr_base = TESTSCR_BASE;
  A.testscr_end  = TESTSCR_BASE + L.testscr_size_bits;
  A.testg        = TESTSCR_BASE;

  A.word_bor  = WORD_BOR;
  A.word_bxor = WORD_BXOR;

  /* 2a */
  A.word_add24 = WORD_ADD24;
  A.var_a24    = VAR_A24;
  A.var_b24    = VAR_B24;
  A.var_sum24  = VAR_SUM24;
  A.var_cout   = VAR_COUT;
  A.word_eq24  = WORD_EQ24;
  A.var_eq     = VAR_EQ;
  A.word_lt24  = WORD_LT24;
  A.var_lt     = VAR_LT;

  /* 2b */
  A.word_litap = WORD_LITAP;
  A.word_litbp = WORD_LITBP;
  A.word_litrp = WORD_LITRP;
  A.var_ap     = VAR_AP;
  A.var_bp     = VAR_BP;
  A.var_rp     = VAR_RP;
  A.offtab     = OFFTAB;
  A.word_eq24p = WORD_EQ24P;

  /* devices/bus */
  A.bus_base   = BUS_BASE;
  A.term0_desc = DEV.term0_desc;
  A.word_load24ap  = WORD_LOAD24AP;
  A.word_load24bp  = WORD_LOAD24BP;
  A.word_store24rp = WORD_STORE24RP;

  std7_fixed_write_artifacts(&vm, ART, &A); // }}

  // INIT compilation: token -> VAR_TOKEN, len=ADDR_BITS, IN_REQ=1, load BRANCH
  nop_fill_processor(&vm);
  vm_write_uint(&vm, vm.mmio.in_dst, vm.addr_bits, (uint64_t)VAR_TOKEN);
  vm_write_uint(&vm, vm.mmio.in_len, vm.n_bits, (uint64_t)vm.addr_bits);
  vm_bit_set(&vm, vm.mmio.in_req, 1);

  vm_write_inst(&vm, vm_proc_slot_ip(&vm, vm.processor_n-1),
                (vm_inst_t){ .n=(uint64_t)vm.processor_bits, .dst=0, .src=(uint64_t)BRANCH_IMG });

  std7_fixed_print_summary(stderr, out_path, &L, ART, &A);

  int rc = save_space(&vm, out_path);
  vm_free(&vm);
  return rc ? 1 : 0;
}
