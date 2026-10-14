"""Conditional aggregate values, branch effects and result categories."""
valid = [
    ("aggregate-conditional-true",b"int main(){struct S{int x,y;}a={3,4},b={9,8};struct S s=1?a:b;return s.x+s.y;}",7),
    ("aggregate-conditional-false",b"int main(){struct S{int x,y;}a={3,4},b={9,8};struct S s=0?a:b;return s.x+s.y;}",17),
    ("aggregate-conditional-member",b"int main(){struct S{int x;}a={3},b={7};int n=0;return (n?a:b).x;}",7),
    ("aggregate-conditional-array",b"int main(){struct S{int a[3];}s={{1,2,3}},t={{4,5,7}};return (0?s:t).a[2];}",7),
    ("aggregate-conditional-nested",b"int main(){struct S{int x;}a={1},b={3},c={7};struct S s=1?(0?a:b):c;return s.x;}",3),
    ("aggregate-conditional-copy",b"int main(){struct S{int x;}a={3},b={7},s=0?a:b;b.x=9;return s.x;}",7),
    ("aggregate-conditional-const",b"int main(){struct S{int x;}a={3};const struct S b={7};struct S s=0?a:b;return s.x;}",7),
    ("aggregate-conditional-union",b"int main(){union U{int x;char c[4];}a={3},b={7},s=0?a:b;return s.x;}",7),
    ("aggregate-conditional-packed",b"int main(){struct __attribute__((packed)) S{char c;int x;}a={1,2},b={3,4},s=0?a:b;return s.c+s.x;}",7),
    ("aggregate-conditional-return",b"struct S{int x,y,z;};struct S f(int n){struct S a={1,2,4},b={3,5,7};return n?a:b;}int main(){struct S s=f(1);return s.x+s.y+s.z;}",7),
    ("aggregate-conditional-argument",b"struct S{int x;};int f(struct S s){return s.x;}int main(){struct S a={3},b={7};return f(0?a:b);}",7),
    ("aggregate-conditional-branch-effects",b"struct S{int x;};int n=0;struct S f(int x){struct S s={x};n++;return s;}int main(){struct S s=1?f(7):f(9);return s.x+n;}",8),
    ("aggregate-conditional-false-effects",b"struct S{int x;};int n=0;struct S f(int x){struct S s={x};n++;return s;}int main(){struct S s=0?f(9):f(7);return s.x+n;}",8),
    ("aggregate-conditional-condition-once",b"int main(){struct S{int x;}a={7},b={9};int n=0;struct S s=(++n)?a:b;return s.x+n;}",8),
    ("aggregate-conditional-pointer-branch",b"int main(){struct S{int x;}a={7};struct S*p=0;struct S s=1?a:*p;return s.x;}",7),
    ("aggregate-conditional-type",b"int main(){struct S{int x;}a={3},b={7};return __builtin_types_compatible_p(typeof(1?a:b),struct S);}",1),
    ("aggregate-conditional-sizeof-effects",b"struct S{int x;};int n=0;struct S f(){struct S s={7};n++;return s;}int main(){return sizeof(1?f():f())+n;}",4),
    ("aggregate-conditional-void-left",b"int main(){struct S{int x;}s={7};int n=0;0?(void)n++:s;return n+sizeof(1?(void)0:s);}",1),
    ("aggregate-conditional-void-right",b"int main(){struct S{int x;}s={7};int n=0;0?s:(void)n++;return n+sizeof(1?s:(void)0);}",2),
]
invalid = [
    ("aggregate-conditional-incompatible",b"int main(){struct S{int x;}s;struct T{int x;}t;return (1?s:t).x;}"),
    ("aggregate-conditional-scalar-right",b"int main(){struct S{int x;}s;1?s:7;return 0;}"),
    ("aggregate-conditional-scalar-left",b"int main(){struct S{int x;}s;1?7:s;return 0;}"),
    ("aggregate-conditional-address",b"int main(){struct S{int x;}a={3},b={7};struct S*p=&(1?a:b);return p->x;}"),
    ("aggregate-conditional-field-write",b"int main(){struct S{int x;}a={3},b={7};(1?a:b).x=9;return 0;}"),
]
