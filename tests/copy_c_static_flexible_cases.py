"""GNU static flexible tail initialization without changing the record type."""
valid = [
    ("static-flex-values",b"struct S{int n;int data[];};struct S s={1,{2,5}};int main(){return s.data[0]+s.data[1];}",7),
    ("static-flex-sizeof",b"struct S{int n;int data[];};struct S s={1,{2,5}};int main(){return sizeof(s);}",4),
    ("static-flex-neighbor",b"struct S{int n;int data[];};struct S s={1,{2,5}};int guard=123;int main(){if(guard!=123)return 99;return s.data[0]+s.data[1];}",7),
    ("static-flex-empty-tail",b"struct S{int n;int data[];};struct S s={7,{}};int main(){return s.n;}",7),
    ("static-flex-char-string",b'struct S{int n;char data[];};struct S s={1,"ab"};int main(){return s.data[0]+s.data[1]+s.data[2];}',195),
    ("static-flex-designated",b"struct S{int n;int data[];};struct S s={.data={[2]=7},.n=1};int main(){return s.data[0]+s.data[1]+s.data[2];}",7),
    ("static-flex-range",b"struct S{int n;int data[];};struct S s={1,{[0 ... 2]=7}};int main(){return s.data[0]+s.data[1]+s.data[2];}",21),
    ("static-flex-packed",b"struct __attribute__((packed)) S{char n;int data[];};struct S s={1,{2,5}};int main(){return s.data[0]+s.data[1];}",7),
    ("static-flex-local-static",b"int f(){static struct S{int n;int data[];}s={1,{2,5}};return s.data[0]+s.data[1];}int main(){return f();}",7),
    ("static-flex-tail-padding",b'struct S{int n;char c;char data[];};struct S s={1,2,"ab"};int guard=123;int main(){if(guard!=123)return 99;return s.data[0]+s.data[1]+sizeof(s);}',203),
]
