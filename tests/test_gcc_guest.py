"""Execute actual cc1 in primitive Space; host GCC is an output oracle only."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts/rv32i"))
from space_segments import execute_segments


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image",type=Path,required=True,help="directory prepared by prepare_image.py")
    parser.add_argument("--artifacts",type=Path,required=True)
    args=parser.parse_args()
    image=args.image.resolve(); manifest=json.loads((image/"image.json").read_text())
    if digest(image/"gcc.stream")!=manifest["stream_sha256"]: raise ValueError("image changed")
    root=args.artifacts.resolve(); root.mkdir(parents=True,exist_ok=False)
    files=[(b"main.c",b'#include "value.h"\n#define BASE 3\nunsigned value(void) { return BASE + VALUE; }\n'),
           (b"include/value.h",b"#define VALUE 4\n")]
    for name,data in files:
        path=root/"native-inputs"/name.decode()
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    native=["gcc","-E","-P","-nostdinc","-Iinclude","main.c"]
    (root/"native-command.json").write_text(json.dumps(native)+"\n")
    expected=subprocess.run(native,cwd=root/"native-inputs",capture_output=True)
    (root/"native.out").write_bytes(expected.stdout); (root/"native.err").write_bytes(expected.stderr)
    if expected.returncode or expected.stdout!=b"unsigned value(void) { return 3 + 4; }\n":
        raise RuntimeError("native oracle differs from independent expected output")
    packet=b"\0CCFILES1"+struct.pack("<III",len(files),0,1)+struct.pack("<I",7)+b"include"
    for name,data in files:
        packet+=struct.pack("<II",len(name),len(data))+name+data
    argv=[b"cc1",b"-E",b"-P",b"-quiet",b"-nostdinc",b"-Iinclude",b"main.c"]
    job=b"GCCJOB1\0"+struct.pack("<II",len(argv),len(packet))
    for arg in argv: job+=struct.pack("<I",len(arg))+arg
    job+=packet
    (root/"job.bin").write_bytes(job)
    (root/"argv.json").write_text(json.dumps([a.decode() for a in argv])+"\n")
    with (root/"in.bin").open("wb") as target, (image/"gcc.stream").open("rb") as source:
        while block:=source.read(1024*1024): target.write(block)
        target.write(job)
    print("Executing actual cc1 through primitive Space; preprocessing supplied C",flush=True)
    execution=execute_segments(ROOT/"build/bin/space",root/"space",root/"in.bin",
        space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
        ticks=100000,timeout=300,compression="zstd")
    output=(root/"space/program.in").read_bytes()
    raw=(root/"space/space.bin").read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    status,code=word(132128),word(132160)
    evidence={"scope":"actual guest cc1 preprocessing only; copy backend still required",
        "image_sha256":manifest["stream_sha256"],"elf_sha256":manifest["elf_sha256"],
        "job_sha256":digest(root/"job.bin"),"in_sha256":digest(root/"in.bin"),
        "guest_status":status,"guest_exit":code,"output_hex":output.hex(),
        "native_output_sha256":digest(root/"native.out"),**execution}
    (root/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
    assert status==10 and code==0,(status,code,output)
    assert raw[:manifest["layer_bits"]//8]==bytes(manifest["layer_bits"]//8)
    assert output==expected.stdout,output
    print("OK actual cc1 in Space: full preprocessed output matches GCC; guest exit 0",flush=True)


if __name__=="__main__": main()
