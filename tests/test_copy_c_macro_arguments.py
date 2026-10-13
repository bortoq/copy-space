"""Check raw argument boundaries and GNU variadic arity against GCC."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "tmp/space-tests/copy-c-macro-arguments"
folder.mkdir(parents=True, exist_ok=True)
source = r'''
#include <stdio.h>
#include <string.h>
#include "runtime/copy_c/preprocess_macros.h"
int main(void) {
    unsigned char names[4096],input[4096]; cc_pp_parameters parameters;
    if (!fgets((char *)names,4096,stdin)) return 2;
    cc_pp_reader definition={names,strlen((char *)names),0,0};
    if (!cc_pp_read_parameters(&definition,&parameters)) return 2;
    unsigned size=fread(input,1,4096,stdin);
    cc_pp_reader reader={input,size,0,0},arguments[128]; int omitted[128];
    if (parameters.count>128 || cc_pp_next(&reader).kind != '(') return 2;
    if (!cc_pp_read_arguments(&reader,parameters,arguments,omitted)) return 2;
    if (cc_pp_next(&reader).kind || reader.failed) return 2;
    for (unsigned i=0;i<parameters.count;++i) {
        printf("%d %u\n",omitted[i],arguments[i].size);
        fwrite(arguments[i].text,1,arguments[i].size,stdout); putchar('\n');
    }
    return 0;
}
'''
path = folder / "test.c"
path.write_text(source)
command = ["cc", "-std=c99", "-O2", "-I", str(root), str(path), "-o", str(folder / "test")]
(folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
compiled = subprocess.run(command, capture_output=True)
(folder / "compile.stderr").write_bytes(compiled.stderr)
assert compiled.returncode == 0, compiled.stderr
cases = [
    (b"", b"()", []), (b"", b"( /**/ )", []),
    (b"a", b"()", [(b"",0)]), (b"a,b", b"(,)", [(b"",0),(b"",0)]),
    (b"a,b", b"((x,y),z)", [(b"(x,y)",0),(b"z",0)]),
    (b"a,b", b'("x,y",\',\')', [(b'"x,y"',0),(b"','",0)]),
    (b"a", b"( a/**/b\n )", [(b" a/**/b\n ",0)]),
    (b"a,...", b"(1)", [(b"1",0),(b"",1)]),
    (b"a,...", b"(1,)", [(b"1",0),(b"",0)]),
    (b"a,...", b"(1,x,y)", [(b"1",0),(b"x,y",0)]),
    (b"args...", b"()", [(b"",1)]),
    (b"...", b"(,)", [(b",",0)]),
    (b"a,args...", b"(x,(y,z),w)", [(b"x",0),(b"(y,z),w",0)]),
    (b"a,b", b"(1)", None), (b"a", b"(1,2)", None),
    (b"", b"(1)", None), (b"a,b", b"({1,2})", [(b"{1",0),(b"2}",0)]),
    (b"a", b"((x)", None), (b"a", b"(x", None),
]
for index, (names, invocation, expected) in enumerate(cases):
    case = folder / str(index)
    case.mkdir(exist_ok=True)
    incoming = names+b")\n"+invocation
    (case / "argument.in").write_bytes(incoming)
    result = subprocess.run([str(folder / "test")], input=incoming, capture_output=True)
    reference_source = b"#define F("+names+b") 7\nF"+invocation+b"\n"
    (case / "reference.c").write_bytes(reference_source)
    command = ["gcc", "-E", "-P", "-std=gnu11", "-x", "c", "-"]
    (case / "args.json").write_text(json.dumps(command)+"\n")
    reference = subprocess.run(command, input=reference_source, capture_output=True)
    (case / "result.out").write_bytes(result.stdout)
    (case / "reference.out").write_bytes(reference.stdout)
    (case / "reference.stderr").write_bytes(reference.stderr)
    valid = expected is not None
    assert (result.returncode == 0) == valid == (reference.returncode == 0), (index, result, reference)
    if valid:
        wanted = b"".join(f"{omitted} {len(raw)}\n".encode()+raw+b"\n" for raw,omitted in expected)
        assert result.stdout == wanted, (index, result.stdout, wanted)
    print(f"OK macro argument grammar and raw boundaries: {index}")
