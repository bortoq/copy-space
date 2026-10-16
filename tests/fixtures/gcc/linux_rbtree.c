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

struct interval {
	struct rb_node link;
	unsigned start;
	unsigned last;
	unsigned subtree;
};

#define AUPOOL 12

static struct interval apool[AUPOOL];
static struct rb_root aroot = RB_ROOT;

static bool compute_sub(struct interval *node, bool done)
{
	unsigned top = node->last;
	struct interval *child;
	if (node->link.rb_left) {
		child = rb_entry(node->link.rb_left, struct interval, link);
		if (child->subtree > top)
			top = child->subtree;
	}
	if (node->link.rb_right) {
		child = rb_entry(node->link.rb_right, struct interval, link);
		if (child->subtree > top)
			top = child->subtree;
	}
	if (done && node->subtree == top)
		return true;
	node->subtree = top;
	return false;
}

RB_DECLARE_CALLBACKS(static, aug, struct interval, link, subtree, compute_sub)

__attribute__((__noinline__)) static void ainsert(struct interval *node)
{
	struct rb_node **link = &aroot.rb_node, *parent = NULL;
	/* A fresh node has no children yet: seed its own augmented value
	 * before linking, as interval-tree users do; propagate() only
	 * refreshes ancestors. */
	node->subtree = node->last;
	while (*link) {
		parent = *link;
		if (node->start < rb_entry(parent, struct interval, link)->start)
			link = &parent->rb_left;
		else
			link = &parent->rb_right;
	}
	rb_link_node(&node->link, parent, link);
	aug.propagate(parent, NULL);
	rb_insert_augmented(&node->link, &aroot, &aug);
}

__attribute__((__noinline__)) static unsigned long aref(unsigned *alive, unsigned n)
{
	unsigned i, top = 0;
	(void)n;
	for (i = 0; i < AUPOOL; ++i) {
		if (!alive[i])
			continue;
		if (apool[i].last > top)
			top = apool[i].last;
		if (apool[i].subtree > top)
			top = apool[i].subtree;
	}
	return top;
}

__attribute__((__noinline__)) static unsigned acheck(unsigned *alive, unsigned n)
{
	struct rb_node *node;
	unsigned count = 0, prev = 0, first = 1;
	for (node = rb_first(&aroot); node; node = rb_next(node)) {
		unsigned start = rb_entry(node, struct interval, link)->start;
		if (!first && start < prev)
			return 0;
		first = 0;
		prev = start;
		++count;
	}
	if (count != n)
		return 0;
	if (n && rb_entry(aroot.rb_node, struct interval, link)->subtree != aref(alive, AUPOOL))
		return 0;
	return 1;
}

unsigned augmented(unsigned a, unsigned b)
{
	unsigned alive[AUPOOL], i, passed = 0, count = 0;
	(void)b;
	for (i = 0; i < AUPOOL; ++i) {
		apool[i].start = (a + i * 5U) & 15U;
		apool[i].last = apool[i].start + (i * 3U & 7U);
		apool[i].subtree = 0;
		alive[i] = 1;
		ainsert(&apool[i]);
		++count;
		passed += acheck(alive, count);
	}
	for (i = 0; i < AUPOOL; i += 2) {
		alive[i] = 0;
		rb_erase_augmented(&apool[i].link, &aroot, &aug);
		--count;
		passed += acheck(alive, count);
	}
	for (i = 1; i < AUPOOL; i += 2) {
		alive[i] = 0;
		rb_erase_augmented(&apool[i].link, &aroot, &aug);
		--count;
		passed += acheck(alive, count);
	}
	passed += rb_first(&aroot) == NULL && count == 0;
	return passed;
}
