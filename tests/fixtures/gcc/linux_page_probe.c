/* NOMMU header contracts; not evidence of an allocator or a booting kernel. */
struct page { unsigned long marker; };
#include <asm/page.h>
#include <asm/page.h>
#include <asm/pgtable.h>
#include <asm/pgtable.h>
#include <asm/mmu.h>
#include <asm/mmu.h>

static struct page pages[4];
struct page *mem_map = pages;
unsigned long max_mapnr = 4;
static unsigned address_calls;
static unsigned page_calls;

static __attribute__((noipa)) struct page *page_once(void)
{
	++page_calls;
	return &pages[2];
}

static __attribute__((noipa)) unsigned long address_once(void)
{
	++address_calls;
	return PAGE_OFFSET;
}

static __attribute__((noipa)) int dynamic_order(unsigned long size)
{
	return get_order(size);
}

unsigned value(void)
{
	unsigned passed = 0;
	passed += __pa(PAGE_OFFSET) == 0;
	passed += __va(0) == (void *)PAGE_OFFSET;
	passed += virt_to_pfn(PAGE_OFFSET + 3 * PAGE_SIZE) == 3;
	passed += pfn_to_page(0) == &pages[0];
	passed += page_to_pfn(&pages[3]) == 3;
	passed += page_to_phys(&pages[0]) == 0;
	passed += page_to_phys(&pages[3]) == 3 * PAGE_SIZE;
	passed += page_to_phys(page_once()) == 2 * PAGE_SIZE && page_calls == 1;
	passed += sizeof(page_to_phys(&pages[0])) == sizeof(phys_addr_t);
	passed += virt_to_page(PAGE_OFFSET + PAGE_SIZE) == &pages[1];
	passed += pfn_valid(0) && pfn_valid(3);
	passed += !pfn_valid(4) && !pfn_valid(~0UL);
	max_mapnr = 0;
	passed += !pfn_valid(0);
	max_mapnr = 4;

	pte_t entry = pfn_pte(3, PAGE_WRITE);
	passed += pte_pfn(entry) == 3;
	passed += pgprot_val(pte_pgprot(entry)) == pgprot_val(PAGE_WRITE);
	passed += pte_page(entry) == &pages[3];
	entry = pte_mkdirty(pte_mkyoung(entry));
	entry = pte_modify(entry, PAGE_NONE);
	passed += pte_pfn(entry) == 3 && pte_dirty(entry) && pte_young(entry);
	passed += !pte_write(entry) && pte_present(entry);
	entry = pte_modify(entry, PAGE_READONLY);
	passed += !(pte_val(entry) & _PAGE_PROT_NONE) && pte_present(entry);
	passed += pte_write(pte_mkwrite_novma(entry)) != 0;
	passed += pgprot_val(pgprot_modify(PAGE_WRITE, PAGE_READONLY)) == pgprot_val(PAGE_READONLY);
	pte_clear((struct mm_struct *)0, PAGE_OFFSET, &entry);
	passed += pte_none(entry);
	passed += virt_addr_valid(PAGE_OFFSET);
	passed += virt_addr_valid(PAGE_OFFSET + 4 * PAGE_SIZE - 1);
	passed += !virt_addr_valid(PAGE_OFFSET + 4 * PAGE_SIZE);
	passed += !virt_addr_valid(PAGE_OFFSET - 1);
	passed += !virt_addr_valid(0);
	passed += virt_addr_valid(address_once()) && address_calls == 1;
	max_mapnr = 0;
	passed += !virt_addr_valid(PAGE_OFFSET);
	max_mapnr = 4;
	passed += get_order(1) == 0;
	passed += get_order(4096) == 0;
	passed += get_order(4097) == 1;
	passed += get_order(8192) == 1;
	passed += get_order(8193) == 2;
	passed += get_order(65536) == 4;
	passed += get_order(65537) == 5;
	passed += get_order(~0UL) == (int)(sizeof(long) * 8 - PAGE_SHIFT);
	static const unsigned long sizes[] = {
		1, 4095, 4096, 4097, 8192, 8193, 16384, 16385,
		65536, 65537, 0x80000000UL, 0xffffffffUL
	};
	static const unsigned orders[] = { 0, 0, 0, 1, 1, 2, 2, 3, 4, 5, 19, 20 };
	for (unsigned i = 0; i < sizeof(sizes) / sizeof(sizes[0]); ++i)
		passed += dynamic_order(sizes[i]) == (int)orders[i];
	passed += dynamic_order(~0UL) == (int)(sizeof(long) * 8 - PAGE_SHIFT);
	mm_context_t context = { .end_brk = PAGE_OFFSET + PAGE_SIZE };
	passed += context.end_brk == PAGE_OFFSET + PAGE_SIZE;
	context.end_brk += PAGE_SIZE;
	passed += context.end_brk == PAGE_OFFSET + 2 * PAGE_SIZE;
	return passed;
}
