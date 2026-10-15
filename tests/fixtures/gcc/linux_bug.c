/* SPDX-License-Identifier: GPL-2.0 */
#include <linux/bug.h>

/* An isolated logging sink for testing the generic WARN calling contract. */
static unsigned warnings;
void warn_slowpath_fmt(const char *file, int line, unsigned taint,
                       const char *format, ...)
{
    if (!file || line <= 0 || taint != TAINT_WARN || format)
        __builtin_trap();
    ++warnings;
}

unsigned value(unsigned a, unsigned b)
{
    BUG_ON(a == b);
    return a + b;
}

unsigned fatal(unsigned a, unsigned b)
{
    BUG();
}

unsigned conditional_trap(unsigned a, unsigned b)
{
    BUG_ON(a != b);
    return a + b;
}

unsigned condition_once(unsigned a, unsigned b)
{
    unsigned count = 0;
    BUG_ON(count++ == a);
    return count + b;
}

unsigned warning_once(unsigned a, unsigned b)
{
    unsigned count = 0;
    for (unsigned i = 0; i < a; ++i)
        if (WARN_ON_ONCE(i < 2))
            ++count;
    return count * 10 + warnings;
}

unsigned warning_return(unsigned a, unsigned b)
{
    unsigned happened = WARN_ON(a == 3);
    return happened + 100 * warnings;
}
