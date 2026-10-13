"""Compare the guest stringification helper with GCC preprocessing."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "tmp/space-tests/copy-c-macro-stringify"
folder.mkdir(parents=True, exist_ok=True)
source = r'''
#include <stdio.h>
#include "runtime/copy_c/preprocess_macros.h"
int main(void) {
    unsigned char input[4096]; unsigned size=fread(input,1,sizeof(input),stdin);
    cc_pp_reader reader={input,size,0,0}; cc_pp_token result;
    if (!cc_pp_stringify(reader,&result)) return 2;
    fwrite(result.text,1,result.size,stdout); return 0;
}
'''
path = folder / "test.c"
path.write_text(source)
command = ["cc", "-std=c99", "-O2", "-I", str(root), str(path), "-o", str(folder / "test")]
(folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
compiled = subprocess.run(command, capture_output=True)
(folder / "compile.stderr").write_bytes(compiled.stderr)
assert compiled.returncode == 0, compiled.stderr
cases = [b"", b"  ", b"a+b", b"a + b", b"a\t\t+b", b"a/**/b",
         b"a/* one\n two */b", b"a\nb", b'"a b"', b'"a\\n\\\\b"',
         b"'\\n'", b"  a + b  ", b"L\"a\\\"b\"", b"a//end\nb"]
for index, raw in enumerate(cases):
    case = folder / str(index)
    case.mkdir(exist_ok=True)
    (case / "argument.in").write_bytes(raw)
    result = subprocess.run([str(folder / "test")], input=raw, capture_output=True)
    incoming = b"#define S(x) #x\nS("+raw+b")\n"
    (case / "reference.c").write_bytes(incoming)
    command = ["gcc", "-E", "-P", "-std=gnu11", "-x", "c", "-"]
    (case / "args.json").write_text(json.dumps(command)+"\n")
    reference = subprocess.run(command, input=incoming, capture_output=True)
    (case / "result.out").write_bytes(result.stdout)
    (case / "reference.out").write_bytes(reference.stdout)
    (case / "reference.stderr").write_bytes(reference.stderr)
    assert result.returncode == reference.returncode == 0, (index, reference.stderr)
    assert result.stdout == reference.stdout.strip(), (index, result.stdout, reference.stdout)
    print(f"OK stringification matches GCC: {index}")
