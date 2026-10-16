#include "nested_callbacks.h"
#define NOIPA __attribute__((noinline,noipa))
NOIPA unsigned plain_callback(unsigned x) { return 100+x; }

unsigned callback_capture(void)
{
    volatile unsigned bias=10;
    NOIPA unsigned nested(unsigned x) { return bias+x; }
    return invoke(nested,7);
}

unsigned callback_modify(void)
{
    volatile unsigned bias=10;
    NOIPA unsigned nested(unsigned x) { bias+=x; return bias; }
    unsigned a=invoke(nested,7),b=invoke(nested,5);
    return a+b+bias;
}

unsigned callback_array(void)
{
    volatile unsigned bias=10;
    NOIPA unsigned first(unsigned x) { return bias+x; }
    NOIPA unsigned second(unsigned x) { return 2*bias+x; }
    callback choices[]={first,plain_callback,second};
    unsigned sum=0;
    for (unsigned i=0;i<3;++i) sum+=invoke(choices[i],3+i);
    return sum;
}

unsigned callback_recursive(void)
{
    volatile unsigned bias=5;
    NOIPA unsigned nested(unsigned n)
    {
        if (!n) return bias;
        return invoke(nested,n-1)+n;
    }
    return invoke(nested,4);
}

unsigned callback_void(void)
{
    volatile unsigned bias=30;
    NOIPA void nested(unsigned x) { bias+=x; }
    notify(nested,5);notify(nested,7);
    return bias;
}

unsigned callback_arguments(void)
{
    volatile unsigned bias=6;
    NOIPA unsigned nested(unsigned a,unsigned b,unsigned c,unsigned d,
                          unsigned e,unsigned f,unsigned g,unsigned h)
    { return bias+a+b+c+d+e+f+g+h; }
    return invoke_many(nested,1,2,3,4,5,6,7,8);
}

unsigned callback_structure(void)
{
    volatile unsigned bias=10;
    NOIPA struct callback_result nested(unsigned x)
    {
        struct callback_result r={bias+x,bias+2*x,bias+3*x,bias+4*x};
        return r;
    }
    struct callback_result r=collect(nested,3);
    return r.a+r.b+r.c+r.d;
}

unsigned callback_deep(void)
{
    volatile unsigned outer=10;
    NOIPA unsigned middle(unsigned input)
    {
        volatile unsigned inner=input;
        NOIPA unsigned nested(unsigned x) { return outer+inner+x; }
        return invoke(nested,4);
    }
    return invoke(middle,3);
}

unsigned callback_equal(void)
{
    volatile unsigned bias=10;
    NOIPA unsigned first(unsigned x) { return bias+x; }
    NOIPA unsigned second(unsigned x) { return bias+2*x; }
    callback a=first,b=first,c=second;
    return compare_callbacks(a,b)+!compare_callbacks(a,c)
           +!compare_callbacks(a,0)+!compare_callbacks(a,plain_callback);
}

unsigned callback_label(void)
{
    __label__ target;
    volatile unsigned bias=5;
    NOIPA void nested(unsigned x) { bias+=x; goto target; }
    notify(nested,37);
    bias=99;
target:
    return bias;
}
