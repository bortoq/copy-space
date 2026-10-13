"""GNU auto type deduction and binding after the initializer."""
valid = [
    ("auto-int", b"int main(){__auto_type x=7;return x;}", 7),
    ("auto-wide", b"int main(){__auto_type x=1ULL<<32;return sizeof(x)+(x>>32);}", 9),
    ("auto-char", b"int main(){char c=7;__auto_type x=c;return sizeof(x)+x;}", 8),
    ("auto-qualifier", b"int main(){const int c=3;__auto_type x=c;x=7;return x;}", 7),
    ("auto-pointer", b"int main(){int n=3;__auto_type p=&n;*p=7;return n;}", 7),
    ("auto-array-decay", b"int main(){int a[2]={3,4};__auto_type p=a;return p[0]+p[1];}", 7),
    ("auto-function", b"int f(int n){return n+3;}int main(){__auto_type p=f;return p(4);}", 7),
    ("auto-shadow", b"int main(){int x=7;{__auto_type x=x;return x;}}", 7),
    ("auto-once", b"int main(){int n=3;__auto_type x=n++;return x+n;}", 7),
    ("auto-statement-expression", b"int main(){return ({__auto_type x=3;__auto_type y=4;x+y;});}", 7),
    ("auto-guest", b"int main(){int n=3;__auto_type x=n++;return x+n;}", 7),
]
invalid = [
    ("auto-no-initializer", b"int main(){__auto_type x;return 0;}"),
    ("auto-multiple", b"int main(){__auto_type x=1,y=2;return x+y;}"),
    ("auto-pointer-declarator", b"int main(){int n;__auto_type*p=&n;return 0;}"),
    ("auto-self", b"int main(){__auto_type x=x;return 0;}"),
    ("auto-duplicate", b"int main(){int x=1;__auto_type x=2;return x;}"),
    ("auto-braces", b"int main(){__auto_type x={7};return x;}"),
    ("auto-void", b"void f(){}int main(){__auto_type x=f();return 0;}"),
]
