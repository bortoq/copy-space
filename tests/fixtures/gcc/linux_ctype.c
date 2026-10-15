/* SPDX-License-Identifier: GPL-2.0 */
#include <lib/ctype.c>

unsigned value(unsigned a, unsigned b)
{
    const volatile unsigned char *table = _ctype;
    return table[a + 62];
}
