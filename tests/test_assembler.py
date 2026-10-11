"""Check assembler capacity, encoded last slot and shared include instruction count."""
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--assembler", type=Path, default=Path("build/bin/assembler"))
parser.add_argument("--slots", type=int, default=256)
parser.add_argument("--artifacts", type=Path)
args = parser.parse_args()
binary = args.assembler.resolve()
root = args.artifacts or Path("tmp/space-tests/assembler") / binary.name
root.mkdir(parents=True, exist_ok=True)


def run(name, source, expected_code=0, expected_error=b""):
    folder = root / name
    folder.mkdir(exist_ok=True)
    (folder / "input.copy").write_bytes(source)
    (folder / "args.json").write_text(json.dumps([str(binary)])+"\n")
    result = subprocess.run([str(binary)], input=source, capture_output=True, timeout=10)
    (folder / "output.bin").write_bytes(result.stdout)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == expected_code, (name, result.returncode, result.stderr)
    assert b"Sanitizer" not in result.stderr and b"runtime error:" not in result.stderr, result.stderr
    if expected_error:
        assert expected_error in result.stderr and result.stdout == b"", (name, result)
    else:
        assert result.stderr == b"", (name, result.stderr)
    print(f"OK assembler {name}: code={result.returncode}", flush=True)
    return result.stdout


assert run("empty", b"") == b""
for name, row in [("copy", b"copy 0 0 0\n"), ("short", b"0 0 0\n")]:
    last = b"copy 1 7 9\n" if name == "copy" else b"1 7 9\n"
    output = run(name+"-full", row*(args.slots-1)+last)
    assert len(output) == (args.slots*71+7)//8
    at = (args.slots-1)*71
    values = []
    for width in (23, 24, 24):
        values.append(sum(((output[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(width)))
        at += width
    assert values == [1, 7, 9], values
    run(name+"-overflow", row*(args.slots+1), 1,
        f"<stdin>:{args.slots+1}: too many instructions".encode())

included = root / "included with spaces.copy"
included.write_bytes(b"copy 0 0 0\n"*(args.slots-1))
include = f'include "{included.resolve()}"\n'.encode()
assert len(run("include-full", include+b"copy 0 0 0\n")) == (args.slots*71+7)//8
run("include-overflow-parent", include+b"copy 0 0 0\n"*2, 1,
    b"<stdin>:3: too many instructions")
overflowing = root / "overflowing with spaces.copy"
overflowing.write_bytes(b"copy 0 0 0\n"*args.slots)
overflow_include = f'include "{overflowing.resolve()}"\n'.encode()
run("include-overflow-child", b"copy 0 0 0\n"+overflow_include, 1,
    f"overflowing with spaces.copy:{args.slots}: too many instructions".encode())
print(f"OK assembler capacity: {args.slots} slots; raw inputs/outputs in {root}", flush=True)
