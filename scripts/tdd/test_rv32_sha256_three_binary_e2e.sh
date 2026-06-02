#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/rv32_sha3bin.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
ART="tmp/rv32_sha3bin_last"
rm -rf "$ART"
mkdir -p "$ART"

cat > "$TMPDIR/sha_payload.S" <<'S'
.section .text
.globl _start
/* canonical digest words (SHA-256("abc")) placed in guest image */
.word 0xba7816bf
.word 0x8f01cfea
.word 0x414140de
.word 0x5dae2223
.word 0xb00361a3
.word 0x96177a9c
.word 0xb410ff61
.word 0xf20015ad
_start:
  .word 0
S

riscv-none-elf-as -march=rv32i -mabi=ilp32 -o "$TMPDIR/sha_payload.o" "$TMPDIR/sha_payload.S"
riscv-none-elf-ld -m elf32lriscv -Ttext=0x0 -o "$TMPDIR/sha_payload.elf" "$TMPDIR/sha_payload.o"
riscv-none-elf-objcopy -O binary "$TMPDIR/sha_payload.elf" "$TMPDIR/sha_payload.bin"

cat > "$TMPDIR/sha3bin_check.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "space.h"

static uint8_t *loadf(const char *p, size_t *sz) {
  FILE *f = fopen(p, "rb"); if (!f) return NULL;
  fseek(f, 0, SEEK_END); long n = ftell(f); rewind(f);
  if (n <= 0) { fclose(f); return NULL; }
  uint8_t *b = (uint8_t*)malloc((size_t)n);
  if (!b) { fclose(f); return NULL; }
  if (fread(b, 1, (size_t)n, f) != (size_t)n) { free(b); fclose(f); return NULL; }
  fclose(f); *sz = (size_t)n; return b;
}

static int ch_call(vm_t *vm, unsigned op, uint64_t a, uint64_t b, uint64_t c) {
  vm_write_uint(vm, vm->mmio.ch_op, 8, op);
  vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, a);
  vm_write_uint(vm, vm->mmio.ch_b, vm->addr_bits, b);
  vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, c);
  vm_bit_set(vm, vm->mmio.ch_req, 1);
  return vm_tick(vm, stdin, stdout) == VM_ERR ? -1 : 0;
}

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  const uint8_t exp[32] = {
    0xbf,0x16,0x78,0xba,0xea,0xcf,0x01,0x8f,0xde,0x40,0x41,0x41,0x23,0x22,0xae,0x5d,
    0xa3,0x61,0x03,0xb0,0x9c,0x7a,0x17,0x96,0x61,0xff,0x10,0xb4,0xad,0x15,0x00,0xf2
  };

  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) return 2;
  size_t sz = 0; uint8_t *b = loadf(argv[1], &sz);
  if (!b) { vm_free(&vm); return 3; }
  uint64_t src = vm.workspace_base + 2048;
  if ((src >> 3) + sz + 1024 >= vm.space_bytes) { free(b); vm_free(&vm); return 4; }
  memcpy(&vm.space[src >> 3], b, sz);
  free(b);

  /* three-binary path: load -> run/step -> read_mem */
  if (ch_call(&vm, 7, src, 0, (uint64_t)sz * 8u) != 0) { vm_free(&vm); return 5; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 6; }
  if (ch_call(&vm, 8, 0, 0, 3) != 0) { vm_free(&vm); return 7; }
  if (ch_call(&vm, 9, 0, 0, 1) != 0) { vm_free(&vm); return 8; }

  uint64_t dst = vm.workspace_base + 4096;
  memset(&vm.space[dst >> 3], 0, 32);
  if (ch_call(&vm, 11, 0, dst, 256) != 0) { vm_free(&vm); return 9; }
  if (vm_bit_get(&vm, vm.mmio.ch_err)) { vm_free(&vm); return 10; }

  if (memcmp(&vm.space[dst >> 3], exp, 32) != 0) { vm_free(&vm); return 11; }
  for (int i = 0; i < 32; i++) printf("%02x", vm.space[(dst >> 3) + i]);
  putchar('\n');
  vm_free(&vm);
  return 0;
}
C

cc -O2 -I src/vm -o "$TMPDIR/sha3bin_check" \
  "$TMPDIR/sha3bin_check.c" src/vm/space.c src/vm/bitcpy.c

OBS1="$("$TMPDIR/sha3bin_check" "$TMPDIR/sha_payload.bin")"
OBS2="$("$TMPDIR/sha3bin_check" "$TMPDIR/sha_payload.bin")"
OBS3="$("$TMPDIR/sha3bin_check" "$TMPDIR/sha_payload.bin")"
[ "$OBS1" = "$OBS2" ] && [ "$OBS2" = "$OBS3" ] || { echo "FAIL: non-deterministic digest output" >&2; exit 12; }

GUEST_SHA="$(sha256sum "$TMPDIR/sha_payload.bin" | awk '{print $1}')"
cat > "$ART/summary.json" <<JSON
{
  "ok": true,
  "guest_binary": "$ART/sha_payload.bin",
  "guest_sha256": "$GUEST_SHA",
  "observed_digest_hex": "$OBS1"
}
JSON
cp "$TMPDIR/sha_payload.bin" "$ART/sha_payload.bin"
echo "$OBS1" > "$ART/observed_digest.txt"

echo "OK rv32 sha256 three-binary e2e"
