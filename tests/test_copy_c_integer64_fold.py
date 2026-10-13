"""Check the compiler guest's cell helper against independent arithmetic vectors."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from test_copy_c_integer64 import OPS, cases

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    folder=parser.parse_args().artifacts.resolve()
    folder.mkdir(parents=True,exist_ok=False)
    for name,path in (("integer64_fold.h", ROOT/"runtime/copy_c/integer64_fold.h"),
                      ("reference.c", ROOT/"tests/fixtures/copy_c/integer64_fold_reference.c")):
        (folder/name).write_bytes(path.read_bytes())
    command=["gcc","-std=gnu11","-O2","-Wall","-Wextra","-Werror",str(folder/"reference.c"),"-o",str(folder/"reference")]
    (folder/"args.json").write_text(json.dumps(command,indent=2)+"\n")
    build=subprocess.run(command,capture_output=True,timeout=30)
    (folder/"build.stderr").write_bytes(build.stderr)
    assert build.returncode==0,build.stderr
    good,bad=cases()
    good=[c for c in good if c[1]!="chain"]
    bad += [("signed-overflow",op,1<<63,(1<<64)-1,b"") for op in ("div","mod")]
    rows=good+bad
    incoming="".join(f"{OPS.index(op)} {a:x} {b:x}\n" for _,op,a,b,_ in rows).encode()
    (folder/"in.txt").write_bytes(incoming)
    result=subprocess.run([str(folder/"reference")],input=incoming,capture_output=True,timeout=30)
    (folder/"out.txt").write_bytes(result.stdout)
    (folder/"stderr.txt").write_bytes(result.stderr)
    assert result.returncode==0 and result.stderr==b""
    actual=[tuple(int(v,16) for v in row.split()) for row in result.stdout.splitlines()]
    assert len(actual)==len(rows)
    for vector,want in zip(rows,actual):
        expected=vector[4]
        assert want==(0,0) if isinstance(expected,bytes) else want==(1,expected), (vector[0],want,expected)
    proof={"scope":"native cell helper; space compilation is checked separately",
           "valid":len(good),"invalid":len(bad),"header_sha256":hashlib.sha256((folder/"integer64_fold.h").read_bytes()).hexdigest()}
    (folder/"summary.json").write_text(json.dumps(proof,indent=2)+"\n")
    print(f"OK integer64 cell helper: {len(good)} results, {len(bad)} invalid operations",flush=True)


if __name__=="__main__":
    main()
