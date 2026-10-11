#include "copy_space.h"

int main(void)
{
    unsigned char buffer[8];
    memset(buffer, 0, sizeof buffer);
    if(memcmp(buffer, "\0\0\0\0\0\0\0\0", sizeof buffer))
        return 1;
    memcpy(buffer, "ABCDEFGH", sizeof buffer);
    memmove(buffer+1, buffer, 7);
    if(memcmp(buffer, "AABCDEFG", sizeof buffer))
        return 2;
    memmove(buffer, buffer+1, 7);
    if(memcmp(buffer, "ABCDEFGG", sizeof buffer))
        return 3;
    if(memcmp(buffer, "BBCDEFGG", sizeof buffer) >= 0)
        return 4;
    return cs_write(buffer, sizeof buffer) == (int)sizeof buffer ? 0 : 5;
}
