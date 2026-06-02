#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_freertos_chio.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
ART="tmp/rv32_freertos_last"
rm -rf "$ART"
mkdir -p "$ART"

cat > "$TMPDIR/freertos_chio.S" <<'S'
.section .text
.globl _start
_start:
loop:
  lw t0, 0x180(zero)    # cmd
  beq t0, zero, loop
  addi t1, zero, 1
  bne t0, t1, loop

  addi t2, zero, 0
  sw t2, 0x180(zero)    # clear cmd

  lw t3, 0x190(zero)    # tick_count
  addi t3, t3, 1
  sw t3, 0x190(zero)

  addi t4, zero, 1
  sw t4, 0x18c(zero)    # task_count=1

  addi t5, zero, 112    # 0x70
  sw t5, 0x194(zero)    # heap_watermark

  addi t6, zero, 0x91
  sw t6, 0x188(zero)    # rsp

  jal zero, loop
S

riscv-none-elf-as -march=rv32im -mabi=ilp32 -o "$TMPDIR/freertos_chio.o" "$TMPDIR/freertos_chio.S"
riscv-none-elf-ld -m elf32lriscv -Ttext=0x0 -o "$TMPDIR/freertos_chio.elf" "$TMPDIR/freertos_chio.o"
riscv-none-elf-objcopy -O binary "$TMPDIR/freertos_chio.elf" "$TMPDIR/freertos_chio.bin"
cp "$TMPDIR/freertos_chio.bin" "$ART/freertos_chio.bin"

cat > "$TMPDIR/freertos_chio_check.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "space.h"

static int ch_call(vm_t *vm, unsigned op, uint64_t a, uint64_t b, uint64_t c) {
  vm_write_uint(vm, vm->mmio.ch_op, 8, op);
  vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, a);
  vm_write_uint(vm, vm->mmio.ch_b, vm->addr_bits, b);
  vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, c);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
  return vm_tick(vm, stdin, stdout) == VM_ERR ? -1 : 0;
}

static uint8_t *loadf(const char *p, size_t *sz) {
  FILE *f = fopen(p, "rb"); if (!f) return NULL;
  fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
  if (n <= 0) { fclose(f); return NULL; }
  uint8_t *b = (uint8_t*)malloc((size_t)n);
  if (!b) { fclose(f); return NULL; }
  if (fread(b, 1, (size_t)n, f) != (size_t)n) { free(b); fclose(f); return NULL; }
  fclose(f); *sz = (size_t)n; return b;
}

static uint32_t rd32le(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int run_session(const char *bin, char out[64]) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;
  size_t sz = 0;
  uint8_t *b = loadf(bin, &sz);
  if (!b) { vm_free(&vm); return 3; }
  uint64_t src = vm.workspace_base + 2048;
  memcpy(&vm.space[src >> 3], b, sz);
  free(b);

  if (ch_call(&vm, 7, src, 0, (uint64_t)sz * 8u) != 0) { vm_free(&vm); return 4; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 5; }

  if (ch_call(&vm, 8, 0, 0, 5000) != 0) { vm_free(&vm); return 6; }

  uint64_t wbuf = vm.workspace_base + 4096;
  memset(&vm.space[wbuf >> 3], 0, 8);
  vm.space[wbuf >> 3] = 1; /* cmd=1 */
  if (ch_call(&vm, 12, wbuf, 0x180ULL * 8ULL, 32) != 0) { vm_free(&vm); return 7; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 8; }

  uint64_t rbuf = vm.workspace_base + 8192;
  int ok = 0;
  for (int i = 0; i < 256; i++) {
    if (vm_tick(&vm, stdin, stdout) == VM_ERR) { vm_free(&vm); return 9; }
    memset(&vm.space[rbuf >> 3], 0, 16);
    if (ch_call(&vm, 11, 0x188ULL * 8ULL, rbuf, 128) != 0) { vm_free(&vm); return 10; }
    if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 11; }
    uint8_t *p = &vm.space[rbuf >> 3];
    uint32_t rsp = rd32le(p + 0);
    uint32_t taskc = rd32le(p + 4);
    uint32_t ticks = rd32le(p + 8);
    uint32_t heapw = rd32le(p + 12);
    if (rsp == 0x91u) {
      if (taskc != 1u) { vm_free(&vm); return 12; }
      if (ticks < 1u) { vm_free(&vm); return 13; }
      if (heapw != 0x70u) { vm_free(&vm); return 14; }
      snprintf(out, 64, "%08x-%08x-%08x-%08x", rsp, taskc, ticks, heapw);
      ok = 1;
      break;
    }
  }

  if (!ok) { vm_free(&vm); return 15; }
  vm_free(&vm);
  return 0;
}

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  char a[64], b[64], c[64];
  if (run_session(argv[1], a) != 0) return 2;
  if (run_session(argv[1], b) != 0) return 3;
  if (run_session(argv[1], c) != 0) return 4;
  if (strcmp(a, b) || strcmp(b, c)) return 5;
  puts(a);
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/freertos_chio_check" \
  "$TMPDIR/freertos_chio_check.c" src/vm/space.c src/vm/bitcpy.c

OBS="$("$TMPDIR/freertos_chio_check" "$TMPDIR/freertos_chio.bin")"
TRANSCRIPT='LOAD_CODE,RUN,WRITE_MEM,STEP,READ_MEM'
GUEST_SHA="$(sha256sum "$TMPDIR/freertos_chio.bin" | awk '{print $1}')"
TRANSCRIPT_SHA="$(printf '%s' "$TRANSCRIPT" | sha256sum | awk '{print $1}')"

python3 - <<PY
import json
obs = "${OBS}".strip()
parts = obs.split('-')
if len(parts) != 4:
    raise SystemExit("FAIL: malformed OBS")
rsp, taskc, ticks, heapw = [int(x, 16) for x in parts]
bundle = {
  "ok": True,
  "guest_binary": "tmp/rv32_freertos_last/freertos_chio.bin",
  "guest_sha256": "${GUEST_SHA}",
  "command_transcript": "${TRANSCRIPT}",
  "command_transcript_hash": "${TRANSCRIPT_SHA}",
  "final_snapshot": {
    "rsp": rsp,
    "task_count": taskc,
    "tick_count": ticks,
    "heap_watermark": heapw,
  },
}
open("tmp/rv32_freertos_last/summary.json", "w", encoding="utf-8").write(json.dumps(bundle, indent=2) + "\n")
print("OK rv32 freertos channel io e2e")
PY
