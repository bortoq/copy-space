"""Independent function frames and persistent call signatures."""
valid = [
    ("frame-large-functions", b'int f(){char a[1200];a[1199]=3;return a[1199];}int g(){char a[1200];a[1199]=4;return a[1199];}int main(){return f()+g();}', 7),
    ("frame-mixed-results", b'signed char f(){return 128;}unsigned short g(){return 65535;}int main(){return f()+135+(g()==65535)-1;}', 7),
    ("frame-prototype-after-body", b'int f(short);int g(int *p){return *p;}int f(short n){return n+4;}int main(){int n=7;return f(3)+g(&n)-7;}', 7),
    ("frame-caller-types", b'int f(unsigned char n){return n;}int main(){signed char n=-1;int x=f(n);return x==255&&n==-1?7:9;}', 7),
    ("frame-packed-call", b'int f(char a,short b){return a+b;}int g(int *p){return *p;}int main(){int n=4;return f(1,2)+g(&n);}', 7),
    ("frame-recursive-pointer", b'int f(int n,int *p){int v=n;if(n)return f(n-1,&v)+*p;return *p;}int main(){int n=4;return f(2,&n);}', 7),
    ("frame-mixed-callbacks", b'int f(signed char n){return n+135;}int g(unsigned short n){return n==65535?7:9;}int main(){int (*p)(signed char)=f;int (*q)(unsigned short)=g;return p(128)+q(-1)-7;}', 7),
]
