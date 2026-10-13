"""Compare actual guest preprocessing with GCC, independently of C parsing."""
import json
import subprocess
from pathlib import Path
from copy_c_object_macro_cases import valid as object_cases
from copy_c_conditional_cases import valid as condition_cases
from copy_c_preprocess_cases import valid as phase2_cases
from copy_c_function_macro_cases import valid as function_cases

root = Path(__file__).resolve().parents[1]
folder = root / "tmp/space-tests/copy-c-preprocessor"
folder.mkdir(parents=True, exist_ok=True)
source = r'''
#include <stdio.h>
#include "runtime/copy_c/preprocess_phase2.h"
#include "runtime/copy_c/preprocess_macros.h"
static unsigned char input[CC_PP_OUTPUT];
int main(int argc,char **argv) {
    (void)argv;
    unsigned size=fread(input,1,sizeof(input),stdin);
    if (argc == 1) {
        int result=cc_preprocess_macros(input,cc_preprocess_phase2(input,size));
        if (result<0) return 2;
        size=(unsigned)result;
    }
    cc_pp_reader reader={input,size,0,0};
    for (;;) {
        cc_pp_token token=cc_pp_next(&reader);
        if (reader.failed) return 3;
        if (!token.kind) break;
        if (token.kind == '\n') continue;
        fwrite(token.text,1,token.size,stdout); putchar(' ');
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
cases = object_cases+condition_cases+phase2_cases+function_cases
for name, incoming, *_ in cases:
    case = folder / name
    case.mkdir(exist_ok=True)
    (case / "source.c").write_bytes(incoming)
    result = subprocess.run([str(folder / "test")], input=incoming, capture_output=True, timeout=30)
    command = ["gcc", "-E", "-P", "-std=gnu11", "-x", "c", "-"]
    (case / "args.json").write_text(json.dumps(command)+"\n")
    reference = subprocess.run(command, input=incoming, capture_output=True, timeout=30)
    canonical = subprocess.run([str(folder / "test"), "tokens"], input=reference.stdout, capture_output=True)
    (case / "result.out").write_bytes(result.stdout)
    (case / "reference.out").write_bytes(reference.stdout)
    (case / "reference.stderr").write_bytes(reference.stderr)
    assert result.returncode == reference.returncode == canonical.returncode == 0, (name, result, reference)
    assert result.stdout == canonical.stdout, (name, result.stdout, canonical.stdout)
    print(f"OK guest preprocessor matches GCC tokens: {name}")
(folder / "summary.json").write_text(json.dumps({"gcc_token_comparisons":len(cases)},indent=2)+"\n")
