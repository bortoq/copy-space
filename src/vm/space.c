/* space.c — VM core implementation and MMIO handshake
 */

#include "space.h"
#include "rv32.h"
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

/* -------- utilities: ceil_log2 and rounding -------- */

static unsigned ceil_log2_u64(uint64_t x) {
  /* minimal k such that 2^k >= x; x>=1 */
  unsigned k = 0;
  uint64_t p = 1;
  while (p < x) { p <<= 1; k++; }
  return k;
}
static unsigned round_up_to_8(unsigned x) {
  return (x + 7u) & ~7u;
}

/* -------- bit primitives (MSB-first) -------- */

unsigned vm_bit_get(const vm_t *vm, bitaddr_t pos) {
  uint8_t byte = vm->space[(size_t)(pos >> 3)];
  unsigned shift = 7u - (unsigned)(pos & 7u);
  return (byte >> shift) & 1u;
}

void vm_bit_set(vm_t *vm, bitaddr_t pos, unsigned v) {
  uint8_t *b = &vm->space[(size_t)(pos >> 3)];
  unsigned shift = 7u - (unsigned)(pos & 7u);
  uint8_t mask = (uint8_t)(1u << shift);
  if (v) *b |= mask;
  else   *b &= (uint8_t)~mask;
}

uint64_t vm_read_uint(const vm_t *vm, bitaddr_t pos, unsigned width) {
  if (width == 0 || width > 64) return 0;
  uint64_t v = 0;
  for (unsigned i = 0; i < width; i++) {
    v = (v << 1) | (uint64_t)vm_bit_get(vm, pos + (bitaddr_t)i);
  }
  return v;
}

void vm_write_uint(vm_t *vm, bitaddr_t pos, unsigned width, uint64_t value) {
  if (width == 0 || width > 64) return;
  for (unsigned i = 0; i < width; i++) {
    unsigned bit = (unsigned)((value >> (width - 1u - i)) & 1u);
    vm_bit_set(vm, pos + (bitaddr_t)i, bit);
  }
}

/* -------- instruction encoding -------- */

vm_inst_t vm_read_inst(const vm_t *vm, bitaddr_t ip) {
  vm_inst_t in;
  in.n   = vm_read_uint(vm, ip + (bitaddr_t)vm->off_n,   vm->n_bits);
  in.dst = vm_read_uint(vm, ip + (bitaddr_t)vm->off_dst, vm->addr_bits);
  in.src = vm_read_uint(vm, ip + (bitaddr_t)vm->off_src, vm->addr_bits);
  return in;
}

void vm_write_inst(vm_t *vm, bitaddr_t ip, vm_inst_t in) {
  vm_write_uint(vm, ip + (bitaddr_t)vm->off_n,   vm->n_bits,   in.n);
  vm_write_uint(vm, ip + (bitaddr_t)vm->off_dst, vm->addr_bits, in.dst);
  vm_write_uint(vm, ip + (bitaddr_t)vm->off_src, vm->addr_bits, in.src);
}

/* -------- MMIO layout -------- */

static void vm_compute_mmio_layout(vm_t *vm) {
  const bitaddr_t RV_GUEST_MMIO_GUARD = 0x001600ULL;

  /* Keep MMIO above the fixed guest state window:
   *   G_PC       = 0x001000
   *   G_REG_BASE = 0x001200 .. 0x0015ff
   */
  bitaddr_t p = vm->processor_bits;
  if (p < RV_GUEST_MMIO_GUARD) p = RV_GUEST_MMIO_GUARD;
  vm->mmio.base = p;

  /* IN */
  vm->mmio.in_req  = p; p += 1;
  vm->mmio.in_done = p; p += 1;
  vm->mmio.in_eof  = p; p += 1;
  vm->mmio.in_err  = p; p += 1;

  vm->mmio.in_dst  = p; p += vm->addr_bits;
  vm->mmio.in_len  = p; p += vm->n_bits;
  vm->mmio.in_got  = p; p += vm->n_bits;

  /* OUT */
  vm->mmio.out_req  = p; p += 1;
  vm->mmio.out_done = p; p += 1;
  vm->mmio.out_err  = p; p += 1;

  vm->mmio.out_src  = p; p += vm->addr_bits;
  vm->mmio.out_len  = p; p += vm->n_bits;
  vm->mmio.out_got  = p; p += vm->n_bits;

  /* Control */
  vm->mmio.halt = p; p += 1;

  /* In-space source */
  vm->mmio.in_src_mode = p; p += 1;
  vm->mmio.in_src_addr = p; p += vm->addr_bits;
  vm->mmio.in_src_end  = p; p += vm->addr_bits;

  /* Loader channel */
  vm->mmio.load_req  = p; p += 1;
  vm->mmio.load_done = p; p += 1;
  vm->mmio.load_err  = p; p += 1;
  vm->mmio.load_src  = p; p += vm->addr_bits;
  vm->mmio.load_bits = p; p += vm->n_bits;

  /* Watchdog */
  vm->mmio.wd_enable = p; p += 1;
  vm->mmio.wd_fired  = p; p += 1;
  vm->mmio.wd_limit  = p; p += vm->n_bits;
  vm->mmio.wd_ticks  = p; p += vm->n_bits;

  /* Generic channel mailbox */
  vm->mmio.ch_req  = p; p += 1;
  vm->mmio.ch_done = p; p += 1;
  vm->mmio.ch_err  = p; p += 1;
  vm->mmio.ch_op   = p; p += 8;
  vm->mmio.ch_a    = p; p += vm->addr_bits;
  vm->mmio.ch_b    = p; p += vm->addr_bits;
  vm->mmio.ch_c    = p; p += vm->n_bits;
  vm->mmio.ch_abi_version = p; p += 8;

  /* round MMIO end up to next byte boundary for nicer workspace */
  vm->mmio.end = (p + 7u) & ~(bitaddr_t)7u;
  vm->workspace_base = vm->mmio.end;
}

/* -------- init/free -------- */

int vm_init(vm_t *vm, size_t space_bytes, unsigned processor_n) {
  if (!vm) return -1;
  memset(vm, 0, sizeof *vm);

  if (space_bytes == 0) return -1;
  if (processor_n == 0) return -1;

  vm->space = (uint8_t*)calloc(1, space_bytes);
  if (!vm->space) return -1;

  vm->rv_trace_records = (rv_trace_record_t*)calloc(VM_RV_TRACE_MAX_RECORDS, sizeof(rv_trace_record_t));
  if (!vm->rv_trace_records) {
    free(vm->space);
    memset(vm, 0, sizeof *vm);
    return -1;
  }
  vm->rv_trace_capacity = VM_RV_TRACE_MAX_RECORDS;

  vm->space_bytes = space_bytes;
  vm->space_bits  = (bitaddr_t)space_bytes * 8u;
  vm->processor_n = processor_n;

  /* derive widths */
  unsigned raw = ceil_log2_u64((uint64_t)vm->space_bits);
  vm->addr_bits = round_up_to_8(raw);
  if (vm->addr_bits < 8) vm->addr_bits = 8;

  vm->n_bits = vm->addr_bits;

  vm->instr_bits  = 3u * vm->addr_bits;
  vm->instr_bytes = vm->instr_bits / 8u;

  vm->processor_start = 0;
  vm->processor_bits  = (bitaddr_t)vm->processor_n * (bitaddr_t)vm->instr_bits;

  vm->off_n   = 0;
  vm->off_dst = vm->n_bits;
  vm->off_src = vm->n_bits + vm->addr_bits;

  /* sanity: processor must fit */
  if (vm->processor_bits > vm->space_bits) { vm_free(vm); return -1; }

  vm_compute_mmio_layout(vm);

  /* sanity: mmio must fit */
  if (vm->mmio.end > vm->space_bits) { vm_free(vm); return -1; }

  vm_write_uint(vm, vm->mmio.ch_abi_version, 8, 1);

  return 0;
}

void vm_free(vm_t *vm) {
  if (!vm) return;
  free(vm->rv_trace_records);
  free(vm->space);
  memset(vm, 0, sizeof *vm);
}

/* -------- MMIO handshake service --------
 *
 * Semantics:
 * - The device checks *_REQ at the start of the tick.
 * - If REQ=1:
 *     - clears DONE/ERR/(EOF) and GOT
 *     - performs the operation (byte-aligned)
 *     - writes GOT, sets DONE=1 and (if needed) EOF/ERR
 *     - clears REQ=0
 * - DONE remains 1 until the program overwrites it via copy (if it wants to).
 */

static int service_in(vm_t *vm, FILE *in) {
  if (!vm_bit_get(vm, vm->mmio.in_req)) return 0;

  /* clear status */
  vm_bit_set(vm, vm->mmio.in_done, 0);
  vm_bit_set(vm, vm->mmio.in_eof,  0);
  vm_bit_set(vm, vm->mmio.in_err,  0);
  vm_write_uint(vm, vm->mmio.in_got, vm->n_bits, 0);

  uint64_t dst = vm_read_uint(vm, vm->mmio.in_dst, vm->addr_bits);
  uint64_t len = vm_read_uint(vm, vm->mmio.in_len, vm->n_bits);

  /* require byte alignment */
  if ((dst & 7u) || (len & 7u)) {
    vm_bit_set(vm, vm->mmio.in_err, 1);
    vm_bit_set(vm, vm->mmio.in_done, 1);
    vm_bit_set(vm, vm->mmio.in_req, 0);
    return 0;
  }

  bitaddr_t bd = (bitaddr_t)dst;
  bitaddr_t bl = (bitaddr_t)len;

  if (bd + bl > vm->space_bits) {
    vm_bit_set(vm, vm->mmio.in_err, 1);
    vm_bit_set(vm, vm->mmio.in_done, 1);
    vm_bit_set(vm, vm->mmio.in_req, 0);
    return 0;
  }

  /* Check in-space source mode */
  if (vm_bit_get(vm, vm->mmio.in_src_mode)) {
    uint64_t src_raw = vm_read_uint(vm, vm->mmio.in_src_addr, vm->addr_bits);
    uint64_t end_raw = vm_read_uint(vm, vm->mmio.in_src_end,  vm->addr_bits);
    bitaddr_t src_addr = (bitaddr_t)src_raw;
    bitaddr_t end_addr = (bitaddr_t)end_raw;

    if (src_addr + bl > end_addr || src_addr >= end_addr) {
      /* EOF: no more data in buffer */
      vm_bit_set(vm, vm->mmio.in_eof, 1);
    } else {
      bitcpy((size_t)bl, vm->space, (size_t)src_addr, vm->space, (size_t)bd);
      vm_write_uint(vm, vm->mmio.in_got, vm->n_bits, (uint64_t)bl);
      vm_write_uint(vm, vm->mmio.in_src_addr, vm->addr_bits, (uint64_t)(src_addr + bl));
    }
    vm_bit_set(vm, vm->mmio.in_done, 1);
    vm_bit_set(vm, vm->mmio.in_req, 0);
    return 0;
  }

  /* Legacy: read from stdin */
  size_t nbytes = (size_t)(bl >> 3);
  size_t byte_dst = (size_t)(bd >> 3);

  size_t got = 0;
  if (nbytes) {
    got = fread(&vm->space[byte_dst], 1, nbytes, in);
    if (got == 0 && feof(in)) vm_bit_set(vm, vm->mmio.in_eof, 1);
    if (ferror(in)) vm_bit_set(vm, vm->mmio.in_err, 1);
  }

  vm_write_uint(vm, vm->mmio.in_got, vm->n_bits, (uint64_t)got * 8u);
  vm_bit_set(vm, vm->mmio.in_done, 1);
  vm_bit_set(vm, vm->mmio.in_req, 0);
  return 0;
}

static int service_out(vm_t *vm, FILE *out) {
  if (!vm_bit_get(vm, vm->mmio.out_req)) return 0;

  vm_bit_set(vm, vm->mmio.out_done, 0);
  vm_bit_set(vm, vm->mmio.out_err,  0);
  vm_write_uint(vm, vm->mmio.out_got, vm->n_bits, 0);

  uint64_t src = vm_read_uint(vm, vm->mmio.out_src, vm->addr_bits);
  uint64_t len = vm_read_uint(vm, vm->mmio.out_len, vm->n_bits);

  if ((src & 7u) || (len & 7u)) {
    vm_bit_set(vm, vm->mmio.out_err, 1);
    vm_bit_set(vm, vm->mmio.out_done, 1);
    vm_bit_set(vm, vm->mmio.out_req, 0);
    return 0;
  }

  bitaddr_t bs = (bitaddr_t)src;
  bitaddr_t bl = (bitaddr_t)len;

  if (bs + bl > vm->space_bits) {
    vm_bit_set(vm, vm->mmio.out_err, 1);
    vm_bit_set(vm, vm->mmio.out_done, 1);
    vm_bit_set(vm, vm->mmio.out_req, 0);
    return 0;
  }

  size_t nbytes = (size_t)(bl >> 3);
  size_t byte_src = (size_t)(bs >> 3);

  size_t put = 0;
  if (nbytes) {
    put = fwrite(&vm->space[byte_src], 1, nbytes, out);
    if (put != nbytes) vm_bit_set(vm, vm->mmio.out_err, 1);
    fflush(out);
  }

  vm_write_uint(vm, vm->mmio.out_got, vm->n_bits, (uint64_t)put * 8u);
  vm_bit_set(vm, vm->mmio.out_done, 1);
  vm_bit_set(vm, vm->mmio.out_req, 0);
  return 0;
}

static int service_loader(vm_t *vm) {
  if (!vm_bit_get(vm, vm->mmio.load_req)) return 0;

  vm_bit_set(vm, vm->mmio.load_done, 0);
  vm_bit_set(vm, vm->mmio.load_err, 0);

  bitaddr_t src = (bitaddr_t)vm_read_uint(vm, vm->mmio.load_src, vm->addr_bits);
  bitaddr_t nbits = (bitaddr_t)vm_read_uint(vm, vm->mmio.load_bits, vm->n_bits);

  if (nbits != vm->processor_bits || src + nbits > vm->space_bits || src < vm->workspace_base) {
    vm_bit_set(vm, vm->mmio.load_err, 1);
    vm_bit_set(vm, vm->mmio.load_done, 1);
    vm_bit_set(vm, vm->mmio.load_req, 0);
    return 0;
  }

  bitcpy((size_t)nbits, vm->space, (size_t)src, vm->space, (size_t)vm->processor_start);
  vm_bit_set(vm, vm->mmio.load_done, 1);
  vm_bit_set(vm, vm->mmio.load_req, 0);
  return 0;
}

static int service_channel(vm_t *vm) {
  const bitaddr_t G_REG_BASE = 0x001200ULL;
  const bitaddr_t G_MEM_BASE = 0x002000ULL;
  const bitaddr_t REG_FILE_BITS = 32u * 32u;
  const uint64_t CH_E_BOUNDS = 1;
  const uint64_t CH_E_ALIGN = 2;
  const uint64_t CH_E_PROTOCOL = 3;

  if (!vm_bit_get(vm, vm->mmio.ch_req)) return 0;
  vm_bit_set(vm, vm->mmio.ch_done, 0);
  vm_bit_set(vm, vm->mmio.ch_err, 0);

  /* v1 channel ABI operations:
   * op=0: NOP/ACK               — no operation
   * op=1: STOP                  — sets MMIO.HALT
   * op=2: STEP_BUDGET           — ch_c -> wd_limit, enables watchdog
   * op=3: LOAD_IMAGE            — ch_a=src, ch_b=nbits, copy into processor area
   * op=4: LOAD_ACK              — acknowledge load, reset watchdog
   * op=5: IO_WRITE              — ch_a=src, ch_b=len(bytes), write to stdout
   * op=6: STATUS                — tick->ch_a, halt->ch_b[0], error->ch_c
   * op=7: LOAD_CODE             — ch_a=src, ch_b=guest_off(bits), ch_c=nbits -> copy to G_MEM_BASE+off
   * op=8: RUN                   — ch_c=max_ticks (watchdog arm)
   * op=9: STEP                  — ch_c=step_ticks (watchdog arm)
   * op=10: READ_REGS            — ch_a=dst, copies x0..x31 (32*32 bits) from G_REG_BASE
   * op=11: READ_MEM             — ch_a=guest_off(bits), ch_b=dst, ch_c=nbits from G_MEM_BASE+off
   * op=12: WRITE_MEM            — ch_a=src, ch_b=guest_off(bits), ch_c=nbits to G_MEM_BASE+off
   * op=13: TRACE_INFO           — ch_a=dst, copies rv_trace_info_t
   * op=14: TRACE_READ           — ch_a=byte_off, ch_b=dst, ch_c=nbits from bootstrap trace buffer
   */
  unsigned op = (unsigned)vm_read_uint(vm, vm->mmio.ch_op, 8);
  if (op == 0) {
    /* no-op */
  } else if (op == 1) {
    vm_bit_set(vm, vm->mmio.halt, 1);
  } else if (op == 2) {
    uint64_t lim = vm_read_uint(vm, vm->mmio.ch_c, vm->n_bits);
    vm_write_uint(vm, vm->mmio.wd_limit, vm->n_bits, lim);
    vm_write_uint(vm, vm->mmio.wd_ticks, vm->n_bits, 0);
    vm_bit_set(vm, vm->mmio.wd_fired, 0);
    vm_bit_set(vm, vm->mmio.wd_enable, 1);
  } else if (op == 3) {
    bitaddr_t src_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    bitaddr_t nbits = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_b, vm->addr_bits);
    if (nbits != vm->processor_bits || src_a + nbits > vm->space_bits || src_a < vm->workspace_base) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
    } else {
      bitcpy((size_t)nbits, vm->space, (size_t)src_a, vm->space, (size_t)vm->processor_start);
    }
  } else if (op == 4) {
    uint64_t start_addr = vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    (void)start_addr;
    vm_bit_set(vm, vm->mmio.wd_enable, 0);
    vm_bit_set(vm, vm->mmio.wd_fired, 0);
    vm_write_uint(vm, vm->mmio.wd_ticks, vm->n_bits, 0);
  } else if (op == 5) {
    bitaddr_t src_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    uint64_t blen = vm_read_uint(vm, vm->mmio.ch_b, vm->addr_bits);
    if ((src_a & 7u) || src_a + (blen << 3) > vm->space_bits) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, (src_a & 7u) ? CH_E_ALIGN : CH_E_BOUNDS);
    } else {
      size_t byte_src = (size_t)(src_a >> 3);
      size_t nbytes = (size_t)blen;
      if (nbytes && fwrite(&vm->space[byte_src], 1, nbytes, stdout) != nbytes) {
        vm_bit_set(vm, vm->mmio.ch_err, 1);
        vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_PROTOCOL);
      }
      fflush(stdout);
    }
  } else if (op == 6) {
    vm_write_uint(vm, vm->mmio.ch_a, vm->addr_bits, vm->tick_counter);
    vm_bit_set(vm, vm->mmio.ch_b, vm_bit_get(vm, vm->mmio.halt));
    vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, (uint64_t)vm->last_err.kind);
  } else if (op == 7) {
    bitaddr_t src_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    bitaddr_t off = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_b, vm->addr_bits);
    bitaddr_t nbits = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_c, vm->n_bits);
    bitaddr_t dst_a = G_MEM_BASE + off;
    if (src_a + nbits > vm->space_bits || dst_a + nbits > vm->space_bits) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_BOUNDS);
    } else {
      bitcpy((size_t)nbits, vm->space, (size_t)src_a, vm->space, (size_t)dst_a);
      vm->rv_guest_loaded = 1;
      vm->rv_guest_running = 0;
      vm->rv_guest_steps = 0;
      vm->rv_guest_stop_reason = RV_STOP_NONE;
      rv32_trace_reset(vm);
      vm_bit_set(vm, vm->mmio.halt, 0);
      vm_write_uint(vm, 0x001000ULL, 32u, 0u);
    }
  } else if (op == 8 || op == 9) {
    if (!vm->rv_guest_loaded) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_PROTOCOL);
    } else {
    uint64_t lim = vm_read_uint(vm, vm->mmio.ch_c, vm->n_bits);
    vm_write_uint(vm, vm->mmio.wd_limit, vm->n_bits, lim);
    vm_write_uint(vm, vm->mmio.wd_ticks, vm->n_bits, 0);
    vm_bit_set(vm, vm->mmio.wd_fired, 0);
    vm_bit_set(vm, vm->mmio.wd_enable, lim > 0 ? 1 : 0);
    vm->rv_guest_running = lim > 0 ? 1 : 0;
    vm->rv_guest_stop_reason = RV_STOP_NONE;
    if (lim == 0) {
      vm_bit_set(vm, vm->mmio.halt, 0);
      vm->rv_guest_running = 0;
    } else {
      vm_bit_set(vm, vm->mmio.halt, 0);
    }
    }
  } else if (op == 10) {
    bitaddr_t dst_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    if (G_REG_BASE + REG_FILE_BITS > vm->space_bits || dst_a + REG_FILE_BITS > vm->space_bits) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_BOUNDS);
    } else {
      bitcpy((size_t)REG_FILE_BITS, vm->space, (size_t)G_REG_BASE, vm->space, (size_t)dst_a);
    }
  } else if (op == 11) {
    bitaddr_t off = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    bitaddr_t dst_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_b, vm->addr_bits);
    bitaddr_t nbits = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_c, vm->n_bits);
    bitaddr_t src_a = G_MEM_BASE + off;
    if (src_a + nbits > vm->space_bits || dst_a + nbits > vm->space_bits) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_BOUNDS);
    } else {
      bitcpy((size_t)nbits, vm->space, (size_t)src_a, vm->space, (size_t)dst_a);
    }
  } else if (op == 12) {
    bitaddr_t src_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    bitaddr_t off = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_b, vm->addr_bits);
    bitaddr_t nbits = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_c, vm->n_bits);
    bitaddr_t dst_a = G_MEM_BASE + off;
    if (src_a + nbits > vm->space_bits || dst_a + nbits > vm->space_bits) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_BOUNDS);
    } else {
      bitcpy((size_t)nbits, vm->space, (size_t)src_a, vm->space, (size_t)dst_a);
    }
  } else if (op == 13) {
    bitaddr_t dst_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    rv_trace_info_t info;
    if (dst_a + (bitaddr_t)sizeof(info) * 8u > vm->space_bits) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_BOUNDS);
    } else {
      info.version = 1u;
      info.record_bytes = (uint32_t)sizeof(rv_trace_record_t);
      info.record_count = vm->rv_trace_count;
      info.used_bytes = vm->rv_trace_count * (uint32_t)sizeof(rv_trace_record_t);
      info.dropped_records = vm->rv_trace_dropped;
      memcpy(&vm->space[dst_a >> 3], &info, sizeof(info));
    }
  } else if (op == 14) {
    uint64_t byte_off = vm_read_uint(vm, vm->mmio.ch_a, vm->addr_bits);
    bitaddr_t dst_a = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_b, vm->addr_bits);
    bitaddr_t nbits = (bitaddr_t)vm_read_uint(vm, vm->mmio.ch_c, vm->n_bits);
    uint64_t used_bytes = (uint64_t)vm->rv_trace_count * sizeof(rv_trace_record_t);
    if ((nbits & 7u) || dst_a + nbits > vm->space_bits || (byte_off * 8u) + nbits > used_bytes * 8u) {
      vm_bit_set(vm, vm->mmio.ch_err, 1);
      vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_BOUNDS);
    } else {
      memcpy(&vm->space[dst_a >> 3], ((const uint8_t*)vm->rv_trace_records) + byte_off, (size_t)(nbits >> 3));
    }
  } else {
    vm_bit_set(vm, vm->mmio.ch_err, 1);
    vm_write_uint(vm, vm->mmio.ch_c, vm->n_bits, CH_E_PROTOCOL);
  }

  vm_bit_set(vm, vm->mmio.ch_done, 1);
  vm_bit_set(vm, vm->mmio.ch_req, 0);
  return 0;
}

/* -------- execution -------- */

vm_rc_t vm_tick(vm_t *vm, FILE *in, FILE *out) {
  if (!vm || !vm->space) return VM_ERR;

  /* diagnostics: reset last_err for this tick */
  vm->last_err.kind = VM_E_NONE;
  vm->last_err.tick = vm->tick_counter;
  vm->last_err.slot = 0;
  vm->last_err.ins  = (vm_inst_t){0,0,0};
  vm->last_err.space_bits = vm->space_bits;


  /* 1) MMIO at start of tick */
  if (service_out(vm, out) != 0) return VM_ERR;
  if (service_in(vm, in) != 0) return VM_ERR;
  if (service_loader(vm) != 0) return VM_ERR;
  if (service_channel(vm) != 0) return VM_ERR;

  /* watchdog update (bounded-step mode) */
  if (vm_bit_get(vm, vm->mmio.wd_enable)) {
    uint64_t ticks = vm_read_uint(vm, vm->mmio.wd_ticks, vm->n_bits);
    uint64_t limit = vm_read_uint(vm, vm->mmio.wd_limit, vm->n_bits);
    ticks++;
    vm_write_uint(vm, vm->mmio.wd_ticks, vm->n_bits, ticks);
    if (limit > 0 && ticks >= limit) {
      vm_bit_set(vm, vm->mmio.wd_fired, 1);
      vm_bit_set(vm, vm->mmio.halt, 1);
      vm->rv_guest_running = 0;
    }
  }

  /* 2) HALT check after I/O (allows "print first, then stop") */
  if (vm_bit_get(vm, vm->mmio.halt)) { vm->rv_guest_running = 0; vm->tick_counter++; return VM_HALT; }

  if (vm->rv_guest_running) {
    if (rv32_guest_step(vm) != 0) return VM_ERR;
    if (vm_bit_get(vm, vm->mmio.halt)) { vm->rv_guest_running = 0; vm->tick_counter++; return VM_HALT; }
  }

  /* 3) fetch-execute slots */
  if (vm->hooks.tick_begin) vm->hooks.tick_begin(vm->hooks.user, vm->processor_n);
  for (unsigned i = 0; i < vm->processor_n; i++) {
    bitaddr_t ip = vm_proc_slot_ip(vm, i);
    vm_inst_t ins = vm_read_inst(vm, ip);

    if (ins.n == 0) continue; /* NOP */

    bitaddr_t n   = (bitaddr_t)ins.n;
    bitaddr_t src = (bitaddr_t)ins.src;
    bitaddr_t dst = (bitaddr_t)ins.dst;

    if (src + n > vm->space_bits) {
      vm->last_err.kind = VM_E_SRC_BOUNDS;
      vm->last_err.tick = vm->tick_counter;
      vm->last_err.slot = i;
      vm->last_err.ins  = ins;
      vm->last_err.space_bits = vm->space_bits;
      fprintf(stderr,
              "VM_ERR: tick=%" PRIu64 " slot=%u n=%" PRIu64 " dst=%" PRIu64 " src=%" PRIu64 " kind=%d space_bits=%" PRIu64 "\n",
              (uint64_t)vm->last_err.tick,
              (unsigned)vm->last_err.slot,
              (uint64_t)vm->last_err.ins.n,
              (uint64_t)vm->last_err.ins.dst,
              (uint64_t)vm->last_err.ins.src,
              (int)vm->last_err.kind,
              (uint64_t)vm->last_err.space_bits);
      return VM_ERR;
    }
    if (dst + n > vm->space_bits) {
      vm->last_err.kind = VM_E_DST_BOUNDS;
      vm->last_err.tick = vm->tick_counter;
      vm->last_err.slot = i;
      vm->last_err.ins  = ins;
      vm->last_err.space_bits = vm->space_bits;
      fprintf(stderr,
              "VM_ERR: tick=%" PRIu64 " slot=%u n=%" PRIu64 " dst=%" PRIu64 " src=%" PRIu64 " kind=%d space_bits=%" PRIu64 "\n",
              (uint64_t)vm->last_err.tick,
              (unsigned)vm->last_err.slot,
              (uint64_t)vm->last_err.ins.n,
              (uint64_t)vm->last_err.ins.dst,
              (uint64_t)vm->last_err.ins.src,
              (int)vm->last_err.kind,
              (uint64_t)vm->last_err.space_bits);
      return VM_ERR;
    }

    /* bitcpy uses size_t offsets; with 512KB this is safe */
    if (vm->hooks.note_copy) vm->hooks.note_copy(vm->hooks.user, i, (uint64_t)dst, (uint64_t)n, (uint64_t)src);

    bitcpy((size_t)n, vm->space, (size_t)src, vm->space, (size_t)dst);
  }


  if (vm->hooks.tick_end) vm->hooks.tick_end(vm->hooks.user);


  vm->tick_counter++;

  return VM_OK;
}

vm_rc_t vm_run(vm_t *vm, uint64_t life, FILE *in, FILE *out) {
  while (life--) {
    vm_rc_t rc = vm_tick(vm, in, out);
    if (rc != VM_OK) return rc;
  }
  return VM_OK;
}

/* -------- build boot loader layer (pure copycode image) -------- */

static void clear_processor(vm_t *vm) {
  for (unsigned i = 0; i < vm->processor_n; i++) {
    vm_write_inst(vm, vm_proc_slot_ip(vm, i), (vm_inst_t){0,0,0});
  }
}

int vm_build_boot_loader_layer(vm_t *vm, bitaddr_t next_layer_ptr) {
  if (!vm) return -1;

  /* next_layer_ptr must fit in addr_bits */
  if (next_layer_ptr >= ((bitaddr_t)1u << vm->addr_bits)) return -1;

  clear_processor(vm);

  /* slot0: NOP but carries pointer in dst field */
  vm_inst_t meta = { .n = 0, .dst = (uint64_t)next_layer_ptr, .src = 0 };
  vm_write_inst(vm, vm_proc_slot_ip(vm, 0), meta);

  unsigned patch_slot = vm->processor_n - 2;
  unsigned load_slot  = vm->processor_n - 1;

  /* patch: copy ADDR_BITS into src-field of load_slot from dst-field of slot0 */
  bitaddr_t src_field_of_load = vm_proc_slot_field_ip(vm, load_slot, vm->off_src);
  bitaddr_t dst_field_of_slot0 = vm_proc_slot_field_ip(vm, 0, vm->off_dst);

  vm_inst_t patch = {
    .n   = vm->addr_bits,
    .dst = (uint64_t)src_field_of_load,
    .src = (uint64_t)dst_field_of_slot0
  };

  /* load: copy PROCESSOR_BITS into processor_start; src will be patched */
  vm_inst_t load = {
    .n   = (uint64_t)vm->processor_bits,
    .dst = (uint64_t)vm->processor_start,
    .src = 0
  };

  vm_write_inst(vm, vm_proc_slot_ip(vm, patch_slot), patch);
  vm_write_inst(vm, vm_proc_slot_ip(vm, load_slot),  load);

  return 0;
}
