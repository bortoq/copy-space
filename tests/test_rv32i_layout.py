"""Check configurable copy fields against a byte-addressed RV32I oracle."""
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "modules")
from rv32i import Image, Layout, REGS, PC, STATUS
from rv32i_stream import encode_stream, record
from rv32i_reference import execute

ROOT = Path("tmp/space-tests/rv32i-layout")
ROOT.mkdir(parents=True, exist_ok=True)
SPACE_BYTES, MEMORY_BYTES = 67108864, 16777216
cases = []


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def words(*values):
    return b"".join(value.to_bytes(4, "little") for value in values)


def save_dump(folder, raw):
    compressed = folder / "space.bin.gz"
    with (folder / "space.bin").open("rb") as source, gzip.open(compressed, "wb", compresslevel=1) as out:
        shutil.copyfileobj(source, out, 1024*1024)
    with gzip.open(compressed, "rb") as source:
        digest = hashlib.sha256()
        while chunk := source.read(1024*1024):
            digest.update(chunk)
    signature = hashlib.sha256(raw).hexdigest()
    assert digest.hexdigest() == signature, "dump compression lost bytes"
    (folder / "space.bin").unlink()
    return {"dump": compressed.name, "dump_bytes": len(raw), "dump_sha256": signature}


def run_packet(name, packet, manifest, expected=None, expected_memory=None, output=b"",
               input_data=b"", fault=None, channels=None):
    folder = ROOT / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "in.bin").write_bytes(packet+input_data)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    command = ["build/bin/space-64m", "--trace", str(folder / "trace.txt"),
               "--dump-space", str(folder / "space.bin")]
    (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
    result = subprocess.run(command, input=packet+input_data, capture_output=True, timeout=30)
    (folder / "out.bin").write_bytes(result.stdout)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0 and not result.stderr, (name, result.stderr)
    assert result.stdout == output, name
    raw = (folder / "space.bin").read_bytes()
    assert len(raw) == SPACE_BYTES and raw[:2752] == bytes(2752), name
    trace = (folder / "trace.txt").read_text()
    assert trace.endswith(" idle\n") and "copy " in trace and "channel " in trace, name
    if fault is not None:
        assert word(raw, STATUS) == fault, name
    else:
        assert [word(raw, REGS+32*i) for i in range(34)] == expected, name
        base = 33554432
        assert raw[base:base+MEMORY_BYTES] == expected_memory, name
    if channels is not None:
        actual = [[int(v) for v in line.split()[2:]] for line in trace.splitlines()
                  if line.startswith("channel ")]
        actual = actual[-len(channels):] if channels else []
        assert actual == channels, (name, actual, channels)
    evidence = save_dump(folder, raw)
    evidence.update({"name": name, "status": word(raw, STATUS), "pc": word(raw, PC),
                     "input_sha256": hashlib.sha256(packet+input_data).hexdigest(),
                     "output_sha256": hashlib.sha256(result.stdout).hexdigest(),
                     "copy_events": sum(line.startswith("copy ") for line in trace.splitlines()),
                     "channel_events": sum(line.startswith("channel ") for line in trace.splitlines())})
    (folder / "evidence.json").write_text(json.dumps(evidence, indent=2)+"\n")
    cases.append(evidence)
    print(f"OK large layout {name}: status={word(raw, STATUS)}", flush=True)


def run(name, program, registers=None, entry=0, io=None):
    expected, memory, _ = execute(program, registers, entry, io=io,
                                  memory_bytes=MEMORY_BYTES, memory_bit=268435456)
    image, manifest = Image(io=io is not None, layout=Layout(SPACE_BYTES),
                            memory_bytes=MEMORY_BYTES).build().encode(program, entry, registers)
    packet, manifest = encode_stream(image, manifest, program)
    run_packet(name, packet, manifest, expected[-1], memory,
               input_data=io["input"] if io is not None else b"",
               output=io["output"] if io is not None else b"",
               channels=io["channels"] if io is not None else None)
    return packet, manifest


def machine_tests():
    # Golden streams captured from the previous generator before refactoring.
    program = words(0x00a00093, 0x00300113, 0x002081b3, 0x00100073)
    signatures = {"00": "702cbe2b8635f82c717e0a9d5b43a655813d8f8b538d9cea7829890626b6f263",
                  "10": "c09308219dc2ad429ab22fa39a945c3a887338e508e7b8885d606ecc61d944b8",
                  "11": "db2383d035396c85d5aac3cbb38080dee897bf6013d1951f7b25c3d3d2dfb64b"}
    def check_default():
        for io, report in ((False, False), (True, False), (True, True)):
            image, manifest = Image(io=io, report_status=report).build().encode(program)
            packet, _ = encode_stream(image, manifest, program)
            assert hashlib.sha256(packet).hexdigest() == signatures[str(int(io))+str(int(report))]
    check_default()
    run("add", program)
    check_default()  # Large generation must not mutate the default placement.

    # SW/LW, SB/LBU and the highest valid byte and word.
    for address in (524288, 1048576, 8388608, MEMORY_BYTES-4):
        run(f"word-{address}", words(0x0020a023, 0x0000a183, 0x00100073),
            {1: address, 2: 0x89abcdef})
    run("last-byte", words(0x00208023, 0x0000c183, 0x00100073),
        {1: MEMORY_BYTES-1, 2: 0xab})
    for name, instruction, address in (
            ("load-outside", 0x0000a183, MEMORY_BYTES),
            ("store-outside", 0x0020a023, MEMORY_BYTES),
            ("load-negative", 0x0000a183, 0xfffffffc),
            ("word-align", 0x0000a183, MEMORY_BYTES-1),
            ("fetch-outside", 0x00008067, MEMORY_BYTES)):
        run(name, words(instruction, 0x00100073), {1: address})
    full = bytes(MEMORY_BYTES-4)+words(0x00100073)
    packet, manifest = run("full-load", full, entry=MEMORY_BYTES-4)
    run_packet("full-load-short", packet[:-1], manifest, fault=11)
    header = manifest["header_offset"]
    for count in (0, 1, 43):
        run_packet(f"record-short-{count}", packet[:count], manifest, fault=0,
                   output=b"\n[space:C:00000001:00000000]\n")
    run_packet("bad-length", packet[:header]+b"RVS1"+
               (MEMORY_BYTES+1).to_bytes(4, "little")+bytes(4), manifest, fault=11)

    # READ; fd=1; WRITE; EXIT. Read/write entire memory, keeping the code valid.
    io_program = words(0x73, 0x00100513, 0x04000893, 0x73, 0x05d00893, 0x73)
    for pointer, count in ((8388608, 8), (MEMORY_BYTES-1, 1), (MEMORY_BYTES-1, 2),
                           (MEMORY_BYTES, 1), (0xfffffffc, 8), (0, MEMORY_BYTES+1)):
        run(f"io-{pointer}-{count}", io_program,
            {10: 0, 11: pointer, 12: count, 17: 63}, io={"input": b"ABCDEFGH"})
    whole = io_program+b"ABCDEFGH"*((MEMORY_BYTES-len(io_program))//8)
    assert len(whole) == MEMORY_BYTES
    run("io-full", io_program, {10: 0, 11: 0, 12: MEMORY_BYTES, 17: 63}, io={"input": whole})

    # Wider fields also apply to diagnostic records and state frames.
    report_program = words(0x00700513, 0x05d00893, 0x73)
    expected, memory, _ = execute(report_program, io={"input": b""},
                                  memory_bytes=MEMORY_BYTES, memory_bit=268435456)
    image, manifest = Image(io=True, report_status=True, layout=Layout(SPACE_BYTES),
                            memory_bytes=MEMORY_BYTES).build().encode(report_program)
    packet, manifest = encode_stream(image, manifest, report_program)
    run_packet("report-exit", packet, manifest, expected[-1], memory,
               output=b"\n[space:R:0000000A:00000007]\n")
    run_packet("report-short", packet[:manifest["header_offset"]+3], manifest,
               fault=11, output=b"\n[space:L:0000000B:00000000]\n")
    expected, memory, _ = execute(program, memory_bytes=MEMORY_BYTES)
    framed = b"".join(bytes(sum(((value >> (byte*8+i)) & 1) << (7-i)
                               for i in range(8)) for byte in range(4))
                      for frame in expected for value in frame)
    image, manifest = Image(True, layout=Layout(SPACE_BYTES),
                            memory_bytes=MEMORY_BYTES).build().encode(program)
    packet, manifest = encode_stream(image, manifest, program)
    run_packet("state-frames", packet, manifest, expected[-1], memory, output=framed)

    for value in (0, 1048576, 3145728, 536870912):
        try:
            Layout(value)
        except ValueError:
            pass
        else:
            raise AssertionError(value)
    for value in (0, 65535, MEMORY_BYTES+1, MEMORY_BYTES*2):
        try:
            Image(layout=Layout(SPACE_BYTES), memory_bytes=value)
        except ValueError:
            pass
        else:
            raise AssertionError(value)
    for field in range(3):
        row = [0, 0, 0]
        row[field] = 1 << (28 if field == 0 else 29)
        try:
            record([tuple(row), (0, 0, 0), (0, 0, 0), (0, 0, 0)], Layout(SPACE_BYTES))
        except ValueError:
            pass
        else:
            raise AssertionError("installation field overflow accepted")
    for rows in ([(0, 0, 0)]*3, [(0, 0, 0)]*3+[(0, 0)]):
        try:
            record(rows, Layout(SPACE_BYTES))
        except ValueError:
            pass
        else:
            raise AssertionError("incomplete installation accepted")


def c_tests():
    source = Path("tests/fixtures/rv32i/large_layout.c")
    for optimization in ("O0", "O2"):
        for stream in (False, True):
            name = f"c-{optimization}-{'stream' if stream else 'core'}"
            folder = ROOT / name
            folder.mkdir(parents=True, exist_ok=True)
            image = folder / ("program.stream" if stream else "program.core")
            command = [sys.executable, "scripts/rv32i/build.py", str(source), "-o", str(image),
                       "--space-bytes", str(SPACE_BYTES), "--memory-bytes", str(MEMORY_BYTES),
                       "--optimization", optimization]+(["--stream"] if stream else [])
            (folder / "build.json").write_text(json.dumps(command, indent=2)+"\n")
            result = subprocess.run(command, capture_output=True, timeout=30)
            (folder / "build.stderr").write_bytes(result.stderr)
            assert result.returncode == 0, result.stderr
            manifest = json.loads(image.with_name(image.name+".json").read_text())
            program = image.with_name(image.name+".build") / "program.bin"
            assert program.stat().st_size > 1048576
            command = [sys.executable, "scripts/rv32i/run.py", str(image),
                       "--space", "build/bin/space-64m", "--space-bytes", str(SPACE_BYTES),
                       "--trace", str(folder / "trace.txt"), "--dump-space", str(folder / "space.bin")]
            command += ["--stream"] if stream else []
            (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
            (folder / "in.bin").write_bytes(b"D")
            result = subprocess.run(command, input=b"D", capture_output=True, timeout=30)
            (folder / "out.bin").write_bytes(result.stdout)
            (folder / "stderr.txt").write_bytes(result.stderr)
            assert result.returncode == 0 and result.stdout == b"XABCDE" and not result.stderr
            raw = (folder / "space.bin").read_bytes()
            assert len(raw) == SPACE_BYTES and raw[:2752] == bytes(2752)
            assert word(raw, STATUS) == 10 and word(raw, REGS+64) > 16773000
            trace = (folder / "trace.txt").read_text()
            assert trace.endswith(" idle\n")
            assert any(line.startswith("channel ") and int(line.split()[4]) > 268435456+8*8388608
                       for line in trace.splitlines())
            evidence = save_dump(folder, raw)
            evidence.update({"name": name, "status": 10, "output": result.stdout.hex()})
            (folder / "evidence.json").write_text(json.dumps(evidence, indent=2)+"\n")
            cases.append(evidence)
            print(f"OK large C {name}: OUT={result.stdout!r}", flush=True)
    command = [sys.executable, "scripts/rv32i/build.py", str(source), "--space-bytes", str(SPACE_BYTES),
               "--memory-bytes", "8388608", "-o", str(ROOT / "too-small.core")]
    result = subprocess.run(command, capture_output=True, timeout=30)
    (ROOT / "too-small.stderr").write_bytes(result.stderr)
    assert result.returncode != 0 and b"program leaves less than 1024 bytes" in result.stderr


if "--c" in sys.argv:
    c_tests()
else:
    machine_tests()
(ROOT / ("c-summary.json" if "--c" in sys.argv else "summary.json")).write_text(
    json.dumps(cases, indent=2)+"\n")
print(f"OK large layout: {len(cases)} executions; complete traces and lossless dumps in {ROOT}")
