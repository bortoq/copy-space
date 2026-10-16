/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_MMIOWB_H
#define _ASM_COPYSPACE_MMIOWB_H

#include <linux/compiler.h>

/* MMIO writes complete before later writes on one hart with the
 * compiler barrier; no fence instruction exists here. */
#define mmiowb()	barrier()

#include <asm-generic/mmiowb.h>

#endif /* _ASM_COPYSPACE_MMIOWB_H */
