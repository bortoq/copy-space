#include "copy_space.h"

int main(void)
{
    unsigned char buffer[8];
    int count = cs_read(buffer, sizeof buffer);
    if(count < 0)
        return 1;
    if(cs_write(buffer, (unsigned int)count) != count)
        return 3;
    return count == (int)sizeof buffer ? 0 : count == 0 ? 2 : 4;
}
