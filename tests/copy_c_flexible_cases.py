"""C99 flexible array layout and access, including GNU nested structures."""
valid = [
    ("flex-size",b"int main(){return sizeof(struct S{char c;int data[];});}",4),
    ("flex-tail-padding",b"struct S{int n;char c;char data[];};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,data);}",13),
    ("flex-wide-align",b"int main(){return sizeof(struct S{short n;long long data[];})+_Alignof(struct S);}",8),
    ("flex-packed-layout",b"struct __attribute__((packed)) S{char c;int data[];};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,data);}",2),
    ("flex-aligned-owner",b"struct __attribute__((aligned(16))) S{char c;int data[];};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,data);}",20),
    ("flex-aligned-field",b"struct S{char c;char data[] __attribute__((aligned(8)));};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,data);}",16),
    ("flex-static-prefix",b"struct S{int n;int data[];};struct S s={7};int main(){return s.n;}",7),
    ("flex-static-empty",b"struct S{int n;int data[];};struct S s={7,{}};int main(){return s.n;}",7),
    ("flex-runtime",b"struct S{int n;int data[];};int main(){int b[3]={0};struct S*p=(struct S*)b;p->n=1;p->data[0]=2;p->data[1]=5;return p->data[0]+p->data[1];}",7),
    ("flex-packed-runtime",b"struct __attribute__((packed)) S{char c;int data[];};int main(){char b[9]={0};struct S*p=(struct S*)b;p->c=1;p->data[0]=2;p->data[1]=5;return p->data[0]+p->data[1];}",7),
    ("flex-nested-runtime",b"struct I{int n;int data[];};struct O{int x;struct I i;};int main(){int b[4]={0};struct O*p=(struct O*)b;p->i.data[0]=2;p->i.data[1]=5;return p->i.data[0]+p->i.data[1];}",7),
    ("flex-nested-array-size",b"struct I{int n;int data[];};int main(){return sizeof(struct I[2]);}",8),
    ("flex-matrix-layout",b"struct S{char c;int data[][2];};int main(){return sizeof(struct S)+__builtin_offsetof(struct S,data);}",8),
    ("flex-matrix-runtime",b"struct S{int n;int data[][2];};int main(){int b[5]={0};struct S*p=(struct S*)b;p->data[1][0]=7;return p->data[1][0];}",7),
]
invalid = [
    ("flex-only-field",b"struct S{int data[];};int main(){return 0;}"),
    ("flex-union-field",b"union U{int n;int data[];};int main(){return 0;}"),
    ("flex-not-last",b"struct S{int n;int data[];int x;};int main(){return 0;}"),
    ("flex-not-last-list",b"struct S{int n;int data[],x;};int main(){return 0;}"),
    ("flex-sizeof-field",b"struct S{int n;int data[];};int main(){struct S s;return sizeof(s.data);}"),
    ("flex-local-tail-init",b"int main(){struct S{int n;int data[];}s={1,{2}};return s.n;}"),
]
