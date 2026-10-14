"""GNU conditional expressions whose middle operand is omitted."""
valid = [
    ("omitted-true",b"int main(){return 7?:9;}",7),
    ("omitted-false",b"int main(){return 0?:7;}",7),
    ("omitted-postincrement",b"int main(){int n=7;int x=n++?:99;return x+n;}",15),
    ("omitted-postincrement-zero",b"int main(){int n=0;int x=n++?:7;return x+n;}",8),
    ("omitted-call-once",b"int n=0;int f(){n++;return 7;}int main(){int x=f()?:99;return x+n;}",8),
    ("omitted-fallback-skip",b"int main(){int n=0;int x=7?:n++;return x+n;}",7),
    ("omitted-fallback-effect",b"int main(){int n=7;int x=0?:n++;return x+n;}",15),
    ("omitted-volatile",b"int main(){volatile int x=7;return x?:99;}",7),
    ("omitted-pointer",b"int main(){int x=7;int*p=&x;int*q=p?:0;return *q;}",7),
    ("omitted-null-pointer",b"int main(){int x=7;int*p=0;int*q=p?:&x;return *q;}",7),
    ("omitted-array",b"int main(){int a[1]={7};int*p=a?:0;return *p;}",7),
    ("omitted-pointer-effects",b"int main(){int a[2]={3,4};int*p=a;int*q=p++?:a;return *q+*p;}",7),
    ("omitted-wide",b"int main(){return (4294967296ULL?:7)>>32;}",1),
    ("omitted-wide-negative",b"int main(){long long n=-4294967296LL;return (n?:7)>>32;}",-1),
    ("omitted-unsigned-type",b"int main(){return __builtin_types_compatible_p(typeof(1U?:-1),unsigned int);}",1),
    ("omitted-char-promotion",b"int main(){unsigned char c=7;return __builtin_types_compatible_p(typeof(c?:1),int);}",1),
    ("omitted-nested",b"int main(){return 0?:0?:7;}",7),
    ("omitted-mixed-nesting",b"int main(){return 1?(0?:7):(3?:9);}",7),
    ("omitted-sizeof-effects",b"int main(){int n=7;return sizeof(n++?:n++)+n;}",11),
    ("omitted-inferred",b"int main(){int n=0;int a[]={n++?:7};return a[0]+n;}",8),
    ("omitted-macro",b"#define F(x,y) ((x)?: (y))\nint main(){int n=7;return F(n++,99)+n;}",15),
]
invalid = [
    ("omitted-aggregate-condition",b"int main(){struct S{int x;}s={7};s?:s;return 0;}"),
    ("omitted-pointer-integer",b"int main(){int x=7;int*p=&x;return p?:7;}"),
    ("omitted-result-write",b"int main(){int n=7;(n?:9)=2;return 0;}"),
]
volatile_reads = {"omitted-volatile": 1}
