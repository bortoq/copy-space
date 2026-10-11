// resident_copicode_artifact_proof.c - proof gate for resident copicode artifact contract
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  uint32_t artifact_id;
  uint32_t payload_id;
  uint32_t entry;
  uint32_t size;
  uint32_t flags;
  uint32_t status;
} resident_copicode_artifact_t;

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

static void write_rec(uint8_t *p, const resident_copicode_artifact_t *r) {
  wr_u32le(p + 0u, r->artifact_id);
  wr_u32le(p + 4u, r->payload_id);
  wr_u32le(p + 8u, r->entry);
  wr_u32le(p + 12u, r->size);
  wr_u32le(p + 16u, r->flags);
  wr_u32le(p + 20u, r->status);
}

static resident_copicode_artifact_t read_rec(const uint8_t *p) {
  resident_copicode_artifact_t r;
  r.artifact_id = rd_u32le(p + 0u);
  r.payload_id  = rd_u32le(p + 4u);
  r.entry       = rd_u32le(p + 8u);
  r.size        = rd_u32le(p + 12u);
  r.flags       = rd_u32le(p + 16u);
  r.status      = rd_u32le(p + 20u);
  return r;
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  const resident_copicode_artifact_t prepared = {
    .artifact_id = 101u,
    .payload_id = 202u,
    .entry = 0x5000u,
    .size = 0x80u,
    .flags = 0x1u,
    .status = 0u
  };
  const resident_copicode_artifact_t loaded = {
    .artifact_id = 101u,
    .payload_id = 202u,
    .entry = 0x5000u,
    .size = 0x80u,
    .flags = 0x1u,
    .status = 1u
  };
  const resident_copicode_artifact_t handoff_ready = {
    .artifact_id = 101u,
    .payload_id = 202u,
    .entry = 0x5000u,
    .size = 0x80u,
    .flags = 0x1u,
    .status = 2u
  };

  uint8_t *blob = &vm.space[vm.workspace_base >> 3];
  write_rec(blob, &prepared);
  resident_copicode_artifact_t got = read_rec(blob);
  if (memcmp(&got, &prepared, sizeof(got)) != 0) {
    fprintf(stderr, "prepared artifact mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &loaded);
  got = read_rec(blob);
  if (memcmp(&got, &loaded, sizeof(got)) != 0) {
    fprintf(stderr, "loaded artifact mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &handoff_ready);
  got = read_rec(blob);
  if (memcmp(&got, &handoff_ready, sizeof(got)) != 0) {
    fprintf(stderr, "handoff-ready artifact mismatch\n");
    vm_free(&vm);
    return 1;
  }

  puts("OK resident copicode artifact proof");
  vm_free(&vm);
  return 0;
}
