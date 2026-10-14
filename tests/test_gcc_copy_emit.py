"""Execute a guest C emitter, then run its output directly without RV32I."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts/rv32i"))
from build import build
from space_segments import execute_segments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts",type=Path,required=True)
    parser.add_argument("--compiler",required=True)
    parser.add_argument("--newlib",type=Path,required=True)
    parser.add_argument("--fixture",choices=["single","chain"],default="single")
    parser.add_argument("--operation",choices=["add","sub","and","or","xor"],default="add")
    parser.add_argument("--result-space-bytes",type=lambda s:int(s,0),default=2*1024*1024)
    args=parser.parse_args()
    if args.fixture=="single" and args.operation!="add":
        parser.error("other operations require --fixture chain")
    profiles={2*1024*1024:"space",64*1024*1024:"space-64m",256*1024*1024:"space-256m"}
    if args.result_space_bytes not in profiles or (args.fixture=="single" and args.result_space_bytes!=2*1024*1024):
        parser.error("unsupported result space profile")
    result_emulator=ROOT/"build/bin"/profiles[args.result_space_bytes]
    address_bits=(args.result_space_bytes*8-1).bit_length()
    root=args.artifacts.resolve(); root.mkdir(parents=True,exist_ok=False)
    fixture="copy_chain.c" if args.fixture=="chain" else "copy_emit.c"
    sources=[ROOT/"tests/fixtures/gcc"/fixture,ROOT/"runtime/gcc/copy_emit.c"]
    hashes={}
    for source in sources+[ROOT/"runtime/gcc/copy_emit.h"]:
        target=root/"sources"/source.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(source.read_bytes())
        hashes[str(source.relative_to(ROOT))]=hashlib.sha256(target.read_bytes()).hexdigest()
    sources=[root/"sources"/source.relative_to(ROOT) for source in sources]
    include="-I"+str(root/"sources/runtime/gcc")
    native=root/"native"
    command=["gcc","-O2","-Wall","-Wextra","-Werror",include]+[str(s) for s in sources]+["-o",str(native)]
    flags=["-DCS_COPY_CHAIN_OPERATION="+str(["add","sub","and","or","xor"].index(args.operation)),
           "-DCS_COPY_ADDRESS_BITS="+str(address_bits)]
    command[1:1]=flags
    (root/"native-command.json").write_text(json.dumps(command)+"\n")
    subprocess.run(command,check=True,capture_output=True)
    pairs=[(3,4),(0,0),(0xffffffff,1),(0x7fffffff,1),(0xaaaaaaaa,0x55555555),(0xffffffff,0xffffffff)]
    if args.fixture=="chain":
        pairs=[(3,4,5),(0,0,0),(0xffffffff,1,0),(0xffffffff,1,1),(0xffffffff,0xffffffff,2),(0x7fffffff,1,0)]
        pairs.append((0xaaaaaaaa,0x55555555,0xdeadbeef))

    def expected_value(values):
        result=values[0]
        for value in values[1:]:
            if args.operation=="add": result+=value
            elif args.operation=="sub": result-=value
            elif args.operation=="and": result&=value
            elif args.operation=="or": result|=value
            else: result^=value
        return result&0xffffffff

    def direct(image,folder,*values):
        folder.mkdir()
        core=folder/"image.bin"; core.write_bytes(image)
        command=[str(result_emulator),"--core",str(core),"--trace",str(folder/"trace.txt")]
        if args.result_space_bytes==2*1024*1024:
            command.extend(["--dump-space",str(folder/"space.bin")])
        (folder/"command.json").write_text(json.dumps(command)+"\n")
        result=subprocess.run(command,capture_output=True,timeout=10)
        (folder/"out.bin").write_bytes(result.stdout)
        (folder/"stderr.txt").write_bytes(result.stderr)
        assert result.returncode==0 and not result.stderr
        assert result.stdout==struct.pack("<I",expected_value(values)),result.stdout
        return {"image_sha256":hashlib.sha256(image).hexdigest(),"output_hex":result.stdout.hex()}

    results=[]
    for index,values in enumerate(pairs):
        result=subprocess.run([str(native)],input=struct.pack("<"+"I"*len(values),*values),capture_output=True,check=True)
        assert len(result.stdout)==(32768 if args.fixture=="chain" else 16384)
        results.append(direct(result.stdout,root/f"native-{index}",*values))
        if index==0: expected=result.stdout
    alternates=[] if args.fixture=="chain" else [("loaded-layer",["-DCS_COPY_LAYER=65536"]),
                       ("alias-left",["-DCS_COPY_RESULT=49152"]),
                       ("alias-right",["-DCS_COPY_RESULT=49184"])]
    for name,alternate_flags in alternates:
        alternate=root/name
        subprocess.run(command[:-2]+alternate_flags+["-o",str(alternate)],check=True,capture_output=True)
        result=subprocess.run([str(alternate)],input=struct.pack("<II",0xffffffff,1),capture_output=True,check=True)
        results.append(direct(result.stdout,root/(name+"-execution"),0xffffffff,1))
    headers=args.newlib.resolve()/"riscv64-unknown-elf/include"
    manifest=build(sources,root/"generator.stream",compiler=args.compiler,stream=True,optimization="-O2",
        extra_cflags=flags+[include,"-isystem",str(headers)])
    values=pairs[0]
    (root/"in.bin").write_bytes((root/"generator.stream").read_bytes()+struct.pack("<"+"I"*len(values),*values))
    execution=execute_segments(ROOT/"build/bin/space",root/"generator",root/"in.bin",
        space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
        ticks=100000,timeout=300,compression="zstd")
    generated=(root/"generator/program.in").read_bytes()
    assert generated==expected,"guest generator differs from native generator"
    raw=(root/"generator/space.bin").read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    assert word(132128)==10 and word(132160)==0
    guest=direct(generated,root/"guest-result",*values)
    (root/"evidence.json").write_text(json.dumps({"scope":"guest C emitter and direct copies; not GCC integration",
        "fixture":args.fixture,"operation":args.operation,"result_space_bytes":args.result_space_bytes,
        "sources_sha256":hashes,"native_direct_cases":results,"guest_generator_execution":execution,
        "guest_result_direct_execution":guest,"guest_exit":word(132160)},indent=2)+"\n")
    print("OK guest C emitter produced direct copy image;",args.operation,"result",expected_value(values),"no RV32I in result")


if __name__=="__main__": main()
