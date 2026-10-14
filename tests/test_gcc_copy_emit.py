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
    args=parser.parse_args()
    root=args.artifacts.resolve(); root.mkdir(parents=True,exist_ok=False)
    sources=[ROOT/"tests/fixtures/gcc/copy_emit.c",ROOT/"runtime/gcc/copy_emit.c"]
    hashes={}
    for source in sources+[ROOT/"runtime/gcc/copy_emit.h"]:
        target=root/"sources"/source.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(source.read_bytes())
        hashes[str(source.relative_to(ROOT))]=hashlib.sha256(target.read_bytes()).hexdigest()
    sources=[root/"sources"/source.relative_to(ROOT) for source in sources]
    include="-I"+str(root/"sources/runtime/gcc")
    native=root/"native"
    command=["gcc","-O2","-Wall","-Wextra","-Werror",include]+[str(s) for s in sources]+["-o",str(native)]
    (root/"native-command.json").write_text(json.dumps(command)+"\n")
    subprocess.run(command,check=True,capture_output=True)
    pairs=[(3,4),(0,0),(0xffffffff,1),(0x7fffffff,1),(0xaaaaaaaa,0x55555555),(0xffffffff,0xffffffff)]

    def direct(image,folder,a,b):
        folder.mkdir()
        core=folder/"image.bin"; core.write_bytes(image)
        command=[str(ROOT/"build/bin/space"),"--core",str(core),"--trace",str(folder/"trace.txt"),
                 "--dump-space",str(folder/"space.bin")]
        (folder/"command.json").write_text(json.dumps(command)+"\n")
        result=subprocess.run(command,capture_output=True,timeout=10)
        (folder/"out.bin").write_bytes(result.stdout)
        (folder/"stderr.txt").write_bytes(result.stderr)
        assert result.returncode==0 and not result.stderr
        assert result.stdout==struct.pack("<I",(a+b)&0xffffffff),result.stdout
        return {"image_sha256":hashlib.sha256(image).hexdigest(),"output_hex":result.stdout.hex()}

    results=[]
    for index,(a,b) in enumerate(pairs):
        result=subprocess.run([str(native)],input=struct.pack("<II",a,b),capture_output=True,check=True)
        assert len(result.stdout)==16384
        results.append(direct(result.stdout,root/f"native-{index}",a,b))
        if index==0: expected=result.stdout
    for name,flags in [("loaded-layer",["-DCS_COPY_LAYER=65536"]),
                       ("alias-left",["-DCS_COPY_RESULT=49152"]),
                       ("alias-right",["-DCS_COPY_RESULT=49184"])]:
        alternate=root/name
        subprocess.run(command[:-2]+flags+["-o",str(alternate)],check=True,capture_output=True)
        result=subprocess.run([str(alternate)],input=struct.pack("<II",0xffffffff,1),capture_output=True,check=True)
        results.append(direct(result.stdout,root/(name+"-execution"),0xffffffff,1))
    headers=args.newlib.resolve()/"riscv64-unknown-elf/include"
    manifest=build(sources,root/"generator.stream",compiler=args.compiler,stream=True,optimization="-O2",
        extra_cflags=[include,"-isystem",str(headers)])
    (root/"in.bin").write_bytes((root/"generator.stream").read_bytes()+struct.pack("<II",3,4))
    execution=execute_segments(ROOT/"build/bin/space",root/"generator",root/"in.bin",
        space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
        ticks=100000,timeout=300,compression="zstd")
    generated=(root/"generator/program.in").read_bytes()
    assert generated==expected,"guest generator differs from native generator"
    raw=(root/"generator/space.bin").read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    assert word(132128)==10 and word(132160)==0
    guest=direct(generated,root/"guest-result",3,4)
    (root/"evidence.json").write_text(json.dumps({"scope":"guest C emitter and direct copies; not GCC integration",
        "sources_sha256":hashes,"native_direct_cases":results,"guest_generator_execution":execution,
        "guest_result_direct_execution":guest,"guest_exit":word(132160)},indent=2)+"\n")
    print("OK guest C emitter produced direct copy image; result 7, no RV32I in result")


if __name__=="__main__": main()
