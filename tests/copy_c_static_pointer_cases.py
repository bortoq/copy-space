"""Address constants in scalar static initializers, compiled in Forth."""
valid = [
    ("static-pointer-guest", b'int x=7;int*p=&x;int main(){return *p;}', 7),
    ("static-pointer-null", b'int*p=(void*)0;int main(){return p==0;}', 1),
    ("static-pointer-zero-init", b'int*p;int main(){return p==0;}', 1),
    ("static-pointer-write", b'int x=7;int*p=&x;int main(){*p=9;return x;}', 9),
    ("static-pointer-braces", b'int x=7;int*p={&x};int main(){return *p;}', 7),
    ("static-pointer-qualified", b'const int x=7;const int*p=&x;int main(){return *p;}', 7),
    ("static-pointer-void", b'int x=7;void*p=&x;int main(){return *(int*)p;}', 7),
    ("static-pointer-string", b'char*p="abc";int main(){return p[2];}', 99),
    ("static-pointer-string-qualified", b'const char*p="abc";int main(){return p[1];}', 98),
    ("static-pointer-string-offset", b'char*p="abc"+1;int main(){return p[0];}', 98),
    ("static-pointer-offset", b'int x=7;int*p=&x+1;int main(){return *(p-1);}', 7),
    ("static-pointer-extern", b'extern int x;int*p=&x;int x=7;int main(){return *p;}', 7),
    ("static-pointer-repeated", b'int x=7;extern int*p;int*p=&x;extern int*p;int main(){return *p;}', 7),
    ("static-pointer-compatible", b'int x=7;unsigned int p=(unsigned int)&x;int main(){return p==(unsigned int)&x;}', 1),
    ("static-init-extern-sizeof", b'extern int x;int y=sizeof(x);int main(){return y;}', 4),
    ("static-init-extern-generic", b'extern int x;int y=_Generic(1,default:x,int:7);int main(){return y;}', 7),
]
invalid = [
    ("static-pointer-integer", b'int*p=1;int main(){return 0;}'),
    ("static-pointer-qualifier-drop", b'const int x=7;int*p=&x;int main(){return *p;}'),
    ("static-pointer-wrong-type", b'int x=7;char*p=&x;int main(){return 0;}'),
    ("static-pointer-value-read", b'int x=7;int*p=&x;int*q=p;int main(){return 0;}'),
    ("static-pointer-extern-missing", b'extern int x;int*p=&x;int main(){return 0;}'),
    ("static-init-generic-selected", b'extern int x;int y=_Generic(1,int:x);int main(){return y;}'),
]
