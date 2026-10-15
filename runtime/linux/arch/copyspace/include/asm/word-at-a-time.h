/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_WORD_AT_A_TIME_H
#define _ASM_COPYSPACE_WORD_AT_A_TIME_H

#ifdef CONFIG_DCACHE_WORD_ACCESS
#error "copyspace fault-recovering word access is not implemented"
#endif

#include <asm-generic/word-at-a-time.h>

#endif
