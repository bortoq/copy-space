#include "words.h"
#include "words_int.h"
#include <stdint.h>

void write_word_setup_inspace(vm_t *vm, bitaddr_t img, bitaddr_t branch_img,
                               bitaddr_t var_src_addr, bitaddr_t var_src_end,
                               bitaddr_t var_token,
                               bitaddr_t const1_base)
{
  nop_fill_image(vm, img);
  bitaddr_t A = vm->addr_bits;
  bitaddr_t I = (bitaddr_t)vm->instr_bits;
  unsigned patch_slot = vm->processor_n - 2;
  unsigned load_slot  = vm->processor_n - 1;

  /* --- Data area: store literal values past processor area --- */
  bitaddr_t data = (img + vm->processor_bits + 7u) & ~(bitaddr_t)7u;
  vm_write_uint(vm, data,     A, (uint64_t)var_token);
  vm_write_uint(vm, data + A, A, (uint64_t)A);

  /* slot0: NOP, dst = branch_img (chain-load target) */
  vm_write_inst(vm, img + 0, (vm_inst_t){ .n=0, .dst=(uint64_t)branch_img, .src=0 });

  unsigned s = 1;

  /* --- Slot s: copy VAR_SRC_ADDR -> mmio.in_src_addr --- */
  vm_write_inst(vm, img + (bitaddr_t)s * I,
    (vm_inst_t){ .n=A, .dst=(uint64_t)vm->mmio.in_src_addr, .src=(uint64_t)var_src_addr });
  s++;

  /* --- Slot s: copy VAR_SRC_END -> mmio.in_src_end --- */
  vm_write_inst(vm, img + (bitaddr_t)s * I,
    (vm_inst_t){ .n=A, .dst=(uint64_t)vm->mmio.in_src_end, .src=(uint64_t)var_src_end });
  s++;

  /* --- Slot s: copy literal var_token from data -> mmio.in_dst --- */
  vm_write_inst(vm, img + (bitaddr_t)s * I,
    (vm_inst_t){ .n=A, .dst=(uint64_t)vm->mmio.in_dst, .src=(uint64_t)data });
  s++;

  /* --- Slot s: copy literal A from data+A -> mmio.in_len --- */
  vm_write_inst(vm, img + (bitaddr_t)s * I,
    (vm_inst_t){ .n=A, .dst=(uint64_t)vm->mmio.in_len, .src=(uint64_t)(data + A) });
  s++;

  /* --- Slot s: set in_src_mode = 1 --- */
  vm_write_inst(vm, img + (bitaddr_t)s * I,
    (vm_inst_t){ .n=1, .dst=(uint64_t)vm->mmio.in_src_mode, .src=(uint64_t)(const1_base + 42) });
  s++;

  /* --- Slot s: set in_req = 1 --- */
  vm_write_inst(vm, img + (bitaddr_t)s * I,
    (vm_inst_t){ .n=1, .dst=(uint64_t)vm->mmio.in_req, .src=(uint64_t)(const1_base + 43) });
  s++;

  /* --- Chain-load: BRANCH page --- */
  bitaddr_t slot0_dst = vm_proc_slot_field_ip(vm, 0, vm->off_dst);
  bitaddr_t load_src  = vm_proc_slot_field_ip(vm, load_slot, vm->off_src);
  vm_write_inst(vm, img + (bitaddr_t)patch_slot * I,
    (vm_inst_t){ .n=A, .dst=(uint64_t)load_src, .src=(uint64_t)slot0_dst });
  vm_write_inst(vm, img + (bitaddr_t)load_slot * I,
    (vm_inst_t){ .n=vm->processor_bits, .dst=0, .src=0 });
}
