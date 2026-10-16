/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_IO_H
#define _ASM_COPYSPACE_IO_H

#include <linux/compiler.h>
#include <asm/page.h>

/*
 * NOMMU identity I/O: MMIO addresses are plain pointers into the single
 * address space. The generic accessor core works on top of __pa/__va
 * from asm/page.h; fences collapse to compiler barriers on one hart.
 */
#include <asm-generic/io.h>

#endif /* _ASM_COPYSPACE_IO_H */
