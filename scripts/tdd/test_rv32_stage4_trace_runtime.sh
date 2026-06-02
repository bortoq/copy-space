#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_stage4_trace.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

cat > "$TMPDIR/rv32_stage4_trace_check.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "space.h"

static const uint64_t G_REG_BASE = 0x001200ull;

enum {
  CH_OP_LOAD_CODE = 7,
  CH_OP_RUN = 8,
  CH_OP_TRACE_INFO = 13,
  CH_OP_TRACE_READ = 14
};

typedef struct {
  uint32_t version;
  uint32_t record_bytes;
  uint32_t record_count;
  uint32_t used_bytes;
  uint32_t dropped_records;
} trace_info_t;

static int ch_call(vm_t *vm, unsigned op, uint64_t a, uint64_t b, uint64_t c) {
  vm_write_uint(vm, vm->mmio.ch_op, 8, op);
  vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, a);
  vm_write_uint(vm, vm->mmio.ch_b, vm->addr_bits, b);
  vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, c);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
  return vm_tick(vm, stdin, stdout) == VM_ERR ? -1 : 0;
}

static void wr32(vm_t *vm, uint64_t bit_addr, uint32_t v) {
  size_t b = (size_t)(bit_addr >> 3);
  vm->space[b] = (uint8_t)(v & 0xffu);
  vm->space[b + 1] = (uint8_t)((v >> 8) & 0xffu);
  vm->space[b + 2] = (uint8_t)((v >> 16) & 0xffu);
  vm->space[b + 3] = (uint8_t)((v >> 24) & 0xffu);
}

static uint32_t enc_op_imm(unsigned rd, unsigned rs1, int imm, unsigned funct3) {
  return (((uint32_t)imm & 0xfffu) << 20) | ((rs1 & 0x1fu) << 15) |
         ((funct3 & 7u) << 12) | ((rd & 0x1fu) << 7) | 0x13u;
}

static int run_program(vm_t *vm, const uint32_t *prog, size_t n_words, unsigned max_ticks) {
  uint64_t src = vm->workspace_base + 2048;
  uint8_t *buf = &vm->space[src >> 3];
  memset(buf, 0, n_words * 4 + 16);
  for (size_t i = 0; i < n_words; i++) {
    buf[i * 4 + 0] = (uint8_t)(prog[i] & 0xffu);
    buf[i * 4 + 1] = (uint8_t)((prog[i] >> 8) & 0xffu);
    buf[i * 4 + 2] = (uint8_t)((prog[i] >> 16) & 0xffu);
    buf[i * 4 + 3] = (uint8_t)((prog[i] >> 24) & 0xffu);
  }

  if (ch_call(vm, CH_OP_LOAD_CODE, src, 0, (uint64_t)n_words * 32u) != 0) return 1;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return 2;
  if (ch_call(vm, CH_OP_RUN, 0, 0, max_ticks) != 0) return 3;
  if (vm_bit_get(vm, vm->mmio.ch_err)) return 4;

  for (unsigned i = 0; i < max_ticks + 4; i++) {
    if (vm_bit_get(vm, vm->mmio.halt)) return 0;
    if (vm_tick(vm, stdin, stdout) == VM_ERR) return 5;
  }
  return 6;
}

int main(void) {
  vm_t vm;
  trace_info_t info;
  uint8_t records[256];
  uint64_t info_dst;
  uint64_t trace_dst;

  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 10;

  const uint32_t prog[] = {
    enc_op_imm(1, 0, 1, 0),
    enc_op_imm(2, 1, 2, 0),
    0u
  };
  if (run_program(&vm, prog, sizeof(prog) / sizeof(prog[0]), 16) != 0) {
    vm_free(&vm);
    return 11;
  }

  info_dst = vm.workspace_base + 4096;
  memset(&vm.space[info_dst >> 3], 0, sizeof(info));
  if (ch_call(&vm, CH_OP_TRACE_INFO, info_dst, 0, 0) != 0) {
    vm_free(&vm);
    return 12;
  }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) {
    vm_free(&vm);
    return 13;
  }
  memcpy(&info, &vm.space[info_dst >> 3], sizeof(info));
  if (info.version != 1u) {
    vm_free(&vm);
    return 14;
  }
  if (info.record_count < 3u) {
    vm_free(&vm);
    return 15;
  }
  if (info.record_bytes == 0u || info.used_bytes < info.record_bytes) {
    vm_free(&vm);
    return 16;
  }

  trace_dst = vm.workspace_base + 8192;
  memset(&vm.space[trace_dst >> 3], 0, sizeof(records));
  if (ch_call(&vm, CH_OP_TRACE_READ, 0, trace_dst, (uint64_t)info.record_bytes * 8u) != 0) {
    vm_free(&vm);
    return 17;
  }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) {
    vm_free(&vm);
    return 18;
  }
  memcpy(records, &vm.space[trace_dst >> 3], info.record_bytes);
  if (records[0] == 0 && records[1] == 0 && records[2] == 0 && records[3] == 0) {
    vm_free(&vm);
    return 19;
  }

  vm_free(&vm);
  puts("OK rv32 stage4 trace runtime");
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/rv32_stage4_trace_check" \
  "$TMPDIR/rv32_stage4_trace_check.c" src/vm/space.c src/vm/bitcpy.c

"$TMPDIR/rv32_stage4_trace_check"
