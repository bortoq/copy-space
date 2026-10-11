#include "copy_space.h"

extern unsigned int add_words(unsigned int a, unsigned int b);

int main(void)
{
    unsigned int numbers[2], sum;
    int count = cs_read(numbers, sizeof numbers);
    if(count < 0)
        return 1;
    if(count != (int)sizeof numbers)
        return 2;
    sum = add_words(numbers[0], numbers[1]);
    return cs_write(&sum, sizeof sum) == (int)sizeof sum ? 0 : 3;
}
