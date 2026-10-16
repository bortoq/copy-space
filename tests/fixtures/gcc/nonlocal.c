/* GCC builtin environments contain five pointer-sized words. */
typedef __INTPTR_TYPE__ word;
#define NOIPA __attribute__((noinline,noipa))
static word environment[5];
static volatile unsigned phase;

NOIPA static void bounce(void)
{
    phase=7;
    __builtin_longjmp(environment,1);
}

NOIPA static void through_two(void) { bounce(); }
NOIPA static void through_one(void) { through_two(); }

unsigned jump_basic(void)
{
    phase=0;
    if (__builtin_setjmp(environment)==0) bounce();
    return phase+5;
}

unsigned jump_deep(void)
{
    volatile unsigned saved=33;
    phase=0;
    if (__builtin_setjmp(environment)==0) through_one();
    return phase+saved;
}

unsigned jump_repeat(void)
{
    volatile unsigned count=0,total=0;
    while (count<5) {
        phase=0;
        if (__builtin_setjmp(environment)==0) bounce();
        total+=phase;
        ++count;
    }
    return total;
}

NOIPA static unsigned argument_frame(unsigned a,unsigned b,unsigned c,unsigned d,
                                    unsigned e,unsigned f,unsigned g,unsigned h)
{
    if (__builtin_setjmp(environment)==0) bounce();
    return a+b+c+d+e+f+g+h+phase;
}

unsigned jump_arguments(void)
{
    phase=0;
    return argument_frame(1,2,3,4,5,6,7,8);
}

NOIPA static unsigned sum(unsigned a,unsigned b,unsigned c,unsigned d,
                         unsigned e,unsigned f,unsigned g,unsigned h)
{ return a+b+c+d+e+f+g+h; }

unsigned jump_call_after(void)
{
    phase=0;
    if (__builtin_setjmp(environment)==0) bounce();
    return phase+sum(1,2,3,4,5,6,7,8);
}

unsigned jump_label(void)
{
    __label__ target;
    volatile unsigned saved=5;
    phase=0;
    NOIPA void nested(void) { phase=42; goto target; }
    nested();
    phase=99;
target:
    return phase+saved;
}

unsigned jump_label_deep(void)
{
    __label__ target;
    volatile unsigned saved=11;
    phase=0;
    NOIPA void middle(void)
    {
        NOIPA void inner(void) { phase=31; goto target; }
        inner();
        phase=98;
    }
    middle();
    phase=99;
target:
    return phase+saved;
}
