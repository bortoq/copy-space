"""Verify immutable token expansion restrictions and explicit capacity errors."""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "tmp/space-tests/copy-c-macro-hidesets"
folder.mkdir(parents=True, exist_ok=True)
source = r'''
#include <stdio.h>
#include "runtime/copy_c/preprocess_macros.h"
int main(void) {
    if (sizeof(unsigned) != 4) return 1;
    cc_pp_hide_reset();
    unsigned all=0, even=0, odd=0;
    for (unsigned i=0; i<CC_PP_MACROS; ++i) {
        int next=cc_pp_hide_add(all,i); if (next<0) return 2;
        if (cc_pp_hide_contains(all,i)) return 3;
        all=(unsigned)next;
        next=cc_pp_hide_add(i%2 ? odd : even,i); if (next<0) return 4;
        if (i%2) odd=(unsigned)next; else even=(unsigned)next;
        for (unsigned j=0;j<CC_PP_MACROS;++j)
            if (cc_pp_hide_contains(all,j) != (j<=i)) return 5;
    }
    if (cc_pp_hide_merge(even,odd,0) != (int)all) return 6;
    if (cc_pp_hide_merge(even,odd,1) != 0) return 7;
    if (cc_pp_hide_merge(all,even,1) != (int)even) return 8;
    if (cc_pp_hide_merge(all,0,0) != (int)all) return 9;
    unsigned saved=cc_pp_hide_count;
    for (unsigned i=0;i<CC_PP_MACROS;++i)
        if (cc_pp_hide_add(all,i) != (int)all) return 10;
    if (saved != cc_pp_hide_count) return 11;
    unsigned bits[CC_PP_HIDE_WORDS]={0}, counter=1;
    while (cc_pp_hide_count < CC_PP_HIDE_SETS) {
        bits[0]=counter++; bits[1]=0x12345678u;
        if (cc_pp_hide_intern(bits)<0) return 12;
    }
    bits[0]=counter;
    if (cc_pp_hide_intern(bits) != -1 || cc_pp_hide_count != CC_PP_HIDE_SETS) return 13;
    if (cc_pp_hide_merge(all,even,1) != (int)even) return 14;
    if (cc_pp_hide_add(CC_PP_HIDE_SETS,0) != -1 || cc_pp_hide_add(0,CC_PP_MACROS) != -1) return 15;
    cc_pp_hide_reset();
    if (cc_pp_hide_count != 1 || cc_pp_hide_contains(0,0)) return 16;
    unsigned common=(unsigned)cc_pp_hide_add(0,5);
    cc_pp_token left={(const unsigned char *)"fo",2,CC_PP_IDENT,(unsigned)cc_pp_hide_add(common,3),1};
    cc_pp_token right={(const unsigned char *)"o",1,CC_PP_IDENT,(unsigned)cc_pp_hide_add(common,9),0},pasted;
    if (!cc_pp_paste(left,right,&pasted) || !cc_pp_is(pasted,"foo")) return 17;
    if (pasted.hidden != common || pasted.space != 1) return 18;
    cc_pp_reader reader={(const unsigned char *)" /**/word.next",14,0,0};
    cc_pp_token token=cc_pp_next(&reader);
    if (!cc_pp_is(token,"word") || token.space != 1 || token.hidden) return 19;
    token=cc_pp_next(&reader);
    if (token.kind != '.' || token.space || token.hidden) return 20;
    puts("OK immutable sets for 512 macros: membership, union, intersection, reuse, capacity, reset");
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
