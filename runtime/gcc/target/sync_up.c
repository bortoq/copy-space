/* SPDX-License-Identifier: Apache-2.0 */
/* One non-preemptive execution stream: no SMP or interrupt exclusion.
 * Volatile accesses and compiler barriers implement the current target ABI.
 * Arithmetic is unsigned so wraparound is defined. */
typedef unsigned int u32;
typedef unsigned long long u64;
_Static_assert(sizeof(u32)==4 && sizeof(u64)==8, "sync helper widths");
#define BARRIER() __asm__ volatile ("" ::: "memory")

#define FETCH_UPDATE(bytes, type, name, expression) \
    type __sync_fetch_and_##name##_##bytes(volatile void *address, type v) \
    { volatile type *p=address; BARRIER(); type old=*p; \
      *p=(expression); BARRIER(); return old; } \
    type __sync_##name##_and_fetch_##bytes(volatile void *address, type v) \
    { volatile type *p=address; BARRIER(); type old=*p; type next=(expression); \
      *p=next; BARRIER(); return next; }

#define CAS_XCHG(bytes, type) \
    _Bool __sync_bool_compare_and_swap_##bytes(volatile void *address, type o, type n) \
    { volatile type *p=address; BARRIER(); type cur=*p; \
      if (cur==o) *p=n; BARRIER(); return cur==o; } \
    type __sync_val_compare_and_swap_##bytes(volatile void *address, type o, type n) \
    { volatile type *p=address; BARRIER(); type cur=*p; \
      if (cur==o) *p=n; BARRIER(); return cur; } \
    type __sync_lock_test_and_set_##bytes(volatile void *address, type n) \
    { volatile type *p=address; BARRIER(); type cur=*p; \
      *p=n; BARRIER(); return cur; }

#ifdef L_sync_add4
FETCH_UPDATE(4,u32,add,old+v)
#endif
#ifdef L_sync_sub4
FETCH_UPDATE(4,u32,sub,old-v)
#endif
#ifdef L_sync_or4
FETCH_UPDATE(4,u32,or,old|v)
#endif
#ifdef L_sync_and4
FETCH_UPDATE(4,u32,and,old&v)
#endif
#ifdef L_sync_xor4
FETCH_UPDATE(4,u32,xor,old^v)
#endif
#ifdef L_sync_nand4
FETCH_UPDATE(4,u32,nand,~(old&v))
#endif
#ifdef L_sync_cas4
CAS_XCHG(4,u32)
#endif
#ifdef L_sync_add8
FETCH_UPDATE(8,u64,add,old+v)
#endif
#ifdef L_sync_sub8
FETCH_UPDATE(8,u64,sub,old-v)
#endif
#ifdef L_sync_or8
FETCH_UPDATE(8,u64,or,old|v)
#endif
#ifdef L_sync_and8
FETCH_UPDATE(8,u64,and,old&v)
#endif
#ifdef L_sync_xor8
FETCH_UPDATE(8,u64,xor,old^v)
#endif
#ifdef L_sync_nand8
FETCH_UPDATE(8,u64,nand,~(old&v))
#endif
#ifdef L_sync_cas8
CAS_XCHG(8,u64)
#endif
