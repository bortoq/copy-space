/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_COPYSPACE_PAGE_H
#define _ASM_COPYSPACE_PAGE_H

#ifdef CONFIG_MMU
#error "copyspace page tables are not implemented"
#endif
#ifdef CONFIG_64BIT
#error "copyspace requires a 32-bit kernel configuration"
#endif
#if defined(CONFIG_PAGE_SHIFT) && CONFIG_PAGE_SHIFT != 12
#error "copyspace requires 4096-byte logical pages"
#endif

/* Logical page geometry, shared with the guest runtime's sysconf. Page
 * allocation and kernel memory mappings are separate unfinished work. */
#define PAGE_SHIFT 12
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE - 1))

#endif
