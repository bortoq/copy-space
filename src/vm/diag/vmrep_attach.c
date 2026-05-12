/* vmrep_attach.c — attach vmrep instrumentation to VM hooks */
#include "vmrep_attach.h"
#include "vmrep.h"

static void vmrep_hook_tick_begin(void *user, size_t slots_cap) {
  (void)user;
  vmrep_tick_begin(slots_cap);
}

static void vmrep_hook_note_copy(void *user, uint64_t dst, uint64_t n, uint64_t src) {
  (void)user;
  (void)src;
  vmrep_note_copy(dst, n);
}

static void vmrep_hook_tick_end(void *user) {
  (void)user;
  vmrep_tick_end();
}

void vmrep_attach(vm_t *vm) {
  if (!vm) return;
  vm->hooks.user = NULL;
  vm->hooks.tick_begin = vmrep_hook_tick_begin;
  vm->hooks.note_copy  = vmrep_hook_note_copy;
  vm->hooks.tick_end   = vmrep_hook_tick_end;
}
