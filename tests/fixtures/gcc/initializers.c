#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static int initialized;
static void before(void) __attribute__((constructor(101)));
static void after(void) __attribute__((destructor(101)));
static void before(void) { initialized=7; }
static void after(void) { assert(initialized==9); puts("gcc-fini:7"); }
static void cleanup(void) { assert(initialized==7); initialized=9; puts("gcc-exit:7"); }
int main(void)
{
    assert(initialized==7);
    assert(atexit(cleanup)==0);
    puts("gcc-init:7");
    return 0;
}
