"""Exercise real IN loading, failures and guest I/O; retain raw executions."""
import json
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "modules")
from rv32i import Image, REGS, STATUS, PC, MEMORY
from rv32i_stream import encode_stream

ROOT = Path("tmp/space-tests/rv32i-stream")
ROOT.mkdir(parents=True, exist_ok=True)
cases = 0
CORE_ERROR = b"\n[space:C:00000001:00000000]\n"


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def packet_for(program, io=False, entry=0):
    image, manifest = Image(io=io).build().encode(program, entry)
    packet, manifest = encode_stream(image, manifest, program)
    return packet, manifest, image


def run(name, packet, status, output=b"", ticks=None, input_path=None):
    global cases
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    (folder / "in.bin").write_bytes(packet)
    args = ["build/bin/space_image_proof", "--in", str(input_path or folder / "in.bin"),
            "--out", str(folder / "out.bin"), "--dump-space", str(folder / "space.bin"),
            "--trace", str(folder / "trace.txt"), "--report", str(folder / "report.txt")]
    args += ["--unlimited"] if ticks is None else ["--ticks", str(ticks)]
    (folder / "args.json").write_text(json.dumps(args, indent=2)+"\n")
    result = subprocess.run(args, capture_output=True, timeout=20)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, (name, result.stderr)
    raw = (folder / "space.bin").read_bytes()
    trace = (folder / "trace.txt").read_text()
    report = dict(line.split("=", 1) for line in (folder / "report.txt").read_text().splitlines())
    assert (folder / "out.bin").read_bytes() == output, name
    assert word(raw, STATUS) == status, (name, word(raw, STATUS))
    assert report["stop"] == ("idle" if ticks is None else "limit"), (name, report)
    if ticks is None:
        assert raw[:2272] == bytes(2272), name
    cases += 1
    print(f"OK IN load {name}: status={status}, ticks={report['ticks']}")
    return raw, trace


# ADDI x1,10; ADDI x2,3; ADD x3,x1,x2; EBREAK.
program = bytes.fromhex("9300a00013013000b381200073001000")
packet, manifest, cpu = packet_for(program)
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
raw, trace = run("add", packet, 2)
assert word(raw, REGS+96) == 13 and word(raw, PC) == 12
assert raw[MEMORY//8:MEMORY//8+len(program)] == program
assert "--core" not in (ROOT / "add/args.json").read_text()
assert f"{manifest['labels']['add']}\n" in trace

# Standard core rejects every possible incomplete first installation record.
for count in range(37):
    raw, trace = run(f"first-short-{count}", packet[:count], 0, CORE_ERROR)
    assert trace.endswith("stop 2 idle\n")
run("first-device-error", b"", 0, CORE_ERROR, input_path=ROOT)
run("later-record-short", packet[:37+20], 0, CORE_ERROR)
run("last-record-short", packet[:manifest["installation_bytes"]-1], 0, CORE_ERROR)

installed = manifest["installation_bytes"]
header_at = manifest["header_offset"]
for length in (0, 1, manifest["cpu_payload_bytes"]-1):
    raw, trace = run(f"cpu-short-{length}", packet[:installed+length], 11)
    assert f"{manifest['labels']['fetch']}\n" not in trace
for length in range(12):
    run(f"header-short-{length}", packet[:header_at+length], 11)
for length in (0, 1, len(program)-1):
    run(f"program-short-{length}", packet[:header_at+12+length], 11)

# Actual fread reports both a partial count and ferror at each loading stage.
(ROOT / "packet.bin").write_bytes(packet)
for name, count, expected in [("first", 3, 0), ("cpu", installed+3, 11),
                               ("header", header_at+3, 11),
                               ("program", header_at+12+1, 11)]:
    folder = ROOT / (name+"-partial-error")
    folder.mkdir(exist_ok=True)
    command = ["build/bin/test_rv32i_io_partial", str(ROOT / "packet.bin"), "stream",
               str(folder / "trace.txt"), str(folder / "space.bin"),
               str(folder / "out.bin"), str(count)]
    (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
    result = subprocess.run(command, capture_output=True, timeout=20)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, (name, result.stderr)
    raw = (folder / "space.bin").read_bytes()
    trace = (folder / "trace.txt").read_text()
    assert raw[:2272] == bytes(2272) and word(raw, STATUS) == expected, name
    assert any(line.startswith("channel ") and line.endswith(" 1")
               for line in trace.splitlines()), name
    cases += 1

for name, header in [
    ("signature", b"BAD!"+struct.pack("<II", 16, 0)),
    ("length-zero", b"RVS1"+struct.pack("<II", 0, 0)),
    ("length-three", b"RVS1"+struct.pack("<II", 3, 0)),
    ("length-large", b"RVS1"+struct.pack("<II", 524289, 0)),
    ("length-max", b"RVS1"+struct.pack("<II", 0xffffffff, 0)),
    ("entry-align", b"RVS1"+struct.pack("<II", 16, 2)),
    ("entry-outside", b"RVS1"+struct.pack("<II", 16, 16)),
    ("entry-overflow", b"RVS1"+struct.pack("<II", 16, 0xfffffffc)),
]:
    run("bad-"+name, packet[:header_at]+header+program, 11)

# The CPU's actual layers/tables have arrived unchanged through IN.
raw, trace = run("cpu-loaded", packet, 0, ticks=manifest["installation_records"]*3+2)
assert raw[0x24000//8:manifest["code_end_bit"]//8] == cpu[0x24000//8:manifest["code_end_bit"]//8]
assert raw[REGS//8:REGS//8+136] == cpu[REGS//8:REGS//8+136]

# Maximum guest payload, with entry at its last instruction.
full = bytes(65532)+bytes.fromhex("73001000")
boundary, _, _ = packet_for(full, entry=65532)
raw, _ = run("guest-64k", boundary, 2)
assert word(raw, PC) == 65532 and raw[MEMORY//8:MEMORY//8+65536] == full

# Compile actual C and use the normal space executable, without --core.
cpacket = ROOT / "sum.stream"
build = [sys.executable, "scripts/rv32i/build.py", "examples/rv32i/sum.c",
         "--stream", "-o", str(cpacket)]
result = subprocess.run(build, capture_output=True)
(ROOT / "build.json").write_text(json.dumps(build, indent=2)+"\n")
(ROOT / "build.stderr").write_bytes(result.stderr)
assert result.returncode == 0, result.stderr
prefix = cpacket.read_bytes()
for name, data, output in [("sum", b"1 2\n", b"3\n"),
                           ("sum-wrap", b"4294967295 1\n", b"0\n"),
                           ("sum-eof", b"", b"")]:
    raw, trace = run(name, prefix+data, 10, output)
    guest_exit = word(raw, 132160)
    assert guest_exit == (2 if name == "sum-eof" else 0)
    direct = subprocess.run(["build/bin/space"], input=prefix+data, capture_output=True, timeout=20)
    (ROOT / name / "space.out").write_bytes(direct.stdout)
    assert direct.returncode == 0 and direct.stdout == output and direct.stderr == b""
    command = [sys.executable, "scripts/rv32i/run.py", "--stream", str(cpacket),
               "--dump-space", str(ROOT / name / "wrapper-space.bin"),
               "--trace", str(ROOT / name / "wrapper-trace.txt")]
    result = subprocess.run(command, input=data, capture_output=True, timeout=20)
    (ROOT / name / "wrapper-args.json").write_text(json.dumps(command, indent=2)+"\n")
    (ROOT / name / "wrapper.out").write_bytes(result.stdout)
    (ROOT / name / "wrapper.stderr").write_bytes(result.stderr)
    assert result.returncode == guest_exit and result.stdout == output and result.stderr == b""

# A live input stream can remain open when the guest finishes.
command = [sys.executable, "scripts/rv32i/run.py", "--stream", str(cpacket)]
live = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
try:
    live.stdin.write(b"1 2\n")
    live.stdin.flush()
    assert live.wait(timeout=20) == 0
    assert live.stdout.read() == b"3\n" and live.stderr.read() == b""
finally:
    live.stdin.close()
    live.stdout.close()
    live.stderr.close()
    if live.poll() is None:
        live.kill()
        live.wait()
(ROOT / "live-input-args.json").write_text(json.dumps(command, indent=2)+"\n")
(ROOT / "live-input.out").write_bytes(b"3\n")

data_file, out_file = ROOT / "file-input.txt", ROOT / "file-output.txt"
data_file.write_bytes(b"15 17\n")
result = subprocess.run(command+["--in", str(data_file), "--out", str(out_file)],
                        input=b"", capture_output=True, timeout=20)
assert result.returncode == 0 and result.stdout == b"" and result.stderr == b""
assert out_file.read_bytes() == b"32\n"
result = subprocess.run(command+["--ticks", "0"], input=b"", capture_output=True, timeout=20)
assert result.returncode == 125 and b"did not complete" in result.stderr
cases += 3

print(f"OK IN load: {cases} cases; raw evidence in {ROOT}")
