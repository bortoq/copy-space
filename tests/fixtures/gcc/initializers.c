#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static int initialized;
static unsigned callbacks;
static void before(void) __attribute__((constructor(101)));
static void after(void) __attribute__((destructor(101)));
static void before(void) { initialized=7; }
static void after(void) { assert(initialized==9 && callbacks==40); puts("gcc-fini:7"); }
static void repeated(void) { assert(initialized==9); ++callbacks; }
static void cleanup(void) { assert(initialized==7); initialized=9; puts("gcc-exit:7"); }
int main(void)
{
    assert(initialized==7);
    for (unsigned i=0;i<40;++i) assert(atexit(repeated)==0);
    assert(atexit(cleanup)==0);
    puts("gcc-init:7");
    return 0;
}
