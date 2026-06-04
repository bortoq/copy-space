// resident_copicode_toolchain_control_records_proof.c - proof gate for resident copicode toolchain control records
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  uint32_t artifact_id;
  uint32_t toolchain_id;
  uint32_t control_id;
  uint32_t stage;
  uint32_t mode;
  uint32_t status;
} resident_copicode_toolchain_control_record_t;

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

static void write_rec(uint8_t *p, const resident_copicode_toolchain_control_record_t *r) {
  wr_u32le(p + 0u, r->artifact_id);
  wr_u32le(p + 4u, r->toolchain_id);
  wr_u32le(p + 8u, r->control_id);
  wr_u32le(p + 12u, r->stage);
  wr_u32le(p + 16u, r->mode);
  wr_u32le(p + 20u, r->status);
}

static resident_copicode_toolchain_control_record_t read_rec(const uint8_t *p) {
  resident_copicode_toolchain_control_record_t r;
  r.artifact_id = rd_u32le(p + 0u);
  r.toolchain_id = rd_u32le(p + 4u);
  r.control_id = rd_u32le(p + 8u);
  r.stage = rd_u32le(p + 12u);
  r.mode = rd_u32le(p + 16u);
  r.status = rd_u32le(p + 20u);
  return r;
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  const resident_copicode_toolchain_control_record_t prepared = {
    .artifact_id = 101u,
    .toolchain_id = 202u,
    .control_id = 303u,
    .stage = 1u,
    .mode = 2u,
    .status = 0u
  };
  const resident_copicode_toolchain_control_record_t controlled = {
    .artifact_id = 101u,
    .toolchain_id = 202u,
    .control_id = 303u,
    .stage = 1u,
    .mode = 2u,
    .status = 1u
  };
  const resident_copicode_toolchain_control_record_t materialized = {
    .artifact_id = 101u,
    .toolchain_id = 202u,
    .control_id = 303u,
    .stage = 1u,
    .mode = 2u,
    .status = 2u
  };

  uint8_t *blob = &vm.space[vm.workspace_base >> 3];
  write_rec(blob, &prepared);
  resident_copicode_toolchain_control_record_t got = read_rec(blob);
  if (memcmp(&got, &prepared, sizeof(got)) != 0) {
    fprintf(stderr, "prepared toolchain control mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &controlled);
  got = read_rec(blob);
  if (memcmp(&got, &controlled, sizeof(got)) != 0) {
    fprintf(stderr, "controlled toolchain control mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &materialized);
  got = read_rec(blob);
  if (memcmp(&got, &materialized, sizeof(got)) != 0) {
    fprintf(stderr, "materialized toolchain control mismatch\n");
    vm_free(&vm);
    return 1;
  }

  puts("OK resident copicode toolchain control records proof");
  vm_free(&vm);
  return 0;
}
