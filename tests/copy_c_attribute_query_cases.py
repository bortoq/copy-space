"""Attribute capability queries in conditions, expansions and ordinary text."""
valid = [
    ("attr-query-defined",b"#if defined(__has_attribute)\nint main(){return 7;}\n#else\n#error missing query\n#endif\n",7),
    ("attr-query-packed",b"#if __has_attribute(packed)\nint main(){return 7;}\n#else\n#error missing packed\n#endif\n",7),
    ("attr-query-aligned",b"int main(){return 7*__has_attribute(aligned);}",7),
    ("attr-query-alias-spelling",b"int main(){return 3*__has_attribute(__packed__)+4*__has_attribute(__aligned__);}",7),
    ("attr-query-unknown",b"#if __has_attribute(copy_space_unknown_attribute)\n#error wrong capability\n#endif\nint main(){return 7;}\n",7),
    ("attr-query-object-macro",b"#define A aligned\nint main(){return 7*__has_attribute(A);}\n",7),
    ("attr-query-function-macro",b"#define A(x) x\nint main(){return 7*__has_attribute(A(packed));}\n",7),
    ("attr-query-wrapper",b"#define Q(x) __has_attribute(x)\nint main(){return 7*Q(aligned);}\n",7),
    ("attr-query-name-alias",b"#define Q __has_attribute\nint main(){return 7*Q(aligned);}\n",7),
    ("attr-query-gnu-namespace",b"int main(){return 7*__has_attribute(gnu::aligned);}",7),
    ("attr-query-underscore-namespace",b"int main(){return 7*__has_attribute(__gnu__::__packed__);}",7),
    ("attr-query-other-namespace",b"int main(){return 7*(1-__has_attribute(copy_space::aligned));}",7),
    ("attr-query-undef",b"#undef __has_attribute\n#ifdef __has_attribute\n#error still enabled\n#endif\nint main(){return 7;}\n",7),
    ("attr-query-override",b"#undef __has_attribute\n#define __has_attribute(x) 7\nint main(){return __has_attribute(ignored);}\n",7),
    ("attr-query-unused-argument",b"#define F(x) 7\nint main(){return F(__has_attribute());}\n",7),
]
invalid = [
    ("attr-query-empty",b"int main(){return __has_attribute();}"),
    ("attr-query-number",b"int main(){return __has_attribute(7);}"),
    ("attr-query-string",b"int main(){return __has_attribute(\"packed\");}"),
    ("attr-query-two-identifiers",b"int main(){return __has_attribute(packed aligned);}"),
    ("attr-query-unclosed",b"int main(){return __has_attribute(packed;}"),
]
