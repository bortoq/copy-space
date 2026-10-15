/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_BITOPS_H
#define _ASM_COPYSPACE_BITOPS_H

#ifndef _LINUX_BITOPS_H
#error "Only <linux/bitops.h> can be included directly"
#endif

/* C implementations for scans and non-atomic operations. Atomic bitops and
 * interrupt masking still need an architecture implementation. */
#include <asm-generic/bitops/__ffs.h>
#include <asm-generic/bitops/__fls.h>
#include <asm-generic/bitops/ffs.h>
#include <asm-generic/bitops/fls.h>
#include <asm-generic/bitops/fls64.h>
#include <asm-generic/bitops/hweight.h>
#include <asm-generic/bitops/non-atomic.h>

#endif
