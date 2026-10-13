"""Programs whose headers must be resolved by the guest, never the packer."""
valid = [
    ("include-main-index", [("unused.c",b"this must not be parsed"), ("main.c",b"int main(){return 7;}\n")], [""], 1),
    ("include-quote-local", [("src/main.c",b'#include "value.h"\nint main(){return V;}\n'), ("src/value.h",b"#define V 7\n"), ("sys/value.h",b"#define V 2\n")], ["sys"], 0),
    ("include-angle-order", [("src/main.c",b'#include <value.h>\nint main(){return V;}\n'), ("src/value.h",b"#define V 1\n"), ("a/value.h",b"#define V 7\n"), ("b/value.h",b"#define V 2\n")], ["a","b"], 0),
    ("include-nested-relative", [("src/main.c",b'#include "detail/outer.h"\nint main(){return V;}\n'), ("src/detail/outer.h",b'#include ".././config.h"\n'), ("src/config.h",b"#define V 7\n")], [], 0),
    ("include-macro-quote", [("main.c",b'#define ID(x) x\n#define H "value.h"\n#include ID(H)\nint main(){return V;}\n'), ("value.h",b"#define V 7\n")], [""], 0),
    ("include-macro-angle", [("main.c",b'#define H(x) <x.h>\n#include H(value)\nint main(){return V;}\n'), ("value.h",b"#define V 7\n")], [""], 0),
    ("include-literal-no-expand", [("main.c",b'#define value other\n#include <value.h>\nint main(){return V;}\n'), ("value.h",b"#define V 7\n"), ("other.h",b"#define V 1\n")], [""], 0),
    ("include-angle-comment-bytes", [("main.c",b'#include <x/*y>\nint main(){return V;}\n'), ("x/*y",b"#define V 7\n")], [""], 0),
    ("include-next", [("main.c",b'#include <value.h>\nint main(){return V+W;}\n'), ("a/value.h",b'#define W 3\n#include_next "value.h"\n'), ("b/value.h",b"#define V 4\n")], ["a","b"], 0),
    ("include-guard-self", [("main.c",b'#include "value.h"\n#include "value.h"\nint main(){return V;}\n'), ("value.h",b'#ifndef GUARD\n#define GUARD\n#include "value.h"\n#define V 7\n#endif\n')], [""], 0),
    ("include-pragma-once", [("main.c",b'#include "value.h"\n#include "./value.h"\nint main(){return value;}\n'), ("value.h",b'#pragma once\n#include "value.h"\nint value=7;\n')], [""], 0),
    ("include-inactive", [("main.c",b'#if 0\n#include "missing.h"\n#include broken(\n#endif\nint main(){return 7;}\n')], [], 0),
    ("include-parent-condition", [("main.c",b'#if 1\n#include "value.h"\n#else\n#error wrong\n#endif\nint main(){return V;}\n'), ("value.h",b'#if 1\n#define V 7\n#endif\n')], [""], 0),
    ("include-no-final-newline", [("main.c",b'#include "value.h"\nint main(){return V;}'), ("value.h",b"#define V 7")], [""], 0),
    ("include-expression-fragment", [("main.c",b'int main(){return\n#include "value.h"\n;}\n'), ("value.h",b"7")], [""], 0),
    ("include-completed-macro-arguments", [("main.c",b'#define ADD(a,b) ((a)+(b))\nint main(){return ADD(\n#include "args.h"\n;}\n'), ("args.h",b"3,4)\n")], [""], 0),
    ("include-phase2-header", [("main.c",b'#include "value.h"\nint main(){return V;}\n'), ("value.h",b"#def\\\r\nine V 7\r\n")], [""], 0),
    ("include-empty-header", [("main.c",b'#include "empty.h"\nint main(){return 7;}\n'), ("empty.h",b"")], [""], 0),
    ("include-comments-around-name", [("main.c",b'#include /*before*/ "value.h" /*after*/\nint main(){return V;}\n'), ("value.h",b"#define V 7\n")], [""], 0),
]
invalid = [
    ("include-macro-arguments", [("main.c",b'#define ADD(a,b) ((a)+(b))\nint main(){return ADD(\n#include "args.h"\n);}\n'), ("args.h",b"3,4\n")], [""], 0),
    ("include-missing", [("main.c",b'#include "missing.h"\n')], [""], 0),
    ("include-trailing-token", [("main.c",b'#include "value.h" extra\n'), ("value.h",b"")], [""], 0),
    ("include-parent-endif", [("main.c",b'#if 1\n#include "value.h"\n#endif\n'), ("value.h",b"#endif\n")], [""], 0),
    ("include-parent-else", [("main.c",b'#if 1\n#include "value.h"\n#endif\n'), ("value.h",b"#else\n")], [""], 0),
    ("include-unclosed-condition", [("main.c",b'#include "value.h"\n#endif\n'), ("value.h",b"#if 1\n")], [""], 0),
    ("include-outside-root", [("main.c",b'#include "../value.h"\n'), ("value.h",b"")], [""], 0),
    ("include-recursion-limit", [("main.c",b'#include "value.h"\n'), ("value.h",b'#include "value.h"\n')], [""], 0),
    ("include-bad-computed", [("main.c",b'#define H 3\n#include H\n')], [""], 0),
    ("include-computed-trailing", [("main.c",b'#define H "value.h"\n#include H H\n'), ("value.h",b"")], [""], 0),
]

def query_case(name,condition,*,prefix=b"",files=None,roots=None):
    source=prefix+b"#if "+condition+b"\nint main(){return 7;}\n#else\n#error wrong query result\n#endif\n"
    return name,[("main.c",source)]+(files or []),roots if roots is not None else [""],0

valid += [
    ("include-next-duplicate-root",[("main.c",b'#include <value.h>\nint main(){return w+V;}\n'),("a/value.h",b'int w=3;\n#include_next <value.h>\n'),("b/value.h",b'#define V 4\n')],["a","a","b"],0),
    query_case("has-include-defined",b"defined(__has_include) && defined __has_include_next"),
    query_case("has-include-missing",b'!__has_include("missing.h")'),
    query_case("has-include-present",b'__has_include("value.h")',files=[("value.h",b"#error must not be loaded\n")]),
    query_case("has-include-literal-no-expand",b'__has_include(<value.h>)',prefix=b"#define value missing\n",files=[("value.h",b"")]),
    query_case("has-include-macro-quote",b'__has_include(ID(H))',prefix=b'#define H "value.h"\n#define ID(x) x\n',files=[("value.h",b"")]),
    query_case("has-include-macro-angle",b'__has_include(H)',prefix=b'#define H <value.h>\n',files=[("value.h",b"")]),
    query_case("has-include-alias",b'HI(<x/*y>)',prefix=b'#define HI __has_include\n',files=[("x/*y",b"")]),
    query_case("has-include-literal-comment",b'__has_include(<x/*y>)',files=[("x/*y",b"")]),
    query_case("has-include-paren-name",b'__has_include(<x)y.h>)',files=[("x)y.h",b"")]),
    query_case("has-include-function-produced",b'QUERY("value.h")',prefix=b'#define QUERY(x) __has_include(x)\n',files=[("value.h",b"")]),
    query_case("has-include-used-argument",b'ID(__has_include(<value.h>))',prefix=b'#define ID(x) x\n',files=[("value.h",b"")]),
    query_case("has-include-unused-argument",b'IGNORE(__has_include(3))',prefix=b'#define IGNORE(x) 1\n'),
    query_case("has-include-undef",b'!defined(__has_include)',prefix=b'#undef __has_include\n'),
    query_case("has-include-override",b'__has_include(3)',prefix=b'#define __has_include(x) 1\n'),
    ("has-include-next",[("main.c",b'#include <wrapper.h>\nint main(){return V;}\n'),("a/wrapper.h",b'#if __has_include_next(<value.h>)\n#define V 7\n#else\n#error missing next file\n#endif\n'),("a/value.h",b"#error wrong first root\n"),("b/value.h",b"#error must not load\n")],["a","b"],0),
    ("has-include-next-missing",[("main.c",b'#include <wrapper.h>\nint main(){return V;}\n'),("a/wrapper.h",b'#if !__has_include_next("value.h")\n#define V 7\n#else\n#error found same root\n#endif\n'),("a/value.h",b"#error must not load\n")],["a","empty"],0),
    ("has-include-once-present",[("main.c",b'#include "value.h"\n#if __has_include("value.h")\nint main(){return 7;}\n#else\n#error once is still present\n#endif\n'),("value.h",b"#pragma once\n")],[""],0),
    ("has-include-inactive",[("main.c",b'#if 0\n#if __has_include(3)\n#endif\n#endif\nint main(){return 7;}\n')],[],0),
]
for name,expression in [
    ("has-include-bare",b"__has_include"),
    ("has-include-empty",b"__has_include()"),
    ("has-include-number",b"__has_include(3)"),
    ("has-include-empty-name",b'__has_include("")'),
    ("has-include-extra",b'__has_include("value.h" extra)'),
    ("has-include-unclosed",b'__has_include("value.h"'),
]:
    invalid.append(query_case(name,expression))
invalid.extend([
    query_case("has-include-operator-argument",b'CALL(__has_include)',prefix=b'#define CALL(f) f("value.h")\n',files=[("value.h",b"")]),
    query_case("has-include-returned-operator",b'ID(__has_include)("value.h")',prefix=b'#define ID(x) x\n',files=[("value.h",b"")]),
])
invalid.append(("has-include-outside-condition",[("main.c",b'int main(){return __has_include("value.h");}\n'),("value.h",b"")],[""],0))
invalid.append(("has-include-next-no-search-path",[("main.c",b'#include <wrapper.h>\n'),("a/wrapper.h",b'#if __has_include_next("value.h")\n#endif\n')],["a"],0))
