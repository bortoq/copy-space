#include "copy_space.h"

static const unsigned char payload[70000] = {[69999] = 'X'};
static volatile unsigned char arena[262144];

int main(void)
{
    volatile unsigned char stack_value = 'E';
    arena[65536] = 'A';
    arena[131072] = 'B';
    arena[262142] = 'C';
    if(cs_read((void *)&arena[262143], 1) != 1)
        return 1;
    if(cs_write(&payload[69999], 1) != 1 ||
       cs_write((const void *)&arena[65536], 1) != 1 ||
       cs_write((const void *)&arena[131072], 1) != 1 ||
       cs_write((const void *)&arena[262142], 2) != 2 ||
       cs_write((const void *)&stack_value, 1) != 1)
        return 2;
    return 0;
}
