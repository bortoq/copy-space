"""Check the guest definition parser; this does not prove macro expansion."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "tmp/space-tests/copy-c-macro-parameters"
folder.mkdir(parents=True, exist_ok=True)
source = r'''
#include <stdio.h>
#include <string.h>
#include "runtime/copy_c/preprocess_macros.h"
int main(void) {
    struct sample { const char *text; int valid; unsigned count; int variadic; } cases[] = {
        { ") rest", 1, 0, 0 }, { "a) rest", 1, 1, 0 },
        { "a,b,c) rest", 1, 3, 0 }, { "...) rest", 1, 1, 1 },
        { "a,...) rest", 1, 2, 1 }, { "args...) rest", 1, 1, 1 },
        { "a,args...) rest", 1, 2, 1 }, { "a/**/,b) rest", 1, 2, 0 },
        { "a,a) rest", 0, 0, 0 }, { "a,) rest", 0, 0, 0 },
        { ",a) rest", 0, 0, 0 }, { "...,a) rest", 0, 0, 0 },
        { "a...,b) rest", 0, 0, 0 }, { "42) rest", 0, 0, 0 },
        { "a+b) rest", 0, 0, 0 }, { "a\n) rest", 0, 0, 0 },
        { "a", 0, 0, 0 }, { "a,", 0, 0, 0 },
    };
    for (unsigned i=0; i<sizeof(cases)/sizeof(*cases); ++i) {
        cc_pp_parameter_count=0;
        cc_pp_reader reader={(const unsigned char *)cases[i].text,strlen(cases[i].text),0,0};
        cc_pp_parameters parameters={0,0,0};
        int valid=cc_pp_read_parameters(&reader,&parameters);
        if (valid != cases[i].valid) return 1;
        if (valid) {
            if (parameters.count != cases[i].count || parameters.variadic != cases[i].variadic) return 2;
            if (!cc_pp_is(cc_pp_next(&reader),"rest")) return 3;
            if (parameters.variadic && strstr(cases[i].text,"args"))
                if (!cc_pp_is(cc_pp_parameter_names[parameters.count-1],"args")) return 4;
        } else if (cc_pp_parameter_count) return 5;
        printf("OK parameter grammar %u\n",i);
    }
    cc_pp_parameter_count=CC_PP_PARAMETERS;
    cc_pp_reader reader={(const unsigned char *)"x)",2,0,0};
    cc_pp_parameters parameters;
    if (cc_pp_read_parameters(&reader,&parameters) || cc_pp_parameter_count != CC_PP_PARAMETERS) return 6;
    puts("OK parameter capacity preserves previous definitions");
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
result = subprocess.run([str(folder / "test")], capture_output=True)
(folder / "result.out").write_bytes(result.stdout)
(folder / "stderr.txt").write_bytes(result.stderr)
assert result.returncode == 0, (result.returncode, result.stderr)
print(result.stdout.decode(), end="")
