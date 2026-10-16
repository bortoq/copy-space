/* Single-hart out-of-line __sync_* fetch/update/CAS helpers for copyspace.
 *
 * The copyspace GCC backend emits __sync_*_4/_8 libcalls for
 * read-modify-write builtins; plain atomic load/store lower to single
 * copies and __sync_synchronize/__sync_lock_release need no out-of-line
 * helper. The guest executes on one hart with sequentially executed
 * copies, so each helper performs its read-modify-write as plain volatile
 * accesses plus a compiler barrier. This is correct only while the guest
 * stays single-hart with no preemptive interruption between the load and
 * the store; it must not be used to claim SMP safety. The nand forms use
 * the post-GCC-4.4 semantics (*ptr = ~old & value), verified against
 * native GCC.
 */
typedef __UINT32_TYPE__ u32;
typedef __UINT64_TYPE__ u64;
typedef __INT32_TYPE__ s32;
typedef __INT64_TYPE__ s64;

#define BARRIER() __asm__ volatile ("" ::: "memory")

#define FETCH_OP_4(name, op) \
  s32 __sync_fetch_and_##name##_4 (volatile s32 *p, s32 v) \
  { s32 old = *p; BARRIER(); *(volatile s32 *)p = (s32)(old op v); BARRIER(); return old; }

#define FETCH_OP_8(name, op) \
  s64 __sync_fetch_and_##name##_8 (volatile s64 *p, s64 v) \
  { s64 old = *p; BARRIER(); *(volatile s64 *)p = (s64)(old op v); BARRIER(); return old; }

#define UPDATE_OP_4(name, op) \
  s32 __sync_##name##_and_fetch_4 (volatile s32 *p, s32 v) \
  { s32 old = *p; s32 next = (s32)(old op v); BARRIER(); *(volatile s32 *)p = next; BARRIER(); return next; }

#define UPDATE_OP_8(name, op) \
  s64 __sync_##name##_and_fetch_8 (volatile s64 *p, s64 v) \
  { s64 old = *p; s64 next = (s64)(old op v); BARRIER(); *(volatile s64 *)p = next; BARRIER(); return next; }

FETCH_OP_4 (add, +)
FETCH_OP_4 (sub, -)
FETCH_OP_4 (or, |)
FETCH_OP_4 (and, &)
FETCH_OP_4 (xor, ^)
FETCH_OP_8 (add, +)
FETCH_OP_8 (sub, -)
FETCH_OP_8 (or, |)
FETCH_OP_8 (and, &)
FETCH_OP_8 (xor, ^)

static s32 fetch_nand_4 (volatile s32 *p, s32 v)
{ s32 old = *p; BARRIER(); *(volatile s32 *)p = (s32)(~(old & v)); BARRIER(); return old; }
static s64 fetch_nand_8 (volatile s64 *p, s64 v)
{ s64 old = *p; BARRIER(); *(volatile s64 *)p = (s64)(~(old & v)); BARRIER(); return old; }
static s32 update_nand_4 (volatile s32 *p, s32 v)
{ s32 old = *p; s32 next = (s32)(~(old & v)); BARRIER(); *(volatile s32 *)p = next; BARRIER(); return next; }
static s64 update_nand_8 (volatile s64 *p, s64 v)
{ s64 old = *p; s64 next = (s64)(~(old & v)); BARRIER(); *(volatile s64 *)p = next; BARRIER(); return next; }
s32 __sync_fetch_and_nand_4 (volatile s32 *p, s32 v) { return fetch_nand_4 (p, v); }
s64 __sync_fetch_and_nand_8 (volatile s64 *p, s64 v) { return fetch_nand_8 (p, v); }
s32 __sync_nand_and_fetch_4 (volatile s32 *p, s32 v) { return update_nand_4 (p, v); }
s64 __sync_nand_and_fetch_8 (volatile s64 *p, s64 v) { return update_nand_8 (p, v); }

UPDATE_OP_4 (add, +)
UPDATE_OP_4 (sub, -)
UPDATE_OP_4 (or, |)
UPDATE_OP_4 (and, &)
UPDATE_OP_4 (xor, ^)
UPDATE_OP_8 (add, +)
UPDATE_OP_8 (sub, -)
UPDATE_OP_8 (or, |)
UPDATE_OP_8 (and, &)
UPDATE_OP_8 (xor, ^)

static int cas_4 (volatile s32 *p, s32 oldv, s32 newv)
{ s32 cur = *p; if (cur == oldv) { BARRIER(); *(volatile s32 *)p = newv; BARRIER(); return 1; } return 0; }
static int cas_8 (volatile s64 *p, s64 oldv, s64 newv)
{ s64 cur = *p; if (cur == oldv) { BARRIER(); *(volatile s64 *)p = newv; BARRIER(); return 1; } return 0; }
int __sync_bool_compare_and_swap_4 (volatile s32 *p, s32 oldv, s32 newv) { return cas_4 (p, oldv, newv); }
int __sync_bool_compare_and_swap_8 (volatile s64 *p, s64 oldv, s64 newv) { return cas_8 (p, oldv, newv); }
static s32 val_cas_4 (volatile s32 *p, s32 oldv, s32 newv)
{ s32 cur = *p; if (cur == oldv) { BARRIER(); *(volatile s32 *)p = newv; BARRIER(); } return cur; }
static s64 val_cas_8 (volatile s64 *p, s64 oldv, s64 newv)
{ s64 cur = *p; if (cur == oldv) { BARRIER(); *(volatile s64 *)p = newv; BARRIER(); } return cur; }
s32 __sync_val_compare_and_swap_4 (volatile s32 *p, s32 oldv, s32 newv) { return val_cas_4 (p, oldv, newv); }
s64 __sync_val_compare_and_swap_8 (volatile s64 *p, s64 oldv, s64 newv) { return val_cas_8 (p, oldv, newv); }
static s32 test_and_set_4 (volatile s32 *p, s32 v)
{ s32 old = *p; BARRIER(); *(volatile s32 *)p = v; BARRIER(); return old; }
static s64 test_and_set_8 (volatile s64 *p, s64 v)
{ s64 old = *p; BARRIER(); *(volatile s64 *)p = v; BARRIER(); return old; }
s32 __sync_lock_test_and_set_4 (volatile s32 *p, s32 v) { return test_and_set_4 (p, v); }
s64 __sync_lock_test_and_set_8 (volatile s64 *p, s64 v) { return test_and_set_8 (p, v); }
