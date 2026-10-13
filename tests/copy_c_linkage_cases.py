"""Internal/external linkage rules preserved for the future guest linker."""
valid = [
    ("static-init-full-guest", b'extern int x;static int*p=&x;int main(){return *p;}int x=7;', 7),
    ("linkage-static-zero", b'static int x;int main(){return x;}', 0),
    ("linkage-static-object", b'static int x=7;int main(){return x;}', 7),
    ("linkage-static-repeat", b'static int x;static int x;int main(){return x;}', 0),
    ("linkage-static-initialized", b'static int x;static int x=7;int main(){return x;}', 7),
    ("linkage-static-extern", b'static int x=7;extern int x;int main(){return x;}', 7),
    ("linkage-static-extern-definition", b'static int x;extern int x=7;int main(){return x;}', 7),
    ("linkage-static-function", b'static int f(){return 7;}int main(){return f();}', 7),
    ("linkage-function-inherit", b'static int f(void);int f(void){return 7;}int main(){return f();}', 7),
    ("linkage-function-extern", b'static int f(void);extern int f(void);static int f(void){return 7;}int main(){return f();}', 7),
]
invalid = [
    ("linkage-object-default-after", b'static int x;int x;int main(){return 0;}'),
    ("linkage-object-static-after", b'int x;static int x;int main(){return 0;}'),
    ("linkage-object-extern-before", b'extern int x;static int x;int main(){return 0;}'),
    ("linkage-function-static-after", b'int f(void);static int f(void){return 7;}int main(){return f();}'),
    ("linkage-function-extern-before", b'extern int f(void);static int f(void){return 7;}int main(){return f();}'),
    ("linkage-object-two-definitions", b'static int x=3;static int x=4;int main(){return x;}'),
    ("linkage-conflicting-classes", b'extern static int x;int main(){return 0;}'),
]
