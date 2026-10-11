"""Independent instruction bytes and state checks; keep execution artifacts."""
import json
import subprocess
from pathlib import Path

ROOT = Path("tmp/space-tests")
ROOT.mkdir(parents=True, exist_ok=True)
SPACE_BYTES = 2097152
WIDTHS = (23, 24, 24)
CORE = [(10, 269, 118), (296, 18176, 0), (0, 0, 0), (284, 0, 524288)]
NOP = (0, 0, 0)


def instructions(rows):
    bits = [value >> bit & 1 for row in rows
            for value, width in zip(row, WIDTHS) for bit in range(width)]
    data = bytearray((len(bits) + 7) // 8)
    for i, value in enumerate(bits):
        data[i // 8] |= value << (7 - i % 8)
    return bytes(data)


def decode(data, slot):
    values, start = [], slot * 71
    for width in WIDTHS:
        values.append(sum(((data[(start+i)//8] >> (7-(start+i)%8)) & 1) << i
                          for i in range(width)))
        start += width
    return values


def image(rows, tail=b""):
    assert len(rows) == 4
    return instructions(rows) + b"\0" + tail


def run(name, data, ticks=4, stop="limit", completed=None, error=False, input_path=None,
        output_path=None, core=None):
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    (folder / "in.bin").write_bytes(data)
    args = ["build/bin/space_image_proof", "--in", str(input_path or folder / "in.bin"),
            "--out", str(output_path or folder / "out.bin"), "--ticks", str(ticks),
            "--dump-space", str(folder / "space.bin"), "--dump-processor",
            str(folder / "processor.txt"), "--report", str(folder / "report.txt"),
            "--trace", str(folder / "trace.txt")]
    if ticks is None:
        index = args.index("--ticks")
        args[index:index+2] = ["--unlimited"]
    if core is not None:
        (folder / "core.bin").write_bytes(core)
        args += ["--core", str(folder / "core.bin")]
    (folder / "args.json").write_text(json.dumps(args, ensure_ascii=False, indent=2) + "\n")
    result = subprocess.run(args, capture_output=True, timeout=5)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == int(error), (name, result.returncode, result.stderr)
    report = dict(line.split("=", 1) for line in (folder / "report.txt").read_text().splitlines())
    assert report["stop"] == stop, (name, report)
    if completed is not None:
        assert int(report["ticks"]) == completed, (name, report)
    raw = (folder / "space.bin").read_bytes()
    assert len(raw) == SPACE_BYTES
    rows = [[int(x) for x in line.split()] for line in (folder / "processor.txt").read_text().splitlines()]
    assert rows == [[slot, *decode(raw, slot)] for slot in range(256)], name
    trace = (folder / "trace.txt").read_text()
    assert trace.endswith(f"stop {report['ticks']} {stop}\n"), name
    print(f"OK {name}: ticks={report['ticks']} stop={stop}")
    return raw, (folder / "out.bin").read_bytes() if output_path is None else b"", trace


def field_value(raw, start, width):
    return sum(((raw[(start+i)//8] >> (7-(start+i)%8)) & 1) << i for i in range(width))


# Zero ticks: independently encoded core and zero-filled memory.
raw, out, _ = run("initial", b"", 0, completed=0)
expected = bytearray(SPACE_BYTES)
expected[:36] = instructions(CORE)
expected[2336:2336+36] = instructions(CORE)
core_error = b"\n[space:C:00000001:00000000]\n"
expected[2372:2372+len(core_error)] = core_error
for entry in range(1024):
    at = 65536+entry*64
    rows = ([NOP, NOP, NOP, (284, 0, 18176)] if entry == 592 else
            [NOP, NOP, (232, 18976, 0), (284, 0, 19208)])
    expected[at:at+36] = instructions(rows)
initial_space = bytes(expected)
assert raw == expected and out == b""

# A custom initial image can halt without any bootstrap or input.
raw, out, _ = run("empty-core", b"", ticks=None, stop="idle", completed=0, core=b"")
assert raw == bytes(SPACE_BYTES) and out == b""

# A chain of layers needs more than the old compulsory 1024 ticks.
long_core = bytearray(4096 + 1100 * 36 + 1)
marker_address = (len(long_core)-1)*8
long_core[-1] = 0xA5
long_core[:36] = instructions([NOP, NOP, NOP, (284, 0, 32768)])
for i in range(1100):
    source = 32768 + (i+1)*288 if i < 1099 else 16776704
    output = (8, marker_address, 0) if i == 1099 else NOP
    long_core[4096+i*36:4096+(i+1)*36] = instructions([NOP, NOP, output, (284, 0, source)])
raw, out, trace = run("unlimited", b"", ticks=None, stop="idle", completed=1101, core=long_core)
assert raw[:36] == bytes(36) and out == b"\xA5"
assert "copy 1100 3 284 0 16776704\n" in trace
unlimited = ROOT / "unlimited"
result = subprocess.run(["build/bin/space", "--core", str(unlimited / "core.bin")],
                        input=b"", capture_output=True, timeout=5)
assert result.returncode == 0 and result.stdout == b"\xA5"
_, out, _ = run("explicit-limit", b"", 1100, completed=1100, core=long_core)
assert out == b""
run("explicit-zero", b"", 0, completed=0, core=long_core)

# Stop after a layer clears itself; compare the entire space, not only OUT.
clear_layer = [NOP, NOP, NOP, (284, 0, 131072)]
data = image(clear_layer)
raw, out, trace = run("idle", data, 100, "idle", 3)
expected = bytearray(initial_space)
expected[:64] = bytes(64)
expected[2272:2272+len(data)] = data
assert raw == expected and out == b""
assert "copy 2 3 284 0 131072\n" in trace
raw, _, _ = run("limit", data, 2, completed=2)
assert [decode(raw, i) for i in range(4)] == [list(row) for row in clear_layer]

# The actual assembled first layer: output appears on tick two, then idle.
first_layer = subprocess.run(["build/bin/assembler"],
                            input=Path("modules/proof_first_layer_out.copy").read_bytes(),
                            capture_output=True, check=True).stdout + b"\x03"
for ticks, stop, completed, expected_out in ((1, "limit", 1, b""),
                                            (2, "limit", 2, b""),
                                            (3, "idle", 3, b"\x03"),
                                            (10, "idle", 3, b"\x03")):
    raw, out, trace = run(f"first-layer-{ticks}", first_layer, ticks, stop, completed)
    assert out == expected_out
    if completed == 3:
        expected = bytearray(initial_space)
        expected[:64] = bytes(64)
        expected[2272:2272+len(first_layer)] = first_layer
        assert raw == expected
        assert "channel 2 2 8 18464 8 0\n" in trace

# Full, partial and empty bootstrap input; partial bytes remain in the buffer.
for count in (0, 1, 36):
    partial = data[:count]
    rows = [NOP, (296, 18176, 0), NOP, (1, 90000, 118)]
    raw, out, trace = run(f"input-short-{count}", partial, ticks=1, completed=1,
                         core=instructions(rows))
    expected = bytearray(SPACE_BYTES)
    rows[1] = (296, 18176, count * 16)
    expected[:36] = instructions(rows)
    expected[2272:2272+count] = partial
    assert raw == expected and out == b""
    assert "copy 0 3 1 90000 118\n" in trace

# Full input status; disabled channels ignore their unused non-aligned fields.
rows = [NOP, (8, 65536, 0), NOP, NOP]
raw, _, _ = run("input-full", image(rows, b"\xA5"), 3, completed=3)
assert raw[8192] == 0xA5 and decode(raw, 1) == [8, 65536, 16]
raw, _, _ = run("input-eof", image(rows), 3, completed=3)
assert decode(raw, 1) == [8, 65536, 0]
raw, _, _ = run("input-partial", image([NOP, (16, 65536, 0), NOP, NOP], b"\xA5"),
                3, completed=3)
assert raw[8192:8194] == b"\xA5\0" and decode(raw, 1)[2] == 16

# Read the packed status in the same tick and stop using the image's own code.
for label, tail, request, status in (("eof", b"", 8, 0),
                                     ("partial", b"\xA5", 16, 16),
                                     ("full", b"\xA5", 8, 16)):
    rows = [(24, 90000, 118), (request, 65536, 0), NOP, (284, 0, 131072)]
    raw, _, trace = run(f"handle-{label}", image(rows, tail), 20, "idle", 3)
    assert field_value(raw, 90000, 24) == status
    assert raw[:36] == bytes(36)
    assert "copy 2 0 24 90000 118\n" in trace

# Invalid channel alignment is visible to instructions, not a host-side stop.
rows = [(1, 90000, 118), (8, 65537, 0), NOP, (284, 0, 131072)]
raw, _, _ = run("handle-channel-error", image(rows), 20, "idle", 3)
assert raw[90000 // 8] == 0x80 and raw[:36] == bytes(36)
raw, _, _ = run("disabled", image([NOP, (0, 1, 7), (0, 3, 9), NOP]), 9, "idle", 2)
assert decode(raw, 1) == [0, 1, 7] and decode(raw, 2) == [0, 3, 9]

# Invalid internal ranges and channels fail without changing their destination.
for name, rows, slot in (
    ("copy-bounds", [NOP, NOP, NOP, (8, 16777212, 65536)], 3),
    ("input-align", [NOP, (8, 65537, 0), NOP, NOP], 1),
    ("input-bounds", [NOP, (16, 16777208, 0), NOP, NOP], 1),
    ("output-align", [NOP, NOP, (7, 65536, 0), NOP], 2),
):
    internal = slot == 3
    raw, _, _ = run(name, image(rows), 3, "error" if internal else "limit",
                    2 if internal else 3, internal)
    if slot in (1, 2):
        assert decode(raw, slot)[2] == 1
    assert raw[-16:] == b"\0" * 16

# Linux device errors, distinct from EOF.
raw, _, trace = run("input-error", b"", ticks=1, completed=1, input_path=ROOT,
                    core=instructions([NOP, (8, 65536, 0), NOP, (1, 90000, 118)]))
assert decode(raw, 1)[2] == 1
assert raw[90000 // 8] == 0x80 and "copy 0 3 1 90000 118\n" in trace
rows = [NOP, NOP, (8, 18176, 0), NOP]
raw, _, _ = run("output-error", image(rows), 3, completed=3, output_path="/dev/full")
assert decode(raw, 2)[2] == 1
raw, out, _ = run("output-full", image(rows), 3, completed=3)
assert out == b"\0" and decode(raw, 2)[2] == 16

# A later instruction sees a same-tick change to its source field.
rows = [(24, 260, 18223), NOP, NOP, (1, 90000, 65536)]
raw, _, trace = run("instruction-order", image(rows), 3, completed=3)
assert decode(raw, 3) == [1, 90000, 18223]
assert raw[90000 // 8] == 0x80
assert "copy 2 3 1 90000 18223\n" in trace

# Independent assembler bytes: crossing byte boundaries and high field bits.
rows = [(1, 3, 5), (7, 16777215, 8388608), (8388607, 65537, 32769), NOP]
assembly = "\n".join(f"copy {n} {dst} {src}" for n, dst, src in rows) + "\n"
folder = ROOT / "assembler"
folder.mkdir(exist_ok=True)
(folder / "input.copy").write_text(assembly)
actual = subprocess.run(["build/bin/assembler"], input=assembly.encode(), capture_output=True, check=True).stdout
(folder / "actual.bin").write_bytes(actual)
(folder / "expected.bin").write_bytes(instructions(rows))
assert actual == instructions(rows)
print("OK assembler: independent instruction bytes")

for value in ("-1", "abc", "1x", "18446744073709551616", ""):
    result = subprocess.run(["build/bin/space_image_proof", "--in", str(ROOT / "initial/in.bin"),
                             "--ticks", value], capture_output=True)
    assert result.returncode != 0, value
    result = subprocess.run(["build/bin/space", "--ticks", value], capture_output=True, timeout=5)
    assert result.returncode != 0, value
print("OK invalid tick arguments")

for binary in ("build/bin/space", "build/bin/space_image_proof"):
    for name in ("missing", "oversize"):
        path = ROOT / f"{name}-core.bin"
        if name == "oversize":
            path.write_bytes(bytes(SPACE_BYTES + 1))
        args = [binary, "--core", str(path), "--ticks", "0"]
        if binary.endswith("space_image_proof"):
            args += ["--in", str(ROOT / "initial/in.bin")]
        result = subprocess.run(args, capture_output=True, timeout=5)
        assert result.returncode != 0, (binary, name)
print("OK invalid core images")
