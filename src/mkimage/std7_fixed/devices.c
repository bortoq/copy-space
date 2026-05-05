/* file: src/mkimage/std7_fixed/devices.c
 * date: 2026-05-04
 * purpose: build self-describing terminal device (desc + 3 channel headers)
 */
#include "devices.h"
#include <stdint.h>

/* typed writers (byte offsets; bitaddr is MSB-first within byte, handled by vm_write_uint) */
static void w8(vm_t *vm, bitaddr_t base, unsigned byte_off, uint8_t v) {
  vm_write_uint(vm, base + (bitaddr_t)byte_off * 8u, 8, v);
}
static void w16(vm_t *vm, bitaddr_t base, unsigned byte_off, uint16_t v) {
  vm_write_uint(vm, base + (bitaddr_t)byte_off * 8u, 16, v);
}
static void w32(vm_t *vm, bitaddr_t base, unsigned byte_off, uint32_t v) {
  vm_write_uint(vm, base + (bitaddr_t)byte_off * 8u, 32, v);
}
static void w64(vm_t *vm, bitaddr_t base, unsigned byte_off, uint64_t v) {
  vm_write_uint(vm, base + (bitaddr_t)byte_off * 8u, 64, v);
}
static void wA(vm_t *vm, bitaddr_t base, unsigned byte_off, bitaddr_t v) {
  vm_write_uint(vm, base + (bitaddr_t)byte_off * 8u, vm->addr_bits, (uint64_t)v);
}

/* constants */
enum {
  DEV_MAGIC_CDEV = 0x43444556u, /* "CDEV" */
  CH_MAGIC_CHN1  = 0x43484E31u, /* "CHN1" */

  DEV_TYPE_TERM  = 1,
  PROTO_CHN1     = 1,

  PORT_STDIN  = 0,
  PORT_STDOUT = 1,
  PORT_STDERR = 2,
};

int std7_fixed_build_devices(vm_t *vm, bitaddr_t bus_base, std7_devices_t *out) {
  if (!vm || !out) return -1;

  /* layout within bus region (byte-aligned) */
  bitaddr_t term_desc = bus_base;                /* 64 bytes descriptor */
  bitaddr_t ch_in     = bus_base +  64u * 8u;    /* 32 bytes channel */
  bitaddr_t ch_out    = bus_base +  96u * 8u;    /* 32 bytes channel */
  bitaddr_t ch_err    = bus_base + 128u * 8u;    /* 32 bytes channel */

  /* deterministic instance id */
  uint64_t dev_id = 0x5445524D00000001ULL; /* "TERM" + 1 */

  /* -------- Device descriptor (DEV_DESC) --------
     Layout (bytes):
       0  magic      u32   "CDEV"
       4  version    u16
       6  dev_type   u16
       8  device_id  u64
      16  port_count u8
      17..19 reserved
      20  ports[3] each 8 bytes:
          +0 port_id u8
          +1 proto   u8
          +2 flags   u16
          +4 chan_base (ADDR_BITS bits stored in bytes; for ADDR_BITS=24 consumes 3 bytes; remaining bytes reserved)
  */
  w32(vm, term_desc, 0, DEV_MAGIC_CDEV);
  w16(vm, term_desc, 4, 1);
  w16(vm, term_desc, 6, DEV_TYPE_TERM);
  w64(vm, term_desc, 8, dev_id);
  w8 (vm, term_desc, 16, 3);

  /* port 0: stdin */
  w8 (vm, term_desc, 20 + 0*8 + 0, PORT_STDIN);
  w8 (vm, term_desc, 20 + 0*8 + 1, PROTO_CHN1);
  w16(vm, term_desc, 20 + 0*8 + 2, 0);
  wA (vm, term_desc, 20 + 0*8 + 4, ch_in);

  /* port 1: stdout */
  w8 (vm, term_desc, 20 + 1*8 + 0, PORT_STDOUT);
  w8 (vm, term_desc, 20 + 1*8 + 1, PROTO_CHN1);
  w16(vm, term_desc, 20 + 1*8 + 2, 0);
  wA (vm, term_desc, 20 + 1*8 + 4, ch_out);

  /* port 2: stderr */
  w8 (vm, term_desc, 20 + 2*8 + 0, PORT_STDERR);
  w8 (vm, term_desc, 20 + 2*8 + 1, PROTO_CHN1);
  w16(vm, term_desc, 20 + 2*8 + 2, 0);
  wA (vm, term_desc, 20 + 2*8 + 4, ch_err);

  /* -------- Channel header (CHAN_HDR) --------
     Layout (bytes):
       0  magic      u32   "CHN1"
       4  proto      u16   (=1)
       6  port_id    u16
       8  device_id  u64   (must match DEV_DESC)
      16  req        u8
      17  done       u8
      18  err        u8
      19  reserved   u8
      20  seq        u32
      24  len        u32   (bytes)
      28  buf_ptr    ADDR_BITS (bitaddr of payload buffer)  (we place it at byte 28)
     Notes:
       - For now we keep buf_ptr=0 and do not implement actual I/O via this channel in baseline.
       - This is enough to "prove grouping": ports share same device_id and are listed in DEV_DESC.
  */
  for (int k = 0; k < 3; k++) {
    bitaddr_t ch = (k == 0) ? ch_in : (k == 1) ? ch_out : ch_err;
    uint16_t port = (k == 0) ? PORT_STDIN : (k == 1) ? PORT_STDOUT : PORT_STDERR;

    w32(vm, ch, 0, CH_MAGIC_CHN1);
    w16(vm, ch, 4, PROTO_CHN1);
    w16(vm, ch, 6, port);
    w64(vm, ch, 8, dev_id);

    w8(vm, ch, 16, 0); /* req */
    w8(vm, ch, 17, 0); /* done */
    w8(vm, ch, 18, 0); /* err */
    w8(vm, ch, 19, 0); /* reserved */
    w32(vm, ch, 20, 0); /* seq */
    w32(vm, ch, 24, 0); /* len (bytes) */
    wA(vm, ch, 28, 0);  /* buf_ptr (bitaddr) */
  }

  out->term0_desc = term_desc;
  out->term0_ch_in = ch_in;
  out->term0_ch_out = ch_out;
  out->term0_ch_err = ch_err;
  out->term0_device_id = dev_id;
  return 0;
}
