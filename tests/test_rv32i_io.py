"""Independent I/O oracle and raw copy/channel evidence; no cross compiler needed."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules"))
from rv32i import Image
from rv32i_reference import execute

ROOT = Path("tmp/space-tests/rv32i-io")
ROOT.mkdir(parents=True, exist_ok=True)
BASE, MANIFEST = Image(io=True, memory_bytes=65536).build().encode(registers={})
(ROOT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2)+"\n")
MEMORY_BYTE = 8388608//8
cases = 0


def iword(rd, rs1=0, imm=0):
    return ((imm & 4095) << 20) | (rs1 << 15) | (rd << 7) | 0x13


def store(rs, address):
    return ((address >> 5) << 25) | (rs << 20) | (2 << 12) | ((address & 31) << 7) | 0x23


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def set_word(raw, address, value):
    for i in range(32):
        mask = 1 << (7-(address+i)%8)
        index = (address+i)//8
        raw[index] = (raw[index] & ~mask) | (mask if (value >> i) & 1 else 0)


def run(name, words, regs, data=b"", memory=None, read_error=False, write_error=False):
    global cases
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    program = b"".join(value.to_bytes(4, "little") for value in words)
    io = {"input": data, "read_error": read_error, "write_error": write_error}
    expected, expected_memory, _ = execute(program, regs, initial_memory=memory, io=io)
    assert expected[-1][-1] == 10
    core = bytearray(BASE)
    for register, value in regs.items():
        if register:
            set_word(core, 131072+register*32, value)
    for address, content in (memory or {}).items():
        core[MEMORY_BYTE+address:MEMORY_BYTE+address+len(content)] = content
    core[MEMORY_BYTE:MEMORY_BYTE+len(program)] = program
    (folder / "core.bin").write_bytes(core)
    (folder / "program.bin").write_bytes(program)
    (folder / "in.bin").write_bytes(data)
    (folder / "initial.json").write_text(json.dumps(regs, indent=2)+"\n")
    args = ["build/bin/space_image_proof", "--core", str(folder / "core.bin"),
            "--in", str(folder if read_error else folder / "in.bin"),
            "--out", "/dev/full" if write_error else str(folder / "out.bin"),
            "--dump-space", str(folder / "space.bin"), "--trace", str(folder / "trace.txt"),
            "--report", str(folder / "report.txt"), "--ticks", "10000"]
    (folder / "args.json").write_text(json.dumps(args, indent=2)+"\n")
    result = subprocess.run(args, capture_output=True, timeout=15)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, (name, result.stderr)
    raw = (folder / "space.bin").read_bytes()
    actual = [word(raw, 131072+32*i) for i in range(34)]
    assert actual == expected[-1], (name, actual, expected[-1])
    assert word(raw, 132160) == io["exit_code"], name
    assert raw[MEMORY_BYTE:MEMORY_BYTE+65536] == expected_memory, name
    assert raw[:2272] == bytes(2272), name
    if not write_error:
        assert (folder / "out.bin").read_bytes() == io["output"], name
    trace = (folder / "trace.txt").read_text().splitlines()
    observed = [[int(value) for value in line.split()[2:]] for line in trace if line.startswith("channel ")]
    assert observed == io["channels"], (name, observed, io["channels"])
    assert trace[-1].endswith(" idle")
    (folder / "calls.json").write_text(json.dumps(io["calls"], indent=2)+"\n")
    if not read_error and not write_error:
        main_args = ["build/bin/space", "--core", str(folder / "core.bin"),
                     "--dump-space", str(folder / "main-space.bin"), "--trace", str(folder / "main-trace.txt")]
        actual_main = subprocess.run(main_args, input=data, capture_output=True, check=True, timeout=15)
        (folder / "main-out.bin").write_bytes(actual_main.stdout)
        assert actual_main.stdout == io["output"], name
        assert (folder / "main-space.bin").read_bytes() == raw, name
        assert (folder / "main-trace.txt").read_bytes() == (folder / "trace.txt").read_bytes(), name
    cases += 1
    print(f"OK RV32I I/O {name}: calls={io['calls']}, exit={io['exit_code']}")
    return folder


# ECALL result is saved before exit, with all untouched registers checked.
simple = [0x73, store(10, 512), iword(17, imm=93), 0x73]
saved = {i: (0x12340000+i) for i in range(1, 32)}
for name, operation, descriptor, pointer, count, data, memory in [
    ("read-full", 63, 0, 1024, 8, b"abcdefgh", None),
    ("read-short", 63, 0, 1025, 8, b"abc", None),
    ("read-eof", 63, 0, 1024, 8, b"", None),
    ("write-full", 64, 1, 1025, 4, b"", {1025: b"TEST"}),
    ("zero-read", 63, 0, 0xffffffff, 0, b"unused", None),
    ("zero-write", 64, 1, 0xffffffff, 0, b"", None),
    ("last-byte-read", 63, 0, 65535, 1, b"X", None),
    ("last-byte-write", 64, 1, 65535, 1, b"", {65535: b"Z"}),
    ("read-cross-end", 63, 0, 65535, 2, b"XX", None),
    ("write-cross-end", 64, 1, 65535, 2, b"", {65535: b"Z"}),
    ("buffer-outside", 63, 0, 65536, 1, b"X", None),
    ("address-overflow", 64, 1, 0xffffffff, 2, b"", None),
    ("count-overflow", 63, 0, 1024, 0xffffffff, b"X", None),
    ("count-too-large", 63, 0, 0, 65537, b"X", None),
    ("read-bad-fd", 63, 1, 1024, 1, b"X", None),
    ("write-bad-fd", 64, 0, 1024, 1, b"", None),
    ("zero-bad-fd", 63, 1, 0xffffffff, 0, b"", None),
    ("unknown", 62, 0, 0, 0, b"", None),
    ("unknown-high-bits", 0x8000003f, 0, 1024, 1, b"X", None),
]:
    regs = saved.copy()
    regs.update({10: descriptor, 11: pointer, 12: count, 17: operation})
    run(name, simple, regs, data, memory)
run("read-error", simple, {10: 0, 11: 1024, 12: 8, 17: 63}, read_error=True)
run("write-error", simple, {10: 1, 11: 1024, 12: 4, 17: 64},
    memory={1024: b"TEST"}, write_error=True)

# Repeated short read and EOF; a second service uses a previously patched layer.
run("read-twice", [0x73, store(10, 512), iword(10), 0x73, store(10, 516), iword(17, imm=93), 0x73],
    {10: 0, 11: 1024, 12: 8, 17: 63}, b"abc")
run("write-twice", [0x73, store(10, 512), iword(10, imm=1), iword(12, imm=2), 0x73,
                    store(10, 516), iword(17, imm=93), 0x73],
    {10: 1, 11: 1024, 12: 4, 17: 64}, memory={1024: b"TEST"})

# Full 64 KiB request includes guest code; reread instructions are still valid.
full_words = [0x73, iword(17, imm=93), 0x73]
full_program = b"".join(w.to_bytes(4, "little") for w in full_words)
run("full-memory-read", full_words, {10: 0, 11: 0, 12: 65536, 17: 63},
    full_program+bytes(65536-len(full_program)))

# Real fread/fwrite return a positive byte count together with ferror.
for direction, source in [("in", "read-full"), ("out", "write-full")]:
    folder = ROOT / ("partial-error-"+direction)
    folder.mkdir(exist_ok=True)
    args = ["build/bin/test_rv32i_io_partial", str(ROOT / source / "core.bin"), direction,
            str(folder / "trace.txt"), str(folder / "space.bin"), str(folder / "out.bin")]
    (folder / "args.json").write_text(json.dumps(args, indent=2)+"\n")
    result = subprocess.run(args, capture_output=True, timeout=10)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    raw = (folder / "space.bin").read_bytes()
    assert word(raw, 132128) == 10 and word(raw, 132160) == 3
    assert raw[:2272] == bytes(2272)
    assert raw[MEMORY_BYTE+512:MEMORY_BYTE+516] == b"\3\0\0\0"
    if direction == "in":
        assert raw[MEMORY_BYTE+1024:MEMORY_BYTE+1027] == b"abc"
    else:
        assert (folder / "out.bin").read_bytes() == b"TES"
    channels = [line.split() for line in (folder / "trace.txt").read_text().splitlines()
                if line.startswith("channel ")]
    assert len(channels) == 1 and channels[0][5:] == ["24", "1"], channels
    print(f"OK RV32I I/O partial-error-{direction}: returned=3, copied_bits=24, error=1")

try:
    Image(state_output=True, io=True)
    raise AssertionError("I/O must reject mixing state frames into OUT")
except ValueError:
    pass
# Generic CLI diagnostics must report failing files, including buffered writes.
for option, target in [("--trace", ROOT / "missing" / "trace.txt"),
                       ("--dump-space", ROOT / "missing" / "space.bin"),
                       ("--trace", Path("/dev/full")), ("--dump-space", Path("/dev/full"))]:
    result = subprocess.run(["build/bin/space", "--core", str(ROOT / "zero-read/core.bin"),
                             option, str(target)], input=b"", capture_output=True, timeout=5)
    assert result.returncode != 0
    assert b"cannot " in result.stderr
print(f"OK RV32I I/O: {cases} programs, independently checked memory/registers/channel events")
