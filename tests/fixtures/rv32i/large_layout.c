#include "copy_space.h"

static const unsigned char payload[1048577] = {[1048576] = 'X'};
static volatile unsigned char arena[8388608];

int main(void)
{
    volatile unsigned char stack_value = 'E';
    arena[65536] = 'A';
    arena[1048576] = 'B';
    arena[8388606] = 'C';
    if(cs_read((void *)&arena[8388607], 1) != 1)
        return 1;
    if(cs_write(&payload[1048576], 1) != 1 ||
       cs_write((const void *)&arena[65536], 1) != 1 ||
       cs_write((const void *)&arena[1048576], 1) != 1 ||
       cs_write((const void *)&arena[8388606], 2) != 2 ||
       cs_write((const void *)&stack_value, 1) != 1)
        return 2;
    return 0;
}
