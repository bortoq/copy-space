typedef unsigned int u32;

volatile u32 values[] = {0, 1, 2, 3, 0xffffffffu, 0x80000000u, 7, 9};
volatile u32 final_sum;

__attribute__((noinline)) u32 add(u32 a, u32 b)
{
    return a + b;
}

u32 rv_example(void)
{
    u32 sum = 0;
    unsigned int i;
    for(i = 0; i < sizeof values / sizeof values[0]; ++i)
    {
        u32 value = values[i];
        sum = add(sum, value);
        if(value & 1u)
            sum ^= value >> 1;
        else
            sum = add(sum, value << 1);
    }
    final_sum = sum;
    return sum;
}
