"""Aggregate zeroing, including padding and storage reused between calls."""
valid = [
    ("zero-object-small", b"int main(){char a[3]={0};return a[0]+a[2];}", 0),
    ("zero-object-array", b"int main(){int a[100]={0};a[99]=7;return a[0]+a[98]+a[99];}", 7),
    ("zero-object-repeat", b"int f(int n){char a[1200]={0};if(n){a[0]=9;a[1199]=9;}return a[0]+a[1199];}int main(){int n=f(1);return n+f(0);}", 18),
    ("zero-object-large", b"int f(){char a[1800]={0};a[1799]=7;return a[0]+a[1798]+a[1799];}int main(){return f();}", 7),
    ("zero-object-wide-array", b"int main(){long long a[80]={0};a[79]=1LL<<32;return (a[0]==0)+(a[78]==0)+(a[79]>>32);}", 3),
    ("zero-object-padding", b"struct S{char c;long long x;short y;};int main(){struct S s={0};unsigned char*p=(unsigned char*)&s;int n=0;for(int i=0;i<sizeof(s);i++)n+=p[i];return n;}", 0),
    ("zero-object-guest", b"int f(){char a[1200]={0};a[1199]=7;return a[0]+a[1199];}int main(){return f();}", 7),
]
