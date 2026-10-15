/* SPDX-License-Identifier: GPL-2.0 */
#include <lib/sort.c>

static unsigned values[8] = {8, 3, 6, 1, 7, 2, 5, 4};

static int compare(const void *left, const void *right)
{
    unsigned a = *(const unsigned *)left;
    unsigned b = *(const unsigned *)right;
    return (a > b) - (a < b);
}

unsigned value(unsigned a, unsigned b)
{
    unsigned result = 0;
    sort(values, 8, sizeof(values[0]), compare, NULL);
    for (unsigned i = 0; i < 8; ++i) {
        if (values[i] != i + 1)
            return 999;
        result += (i + 1) * values[i];
    }
    return result;
}
