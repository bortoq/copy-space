"""Cartesian GNU ranges, field preservation and high-index continuation."""
valid = [
    ("range-chain-guest", b'struct S{int x;}a[2]={[0 ... 1].x=7};int main(){return a[0].x+a[1].x;}', 14),
    ("range-chain-preserve", b'struct S{int x,y;}a[2]={[0].x=3,[1].x=4,[0 ... 1].y=7};int main(){return a[0].x+a[1].x+a[0].y+a[1].y;}', 21),
    ("range-chain-local", b'int main(){struct S{int x,y;}a[2]={[0].x=3,[1].x=4,[0 ... 1].y=7};return a[0].x+a[1].x+a[0].y+a[1].y;}', 21),
    ("range-chain-continue", b'struct S{int x,y,z;}a[2]={[0 ... 1].y=3,4};int main(){return a[0].y+a[0].z+a[1].y+a[1].z;}', 10),
    ("range-chain-matrix", b'int a[2][3]={[0 ... 1][1 ... 2]=7};int main(){return a[0][1]+a[0][2]+a[1][1]+a[1][2];}', 28),
    ("range-chain-matrix-local", b'int main(){int a[2][3]={[0 ... 1][1 ... 2]=7};return a[0][1]+a[0][2]+a[1][1]+a[1][2];}', 28),
    ("range-chain-matrix-continue", b'int a[2][3]={[0 ... 1][0 ... 1]=3,4};int main(){return a[0][0]+a[0][1]+a[0][2]+a[1][0]+a[1][1]+a[1][2];}', 16),
    ("range-chain-singleton", b'struct S{int x,y;}a[2]={[1 ... 1].x=3,4};int main(){return a[1].x+a[1].y;}', 7),
    ("range-chain-inferred", b'struct S{int x,y;}a[]={[0 ... 1].x=7};int main(){return sizeof(a)+a[0].x+a[1].x;}', 30),
    ("range-chain-call-once", b'int n=0;int f(){n++;return 7;}int main(){struct S{int x;}a[2]={[0 ... 1].x=f()};return a[0].x+a[1].x+n;}', 15),
    ("range-chain-matrix-increment", b'int main(){int n=3;int a[2][2]={[0 ... 1][0 ... 1]=n++};return a[0][0]+a[0][1]+a[1][0]+a[1][1]+n;}', 16),
    ("range-chain-array-field", b'struct S{int a[2];int n;}s[2]={[0 ... 1].a={3,4}};int main(){return s[0].a[0]+s[1].a[1];}', 7),
    ("range-chain-nested", b'struct S{struct T{int x,y;}t;}a[2]={[0 ... 1].t.x=3,[0 ... 1].t.y=4};int main(){return a[0].t.x+a[1].t.y;}', 7),
    ("range-chain-string", b'struct S{char s[3];int x;}a[2]={[0 ... 1].s="ab"};int main(){return a[0].s[0]+a[1].s[1];}', 195),
    ("range-chain-union-preserve", b'union U{int n;char s[4];}a[2]={[0].s[0]=3,[1].s[0]=4,[0 ... 1].s[1]=7};int main(){return a[0].s[0]+a[1].s[0]+a[0].s[1]+a[1].s[1];}', 21),
    ("range-chain-union-local", b'int main(){union U{int n;char s[4];}a[2]={[0].s[0]=3,[1].s[0]=4,[0 ... 1].s[1]=7};return a[0].s[0]+a[1].s[0]+a[0].s[1]+a[1].s[1];}', 21),
    ("range-chain-union-switch", b'union U{int n;char s[4];}a[2]={[0 ... 1].n=0x12345678,[0 ... 1].s[1]=7};int main(){return a[0].s[0]+a[1].s[0]+a[0].s[1]+a[1].s[1];}', 14),
    ("range-chain-rhs-nested", b'int main(){struct S{int x;}a[2]={[0 ... 1].x=({int b[2][2]={[0 ... 1][0 ... 1]=3};b[1][1];})};return a[0].x+a[1].x;}', 6),
]
invalid = [
    ("range-chain-scalar", b'int a[2]={[0 ... 1].x=7};int main(){return 0;}'),
    ("range-chain-upper", b'int a[2][2]={[0 ... 1][0 ... 2]=7};int main(){return 0;}'),
    ("range-chain-reversed", b'int a[2][2]={[0 ... 1][1 ... 0]=7};int main(){return 0;}'),
    ("range-chain-negative", b'int a[2][2]={[0 ... 1][-1 ... 0]=7};int main(){return 0;}'),
    ("range-chain-member-missing", b'struct S{int x;}a[2]={[0 ... 1].y=7};int main(){return 0;}'),
]
