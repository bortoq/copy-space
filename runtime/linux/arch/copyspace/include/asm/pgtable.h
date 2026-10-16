/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_PGTABLE_H
#define _ASM_COPYSPACE_PGTABLE_H

#include <linux/const.h>
#include <asm/page.h>

/*
 * Nominal two-level page tables for copyspace. No hardware walker reads
 * these entries on this target; the bit positions mirror the familiar
 * RISC-V RV32 layout so future trap code meets no surprises, but only
 * software consistency is claimed: present/none/dirty/accessed tracking
 * used by generic mm code. pud/pmd fold into pgd through the generic
 * folding headers. NOMMU linear mapping keeps every pfns able to
 * round-trip through pfn_pte/pte_pfn.
 */
#define _PAGE_PRESENT	_AC(0x001, L)
#define _PAGE_READ	_AC(0x002, L)
#define _PAGE_WRITE	_AC(0x004, L)
#define _PAGE_EXEC	_AC(0x008, L)
#define _PAGE_USER	_AC(0x010, L)
#define _PAGE_GLOBAL	_AC(0x020, L)
#define _PAGE_ACCESSED	_AC(0x040, L)
#define _PAGE_DIRTY	_AC(0x080, L)
#define _PAGE_SOFT	_AC(0x300, L)
#define _PAGE_PROT_NONE	_AC(0x400, L)
#define _PAGE_IO	_AC(0x000, L)
#define _PAGE_NOCACHE	_AC(0x000, L)
#define _PAGE_MTMASK	_AC(0x000, L)
#define _PAGE_CHG_MASK	(PAGE_MASK | _PAGE_ACCESSED | _PAGE_DIRTY | _PAGE_SOFT)

#define _PAGE_BASE	(_PAGE_PRESENT | _PAGE_ACCESSED | _PAGE_USER)
#define PAGE_NONE	__pgprot(_PAGE_PROT_NONE | _PAGE_READ)
#define PAGE_READ	__pgprot(_PAGE_BASE | _PAGE_READ)
#define PAGE_WRITE	__pgprot(_PAGE_BASE | _PAGE_READ | _PAGE_WRITE)
#define PAGE_EXEC	__pgprot(_PAGE_BASE | _PAGE_EXEC)
#define PAGE_READ_EXEC	__pgprot(_PAGE_BASE | _PAGE_READ | _PAGE_EXEC)
#define PAGE_WRITE_EXEC	__pgprot(_PAGE_BASE | _PAGE_READ |		\
				 _PAGE_EXEC | _PAGE_WRITE)
#define PAGE_SHARED	PAGE_WRITE
#define PAGE_SHARED_EXEC	PAGE_WRITE_EXEC
#define PAGE_COPY	PAGE_WRITE
#define PAGE_COPY_EXEC	PAGE_WRITE_EXEC
#define PAGE_READONLY	PAGE_READ
#define PAGE_KERNEL	__pgprot(_PAGE_PRESENT | _PAGE_READ | _PAGE_WRITE | \
				 _PAGE_ACCESSED | _PAGE_DIRTY | _PAGE_GLOBAL)
#define PAGE_KERNEL_READ	__pgprot(_PAGE_PRESENT | _PAGE_READ |	\
					 _PAGE_ACCESSED | _PAGE_GLOBAL)
#define PAGE_KERNEL_EXEC	__pgprot(_PAGE_PRESENT | _PAGE_READ | _PAGE_EXEC | \
					 _PAGE_ACCESSED | _PAGE_GLOBAL)
#define PAGE_KERNEL_READ_EXEC	__pgprot(_PAGE_PRESENT | _PAGE_READ |	\
					 _PAGE_EXEC | _PAGE_ACCESSED | _PAGE_GLOBAL)
#define PAGE_KERNEL_NOCACHE	PAGE_KERNEL

#define __P000		PAGE_NONE
#define __P001		PAGE_READ
#define __P010		PAGE_READ
#define __P011		PAGE_READ
#define __P100		PAGE_EXEC
#define __P101		PAGE_READ_EXEC
#define __P110		PAGE_READ_EXEC
#define __P111		PAGE_READ_EXEC
#define __S000		PAGE_NONE
#define __S001		PAGE_READ
#define __S010		PAGE_WRITE
#define __S011		PAGE_WRITE
#define __S100		PAGE_EXEC
#define __S101		PAGE_READ_EXEC
#define __S110		PAGE_WRITE_EXEC
#define __S111		PAGE_WRITE_EXEC

#define PTRS_PER_PTE	(PAGE_SIZE / sizeof(pte_t))
#define PTRS_PER_PGD	(PAGE_SIZE / sizeof(pgd_t))
#define PGDIR_SHIFT	22
#define PGDIR_SIZE	(_AC(1, UL) << PGDIR_SHIFT)
#define PGDIR_MASK	(~(PGDIR_SIZE - 1))
#define MAX_POSSIBLE_PHYSMEM_BITS 32

#include <asm-generic/pgtable-nopmd.h>
#include <asm-generic/pgtable-nopud.h>
#include <asm-generic/pgtable-nop4d.h>

static inline int pte_none(pte_t pte) { return !(pte_val(pte) & ~_PAGE_SOFT); }
static inline int pte_present(pte_t pte)
{ return (pte_val(pte) & (_PAGE_PRESENT | _PAGE_PROT_NONE)); }
static inline void pte_clear(struct mm_struct *mm, unsigned long address, pte_t *ptep)
{ (void)mm; (void)address; ptep->pte = 0; }
static inline int pte_write(pte_t pte) { return pte_val(pte) & _PAGE_WRITE; }
static inline int pte_exec(pte_t pte) { return pte_val(pte) & _PAGE_EXEC; }
static inline int pte_user(pte_t pte) { return pte_val(pte) & _PAGE_USER; }
static inline int pte_dirty(pte_t pte) { return pte_val(pte) & _PAGE_DIRTY; }
static inline int pte_young(pte_t pte) { return pte_val(pte) & _PAGE_ACCESSED; }
static inline pte_t pte_wrprotect(pte_t pte)
{ return __pte(pte_val(pte) & ~_PAGE_WRITE); }
/* linux/pgtable.h provides pte_mkwrite(pte, vma) through this hook. */
static inline pte_t pte_mkwrite_novma(pte_t pte)
{ return __pte(pte_val(pte) | _PAGE_WRITE); }
static inline pte_t pte_mkexec(pte_t pte) { return __pte(pte_val(pte) | _PAGE_EXEC); }
static inline pte_t pte_mkdirty(pte_t pte) { return __pte(pte_val(pte) | _PAGE_DIRTY); }
static inline pte_t pte_mkyoung(pte_t pte) { return __pte(pte_val(pte) | _PAGE_ACCESSED); }
static inline pte_t pte_mkold(pte_t pte) { return __pte(pte_val(pte) & ~_PAGE_ACCESSED); }
static inline pte_t pte_mkclean(pte_t pte) { return __pte(pte_val(pte) & ~_PAGE_DIRTY); }
static inline pte_t pte_modify(pte_t pte, pgprot_t newprot)
{ return __pte((pte_val(pte) & _PAGE_CHG_MASK) | pgprot_val(newprot)); }
static inline int pte_same(pte_t a, pte_t b) { return pte_val(a) == pte_val(b); }
static inline pte_t pfn_pte(unsigned long pfn, pgprot_t prot)
{ return __pte((pfn << PAGE_SHIFT) | pgprot_val(prot)); }
static inline unsigned long pte_pfn(pte_t pte) { return pte_val(pte) >> PAGE_SHIFT; }
#define pte_page(pte) pfn_to_page(pte_pfn(pte))
static inline pte_t mk_pte(struct page *page, pgprot_t prot)
{ return pfn_pte(page_to_pfn(page), prot); }
static inline void set_pte(pte_t *ptep, pte_t pte) { *ptep = pte; }
#define __set_pte set_pte
#define __swp_entry(type, off) ((swp_entry_t) { ((type) | ((off) << 8)) })
#define __swp_type(entry) ((entry).val & 0xffUL)
#define __swp_offset(entry) ((entry).val >> 8)
#define __pte_to_swp_entry(pte) ((swp_entry_t) { pte_val(pte) })
#define __swp_entry_to_pte(entry) (__pte((entry).val))

#define pgprot_noncached(prot) (prot)
#define pgprot_writecombine(prot) (prot)
#define pgprot_device(prot) (prot)
static inline pgprot_t pgprot_modify(pgprot_t oldprot, pgprot_t newprot)
{ (void)oldprot; return newprot; }
#define pgprot_modify pgprot_modify
#define pte_pgprot(pte) __pgprot(pte_val(pte) & ~PAGE_MASK)


/* Flat NOMMU user range is provisional together with the load map. */
#define TASK_SIZE	_AC(0xffffffff, UL)
#define TASK_SIZE_MAX	TASK_SIZE

#endif /* _ASM_COPYSPACE_PGTABLE_H */
