"""Compare field packing with independent bits and an optional old compiler."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--native-reference", type=Path)
parser.add_argument("--artifacts", type=Path, default=Path("tmp/space-tests/copy-c-bitpack"))
options = parser.parse_args()
root = options.artifacts
root.mkdir(parents=True, exist_ok=True)
commands = [b"create block 16 allot\n"]
expected, cases = bytearray(), []
values = (0, 0xffffffff, 0x80000001, 0xa5c33c5a)
for value in values:
    for width in range(33):
        for offset in range(8):
            position = 16+offset
            buffer = bytearray([165]*16)
            for bit in range(width):
                at = position+bit
                mask = 1 << (7-at%8)
                buffer[at//8] = (buffer[at//8] & ~mask) | (((value >> bit) & 1) << (7-at%8))
            expected.extend(buffer)
            cases.append([value, width, position])
            commands.append(f"block 16 165 fill {value} {width} {position} block cc-bits! block 16 cs-write drop\n".encode())
commands.append(b"0 cs-exit\n")
data = b"".join(commands)
(root / "in.fth").write_bytes(data)
(root / "expected.out").write_bytes(expected)
programs = [("new", Path("build/copy-c/compiler.stream.build/compiler32"))]
if options.native_reference:
    programs.append(("old", options.native_reference))
signatures = {}
for name, program in programs:
    result = subprocess.run([str(program)], input=data, capture_output=True, timeout=30)
    (root / (name+".out")).write_bytes(result.stdout)
    (root / (name+".stderr")).write_bytes(result.stderr)
    assert result.returncode == 0 and not result.stderr and result.stdout == expected, name
    signatures[name] = hashlib.sha256(program.read_bytes()).hexdigest()
(root / "evidence.json").write_text(json.dumps({
    "cases": len(cases), "values": values, "widths": list(range(33)),
    "offsets": list(range(8)), "compiler_sha256": signatures,
    "output_sha256": hashlib.sha256(expected).hexdigest(),
    "environment": "native packing comparison; guest execution is verified separately",
}, indent=2)+"\n")
print(f"OK copy-c bit packing: {len(cases)} cases equal independent bits")
