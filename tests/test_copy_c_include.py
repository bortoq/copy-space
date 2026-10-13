"""Check guest header resolution against GCC and reject corrupt IN framing."""
import hashlib
import importlib.util
import json
import struct
import subprocess
from pathlib import Path
from copy_c_include_cases import valid, invalid

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("copy_c_job",root/"scripts/copy_c/job.py")
job=importlib.util.module_from_spec(spec); spec.loader.exec_module(job)
folder=root/"tmp/space-tests/copy-c-include"
folder.mkdir(parents=True,exist_ok=True)
source=r'''
#include <stdio.h>
#include "runtime/copy_c/preprocess_macros.h"
static unsigned char input[CC_PP_OUTPUT];
int main(int argc,char **argv) {
    (void)argv;
    unsigned size=fread(input,1,sizeof(input),stdin);
    if (argc==1) {
        int result=cc_preprocess_macros(input,cc_preprocess_phase2(input,size));
        if (result<0) return 2;
        size=(unsigned)result;
    }
    cc_pp_reader reader={input,size,0,0};
    for (;;) {
        cc_pp_token token=cc_pp_next(&reader);
        if (reader.failed) return 3;
        if (!token.kind) break;
        if (token.kind=='\n') continue;
        fwrite(token.text,1,token.size,stdout); putchar(' ');
    }
    return 0;
}
'''
(folder/"test.c").write_text(source)
command=["cc","-std=c99","-O2","-I",str(root),str(folder/"test.c"),"-o",str(folder/"test")]
(folder/"compile.json").write_text(json.dumps(command)+"\n")
compiled=subprocess.run(command,capture_output=True)
(folder/"compile.stderr").write_bytes(compiled.stderr)
assert compiled.returncode==0,compiled.stderr
for relative in ("input_files.h","preprocess_include.h","preprocess_phase2.h","preprocess_macros.h","preprocess_condition.h","preprocess_queries.h"):
    (folder/relative).write_bytes((root/"runtime/copy_c"/relative).read_bytes())
for reject,cases in ((False,valid),(True,invalid)):
    for name,files,roots,main in cases:
        case=folder/name; case.mkdir(exist_ok=True)
        incoming,_=job.pack_files(files,roots,main)
        (case/"bundle.in").write_bytes(incoming)
        result=subprocess.run([str(folder/"test")],input=incoming,capture_output=True,timeout=30)
        (case/"result.out").write_bytes(result.stdout)
        (case/"result.stderr").write_bytes(result.stderr)
        for file,content in files:
            path=case/"files"/file; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(content)
        command=["gcc","-E","-P","-nostdinc","-std=gnu11","-Werror"]
        if name in ("has-include-undef","has-include-override"):
            command.append("-Wno-error")
        for directory in roots: command.extend(("-I",str(case/"files"/directory)))
        for directory in roots: (case/"files"/directory).mkdir(parents=True,exist_ok=True)
        command.append(str(case/"files"/files[main][0]))
        (case/"gcc.json").write_text(json.dumps(command)+"\n")
        reference=subprocess.run(command,capture_output=True,timeout=30)
        (case/"reference.out").write_bytes(reference.stdout)
        (case/"reference.stderr").write_bytes(reference.stderr)
        if reject:
            assert result.returncode==2 and reference.returncode!=0,(name,result,reference)
        else:
            canonical=subprocess.run([str(folder/"test"),"tokens"],input=reference.stdout,capture_output=True)
            assert result.returncode==reference.returncode==canonical.returncode==0,(name,result,reference)
            assert result.stdout==canonical.stdout,(name,result.stdout,canonical.stdout)
        print("OK include:",name)
good,_=job.pack_files([("main.c",b"int main(){return 7;}")],[""])
bad={"trailing":good+b"x"}
for i in range(9,len(good)): bad["truncated-"+str(i)]=good[:i]
for name,offset,value in (("files-zero",9,0),("files-max",9,1025),("main-index",13,1),("roots-max",17,33),("root-overflow",21,0xffffffff),("name-overflow",25,0xffffffff),("data-overflow",29,0xffffffff)):
    incoming=bytearray(good); incoming[offset:offset+4]=struct.pack("<I",value); bad[name]=bytes(incoming)
def raw(names):
    return job.MAGIC+struct.pack("<III",len(names),0,0)+b"".join(struct.pack("<II",len(n),0)+n for n in names)
bad["duplicate"]=raw([b"main.c",b"main.c"])
for i,name in enumerate((b"",b"/x",b"x/",b"x//y",b"./x",b"x/../y",b"x\0y")):
    bad["bad-name-"+str(i)]=raw([name])
corrupt=folder/"corrupt"; corrupt.mkdir(exist_ok=True)
for name,incoming in bad.items():
    (corrupt/(name+".in")).write_bytes(incoming)
    result=subprocess.run([str(folder/"test")],input=incoming,capture_output=True,timeout=30)
    assert result.returncode==2,(name,result)
    (corrupt/(name+".result.json")).write_text(json.dumps({"returncode":result.returncode})+"\n")
limits=[
    ("max-files",[("f"+str(i),b"") for i in range(1023)]+[("main.c",b"int main(){return 7;}")],[],1023),
    ("max-roots",[("main.c",b"int main(){return 7;}")],["dir"+str(i) for i in range(32)],0),
    ("max-name",[("main.c",b"int main(){return 7;}"),("x"*4096,b"")],[],0),
]
for name,files,roots,main in limits:
    incoming,_=job.pack_files(files,roots,main)
    (folder/(name+".in")).write_bytes(incoming)
    result=subprocess.run([str(folder/"test")],input=incoming,capture_output=True,timeout=30)
    assert result.returncode==0 and result.stdout==b"int main ( ) { return 7 ; } ", (name,result)
    (folder/(name+".out")).write_bytes(result.stdout)
# The CLI must preserve bytes and report real payload offsets.
cli=folder/"cli"; cli.mkdir(exist_ok=True)
(cli/"image.stream").write_bytes(b"image bytes")
(cli/"main.c").write_bytes(b'#include "value.h"\r\nint main(){return V;}\r\n')
(cli/"value.h").write_bytes(b"#define V 7\r\n")
command=["python3",str(root/"scripts/copy_c/job.py"),str(cli/"main.c"),"--image",str(cli/"image.stream"),"--file","value.h="+str(cli/"value.h"),"-o",str(cli/"job.in")]
result=subprocess.run(command,capture_output=True); assert result.returncode==0,result.stderr
metadata=json.loads((cli/"job.in.json").read_text()); incoming=(cli/"job.in").read_bytes()
for record in metadata["files"]:
    content=Path(record["path"]).read_bytes()
    assert content==incoming[record["offset"]:record["offset"]+record["bytes"]]
    assert hashlib.sha256(content).hexdigest()==record["sha256"]
assert metadata["source_offset"]==metadata["files"][0]["offset"]
for protected in ("main.c","value.h","image.stream"):
    before=(cli/protected).read_bytes()
    result=subprocess.run(command[:-1]+[str(cli/protected)],capture_output=True)
    assert result.returncode!=0 and (cli/protected).read_bytes()==before
result=subprocess.run(command+["--main-name",""],capture_output=True)
assert result.returncode!=0
(folder/"summary.json").write_text(json.dumps({"gcc_valid":len(valid),"gcc_rejected":len(invalid),"corrupt_rejected":len(bad),"valid_capacity_boundaries":len(limits),"cli_preserves_original_bytes":True},indent=2)+"\n")
