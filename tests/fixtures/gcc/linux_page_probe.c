/* NOMMU header contracts; not evidence of an allocator or a booting kernel. */
struct page { unsigned long marker; };
#include <asm/page.h>
#include <asm/page.h>
#include <asm/pgtable.h>
#include <asm/pgtable.h>

static struct page pages[4];
struct page *mem_map = pages;
unsigned long max_mapnr = 4;

unsigned value(void)
{
	unsigned passed = 0;
	passed += __pa(PAGE_OFFSET) == 0;
	passed += __va(0) == (void *)PAGE_OFFSET;
	passed += virt_to_pfn(PAGE_OFFSET + 3 * PAGE_SIZE) == 3;
	passed += pfn_to_page(0) == &pages[0];
	passed += page_to_pfn(&pages[3]) == 3;
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
	return passed;
}
