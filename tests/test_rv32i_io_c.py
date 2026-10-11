"""Run compiled C with real stdin/stdout, guest exit codes and raw channel logs."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("tmp/space-tests/rv32i-io-c")
ROOT.mkdir(parents=True, exist_ok=True)
fixtures = Path("tests/fixtures/rv32i")
cases = 0


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def compile_image(name, sources, optimization="O2"):
    image = ROOT / (name+".bin")
    args = [sys.executable, "scripts/rv32i/build.py", *[str(path) for path in sources],
            "-o", str(image), "--optimization", optimization]
    (ROOT / (name+"-build.json")).write_text(json.dumps(args, indent=2)+"\n")
    result = subprocess.run(args, capture_output=True)
    (ROOT / (name+"-build.stderr")).write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    manifest = json.loads(image.with_name(image.name+".json").read_text())
    assert manifest["io"] and not manifest["state_output"]
    return image


def run(name, image, data, output, exit_code, read_error=False, write_error=False, ticks=None):
    global cases
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    (folder / "in.bin").write_bytes(data)
    args = [sys.executable, "scripts/rv32i/run.py", str(image),
            "--dump-space", str(folder / "space.bin"), "--trace", str(folder / "trace.txt")]
    if ticks is not None:
        args += ["--ticks", str(ticks)]
    if read_error:
        args += ["--in", str(folder)]
    (folder / "args.json").write_text(json.dumps(args, indent=2)+"\n")
    if read_error:
        result = subprocess.run(args, input=b"", capture_output=True, timeout=20)
    elif write_error:
        with open("/dev/full", "wb", buffering=0) as sink:
            result = subprocess.run(args, input=data, stdout=sink, stderr=subprocess.PIPE, timeout=20)
            result.stdout = b""
    else:
        result = subprocess.run(args, input=data, capture_output=True, timeout=20)
    (folder / "out.bin").write_bytes(result.stdout)
    (folder / "stderr.txt").write_bytes(result.stderr)
    (folder / "exit.json").write_text(json.dumps({"process": result.returncode, "guest": exit_code})+"\n")
    assert result.returncode == (125 if ticks is not None else exit_code & 255), (name, result.stderr)
    assert result.stdout == output, (name, result.stdout, output)
    raw = (folder / "space.bin").read_bytes()
    trace = (folder / "trace.txt").read_text()
    if ticks is None:
        assert result.stderr == b"", (name, result.stderr)
        assert word(raw, 132128) == 10 and word(raw, 132160) == exit_code, name
        assert raw[:2272] == bytes(2272), name
        assert trace.endswith(" idle\n"), name
    else:
        assert trace.endswith(" limit\n") and b"did not complete" in result.stderr
    channels = [line.split() for line in trace.splitlines() if line.startswith("channel ")]
    assert all(p[2] in ("1", "2") for p in channels)
    if read_error:
        assert any(p[2] == "1" and p[5:] == ["0", "1"] for p in channels)
    if write_error:
        assert any(p[2] == "2" and p[5:] == ["0", "1"] for p in channels)
    cases += 1
    print(f"OK C I/O {name}: OUT={output!r}, guest_exit={exit_code}, process={result.returncode}")
    return channels


sum_image = compile_image("sum", [Path("examples/rv32i/sum.c")])
for a, b in [(1, 2), (0, 0), (0xffffffff, 1), (0xffffffff, 0), (0x80000000, 0x80000000)]:
    data = f"{a} {b}\n".encode()
    run(f"sum-{a}-{b}", sum_image, data, f"{(a+b)&0xffffffff}\n".encode(), 0)
run("sum-whitespace", sum_image, b"\t 15\r\n17", b"32\n", 0)
run("sum-eof", sum_image, b"", b"", 2)
run("sum-incomplete", sum_image, b"7 ", b"", 2)
run("sum-invalid", sum_image, b"1 a\n", b"", 2)
run("sum-input-overflow", sum_image, b"4294967296 1\n", b"", 2)
run("sum-read-error", sum_image, b"", b"", 1, read_error=True)
run("sum-write-error", sum_image, b"1 2\n", b"", 3, write_error=True)
run("sum-limit", sum_image, b"1 2\n", b"", 0, ticks=0)

bulk_image = compile_image("read-once", [fixtures / "io_read_once.c"])
run("bulk-full", bulk_image, b"abcdefgh", b"abcdefgh", 0)
channels = run("bulk-short", bulk_image, b"abc", b"abc", 4)
assert [(p[2], p[3], p[5], p[6]) for p in channels] == [("1", "64", "24", "0"), ("2", "24", "24", "0")]
channels = run("bulk-eof", bulk_image, b"", b"", 2)
assert [(p[2], p[3], p[5], p[6]) for p in channels] == [("1", "64", "0", "0")]

for optimization in ["O0", "O2"]:
    binary_image = compile_image("binary-sum-"+optimization,
                                 [fixtures / "io_binary_sum.c", fixtures / "io_add.c"], optimization)
    run("binary-sum-"+optimization, binary_image,
        (0xffffffff).to_bytes(4, "little")+(1).to_bytes(4, "little"), bytes(4), 0)

source = ROOT / "exit.c"
source.write_text("int main(void) { return 300; }\n")
exit_image = compile_image("exit", [source])
run("exit-300", exit_image, b"", b"", 300)
memory_image = compile_image("memory", [fixtures / "io_memory.c"])
run("memory", memory_image, b"", b"ABCDEFGG", 0)

# Generic command failures: compiler/linker diagnostics and invalid image/profile.
result = subprocess.run([sys.executable, "scripts/rv32i/build.py", str(fixtures / "io_add.c"),
                         "-o", str(ROOT / "missing-main.bin")], capture_output=True)
assert result.returncode != 0 and b"main" in result.stderr
(ROOT / "missing-main.stderr").write_bytes(result.stderr)
result = subprocess.run([sys.executable, "scripts/rv32i/run.py", str(ROOT / "missing.bin")],
                        input=b"", capture_output=True)
assert result.returncode == 125 and b"cannot load core" in result.stderr
assert len((ROOT / "sum.bin.build/program.bin").read_bytes()) > 0
print(f"OK C I/O: {cases} end-to-end cases via ordinary space")
