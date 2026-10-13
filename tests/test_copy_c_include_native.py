"""Control compilation plus direct-copy execution and GCC i386 reference.

This is not evidence that the compiler itself ran inside Space. The resulting
baseline can be passed to test_copy_c_guest.py for that separate check.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from copy_c_include_cases import valid, invalid

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--artifacts",type=Path,required=True)
parser.add_argument("--baseline",type=Path,help="compare whole packets for shared earlier cases")
args=parser.parse_args()
folder=args.artifacts.resolve(); folder.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location("copy_c_job",root/"scripts/copy_c/job.py")
job=importlib.util.module_from_spec(spec); spec.loader.exec_module(job)
compiler=folder/"compiler32"
compiler.write_bytes((root/"build/copy-c/compiler.stream.build/compiler32").read_bytes()); compiler.chmod(0o755)
manifest=json.loads((root/"build/copy-c/compiler.stream.json").read_text())
(folder/"compiler.json").write_text(json.dumps(manifest,indent=2)+"\n")
runtime={}
for name in ("compiler.fth","integer64_fold.h","preprocess_phase2.h","preprocess_macros.h","preprocess_condition.h","input_files.h","preprocess_include.h","preprocess_queries.h"):
    content=(root/"runtime/copy_c"/name).read_bytes()
    key="compiler_"+("forth" if name=="compiler.fth" else Path(name).stem)+"_sha256"
    assert hashlib.sha256(content).hexdigest()==manifest["compiler_dictionary"][key],name
    (folder/name).write_bytes(content); runtime[name]=hashlib.sha256(content).hexdigest()
for name in ("custom.c","clib.c"):
    content=(root/"runtime/pforth"/name).read_bytes()
    (folder/name).write_bytes(content); runtime[name]=hashlib.sha256(content).hexdigest()
wrapper=b'\n#undef main\nvoid _start(void){unsigned value=copy_c_test_main();int result;__asm__ volatile("int $0x80":"=a"(result):"0"(4),"b"(1),"c"(&value),"d"(4):"memory");__asm__ volatile("int $0x80"::"a"(1),"b"(result!=4):"memory");for(;;){}}\n'
equal_packets=0
if args.baseline:
    assert (args.baseline/"compiler.fth").read_bytes()==(folder/"compiler.fth").read_bytes()
for reject,cases in ((False,valid),(True,invalid)):
    for name,files,roots,main in cases:
        native=folder/"native"/name; native.mkdir(parents=True)
        payload,_=job.pack_files(files,roots,main)
        incoming=b"CC-RUN\n"+payload; (native/"in.bin").write_bytes(incoming)
        result=subprocess.run([str(compiler)],input=incoming,capture_output=True,timeout=30)
        (native/"args.json").write_text(json.dumps([str(compiler)])+"\n")
        (native/"program.in").write_bytes(result.stdout); (native/"stderr.txt").write_bytes(result.stderr)
        if reject:
            assert result.returncode==2 and result.stdout.startswith(b"copy-c error at byte ") and not result.stderr,(name,result)
            print("OK rejects:",name,flush=True); continue
        assert result.returncode==0 and not result.stderr,(name,result)
        previous=args.baseline/"native"/name/"program.in" if args.baseline else None
        if previous is not None and previous.is_file():
            assert previous.read_bytes()==result.stdout,name
            equal_packets+=1
        target=folder/"target"/name; target.mkdir(parents=True)
        (target/"in.bin").write_bytes(result.stdout)
        command=[str(root/"build/bin/space"),"--ticks","20000","--trace",str(target/"trace.txt"),"--dump-space",str(target/"space.bin")]
        (target/"args.json").write_text(json.dumps(command)+"\n")
        execution=subprocess.run(command,input=result.stdout,capture_output=True,timeout=60)
        (target/"result.out").write_bytes(execution.stdout); (target/"stderr.txt").write_bytes(execution.stderr)
        assert execution.returncode==0 and execution.stdout==b"\x07\0\0\0" and not execution.stderr,(name,execution)
        raw=(target/"space.bin").read_bytes()
        assert len(raw)==2097152 and raw[:2272]==bytes(2272)
        assert raw[245760//8:262144//8]==bytes(2048)
        assert (target/"trace.txt").read_bytes().splitlines()[-1].endswith(b" idle")
        gcc=folder/"gcc"/name
        for file,content in files:
            path=gcc/"files"/file; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(content)
        path=gcc/"files"/files[main][0]
        path.write_bytes(b"#define main copy_c_test_main\n"+files[main][1]+wrapper)
        command=["gcc","-m32","-std=gnu11","-Werror","-fwrapv","-O0","-ffreestanding","-nostdlib","-nostdinc","-fno-pie","-no-pie","-fno-stack-protector","-Wl,-e,_start"]
        if name in ("has-include-undef","has-include-override"):
            command.append("-Wno-error")
        for directory in roots: command.extend(("-I",str(gcc/"files"/directory)))
        for directory in roots: (gcc/"files"/directory).mkdir(parents=True,exist_ok=True)
        command.extend((str(path),"-o",str(gcc/"reference")))
        (gcc/"args.json").write_text(json.dumps(command)+"\n")
        reference=subprocess.run(command,capture_output=True,timeout=30)
        (gcc/"compile.stderr").write_bytes(reference.stderr)
        assert reference.returncode==0,(name,reference.stderr)
        reference=subprocess.run([str(gcc/"reference")],capture_output=True,timeout=30)
        (gcc/"result.out").write_bytes(reference.stdout)
        assert reference.returncode==0 and reference.stdout==execution.stdout,(name,reference)
        print("OK direct copies and GCC:",name,execution.stdout.hex(),flush=True)
(folder/"evidence.json").write_text(json.dumps({"scope":"native control compilation, direct-copy execution, GCC i386 reference","valid":len(valid),"rejected":len(invalid),"full_previous_packets_equal":equal_packets,"runtime_sources":runtime,"compiler_sha256":hashlib.sha256(compiler.read_bytes()).hexdigest()},indent=2)+"\n")
