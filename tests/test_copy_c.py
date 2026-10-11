"""Real Forth C compilation, copy-only target execution and guest raw evidence."""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from space_trace_audit import audit_trace

ROOT = Path("tmp/space-tests/copy-c")
IMAGE = Path("build/copy-c/compiler.stream")
NATIVE = IMAGE.with_name(IMAGE.name+".build") / "compiler32"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--native-only", action="store_true")
parser.add_argument("--guest-case", action="append", choices=["sum", "control", "loop", "syntax-error"])
parser.add_argument("--artifacts", type=Path, default=ROOT)
options = parser.parse_args()
ROOT = options.artifacts
ROOT.mkdir(parents=True, exist_ok=True)


def record(folder, command, data):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "in.bin").write_bytes(data)
    (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")


def compile_native(name, source, error=False):
    folder = ROOT / "native" / name
    command = [str(NATIVE)]
    record(folder, command, b"CC-RUN\n"+source)
    result = subprocess.run(command, input=b"CC-RUN\n"+source, capture_output=True, timeout=10)
    (folder / "program.in").write_bytes(result.stdout)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.stderr == b"", result.stderr
    if error:
        assert result.returncode == 2 and result.stdout.startswith(b"copy-c error at byte "), (name, result)
    else:
        assert result.returncode == 0 and len(result.stdout) > 37, (name, result)
    return result.stdout


def target(name, packet, expected, *, fault=False):
    folder = ROOT / "target" / name
    command = ["build/bin/space", "--ticks", "20000", "--trace", str(folder / "trace.txt"),
               "--dump-space", str(folder / "space.bin")]
    record(folder, command, packet)
    result = subprocess.run(command, input=packet, capture_output=True, timeout=10)
    (folder / "result.out").write_bytes(result.stdout)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0 and result.stderr == b"", (name, result)
    want = b"copy-c: load error\n" if fault else (expected & 0xffffffff).to_bytes(4, "little")
    assert result.stdout == want, (name, result.stdout.hex(), want.hex())
    raw = (folder / "space.bin").read_bytes()
    assert len(raw) == 2097152 and raw[:2272] == bytes(2272)
    # There is no RV32I guest program or pForth in the resulting space.
    assert raw[1048576:] == bytes(1048576)
    trace = (folder / "trace.txt").read_bytes()
    assert trace.splitlines()[-1].endswith(b" idle") and b"copy " in trace
    assert b"channel " in trace
    if name == "carry":
        reads = []
        for line in trace.splitlines():
            fields = line.split()
            if fields[:1] == [b"copy"] and fields[3:5] == [b"2", b"151680"]:
                reads.append(int(fields[5]))
        assert reads == [196614]+[196618]*31, reads
    print(f"OK copy-c target {name}: OUT={result.stdout.hex()}", flush=True)


valid = [
    ("sum", b"int f(int a,int b){return a+b;}int main(){return f(1,2);}", 3),
    ("literal-sum", b"int main(){return 1+2;}", 3),
    ("carry", b"int main(){return 0xffffffff+1;}", 0),
    ("sign-wrap", b"int main(){return 2147483647+1;}", 0x80000000),
    ("subtract", b"int main(){return 1-2;}", -1),
    ("unary", b"int main(){return -(-17)+!0;}", 18),
    ("precedence", b"int main(){return 1+2<4==1;}", 1),
    ("truth-high-bit", b"int main(){if(256)return 7;else return 8;}", 7),
    ("false", b"int main(){if(0)return 7;else return 8;}", 8),
    ("if-no-else", b"int main(){int a=2;if(0)a=9;return a;}", 2),
    ("dangling-else", b"int main(){if(1)if(0)return 1;else return 2;return 3;}", 2),
    ("locals", b"int main(){int a=7;int b;b=a+3;return b;}", 10),
    ("nested-call", b"int f(int a,int b){return a-b;}int main(){return f(f(9,2),f(5,1));}", 3),
    ("call-chain", b"int f(int a){return a+1;}int g(int a){return f(a)+f(a+1);}int main(){return g(10);}", 23),
    ("zero-args", b"int f(void){return 13;}int main(void){return f();}", 13),
    ("fallthrough", b"int main(){}", 0),
    ("loop", Path("examples/copy_c/loop.c").read_bytes(), 15),
    ("nested-loop", b"int main(){int i=0;int s=0;while(i<3){int j=0;while(j<2){s=s+1;j=j+1;}i=i+1;}return s;}", 6),
    ("comments", b"/* head */ int main() { // line\nreturn 0XFF + /* inner */ 1; } // tail", 256),
    ("case-sensitive", b"int main(){int A=7;int a=2;return A-a;}", 5),
    ("block-names", b"int main(){int s=0;{int a=1;s=s+a;}{int a=2;s=s+a;}return s;}", 3),
    ("control", b"int f(int a){return a+1;}int main(){int i=0;while(i<2){if(i==0)i=f(i);else i=i+1;}return i;}", 2),
]
for name, expression, expected in [
    ("signed-lt", "0x80000000<0", 1), ("signed-gt", "0xffffffff>0", 0),
    ("signed-ge", "0x80000000>=0x80000000", 1), ("signed-le", "7<=6", 0),
    ("equal", "0xffffffff==(-1)", 1), ("not-equal", "0xffffffff!=0", 1),
    ("false-neq", "7!=7", 0), ("signed-min", "0x80000000<0xffffffff", 1),
]:
    valid.append((name, ("int main(){return "+expression+";}").encode(), expected))

packets = {}
for name, source, expected in valid:
    packet = compile_native(name, source)
    packets[name] = packet
    target(name, packet, expected)

invalid = [
    ("missing-main", b"int f(){return 1;}"),
    ("unfinished", b"int main(){return 1;"),
    ("unknown-name", b"int main(){return missing;}"),
    ("duplicate", b"int main(){int a;int a;return 0;}"),
    ("recursive", b"int f(){return f();}int main(){return f();}"),
    ("forward-call", b"int main(){return f();}int f(){return 1;}"),
    ("arity", b"int f(int a){return a;}int main(){return f(1,2);}"),
    ("prototype", b"int f();int main(){return 0;}"),
    ("multiply", b"int main(){return 2*3;}"),
    ("integer-overflow", b"int main(){return 4294967296;}"),
    ("hex-overflow", b"int main(){return 0x100000000;}"),
    ("bad-hex", b"int main(){return 0x;}"),
    ("comment-eof", b"int main(){/* unfinished"),
    ("main-args", b"int main(int a){return a;}"),
    ("reserved-name", b"int main(){int return;return 0;}"),
    ("main-call", b"int main(){return 0;}int f(){return main();}"),
    ("nul-source", b"int main(){return 0;}\0"),
    ("block-scope", b"int main(){{int a=1;}return a;}"),
    ("shadowing", b"int main(){int a=1;{int a=2;}return a;}"),
    ("source-capacity", b" "*8193),
    ("nesting-capacity", b"int main(){return "+b"("*40+b"1"+b")"*40+b";}"),
    ("name-capacity", b"int main(){int "+b"x"*32+b";return 0;}"),
    ("code-capacity", b"int main(){int a=0;"+b"a=a+1;"*100+b"return a;}"),
]
for name, source in invalid:
    compile_native(name, source, True)
    print(f"OK copy-c rejects {name}", flush=True)
def payload_start(packet):
    for start in range(0, len(packet), 37):
        # First installation records carry zero IN length. The last one
        # orders the payload read; decode independently of compiler helpers.
        at = start*8+71
        bits = sum(((packet[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(23))
        if bits:
            assert bits == (len(packet)-start-37)*8
            return start+37
    raise AssertionError("payload bootstrap missing")


for cut in (0, 1, 2271):
    target(f"truncated-{cut}", packets["sum"][:payload_start(packets["sum"])+cut], 0, fault=True)
print(f"OK copy-c native: {len(valid)} valid, {len(invalid)} rejected, 3 truncated packets", flush=True)

if options.native_only:
    raise SystemExit(0)


def guest(name, source, expected=None):
    folder = ROOT / "guest" / name
    image = IMAGE.read_bytes()
    data = image+b"CC-RUN\n"+source
    # The user program is supplied only after the compiler image was built.
    assert source not in (IMAGE.with_name(IMAGE.name+".build") / "program.bin").read_bytes()
    command = ["build/bin/space", "--trace", str(folder / "trace.fifo"),
               "--dump-space", str(folder / "space.bin")]
    record(folder, command, data)
    compiler_source = Path("runtime/copy_c/compiler.fth").read_bytes()
    (folder / "source.c").write_bytes(source)
    (folder / "compiler.fth").write_bytes(compiler_source)
    (folder / "compiler.json").write_bytes(IMAGE.with_name(IMAGE.name+".json").read_bytes())
    fifo = folder / "trace.fifo"
    fifo.unlink(missing_ok=True)
    os.mkfifo(fifo)
    keepalive = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    errors = []

    def compress():
        try:
            with fifo.open("rb", buffering=0) as incoming, gzip.open(folder / "trace.txt.gz", "wb", compresslevel=1) as out:
                shutil.copyfileobj(incoming, out, 1024*1024)
        except Exception as error:
            errors.append(error)

    compressor = threading.Thread(target=compress, daemon=True)
    compressor.start()
    started = time.monotonic()
    try:
        with (folder / "in.bin").open("rb") as incoming, (folder / "program.in").open("wb") as output, (folder / "stderr.txt").open("wb") as error_output:
            result = subprocess.run(command, stdin=incoming, stdout=output, stderr=error_output, timeout=1800)
    finally:
        os.close(keepalive)
        compressor.join(timeout=30)
        fifo.unlink()
    assert not compressor.is_alive() and not errors, errors
    assert result.returncode == 0 and (folder / "stderr.txt").read_bytes() == b""
    output = (folder / "program.in").read_bytes()
    raw = (folder / "space.bin").read_bytes()

    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))

    assert raw[:2272] == bytes(2272) and word(132128) == 10
    if expected is None:
        assert word(132160) == 2 and output.startswith(b"copy-c error at byte ")
    else:
        assert word(132160) == 0 and output == packets[name]
        target("guest-"+name, output, expected)
    copies, channels, last = audit_trace(folder / "trace.txt.gz")
    assert copies > 0 and channels > 0 and last.endswith(b" idle\n")
    (folder / "evidence.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source).hexdigest(), "output_sha256": hashlib.sha256(output).hexdigest(),
        "copy_events": copies, "channel_events": channels, "seconds": time.monotonic()-started,
        "guest_exit": word(132160),
        "compiler_forth_sha256": hashlib.sha256(compiler_source).hexdigest(),
        "compiler_image_sha256": hashlib.sha256(image).hexdigest(),
    }, indent=2)+"\n")
    print(f"OK copy-c guest {name}: {time.monotonic()-started:.1f}s, {copies} copies", flush=True)


for name in options.guest_case or ("sum", "control", "syntax-error"):
    if name == "syntax-error":
        guest(name, b"int main(){return 1+;}\n")
    else:
        _, source, expected = next(case for case in valid if case[0] == name)
        guest(name, source, expected)
print("OK copy-c guest: selected executions passed; full raw evidence in "+str(ROOT), flush=True)
