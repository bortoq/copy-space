/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_CHECKSUM_H
#define _ASM_COPYSPACE_CHECKSUM_H

/* Use the C routines from lib/checksum.c (CONFIG_GENERIC_CSUM in the
 * eventual copyspace Kconfig). RISC-V alternatives and instructions do
 * not describe this target. */
#include <asm-generic/checksum.h>

#endif /* _ASM_COPYSPACE_CHECKSUM_H */
