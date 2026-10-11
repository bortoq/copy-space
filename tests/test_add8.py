"""Complete byte-addressed LUT, independent expected sums, raw artifacts."""
import json
import random
import subprocess
from pathlib import Path

root = Path("tmp/space-tests/add8")
root.mkdir(parents=True, exist_ok=True)
add8 = subprocess.run(["../build/bin/assembler"], cwd="modules",
                      input=Path("modules/add8.copy").read_bytes(), capture_output=True, check=True).stdout
demo = subprocess.run(["../build/bin/assembler"], cwd="modules",
                      input=Path("modules/demo_add8.copy").read_bytes(), capture_output=True, check=True).stdout
halt = subprocess.run(["../build/bin/assembler"], cwd="modules",
                      input=Path("modules/halt_add8.copy").read_bytes(), capture_output=True, check=True).stdout
(root / "add8.bin").write_bytes(add8)
(root / "demo.bin").write_bytes(demo)
assert len(add8) == 418 and len(demo) == 36

payload = bytearray((524288 - 32768 + 65536 * 8) // 8)
payload[:len(add8)] = add8
halt_offset = (163840 - 32768) // 8
payload[halt_offset:halt_offset+len(halt)] = halt
payload[(65584 - 32768) // 8] = 0x10
table_offset = (524288 - 32768) // 8
for b in range(256):
    for a in range(256):
        total = (a + b) % 256
        payload[table_offset + a + 256*b] = int(f"{total:08b}"[::-1], 2)

cases = [(1, 2), (0, 3), (0, 0), (255, 0), (0, 255), (255, 1), (1, 255),
         (255, 255), (127, 1), (128, 128), (127, 128), (15, 1), (16, 16), (254, 2)]
cases += [(1 << bit, 0) for bit in range(8)]
cases += [(0, 1 << bit) for bit in range(8)]
cases += [(1 << bit, 1 << bit) for bit in range(8)]
rng = random.Random(20261011)
cases += [(rng.randrange(256), rng.randrange(256)) for _ in range(16)]
cases = list(dict.fromkeys(cases))
for a, b in cases:
    folder = root / f"{a:02x}-{b:02x}"
    folder.mkdir(exist_ok=True)
    input_file = folder / "in.bin"
    input_file.write_bytes(demo + b"\0" + payload + bytes([a, b]))
    args = ["build/bin/space_image_proof", "--in", str(input_file), "--out", str(folder / "out.bin"),
            "--dump-space", str(folder / "space.bin"), "--dump-processor", str(folder / "processor.txt"),
            "--report", str(folder / "report.txt"), "--trace", str(folder / "trace.txt"), "--ticks", "10"]
    (folder / "args.json").write_text(json.dumps(args, indent=2) + "\n")
    result = subprocess.run(args, capture_output=True)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, (a, b, result.stderr)
    got = (folder / "out.bin").read_bytes()
    expected = bytes([0, (a + b) & 255])
    assert got == expected, (a, b, got.hex(), expected.hex())
    raw = (folder / "space.bin").read_bytes()
    assert raw[65536 // 8:65536 // 8 + 2] == bytes([a, b])
    assert raw[65576 // 8] == expected[-1]
    selected_address = 524288 + (a + 256*b) * 8
    trace = (folder / "trace.txt").read_text()
    assert f"copy 3 35 8 65568 {selected_address}\n" in trace
    assert raw[:2272] == bytes(2272), "PROCESSOR must be cleared by the image"
    report = dict(line.split("=", 1) for line in (folder / "report.txt").read_text().splitlines())
    assert report["stop"] == "idle" and report["ticks"] == "5", report
    actual = subprocess.run(["build/bin/space"], input=input_file.read_bytes(), capture_output=True,
                            check=True, timeout=5).stdout
    (folder / "space.out").write_bytes(actual)
    assert actual == expected, (a, b, actual.hex())
    print(f"OK add8 {a}+{b}: OUT={got.hex()} LUT_address={selected_address}")
print(f"OK add8: {len(cases)} cases with full LUT")
