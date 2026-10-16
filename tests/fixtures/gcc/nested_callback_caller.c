#include "nested_callbacks.h"
#define NOIPA __attribute__((noinline,noipa))
NOIPA unsigned invoke(callback fn,unsigned x) { return fn(x); }
NOIPA unsigned compare_callbacks(callback a,callback b) { return a==b; }
NOIPA void notify(action fn,unsigned x) { fn(x); }
NOIPA unsigned invoke_many(many_callback fn,unsigned a,unsigned b,unsigned c,
                          unsigned d,unsigned e,unsigned f,unsigned g,unsigned h)
{ return fn(a,b,c,d,e,f,g,h); }
NOIPA struct callback_result collect(result_callback fn,unsigned x)
{ return fn(x); }
