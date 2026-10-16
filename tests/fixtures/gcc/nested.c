/* GNU C static chains: no nested function address escapes in these entries. */
#define NOIPA __attribute__((noinline,noipa))

NOIPA unsigned direct(void)
{
    volatile unsigned bias=10;
    NOIPA unsigned nested(unsigned y) { return bias+y; }
    return nested(7);
}

NOIPA unsigned modify(void)
{
    volatile unsigned bias=10;
    NOIPA unsigned nested(unsigned delta) { bias+=delta; return bias; }
    unsigned a=nested(3), b=nested(4);
    return a+b+bias;
}

NOIPA unsigned recursive(void)
{
    volatile unsigned bias=5;
    NOIPA unsigned nested(unsigned n)
    {
        if (!n) return bias;
        return nested(n-1)+n;
    }
    return nested(4);
}

NOIPA unsigned siblings(void)
{
    volatile unsigned bias=10;
    NOIPA unsigned first(unsigned y) { return bias+y; }
    NOIPA unsigned second(unsigned y) { return first(2*y)+bias; }
    return second(3);
}

NOIPA unsigned deep(void)
{
    volatile unsigned x=10;
    NOIPA unsigned middle(unsigned input)
    {
        volatile unsigned y=input;
        NOIPA unsigned inner(unsigned z) { return x+y+z; }
        return inner(4);
    }
    return middle(3);
}

NOIPA unsigned arguments(void)
{
    volatile unsigned bias=6;
    NOIPA unsigned nested(unsigned a,unsigned b,unsigned c,unsigned d,
                          unsigned e,unsigned f,unsigned g,unsigned h)
    { return bias+a+b+c+d+e+f+g+h; }
    return nested(1,2,3,4,5,6,7,8);
}

NOIPA unsigned variadic(void)
{
    volatile unsigned bias=5;
    NOIPA unsigned nested(unsigned count,...)
    {
        __builtin_va_list ap;
        __builtin_va_start(ap,count);
        unsigned total=bias;
        for (unsigned i=0;i<count;++i) total+=__builtin_va_arg(ap,unsigned);
        __builtin_va_end(ap);
        return total;
    }
    return nested(8,1,2,3,4,5,6,7,8);
}

NOIPA unsigned address(void)
{
    volatile unsigned bias=10;
    NOIPA volatile unsigned *nested(void) { return &bias; }
    volatile unsigned *p=nested();
    *p+=33;
    return bias;
}
