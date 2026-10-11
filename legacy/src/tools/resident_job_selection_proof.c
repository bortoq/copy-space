// resident_job_selection_proof.c - proof gate for resident job selection contract
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { TABLE_BYTES = 5u * 4u };

typedef struct {
  uint32_t kind;
  uint32_t entry;
  uint32_t arg0;
  uint32_t arg1;
  uint32_t flags;
} resident_job_desc_t;

static void wr_u32le(uint8_t *dst, uint32_t v) {
  dst[0] = (uint8_t)(v & 0xffu);
  dst[1] = (uint8_t)((v >> 8) & 0xffu);
  dst[2] = (uint8_t)((v >> 16) & 0xffu);
  dst[3] = (uint8_t)((v >> 24) & 0xffu);
}

static uint32_t rd_u32le(const uint8_t *src) {
  return (uint32_t)src[0] |
         ((uint32_t)src[1] << 8) |
         ((uint32_t)src[2] << 16) |
         ((uint32_t)src[3] << 24);
}

static void write_desc(uint8_t *p, const resident_job_desc_t *d) {
  wr_u32le(p + 0u, d->kind);
  wr_u32le(p + 4u, d->entry);
  wr_u32le(p + 8u, d->arg0);
  wr_u32le(p + 12u, d->arg1);
  wr_u32le(p + 16u, d->flags);
}

static int select_job(const uint8_t *table, size_t count) {
  for (size_t i = 0; i < count; i++) {
    const uint8_t *p = table + i * sizeof(resident_job_desc_t);
    uint32_t kind = rd_u32le(p + 0u);
    uint32_t flags = rd_u32le(p + 16u);
    if (kind != 0u && (flags & 1u)) return (int)i;
  }
  return -1;
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  uint8_t *table = &vm.space[vm.workspace_base >> 3];
  memset(table, 0, TABLE_BYTES);

  const resident_job_desc_t jobs[3] = {
    { .kind = 0u, .entry = 0x1000u, .arg0 = 1u, .arg1 = 2u, .flags = 1u },
    { .kind = 2u, .entry = 0x2000u, .arg0 = 3u, .arg1 = 4u, .flags = 1u },
    { .kind = 3u, .entry = 0x3000u, .arg0 = 5u, .arg1 = 6u, .flags = 1u }
  };

  for (size_t i = 0; i < 3; i++) {
    write_desc(table + i * sizeof(resident_job_desc_t), &jobs[i]);
  }

  int idx = select_job(table, 3u);
  if (idx != 1) {
    fprintf(stderr, "selection mismatch: got=%d want=1\n", idx);
    vm_free(&vm);
    return 1;
  }

  const resident_job_desc_t *sel = (const resident_job_desc_t *)(void *)(table + (size_t)idx * sizeof(resident_job_desc_t));
  if (sel->entry != 0x2000u || sel->arg0 != 3u || sel->arg1 != 4u) {
    fprintf(stderr, "selected job fields mismatch\n");
    vm_free(&vm);
    return 1;
  }

  puts("OK resident job selection proof");
  vm_free(&vm);
  return 0;
}
