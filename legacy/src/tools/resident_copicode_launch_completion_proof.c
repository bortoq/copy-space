// resident_copicode_launch_completion_proof.c - proof gate for resident copicode launch completion
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  uint32_t artifact_id;
  uint32_t launch_id;
  uint32_t completion_id;
  uint32_t entry;
  uint32_t status;
} resident_copicode_launch_completion_t;

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

static void write_rec(uint8_t *p, const resident_copicode_launch_completion_t *r) {
  wr_u32le(p + 0u, r->artifact_id);
  wr_u32le(p + 4u, r->launch_id);
  wr_u32le(p + 8u, r->completion_id);
  wr_u32le(p + 12u, r->entry);
  wr_u32le(p + 16u, r->status);
}

static resident_copicode_launch_completion_t read_rec(const uint8_t *p) {
  resident_copicode_launch_completion_t r;
  r.artifact_id = rd_u32le(p + 0u);
  r.launch_id = rd_u32le(p + 4u);
  r.completion_id = rd_u32le(p + 8u);
  r.entry = rd_u32le(p + 12u);
  r.status = rd_u32le(p + 16u);
  return r;
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  const resident_copicode_launch_completion_t prepared = {
    .artifact_id = 101u,
    .launch_id = 202u,
    .completion_id = 303u,
    .entry = 0x5000u,
    .status = 0u
  };
  const resident_copicode_launch_completion_t launched = {
    .artifact_id = 101u,
    .launch_id = 202u,
    .completion_id = 303u,
    .entry = 0x5000u,
    .status = 1u
  };
  const resident_copicode_launch_completion_t completed = {
    .artifact_id = 101u,
    .launch_id = 202u,
    .completion_id = 303u,
    .entry = 0x5000u,
    .status = 2u
  };

  uint8_t *blob = &vm.space[vm.workspace_base >> 3];
  write_rec(blob, &prepared);
  resident_copicode_launch_completion_t got = read_rec(blob);
  if (memcmp(&got, &prepared, sizeof(got)) != 0) {
    fprintf(stderr, "prepared launch completion mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &launched);
  got = read_rec(blob);
  if (memcmp(&got, &launched, sizeof(got)) != 0) {
    fprintf(stderr, "launched completion mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &completed);
  got = read_rec(blob);
  if (memcmp(&got, &completed, sizeof(got)) != 0) {
    fprintf(stderr, "completed launch completion mismatch\n");
    vm_free(&vm);
    return 1;
  }

  puts("OK resident copicode launch completion proof");
  vm_free(&vm);
  return 0;
}
