/* file: src/mkimage/std7_fixed/devices.h
 * date: 2026-05-04
 * purpose: build self-describing devices (device descriptor + channel headers)
 */
#ifndef STD7_FIXED_DEVICES_H_
#define STD7_FIXED_DEVICES_H_

#include "space.h"

typedef struct {
  bitaddr_t term0_desc;
  bitaddr_t term0_ch_in;
  bitaddr_t term0_ch_out;
  bitaddr_t term0_ch_err;
  uint64_t  term0_device_id;
} std7_devices_t;

/* writes device structures into bus region, returns 0 ok */
int std7_fixed_build_devices(vm_t *vm, bitaddr_t bus_base, std7_devices_t *out);

#endif
