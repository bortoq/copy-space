"""Direct file IN/OUT execution; verdict comes from OUT, not a runtime wrapper."""
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from space_trace_audit import audit_trace

sys.path.insert(0, "modules")
from rv32i import Image, PC, STATUS, EXIT_CODE, MEMORY
from rv32i_stream import encode_stream

ROOT = Path("tmp/space-tests/file-job")
ROOT.mkdir(parents=True, exist_ok=True)
cases = 0
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--skip-pforth", action="store_true", help="run loading and RV32I checks without the slow Forth executions")
options = parser.parse_args()


def record(stage, status, detail=0):
    return f"\n[space:{stage}:{status:08X}:{detail:08X}]\n".encode()


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def run(name, payload, expected, stage, status, detail=0, *, input_error=False,
        output_error=False, ticks=None):
    global cases
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    (folder / "job.in").write_bytes(payload)
    fifo = folder / "trace.fifo"
    fifo.unlink(missing_ok=True)
    os.mkfifo(fifo)
    keepalive = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    compression_errors = []

    def compress():
        try:
            with fifo.open("rb", buffering=0) as source, gzip.open(folder / "trace.txt.gz", "wb", compresslevel=1) as target:
                shutil.copyfileobj(source, target, 1024*1024)
        except Exception as error:
            compression_errors.append(error)

    compressor = threading.Thread(target=compress, daemon=True)
    compressor.start()
    command = ["build/bin/space", "--trace", str(fifo), "--dump-space", str(folder / "space.bin")]
    if ticks is not None:
        command += ["--ticks", str(ticks)]
    input_path = folder if input_error else folder / "job.in"
    output_path = Path("/dev/full") if output_error else folder / "result.out"
    (folder / "args.json").write_text(json.dumps({"argv": command, "stdin": str(input_path),
                                                "stdout": str(output_path)}, indent=2)+"\n")
    start = time.monotonic()
    input_fd = os.open(input_path, os.O_RDONLY)
    output_fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o666)
    try:
        with (folder / "stderr.txt").open("wb") as errors:
            process = subprocess.run(command, stdin=input_fd, stdout=output_fd, stderr=errors, timeout=900)
    finally:
        os.close(input_fd)
        os.close(output_fd)
        os.close(keepalive)
        compressor.join(timeout=30)
        fifo.unlink()
    assert not compressor.is_alive() and not compression_errors, compression_errors
    assert process.returncode == 0 and (folder / "stderr.txt").read_bytes() == b""
    output = b"" if output_error else (folder / "result.out").read_bytes()
    trailer = record(stage, status, detail) if stage and not output_error else b""
    if expected is not None:
        assert output == expected+trailer, (name, output, expected+trailer)
    if stage and not output_error:
        # Decide completion solely from the actual final bytes of OUT.
        match = re.fullmatch(rb"\n\[space:([CLR]):([0-9A-F]{8}):([0-9A-F]{8})\]\n", output[-29:])
        assert match and match.groups() == (stage.encode(), f"{status:08X}".encode(), f"{detail:08X}".encode())
    raw = (folder / "space.bin").read_bytes()
    assert len(raw) == 2097152
    if ticks is None:
        assert raw[:2272] == bytes(2272), name
    if stage == "C":
        assert word(raw, STATUS) == 0
    elif stage:
        assert word(raw, STATUS) == status
        if stage == "R":
            assert word(raw, EXIT_CODE if status == 10 else PC) == detail
    copies, channels, last = audit_trace(folder / "trace.txt.gz")
    assert copies > 0 and channels > 0
    assert last.endswith(b" idle\n" if ticks is None else b" limit\n")
    if output_error:
        assert word(raw, STATUS) == 10 and word(raw, EXIT_CODE) == 1
        found, pending = False, b""
        with gzip.open(folder / "trace.txt.gz", "rb") as trace:
            while block := trace.read(8*1024*1024):
                chunk = pending+block
                if re.search(rb"(?:^|\n)channel [^\n]* 1\n", chunk):
                    found = True
                    break
                pending = chunk[-256:]
        assert found, "OUT error missing from raw channel events"
    result = {"stage": stage, "status": status, "detail": detail,
              "seconds": time.monotonic()-start, "copy_events": copies,
              "channel_events": channels, "stop": last.decode().strip()}
    (folder / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    cases += 1
    print(f"OK direct {name}: OUT={output!r}, {result['seconds']:.1f}s", flush=True)
    return raw


task = ROOT / "task.fth"
source = b": file-square dup * ;\n7 file-square . cr\n: file-tally 0 4 0 do i + loop ; file-tally . cr\n1 2 + ."
task.write_bytes(source)
job = ROOT / "pforth.in"
build = [sys.executable, "scripts/pforth/build.py", "--task", str(task), "-o", str(job)]
compiled = subprocess.run(build, capture_output=True, timeout=30)
(ROOT / "build.json").write_text(json.dumps(build, indent=2)+"\n")
(ROOT / "build.stderr").write_bytes(compiled.stderr)
assert compiled.returncode == 0, compiled.stderr
manifest = json.loads(job.with_name(job.name+".json").read_text())
assert manifest["report_status"] and manifest["task_bytes"] == len(source)
assert manifest["task_sha256"] == hashlib.sha256(source).hexdigest()
packet = job.read_bytes()[:manifest["task_offset"]]
assert job.read_bytes() == packet+source and manifest["job_bytes"] == len(packet)+len(source)

# Invalid assembly requests fail before altering the task or invoking GCC.
for name, extra in [("core-task", ["--core", "-o", str(ROOT / "invalid.in")]),
                    ("overwrite-task", ["-o", str(task)])]:
    args = [sys.executable, "scripts/pforth/build.py", "--task", str(task)]+extra
    result = subprocess.run(args, capture_output=True, timeout=10)
    assert result.returncode == 1 and task.read_bytes() == source
    (ROOT / (name+".stderr")).write_bytes(result.stderr)
assert not (ROOT / "invalid.in").exists()

# Complete task: user definitions, loops and the final line without newline.
if not options.skip_pforth:
    raw = run("pforth", job.read_bytes(), b"49 \n6 \n3 ", "R", 10)
    initial = job.with_name(job.name+".build") / "program.bin"
    for name in (b"FILE-SQUARE", b"FILE-TALLY"):
        assert name not in initial.read_bytes() and name in raw[MEMORY//8:MEMORY//8+524288]
    run("unknown-word", packet+b"NO_SUCH_WORD\n",
        b"NO_SUCH_WORD  ? - unrecognized word!\nTHROW code = -13 \nUndefined word!\n", "R", 10, 2)
    run("unfinished", packet+b": unfinished 1", b"pForth: unfinished definition\n", "R", 10, 2)
    run("bye-code", packet+b"hex FEDCBA98 bye-code ! bye\n999 .", b"\n", "R", 10, 0xFEDCBA98)
    run("output-error", packet+b"1 .\n", b"", "R", 10, 1, output_error=True)

for name, length in [("empty", 0), ("first-short", 36), ("later-short", 37+20),
                     ("last-short", manifest["installation_bytes"]-1)]:
    run(name, packet[:length], b"", "C", 1)
run("input-error", b"", b"", "C", 1, input_error=True)
for name, length in [("cpu-short", manifest["installation_bytes"]+1),
                     ("header-short", manifest["header_offset"]+11),
                     ("program-short", len(packet)-1)]:
    run(name, packet[:length], b"", "L", 11)
damaged = bytearray(packet)
damaged[manifest["header_offset"]] = ord("X")
run("bad-header", bytes(damaged), b"", "L", 11)

# All nine RV32I exception reasons and dynamic pc are reported by copies.
faults = [(1, 0x73, 0, {}), (2, 0x100073, 0, {}), (3, 0xFFFFFFFF, 0, {}),
          (4, 0x100073, 524288, {}), (5, 0x100073, 2, {}),
          (6, 0xA183, 0, {1: 524288}), (7, 0xA183, 0, {1: 1}),
          (8, 0x20A023, 0, {1: 524288}), (9, 0x20A023, 0, {1: 1})]
for code, instruction, pc, registers in faults:
    program = instruction.to_bytes(4, "little")
    if pc in (2, 524288):
        # Loader validates entry; JALR x0,x1,0 attempts the invalid next pc.
        program = (0x8067).to_bytes(4, "little")
        registers = {1: pc}
    cpu, layout = Image(report_status=True).build().encode(program, registers=registers)
    fault_packet, _ = encode_stream(cpu, layout, program)
    run(f"fault-{code}", fault_packet, b"", "R", code, 0 if code == 5 else pc)

program = bytes.fromhex("93001000ffffffff")
cpu, layout = Image(report_status=True).build().encode(program)
fault_packet, _ = encode_stream(cpu, layout, program)
run("fault-pc", fault_packet, b"", "R", 3, 4)

# The general C builder exposes the same direct completion profile.
cpacket = ROOT / "sum.in"
args = [sys.executable, "scripts/rv32i/build.py", "examples/rv32i/sum.c",
        "--stream", "--report-status", "-o", str(cpacket)]
result = subprocess.run(args, capture_output=True, timeout=30)
(ROOT / "c-build.json").write_text(json.dumps(args, indent=2)+"\n")
(ROOT / "c-build.stderr").write_bytes(result.stderr)
assert result.returncode == 0, result.stderr
run("c-sum", cpacket.read_bytes()+b"1 2\n", b"3\n", "R", 10)

# A finite external limit must not look like successful guest completion.
run("limit", packet, b"", None, None, ticks=1)
print(f"OK direct file jobs: {cases} executions; raw evidence in {ROOT}", flush=True)
