/* SPDX-License-Identifier: GPL-2.0 */
#include <lib/rbtree.c>

struct key_node {
	struct rb_node link;
	unsigned key;
};

#define POOL 16

static struct key_node pool[POOL];
static struct rb_root root = RB_ROOT;

/* Keys derive from the entry arguments so the compiler cannot fold the
 * whole tree at compile time; helpers stay noinline like the other
 * Linux entry fixtures. */
__attribute__((__noinline__)) static void make_keys(unsigned *keys, unsigned seed)
{
	unsigned i;
	for (i = 0; i < POOL; ++i)
		keys[i] = (seed + i * 5U) & 15U;
}

__attribute__((__noinline__)) static void tree_insert(struct key_node *node)
{
	struct rb_node **link = &root.rb_node, *parent = NULL;
	while (*link) {
		parent = *link;
		if (node->key < rb_entry(parent, struct key_node, link)->key)
			link = &parent->rb_left;
		else
			link = &parent->rb_right;
	}
	rb_link_node(&node->link, parent, link);
	rb_insert_color(&node->link, &root);
}

__attribute__((__noinline__)) static unsigned tree_count(void)
{
	struct rb_node *node;
	unsigned n = 0;
	for (node = rb_first(&root); node; node = rb_next(node))
		++n;
	return n;
}

__attribute__((__noinline__)) static unsigned tree_sorted(unsigned count)
{
	struct rb_node *node;
	unsigned prev = 0, n = 0;
	for (node = rb_first(&root); node; node = rb_next(node)) {
		unsigned key = rb_entry(node, struct key_node, link)->key;
		if (n && key < prev)
			return 0;
		prev = key;
		++n;
	}
	return n == count;
}

__attribute__((__noinline__)) static void tree_erase(struct key_node *node)
{
	rb_erase(&node->link, &root);
}

unsigned value(unsigned a, unsigned b)
{
	unsigned keys[POOL], i, passed = 0, count = 0;
	make_keys(keys, a + b * 3U);
	for (i = 0; i < POOL; ++i) {
		pool[i].key = keys[i];
		tree_insert(&pool[i]);
		++count;
		passed += tree_count() == count;
		passed += tree_sorted(count);
	}
	for (i = 0; i < POOL; ++i) {
		if (!(pool[i].key & 1U))
			continue;
		tree_erase(&pool[i]);
		--count;
		passed += tree_count() == count;
		passed += tree_sorted(count);
	}
	for (i = 0; i < POOL; ++i) {
		if (pool[i].key & 1U)
			continue;
		tree_erase(&pool[i]);
		--count;
		passed += tree_count() == count;
		passed += tree_sorted(count);
	}
	passed += rb_first(&root) == NULL && count == 0;
	return passed;
}
