// vmprep_forth0.c — prepare compiled_space.bin for running compiled Forth0 program.
// Reads artifact from workspace, resets MMIO, sets VAR_IP = START_CELL,
// replaces processor area with boot that loads NEXT_IMG.

#include "space.h"
#include <stdlib.h>
#include <string.h>

static void usage(const char *a0) {
  fprintf(stderr, "usage: %s --image compiled_space.bin [--space-bytes N] [--processor-n N]\n", a0);
}

static int load_image(vm_t *vm, const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { perror("fopen"); return -1; }
  if (fseek(f, 0, SEEK_END) != 0) { perror("fseek"); fclose(f); return -1; }
  long sz = ftell(f);
  if (sz < 0) { perror("ftell"); fclose(f); return -1; }
  rewind(f);
  if ((size_t)sz != vm->space_bytes) {
    fprintf(stderr, "size mismatch: file=%ld expected=%zu\n", sz, vm->space_bytes);
    fclose(f);
    return -1;
  }
  if (fread(vm->space, 1, vm->space_bytes, f) != vm->space_bytes) {
    perror("fread"); fclose(f); return -1;
  }
  fclose(f);
  return 0;
}

static int save_image(const vm_t *vm, const char *path) {
  FILE *f = fopen(path, "wb");
  if (!f) { perror("fopen"); return -1; }
  if (fwrite(vm->space, 1, vm->space_bytes, f) != vm->space_bytes) {
    perror("fwrite"); fclose(f); return -1;
  }
  fclose(f);
  return 0;
}

static void clear_mmio(vm_t *vm) {
  vm_bit_set(vm, vm->mmio.in_req, 0);
  vm_bit_set(vm, vm->mmio.in_done, 0);
  vm_bit_set(vm, vm->mmio.in_eof, 0);
  vm_bit_set(vm, vm->mmio.in_err, 0);
  vm_write_uint(vm, vm->mmio.in_dst, vm->addr_bits, 0);
  vm_write_uint(vm, vm->mmio.in_len, vm->n_bits, 0);
  vm_write_uint(vm, vm->mmio.in_got, vm->n_bits, 0);

  vm_bit_set(vm, vm->mmio.out_req, 0);
  vm_bit_set(vm, vm->mmio.out_done, 0);
  vm_bit_set(vm, vm->mmio.out_err, 0);
  vm_write_uint(vm, vm->mmio.out_src, vm->addr_bits, 0);
  vm_write_uint(vm, vm->mmio.out_len, vm->n_bits, 0);
  vm_write_uint(vm, vm->mmio.out_got, vm->n_bits, 0);

  vm_bit_set(vm, vm->mmio.halt, 0);
}

static void install_boot_load(vm_t *vm, uint64_t next_img) {
  vm_inst_t nop = (vm_inst_t){0,0,0};
  for (unsigned s = 0; s < vm->processor_n; s++)
    vm_write_inst(vm, vm_proc_slot_ip(vm, s), nop);

  vm_inst_t load = (vm_inst_t){
    .n   = (uint64_t)vm->processor_bits,
    .dst = 0,
    .src = next_img
  };
  vm_write_inst(vm, vm_proc_slot_ip(vm, vm->processor_n - 1), load);
}

int main(int argc, char **argv) {
  const char *image = NULL;
  size_t space_bytes = VM_SPACE_BYTES;
  unsigned processor_n = VM_PROCESSOR_N;

  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--image") && i+1 < argc) image = argv[++i];
    else if (!strcmp(argv[i], "--space-bytes") && i+1 < argc) space_bytes = (size_t)strtoull(argv[++i], NULL, 0);
    else if (!strcmp(argv[i], "--processor-n") && i+1 < argc) processor_n = (unsigned)strtoul(argv[++i], NULL, 0);
    else { usage(argv[0]); return 2; }
  }
  if (!image) { usage(argv[0]); return 2; }

  vm_t vm;
  if (vm_init(&vm, space_bytes, processor_n) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }
  if (load_image(&vm, image) != 0) { vm_free(&vm); return 1; }

  bitaddr_t W = vm.workspace_base;
  bitaddr_t ART = (W + 512u + 7u) & ~(bitaddr_t)7u;

  uint64_t start_cell = vm_read_uint(&vm, ART + 0*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t next_img   = vm_read_uint(&vm, ART + 1*(bitaddr_t)vm.addr_bits, vm.addr_bits);
  uint64_t var_ip     = vm_read_uint(&vm, ART + 2*(bitaddr_t)vm.addr_bits, vm.addr_bits);

  clear_mmio(&vm);

  // set VAR_IP = START_CELL
  vm_write_uint(&vm, (bitaddr_t)var_ip, vm.addr_bits, start_cell);

  // install boot to load NEXT
  install_boot_load(&vm, next_img);

  if (save_image(&vm, image) != 0) { vm_free(&vm); return 1; }

  fprintf(stderr, "Prepared %s for Forth0 run: START_CELL=%llu NEXT_IMG=%llu VAR_IP=%llu\n",
          image,
          (unsigned long long)start_cell,
          (unsigned long long)next_img,
          (unsigned long long)var_ip);

  vm_free(&vm);
  return 0;
}