// c3_addi_proof.c - direct proof harness for expanded C3_RUN resident paths
#include "space.h"
#include "mkimage/std7_fixed/artifacts.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
  G_PC          = 0x001000u,
  G_STEP_BUDGET = 0x001020u,
  G_STEPS       = 0x001040u,
  G_STOP_REASON = 0x001080u,
  G_REG_BASE    = 0x001200u,
  G_MEM_BASE    = 0x002000u
};

typedef enum {
  CASE_ADDI = 0,
  CASE_UNSUPPORTED,
  CASE_UNSUPPORTED_STOP_STATE,
  CASE_SW,
  CASE_LW,
  CASE_BNE,
  CASE_JAL,
  CASE_STOP_STATE
} proof_case_t;

static bitaddr_t align8_bits(bitaddr_t x) { return (x + 7u) & ~(bitaddr_t)7u; }

static int load_image(vm_t *vm, const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { perror("fopen(image)"); return -1; }
  if (fseek(f, 0, SEEK_END) != 0) { perror("fseek"); fclose(f); return -1; }
  long sz = ftell(f);
  if (sz < 0) { perror("ftell"); fclose(f); return -1; }
  rewind(f);
  if ((size_t)sz != vm->space_bytes) {
    fprintf(stderr, "image size mismatch: file=%ld bytes expected=%zu bytes\n", sz, vm->space_bytes);
    fclose(f);
    return -1;
  }
  if (fread(vm->space, 1, vm->space_bytes, f) != vm->space_bytes) {
    perror("fread(image)");
    fclose(f);
    return -1;
  }
  fclose(f);
  return 0;
}

static void write_u8(vm_t *vm, bitaddr_t bitpos, uint8_t v) {
  vm_write_uint(vm, bitpos, 8u, v);
}

static uint8_t read_u8(const vm_t *vm, bitaddr_t bitpos) {
  return (uint8_t)vm_read_uint(vm, bitpos, 8u);
}

static void clear_regs_stop_steps(vm_t *vm) {
  for (unsigned i = 0; i < 8; i++) {
    write_u8(vm, G_REG_BASE + (bitaddr_t)i * 8u, 0x00);
  }
  for (unsigned i = 0; i < 4; i++) {
    write_u8(vm, G_STOP_REASON + (bitaddr_t)i * 8u, 0x00);
    write_u8(vm, G_STEPS + (bitaddr_t)i * 8u, 0x00);
    write_u8(vm, G_STEP_BUDGET + (bitaddr_t)i * 8u, 0x00);
  }
}

static void set_pc(vm_t *vm, uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
  write_u8(vm, G_PC +  0u, b0);
  write_u8(vm, G_PC +  8u, b1);
  write_u8(vm, G_PC + 16u, b2);
  write_u8(vm, G_PC + 24u, b3);
}

static void set_x1(vm_t *vm, uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
  write_u8(vm, G_REG_BASE + 32u, b0);
  write_u8(vm, G_REG_BASE + 40u, b1);
  write_u8(vm, G_REG_BASE + 48u, b2);
  write_u8(vm, G_REG_BASE + 56u, b3);
}

static void set_instr_at(vm_t *vm, bitaddr_t addr, uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
  write_u8(vm, addr +  0u, b0);
  write_u8(vm, addr +  8u, b1);
  write_u8(vm, addr + 16u, b2);
  write_u8(vm, addr + 24u, b3);
}

static void set_instr(vm_t *vm, uint8_t b0, uint8_t b1, uint8_t b2, uint8_t b3) {
  set_instr_at(vm, G_MEM_BASE + 0u, b0, b1, b2, b3);
}

static void set_stop_reason(vm_t *vm, uint8_t v) {
  write_u8(vm, G_STOP_REASON + 0u, v);
}

static void set_steps(vm_t *vm, uint8_t v) {
  write_u8(vm, G_STEPS + 0u, v);
}

static void init_guest_state(vm_t *vm, proof_case_t which) {
  clear_regs_stop_steps(vm);
  set_pc(vm, 0x00, 0x20, 0x00, 0x00);

  switch (which) {
    case CASE_ADDI:
    case CASE_STOP_STATE:
      /* ADDI x1, x0, 5 = 0x00500093 */
      set_instr(vm, 0x00, 0x50, 0x00, 0x93);
      set_stop_reason(vm, 0x00);
      set_steps(vm, 0x00);
      break;
    case CASE_UNSUPPORTED:
      /* opcode 0x00 is not supported by current C3_RUN dispatch */
      set_instr(vm, 0x00, 0x00, 0x00, 0x00);
      set_stop_reason(vm, 0x00);
      set_steps(vm, 0x00);
      break;
    case CASE_UNSUPPORTED_STOP_STATE:
      /* Unsupported opcode with non-zero x1 and non-default PC to prove exact stop-state behavior. */
      set_pc(vm, 0x00, 0x24, 0x00, 0x00);
      set_instr(vm, 0x00, 0x00, 0x00, 0x00);
      set_x1(vm, 0x12, 0x34, 0x56, 0x78);
      set_stop_reason(vm, 0x00);
      set_steps(vm, 0x00);
      break;
    case CASE_SW:
      /* SW x1, 4(x0) = 0x00102223 */
      set_instr(vm, 0x00, 0x10, 0x22, 0x23);
      set_x1(vm, 0x12, 0x34, 0x56, 0x78);
      set_stop_reason(vm, 0x00);
      set_steps(vm, 0x00);
      break;
    case CASE_LW:
      /* LW x1, 4(x0) = 0x00402083; data lives after the instruction word */
      set_instr(vm, 0x00, 0x40, 0x20, 0x83);
      write_u8(vm, G_MEM_BASE + 32u, 0x12);
      write_u8(vm, G_MEM_BASE + 40u, 0x34);
      write_u8(vm, G_MEM_BASE + 48u, 0x56);
      write_u8(vm, G_MEM_BASE + 56u, 0x78);
      set_stop_reason(vm, 0x00);
      set_steps(vm, 0x00);
      break;
    case CASE_BNE:
      /* BNE x0, x1, +8 = 0x00101463; x1 starts at 1 so branch is taken */
      set_instr(vm, 0x00, 0x10, 0x14, 0x63);
      set_x1(vm, 0x00, 0x00, 0x00, 0x01);
      set_stop_reason(vm, 0x00);
      set_steps(vm, 0x00);
      break;
    case CASE_JAL:
      /* JAL x1, +8 = 0x008000ef */
      set_instr(vm, 0x00, 0x80, 0x00, 0xef);
      set_x1(vm, 0xaa, 0xbb, 0xcc, 0xdd);
      set_stop_reason(vm, 0x00);
      set_steps(vm, 0x00);
      break;
  }
}

static int verify_state(const vm_t *vm, proof_case_t which) {
  uint8_t expect_x1[4] = {0};
  uint8_t expect_pc[4] = {0};
  uint8_t expect_stop[4] = {0};
  uint8_t expect_steps[4] = {0};
  uint8_t got_x1[4];
  uint8_t got_pc[4];
  uint8_t got_stop[4];
  uint8_t got_steps[4];

  switch (which) {
    case CASE_ADDI:
      expect_x1[3] = 0x05;
      expect_pc[1] = 0x20; expect_pc[2] = 0x20;
      expect_stop[0] = 0x01;
      expect_steps[0] = 0x01;
      break;
    case CASE_UNSUPPORTED:
      expect_pc[1] = 0x20;
      expect_stop[0] = 0x11;
      expect_steps[0] = 0x01;
      break;
    case CASE_UNSUPPORTED_STOP_STATE:
      expect_x1[0] = 0x12; expect_x1[1] = 0x34; expect_x1[2] = 0x56; expect_x1[3] = 0x78;
      expect_pc[1] = 0x24;
      expect_stop[0] = 0x11;
      expect_steps[0] = 0x01;
      break;
    case CASE_SW:
      expect_x1[0] = 0x12; expect_x1[1] = 0x34; expect_x1[2] = 0x56; expect_x1[3] = 0x78;
      expect_pc[1] = 0x20; expect_pc[2] = 0x20;
      expect_stop[0] = 0x01;
      expect_steps[0] = 0x01;
      break;
    case CASE_LW:
      expect_x1[0] = 0x12; expect_x1[1] = 0x34; expect_x1[2] = 0x56; expect_x1[3] = 0x78;
      expect_pc[1] = 0x20; expect_pc[2] = 0x20;
      expect_stop[0] = 0x01;
      expect_steps[0] = 0x01;
      break;
    case CASE_BNE:
      expect_x1[3] = 0x01;
      expect_pc[1] = 0x20; expect_pc[2] = 0x40;
      expect_stop[0] = 0x01;
      expect_steps[0] = 0x01;
      break;
    case CASE_JAL:
      expect_x1[1] = 0x20; expect_x1[2] = 0x20;
      expect_pc[1] = 0x20; expect_pc[2] = 0x40;
      expect_stop[0] = 0x01;
      expect_steps[0] = 0x01;
      break;
    case CASE_STOP_STATE:
      expect_x1[3] = 0x05;
      expect_pc[1] = 0x20; expect_pc[2] = 0x20;
      expect_stop[0] = 0x01;
      expect_steps[0] = 0x01;
      break;
  }

  for (unsigned i = 0; i < 4; i++) {
    got_x1[i] = read_u8(vm, G_REG_BASE + 32u + (bitaddr_t)i * 8u);
    got_pc[i] = read_u8(vm, G_PC + (bitaddr_t)i * 8u);
    got_stop[i] = read_u8(vm, G_STOP_REASON + (bitaddr_t)i * 8u);
    got_steps[i] = read_u8(vm, G_STEPS + (bitaddr_t)i * 8u);
  }

  for (unsigned i = 0; i < 4; i++) {
    if (got_x1[i] != expect_x1[i] ||
        got_pc[i] != expect_pc[i] ||
        got_stop[i] != expect_stop[i] ||
        got_steps[i] != expect_steps[i]) {
      fprintf(stderr,
              "state mismatch\n"
              "  x1   got=%02x%02x%02x%02x expect=%02x%02x%02x%02x\n"
              "  pc   got=%02x%02x%02x%02x expect=%02x%02x%02x%02x\n"
              "  stop got=%02x%02x%02x%02x expect=%02x%02x%02x%02x\n"
              "  step got=%02x%02x%02x%02x expect=%02x%02x%02x%02x\n",
              got_x1[0], got_x1[1], got_x1[2], got_x1[3],
              expect_x1[0], expect_x1[1], expect_x1[2], expect_x1[3],
              got_pc[0], got_pc[1], got_pc[2], got_pc[3],
              expect_pc[0], expect_pc[1], expect_pc[2], expect_pc[3],
              got_stop[0], got_stop[1], got_stop[2], got_stop[3],
              expect_stop[0], expect_stop[1], expect_stop[2], expect_stop[3],
              got_steps[0], got_steps[1], got_steps[2], got_steps[3],
              expect_steps[0], expect_steps[1], expect_steps[2], expect_steps[3]);
      return -1;
    }
  }

  if (which == CASE_SW) {
    uint8_t mem[4] = {
      read_u8(vm, G_MEM_BASE + 32u),
      read_u8(vm, G_MEM_BASE + 40u),
      read_u8(vm, G_MEM_BASE + 48u),
      read_u8(vm, G_MEM_BASE + 56u)
    };
    if (mem[0] != 0x12 || mem[1] != 0x34 || mem[2] != 0x56 || mem[3] != 0x78) {
      fprintf(stderr, "memory mismatch after SW: got=%02x%02x%02x%02x expect=12345678\n",
              mem[0], mem[1], mem[2], mem[3]);
      return -1;
    }
  }

  return 0;
}

static void dump_debug_state(const vm_t *vm) {
  bitaddr_t art_base = align8_bits(vm->workspace_base + 512u);
  bitaddr_t testscr_base =
    (bitaddr_t)vm_read_uint(vm,
                            art_base + (bitaddr_t)ART_TESTSCR_BASE * (bitaddr_t)vm->addr_bits,
                            vm->addr_bits);
  bitaddr_t g_instr = testscr_base + 256u;
  bitaddr_t g_imm = testscr_base + 384u;
  uint8_t step_window[16];

  for (unsigned i = 0; i < 16; i++) {
    step_window[i] = read_u8(vm, G_STEP_BUDGET + (bitaddr_t)i * 8u);
  }

  fprintf(stderr,
          "debug G_PC24=%06llx MEM0=%02x%02x%02x%02x G_INSTR=%02x%02x%02x%02x G_IMM=%02x%02x%02x%02x STEPWIN=%02x%02x%02x%02x %02x%02x%02x%02x %02x%02x%02x%02x %02x%02x%02x%02x\n",
          (unsigned long long)vm_read_uint(vm, G_PC, vm->addr_bits),
          read_u8(vm, G_MEM_BASE + 0u), read_u8(vm, G_MEM_BASE + 8u),
          read_u8(vm, G_MEM_BASE + 16u), read_u8(vm, G_MEM_BASE + 24u),
          read_u8(vm, g_instr + 0u), read_u8(vm, g_instr + 8u),
          read_u8(vm, g_instr + 16u), read_u8(vm, g_instr + 24u),
          read_u8(vm, g_imm + 0u), read_u8(vm, g_imm + 8u),
          read_u8(vm, g_imm + 16u), read_u8(vm, g_imm + 24u),
          step_window[0], step_window[1], step_window[2], step_window[3],
          step_window[4], step_window[5], step_window[6], step_window[7],
          step_window[8], step_window[9], step_window[10], step_window[11],
          step_window[12], step_window[13], step_window[14], step_window[15]);
}

static void dump_tick_state(const vm_t *vm, uint64_t tick) {
  bitaddr_t art_base = align8_bits(vm->workspace_base + 512u);
  bitaddr_t testscr_base =
    (bitaddr_t)vm_read_uint(vm,
                            art_base + (bitaddr_t)ART_TESTSCR_BASE * (bitaddr_t)vm->addr_bits,
                            vm->addr_bits);
  bitaddr_t g_instr = testscr_base + 256u;
  fprintf(stderr,
          "tick=%llu pc=%06llx stop=%02x steps=%02x instr=%02x%02x%02x%02x mem=%02x%02x%02x%02x\n",
          (unsigned long long)tick,
          (unsigned long long)vm_read_uint(vm, G_PC, vm->addr_bits),
          read_u8(vm, G_STOP_REASON),
          read_u8(vm, G_STEPS),
          read_u8(vm, g_instr + 0u), read_u8(vm, g_instr + 8u),
          read_u8(vm, g_instr + 16u), read_u8(vm, g_instr + 24u),
          read_u8(vm, G_MEM_BASE + 0u), read_u8(vm, G_MEM_BASE + 8u),
          read_u8(vm, G_MEM_BASE + 16u), read_u8(vm, G_MEM_BASE + 24u));
}

int main(int argc, char **argv) {
  const char *image_path = "build/std7_c3_addi_proof.bin";
  uint64_t life = 1024u;
  proof_case_t which = CASE_ADDI;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--image") && i + 1 < argc) image_path = argv[++i];
    else if (!strcmp(argv[i], "--life") && i + 1 < argc) life = strtoull(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--case") && i + 1 < argc) {
      const char *name = argv[++i];
      if (!strcmp(name, "addi")) which = CASE_ADDI;
      else if (!strcmp(name, "unsupported")) which = CASE_UNSUPPORTED;
      else if (!strcmp(name, "unsupported-stop-state")) which = CASE_UNSUPPORTED_STOP_STATE;
      else if (!strcmp(name, "sw")) which = CASE_SW;
      else if (!strcmp(name, "lw")) which = CASE_LW;
      else if (!strcmp(name, "bne")) which = CASE_BNE;
      else if (!strcmp(name, "jal")) which = CASE_JAL;
      else if (!strcmp(name, "stop-state")) which = CASE_STOP_STATE;
      else {
        fprintf(stderr, "unknown case: %s\n", name);
        return 2;
      }
    }
    else {
      fprintf(stderr, "usage: %s [--image path] [--life ticks] [--case addi|unsupported|unsupported-stop-state|sw|lw|bne|jal|stop-state]\n", argv[0]);
      return 2;
    }
  }

  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  if (load_image(&vm, image_path) != 0) {
    vm_free(&vm);
    return 1;
  }

  const char *trace_env = getenv("C3_TRACE");

  bitaddr_t art_base = align8_bits(vm.workspace_base + 512u);
  bitaddr_t word_c3_run =
    (bitaddr_t)vm_read_uint(&vm,
                            art_base + (bitaddr_t)ART_WORD_C3_RUN * (bitaddr_t)vm.addr_bits,
                            vm.addr_bits);

  if (word_c3_run == 0 || word_c3_run + vm.processor_bits > vm.space_bits) {
    bitaddr_t art_word = art_base + (bitaddr_t)ART_WORD_C3_RUN * (bitaddr_t)vm.addr_bits;
    fprintf(stderr,
            "invalid WORD_C3_RUN artifact: %llu workspace_base=%llu art_base=%llu art_word=%llu raw=%02x%02x%02x\n",
            (unsigned long long)word_c3_run,
            (unsigned long long)vm.workspace_base,
            (unsigned long long)art_base,
            (unsigned long long)art_word,
            read_u8(&vm, art_word + 0u),
            read_u8(&vm, art_word + 8u),
            read_u8(&vm, art_word + 16u));
    vm_free(&vm);
    return 1;
  }

  if (vm_build_boot_loader_layer(&vm, word_c3_run) != 0) {
    fprintf(stderr, "vm_build_boot_loader_layer failed\n");
    vm_free(&vm);
    return 1;
  }

  init_guest_state(&vm, which);

  for (uint64_t tick = 0; tick < life; tick++) {
    if (trace_env && trace_env[0] != '\0') dump_tick_state(&vm, tick);
    vm_rc_t rc = vm_tick(&vm, stdin, stdout);
    if (rc == VM_ERR) {
      fprintf(stderr, "vm_tick failed at tick=%llu\n", (unsigned long long)tick);
      vm_free(&vm);
      return 1;
    }
    if ((read_u8(&vm, G_STOP_REASON) & 0x01u) != 0u) {
      int ok = verify_state(&vm, which);
      if (ok != 0) dump_debug_state(&vm);
      vm_free(&vm);
      if (ok != 0) return 1;
      puts("OK c3 resident proof");
      return 0;
    }
  }

  fprintf(stderr, "C3_RUN did not complete within life=%llu\n", (unsigned long long)life);
  dump_debug_state(&vm);
  vm_free(&vm);
  return 1;
}
