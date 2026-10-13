"""Test parameter substitution separately from the pending rescan engine."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "tmp/space-tests/copy-c-macro-substitute"
folder.mkdir(parents=True, exist_ok=True)
source = r'''
#include <stdio.h>
#include <string.h>
#include "runtime/copy_c/preprocess_macros.h"
static unsigned tokens(unsigned char *text, cc_pp_token *out) {
    cc_pp_reader reader={text,strlen((char *)text),0,0}; unsigned n=0;
    for (;;) { cc_pp_token t=cc_pp_next(&reader); if (!t.kind) break;
        if (reader.failed || n == 128) return 129;
        if (t.kind != '\n') out[n++]=t;
    } return n;
}
int main(int argc,char **argv) {
    unsigned char text[3][4096]; cc_pp_token body[128],raw[2][128],expanded[2][128],out[256];
    if (argc > 1 && !strcmp(argv[1],"tokens")) {
        unsigned n=fread(text[0],1,4095,stdin); text[0][n]=0;
        n=tokens(text[0],out); if (n>128) return 2;
        for (unsigned i=0;i<n;++i) { fwrite(out[i].text,1,out[i].size,stdout); putchar(' '); }
        return 0;
    }
    for (unsigned i=0;i<3;++i) {
        if (!fgets((char *)text[i],4096,stdin)) return 3;
        unsigned n=strlen((char *)text[i]); if (n && text[i][n-1]=='\n') text[i][n-1]=0;
    }
    cc_pp_reader names={(const unsigned char *)"a,b)",4,0,0}; cc_pp_parameters parameters;
    if (!cc_pp_read_parameters(&names,&parameters)) return 4;
    cc_pp_argument arguments[2];
    for (unsigned i=0;i<2;++i) {
        unsigned n=tokens(text[i+1],raw[i]); if (n>128) return 5;
        for (unsigned j=0;j<n;++j) { expanded[i][j]=raw[i][j];
            if (cc_pp_is(raw[i][j],"X")) { expanded[i][j].text=(const unsigned char *)"7";
                expanded[i][j].size=1; expanded[i][j].kind=CC_PP_NUMBER; } }
        arguments[i].spelling=(cc_pp_reader){text[i+1],strlen((char *)text[i+1]),0,0};
        arguments[i].raw=raw[i]; arguments[i].expanded=expanded[i];
        arguments[i].raw_count=arguments[i].expanded_count=n;
    }
    unsigned size=tokens(text[0],body),count=0;
    if (size>128 || !cc_pp_substitute(body,size,parameters,arguments,out,argc>1 ? 0 : 256,&count)) return 2;
    for (unsigned i=0;i<count;++i) { fwrite(out[i].text,1,out[i].size,stdout); putchar(' '); }
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
    (b"a+b", b"X", b"3", True), (b"a a b", b"X", b"", True),
    (b"#a", b"X", b"", True), (b"#a #b", b"a/**/b", b'"x\\n"', True),
    (b"a##b", b"fo", b"o", True), (b"a##b", b"1", b"e3", True),
    (b"a##b", b"", b"word", True), (b"a##b", b"word", b"", True),
    (b"a##b", b"", b"", True), (b"a##b", b"left + fo", b"o + right", True),
    (b"a##b##z", b"fo", b"o", True), (b"a##b##z", b"", b"", True),
    (b"a##b", b"+", b"+", True), (b"a##b", b"/", b"*", False),
    (b"##a", b"word", b"", False), (b"a##", b"word", b"", False),
    (b"#word", b"word", b"", False), (b"a####b", b"a", b"b", True),
    (b"a## ## ##b", b"a", b"b", True), (b"a####", b"a", b"b", False),
]
for index, (body, a, b, valid) in enumerate(cases):
    case = folder / str(index)
    case.mkdir(exist_ok=True)
    incoming = body+b"\n"+a+b"\n"+b+b"\n"
    (case / "argument.in").write_bytes(incoming)
    result = subprocess.run([str(folder / "test")], input=incoming, capture_output=True)
    reference_source = b"#define X 7\n#define F(a,b) "+body+b"\nF("+a+b","+b+b")\n"
    (case / "reference.c").write_bytes(reference_source)
    command = ["gcc", "-E", "-P", "-std=gnu11", "-x", "c", "-"]
    (case / "args.json").write_text(json.dumps(command)+"\n")
    reference = subprocess.run(command, input=reference_source, capture_output=True)
    canonical = subprocess.run([str(folder / "test"), "tokens"], input=reference.stdout, capture_output=True)
    (case / "result.out").write_bytes(result.stdout)
    (case / "reference.out").write_bytes(reference.stdout)
    (case / "reference.stderr").write_bytes(reference.stderr)
    assert (result.returncode == 0) == valid == (reference.returncode == 0), (index, result, reference)
    if valid:
        assert canonical.returncode == 0 and result.stdout == canonical.stdout, (index, result.stdout, canonical.stdout)
    print(f"OK substitution matches GCC: {index}")
result = subprocess.run([str(folder / "test"), "capacity"], input=b"a\nx\n\n", capture_output=True)
assert result.returncode == 2
print("OK substitution rejects insufficient output capacity")
