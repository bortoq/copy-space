/* GNU C labels as values: absolute pointers and relative relocation tables. */
#define NOIPA __attribute__((noinline,noipa))

#define EXECUTE(dispatch) \
    unsigned pc=0, value=seed; \
    next: ; \
    if (pc==count) return 0xdeadU; \
    unsigned op=code[pc++]; \
    if (op>=4) return 0xbadU; \
    dispatch; \
    add: value+=7; goto next; \
    toggle: value^=0x55U; goto next; \
    multiply: value*=3; goto next; \
    stop: return value

NOIPA unsigned absolute(unsigned seed, const volatile unsigned char *code, unsigned count)
{
    static void *const labels[]={&&add,&&toggle,&&multiply,&&stop};
    EXECUTE(goto *labels[op]);
}

NOIPA unsigned relative(unsigned seed, const volatile unsigned char *code, unsigned count)
{
    static const int offsets[]={&&add-&&next,&&toggle-&&next,&&multiply-&&next,&&stop-&&next};
    EXECUTE(goto *(&&next+offsets[op]));
}

unsigned value(void)
{
    static volatile unsigned char program[]={0,1,2,1,3};
    static volatile unsigned char invalid[]={255};
    static const unsigned seeds[]={0,1,7,0x55,0x12345678,0x7fffffff,0x80000000,0xffffffff};
    unsigned passed=0;
    for (unsigned i=0;i<sizeof(seeds)/sizeof(seeds[0]);++i) {
        unsigned expected=(((seeds[i]+7)^0x55U)*3)^0x55U;
        passed+=absolute(seeds[i],program,5)==expected;
        passed+=relative(seeds[i],program,5)==expected;
    }
    passed+=absolute(9,invalid,1)==0xbadU;
    passed+=relative(9,invalid,1)==0xbadU;
    passed+=absolute(9,program,4)==0xdeadU;
    passed+=relative(9,program,4)==0xdeadU;
    passed+=absolute(9,(const volatile unsigned char *)0,0)==0xdeadU;
    passed+=relative(9,(const volatile unsigned char *)0,0)==0xdeadU;
    return passed;
}
