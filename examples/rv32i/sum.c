#include "copy_space.h"

static int whitespace(unsigned char c)
{
    return c == ' ' || c == '\n' || c == '\r' || c == '\t';
}

/* Returns 1 for a number, 0 for EOF, -1 for invalid input, -2 for IN error. */
static int read_number(unsigned int *result)
{
    unsigned char c;
    unsigned int value = 0;
    int count;
    do
    {
        count = cs_read(&c, 1);
        if(count <= 0)
            return count < 0 ? -2 : 0;
    } while(whitespace(c));
    if(c < '0' || c > '9')
        return -1;
    do
    {
        unsigned int digit = c-'0';
        if(value > 429496729u || (value == 429496729u && digit > 5u))
            return -1;
        value = value*10u + digit;
        count = cs_read(&c, 1);
        if(count < 0)
            return -2;
        if(count == 0)
            break;
        if(whitespace(c))
            break;
        if(c < '0' || c > '9')
            return -1;
    } while(1);
    *result = value;
    return 1;
}

int main(void)
{
    unsigned int a, b, sum, count = 0, i;
    char reversed[10], output[11];
    int result = read_number(&a);
    if(result != 1)
        return result == -2 ? 1 : 2;
    result = read_number(&b);
    if(result != 1)
        return result == -2 ? 1 : 2;
    sum = a+b;
    do
    {
        reversed[count++] = (char)('0'+sum%10u);
        sum /= 10u;
    } while(sum);
    for(i = 0; i < count; ++i)
        output[i] = reversed[count-i-1];
    output[count++] = '\n';
    return cs_write(output, count) == (int)count ? 0 : 3;
}
