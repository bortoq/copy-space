// resident_tool_invocation_proof.c - proof gate for resident tool invocation contract
#include "space.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  uint32_t job_id;
  uint32_t tool_id;
  uint32_t entry;
  uint32_t arg0;
  uint32_t arg1;
  uint32_t status;
} resident_tool_invocation_t;

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

static void write_rec(uint8_t *p, const resident_tool_invocation_t *r) {
  wr_u32le(p + 0u, r->job_id);
  wr_u32le(p + 4u, r->tool_id);
  wr_u32le(p + 8u, r->entry);
  wr_u32le(p + 12u, r->arg0);
  wr_u32le(p + 16u, r->arg1);
  wr_u32le(p + 20u, r->status);
}

static resident_tool_invocation_t read_rec(const uint8_t *p) {
  resident_tool_invocation_t r;
  r.job_id = rd_u32le(p + 0u);
  r.tool_id = rd_u32le(p + 4u);
  r.entry   = rd_u32le(p + 8u);
  r.arg0    = rd_u32le(p + 12u);
  r.arg1    = rd_u32le(p + 16u);
  r.status  = rd_u32le(p + 20u);
  return r;
}

int main(void) {
  vm_t vm;
  if (vm_init(&vm, VM_SPACE_BYTES, VM_PROCESSOR_N) != 0) {
    fprintf(stderr, "vm_init failed\n");
    return 1;
  }

  const resident_tool_invocation_t prepared = {
    .job_id = 7u,
    .tool_id = 3u,
    .entry = 0x4000u,
    .arg0 = 0x11111111u,
    .arg1 = 0x22222222u,
    .status = 0u
  };
  const resident_tool_invocation_t launched = {
    .job_id = 7u,
    .tool_id = 3u,
    .entry = 0x4000u,
    .arg0 = 0x11111111u,
    .arg1 = 0x22222222u,
    .status = 1u
  };
  const resident_tool_invocation_t completed = {
    .job_id = 7u,
    .tool_id = 3u,
    .entry = 0x4000u,
    .arg0 = 0x11111111u,
    .arg1 = 0x22222222u,
    .status = 2u
  };

  uint8_t *blob = &vm.space[vm.workspace_base >> 3];
  write_rec(blob, &prepared);
  resident_tool_invocation_t got = read_rec(blob);
  if (memcmp(&got, &prepared, sizeof(got)) != 0) {
    fprintf(stderr, "prepared invocation record mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &launched);
  got = read_rec(blob);
  if (memcmp(&got, &launched, sizeof(got)) != 0) {
    fprintf(stderr, "launch transition mismatch\n");
    vm_free(&vm);
    return 1;
  }

  write_rec(blob, &completed);
  got = read_rec(blob);
  if (memcmp(&got, &completed, sizeof(got)) != 0) {
    fprintf(stderr, "completion transition mismatch\n");
    vm_free(&vm);
    return 1;
  }

  puts("OK resident tool invocation proof");
  vm_free(&vm);
  return 0;
}
