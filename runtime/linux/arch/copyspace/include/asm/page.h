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
 * allocation and kernel memory mappings are separate unfinished work.
 *
 * NOMMU linear mapping below is provisional: virtual address minus
 * PAGE_OFFSET is physical, and every pfn round-trips through one flat
 * mem_map. The final load map belongs to the kernel link layout. */
#include <linux/const.h>
#define PAGE_OFFSET	_AC(CONFIG_PAGE_OFFSET, UL)
#define PAGE_SHIFT 12
#define PAGE_SIZE (_AC(1, UL) << PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE - 1))
/* __pa(PAGE_OFFSET) is zero in this provisional linear mapping. */
#define ARCH_PFN_OFFSET _AC(0, UL)

#ifndef __ASSEMBLY__
#include <linux/types.h>
#include <linux/string.h>
#include <linux/pfn.h>

/* Page Global Directory entry */
typedef struct {
	unsigned long pgd;
} pgd_t;

/* Page Table entry */
typedef struct {
	unsigned long pte;
} pte_t;

typedef struct {
	unsigned long pgprot;
} pgprot_t;

typedef struct page *pgtable_t;

#define pte_val(x)	((x).pte)
#define pgd_val(x)	((x).pgd)
#define pgprot_val(x)	((x).pgprot)

#define __pte(x)	((pte_t) { (x) })
#define __pgd(x)	((pgd_t) { (x) })
#define __pgprot(x)	((pgprot_t) { (x) })

#define clear_page(pgaddr)	memset((pgaddr), 0, PAGE_SIZE)
#define copy_page(to, from)	memcpy((to), (from), PAGE_SIZE)
#define clear_user_page(pgaddr, vaddr, page)	clear_page(pgaddr)
#define copy_user_page(to, from, vaddr, page)	copy_page((to), (from))

#define __pa(x)		((unsigned long)(x) - PAGE_OFFSET)
#define __va(x)		((void *)((unsigned long)(x) + PAGE_OFFSET))
#define virt_to_pfn(vaddr)	(PFN_DOWN(__pa(vaddr)))
/* Use the kernel's bounded FLATMEM conversion and pfn_valid: the upper
 * limit is max_mapnr, rather than accepting every address above the base. */
#include <asm-generic/memory_model.h>
#define page_to_phys(page)	((phys_addr_t)page_to_pfn(page) << PAGE_SHIFT)
#define virt_to_page(vaddr)	pfn_to_page(virt_to_pfn(vaddr))
#define virt_addr_valid(vaddr)	pfn_valid(virt_to_pfn(vaddr))
extern struct page *mem_map;

#include <asm-generic/getorder.h>

#endif /* !__ASSEMBLY__ */
#endif /* _ASM_COPYSPACE_PAGE_H */
