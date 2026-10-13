"""GNU layout attributes on individual fields, including declarator lists."""
valid = [
    ("field-packed-size",b"int main(){return sizeof(struct S{char c;int x __attribute__((packed));});}",5),
    ("field-aligned-size",b"int main(){return sizeof(struct S{char c;int x __attribute__((aligned(8)));});}",16),
    ("field-packed-prefix",b"int main(){return sizeof(struct S{char c;int __attribute__((packed)) x;});}",5),
    ("field-packed-before-type",b"int main(){return sizeof(struct S{char c;__attribute__((packed)) int x;});}",5),
    ("field-prefix-list",b"int main(){return sizeof(struct S{char c;int __attribute__((aligned(8))) x,y;});}",24),
    ("field-suffix-list",b"struct S{char c;int x __attribute__((aligned(8))),y;};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,y);}",28),
    ("field-prefix-suffix-list",b"struct S{char c;int __attribute__((aligned(8))) x __attribute__((aligned(2))),y;};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,x)+__builtin_offsetof(struct S,y);}",48),
    ("field-multiple-aligned",b"int main(){return sizeof(struct S{char c;int x __attribute__((aligned(8),aligned(2)));});}",16),
    ("field-packed-aligned",b"struct S{char c;int x __attribute__((packed,aligned(2)));};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,x);}",8),
    ("field-aligned-packed-owner",b"struct __attribute__((packed)) S{char c;int x __attribute__((aligned(8)));};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,x);}",24),
    ("field-packed-aligned-owner",b"struct __attribute__((aligned(16))) S{char c;int x __attribute__((packed));};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,x);}",17),
    ("field-packed-runtime",b"int main(){struct S{char c;int x __attribute__((packed));}s={1,6};return s.c+s.x;}",7),
    ("field-packed-array",b"int main(){struct S{char c;int a[2] __attribute__((packed));}s={1,{2,4}};s.a[1]++;return s.a[0]+s.a[1];}",7),
    ("field-packed-nested",b"struct I{char c;int x;};struct O{char c;struct I i __attribute__((packed));};int main(){struct O o={1,{2,4}};o.i.x++;return o.i.c+o.i.x;}",7),
    ("field-aligned-runtime",b"int main(){struct S{char c;int x __attribute__((aligned(8)));}s={1,6};return s.c+s.x;}",7),
    ("field-aligned-packed-runtime",b"int main(){struct __attribute__((packed)) S{char c;int x __attribute__((aligned(8)));}s={1,6};return s.c+s.x;}",7),
    ("field-packed-union",b"union U{int x __attribute__((packed));char c;};int main(){return sizeof(union U)+_Alignof(union U);}",5),
    ("field-packed-static",b"struct S{char c;int x __attribute__((packed));};struct S s={1,6};int main(){return s.c+s.x;}",7),
    ("field-packed-wide",b"int main(){struct S{char c;unsigned long long x __attribute__((packed));}s={1,0x100000006ULL};return (s.x>>32)+(unsigned)s.x;}",7),
]
invalid = [
    ("field-align-three",b"struct S{int x __attribute__((aligned(3)));};int main(){return 0;}"),
    ("field-packed-argument",b"struct S{int x __attribute__((packed(1)));};int main(){return 0;}"),
]
