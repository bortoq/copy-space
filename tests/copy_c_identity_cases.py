"""Compiler identity is predefined by copy-c; GCC remains an independent oracle."""
# The reference compiler identifies itself as GCC. Give only that reference
# branch the project macro used by these scalar preprocessor comparisons.
gcc_reference = b"#if !defined(__COPYSPACE__) && defined(__GNUC__)\n#define __COPYSPACE__ 1\n#endif\n"
valid = [
    ("identity-own", b"#if defined(__COPYSPACE__)\n_Static_assert(__COPYSPACE__==1,\"identity\");\n#if defined(__GNUC__) || defined(__clang__)\n#error false compiler identity\n#endif\nint main(){return 7;}\n#elif defined(__GNUC__)\nint main(){return 7;}\n#else\n#error unknown compiler\n#endif\n", 7),
    ("identity-value", gcc_reference + b"int main(){return 7*__COPYSPACE__;}", 7),
    ("identity-if", gcc_reference + b"#if __COPYSPACE__ != 1\n#error wrong identity\n#endif\nint main(){return 7;}\n", 7),
    ("identity-alias", gcc_reference + b"#define ID __COPYSPACE__\nint main(){return 7*ID;}\n", 7),
    ("identity-argument", gcc_reference + b"#define MUL(x) (7*(x))\nint main(){return MUL(__COPYSPACE__);}\n", 7),
    ("identity-undef", gcc_reference + b"#undef __COPYSPACE__\n#ifdef __COPYSPACE__\n#error still defined\n#endif\nint main(){return 7;}\n", 7),
    ("identity-override", gcc_reference + b"#undef __COPYSPACE__\n#define __COPYSPACE__ 7\nint main(){return __COPYSPACE__;}\n", 7),
    ("identity-function-override", gcc_reference + b"#undef __COPYSPACE__\n#define __COPYSPACE__(x) x\nint main(){return __COPYSPACE__(7);}\n", 7),
    ("identity-stringize", gcc_reference + b"#define S(x) #x\n#define X(x) S(x)\nint main(){char a[]=S(__COPYSPACE__);char b[]=X(__COPYSPACE__);return (a[0]=='_')*3+(b[0]=='1')*4;}\n", 7),
    ("identity-paste", gcc_reference + b"#define P(x,y) x##y\n#define X(x,y) P(x,y)\nint v1=7;int main(){return X(v,__COPYSPACE__);}\n", 7),
    ("identity-capacity", b"".join(b"#define M%d %d\n"%(i,i) for i in range(512))+b"#ifdef __COPYSPACE__\nint main(){return 7*__COPYSPACE__;}\n#else\nint main(){return 7;}\n#endif\n", 7),
]
invalid = [
    ("identity-not-function", b"int main(){return __COPYSPACE__(7);}"),
    ("identity-undef-expression", b"#undef __COPYSPACE__\nint main(){return __COPYSPACE__;}\n"),
]
