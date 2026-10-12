"""GNU integer semantics and lazy evaluation; source is passed unchanged to Forth."""
import random

valid = [
    ("unsigned-function", b"unsigned f(unsigned int);int main(){return f(0xffffffffU)>0;}unsigned f(unsigned int n){return n;}", 1),
    ("unsigned-integer", b"int main(){unsigned int x=0xffffffffU;int y=-1;return x==y;}", 1),
    ("unsigned-convert", b"int main(){unsigned x=-1;return x>1;}", 1),
    ("signed-convert", b"int main(){int x=0xffffffffU;return x<0;}", 1),
    ("signed-specifier", b"signed int f(signed n){return n;}int main(){return f(-3);}", -3),
    ("unsigned-order", b"int main(){unsigned a=0x80000000;unsigned b=0x7fffffff;return a>b;}", 1),
    ("mixed-order", b"int main(){int a=-1;unsigned b=7;return a>b;}", 1),
    ("mixed-arithmetic-type", b"int main(){return (0U-1)>0;}", 1),
    ("integer-bases", b"int main(){return 077+0b101+0B11+0X10u;}", 87),
    ("decimal-unsigned", b"int main(){return 4294967295u>2147483647;}", 1),
    ("unary-plus", b"int main(){return +(+19);}", 19),
    ("cast-signed", b"int main(){return (int)0x80000000<0;}", 1),
    ("cast-unsigned", b"int main(){return (unsigned int)-1>0;}", 1),
    ("cast-pointer", b"int main(){int x=8;unsigned a=(unsigned)&x;int *p=(int*)a;return *p;}", 8),
    ("cast-type-propagation", b"int main(){return ((unsigned)-1>>31)+((int)0x80000000>>31);}", 0),
    ("bitwise", b"int main(){return (0xf0&0x3c)|0x03^0x01;}", 50),
    ("bitwise-unsigned-type", b"int main(){return (0xffffffffU&-1)>0;}", 1),
    ("bitwise-not", b"int main(){return ~0U;}", -1),
    ("bitwise-not-signed", b"int main(){return ~0<0;}", 1),
    ("left-shift", b"int main(){unsigned x=0x81234567U;return x<<13;}", 0x68ace000),
    ("right-shift-unsigned", b"int main(){unsigned x=0x81234567U;return x>>13;}", 0x4091a),
    ("right-shift-signed", b"int main(){int x=(int)0x81234567;return x>>13;}", 0xfffc091a),
    ("shift-sign-by-count", b"int main(){int x=-8;unsigned n=1;return x>>n;}", -4),
    ("shift-edges", b"int main(){return (1U<<31)+(0xffffffffU>>31)+(77<<0);}", 0x8000004e),
    ("shift-precedence", b"int main(){return 1+2<<2+1;}", 24),
    ("multiply", b"int main(){return -7*9;}", -63),
    ("multiply-zero", b"int main(){return 0*0xffffffffU;}", 0),
    ("multiply-wrap", b"int main(){return 0x80000000U*3U;}", 0x80000000),
    ("divide-signed", b"int main(){return -17/5;}", -3),
    ("divide-both-negative", b"int main(){return -17/-5;}", 3),
    ("divide-negative-divisor", b"int main(){return 17/-5;}", -3),
    ("remainder-signed", b"int main(){return -17%5;}", -2),
    ("remainder-negative-divisor", b"int main(){return 17%-5;}", 2),
    ("remainder-both-negative", b"int main(){return -17%-5;}", -2),
    ("divide-unsigned", b"int main(){return 0xffffffffU/3U;}", 0x55555555),
    ("remainder-unsigned", b"int main(){return 0xffffffffU%17U;}", 0),
    ("divide-high-denominator", b"int main(){return 0xffffffffU/0x80000001U;}", 1),
    ("remainder-high-denominator", b"int main(){return 0xffffffffU%0x80000001U;}", 0x7ffffffe),
    ("divide-minimum", b"int main(){return (int)0x80000000/7;}", -306783378),
    ("remainder-minimum", b"int main(){return (int)0x80000000%7;}", -2),
    ("arithmetic-precedence", b"int main(){return 2+3*4-9/2+9%2;}", 11),
    ("logical-and-skip", b"int f(int*p){*p=99;return 1;}int main(){int x=7;int y=0&&f(&x);return x+y;}", 7),
    ("logical-or-skip", b"int f(int*p){*p=99;return 0;}int main(){int x=7;int y=1||f(&x);return x+y;}", 8),
    ("logical-and-run", b"int f(int*p){*p=99;return 7;}int main(){int x=0;int y=2&&f(&x);return x+y;}", 100),
    ("logical-or-run", b"int f(int*p){*p=99;return 7;}int main(){int x=0;int y=0||f(&x);return x+y;}", 100),
    ("logical-null-skip", b"int main(){int *p=0;return (0&&*p)+(1||*p);}", 1),
    ("logical-precedence", b"int main(){return 0||2&&3;}", 1),
    ("logical-normalize", b"int main(){return 256&&0x80000000;}", 1),
    ("conditional-true", b"int main(){int *p=0;return 1?7:*p;}", 7),
    ("conditional-false", b"int main(){int *p=0;return 0?*p:19;}", 19),
    ("conditional-type", b"int main(){return (1?-1:1U)>0;}", 1),
    ("conditional-pointer", b"int main(){int x=9;int*p=1?&x:0;return *p;}", 9),
    ("conditional-association", b"int main(){return 0?3:1?7:9;}", 7),
    ("conditional-nested", b"int main(){return 1?(0?3:5):9;}", 5),
    ("conditional-side-effect", b"int f(int*p){*p=8;return 4;}int main(){int x=0;int y=0?f(&x):3;return x+y;}", 3),
    ("gnu-integer", b"int main(){return (0xffU>>4)&7;}", 7),
    ("logical-divide-skip", b"int main(){return 0&&7/0;}", 0),
    ("conditional-divide-skip", b"int main(){return 1?11:7/0;}", 11),
    ("conditional-null-type", b"int main(){int x=8;int*p=0?0:&x;return *p;}", 8),
    ("repeated-arithmetic", b"int main(){unsigned a=17;unsigned b=5;int x=a/b;int y=a%b;int z=a*b;return x+y+z+(a<<2)+(a>>2);}", 162),
]

# Independent Python arithmetic supplies expected bits; GCC checks the same
# C sources under the 32-bit ABI. Values exercise all integer bit positions.
numbers = random.Random(0xC012)
for i in range(12):
    a, b = numbers.getrandbits(32), numbers.getrandbits(32) or 1
    source = f"int main(){{unsigned a={a}U;unsigned b={b}U;return (a/b)^(a%b);}}".encode()
    valid.append((f"division-random-{i}", source, (a//b)^(a%b)))

invalid = [
    ("decimal-needs-64", b"int main(){return 2147483648;}"),
    ("bad-octal", b"int main(){return 08;}"),
    ("bad-binary", b"int main(){return 0b102;}"),
    ("bad-suffix", b"int main(){return 3uu;}"),
    ("long-suffix", b"int main(){return 3UL;}"),
    ("sign-conflict", b"int main(){unsigned signed x;return 0;}"),
    ("unsigned-prototype-conflict", b"unsigned f(int);int f(int);int main(){return 0;}"),
    ("unsigned-param-conflict", b"int f(unsigned);int f(int);int main(){return 0;}"),
    ("pointer-bitwise", b"int main(){int x;return &x&1;}"),
    ("pointer-shift", b"int main(){int x;return &x<<1;}"),
    ("pointer-multiply", b"int main(){int x;return &x*3;}"),
    ("conditional-pointer-integer", b"int main(){int x;return 1?&x:7;}"),
]

faults = [
    ("divide-zero", b"int main(){return 7/0;}", b"copy-c: divide by zero\n"),
    ("remainder-zero", b"int main(){return 7%0;}", b"copy-c: divide by zero\n"),
    ("shift-negative", b"int main(){return 7<<-1;}", b"copy-c: shift error\n"),
    ("shift-width", b"int main(){return 7>>32;}", b"copy-c: shift error\n"),
    ("shift-high", b"int main(){return 7U>>0xffffffffU;}", b"copy-c: shift error\n"),
]
