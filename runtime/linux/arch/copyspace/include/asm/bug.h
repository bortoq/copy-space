/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_BUG_H
#define _ASM_COPYSPACE_BUG_H

#if !defined(__GNUC__) || !defined(__copyspace__)
#error "copyspace asm/bug.h requires the copyspace GCC target"
#endif

/* No exception handler or bug-table address format has been implemented. */
#ifdef CONFIG_GENERIC_BUG
#error "copyspace does not yet support CONFIG_GENERIC_BUG"
#endif

#include <linux/compiler.h>

/* A fatal BUG stops the direct copy program. Warnings use the generic path. */
#define HAVE_ARCH_BUG
#define BUG() do { __builtin_trap(); } while (0)

#include <asm-generic/bug.h>

#endif
