"""Audit snapshot coverage and restoration in a relocated Forth dictionary."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--compiler", type=Path, default=Path("build/copy-c/compiler.stream.build/compiler32"))
parser.add_argument("--artifacts", type=Path, required=True)
options = parser.parse_args()
source = Path("runtime/copy_c/compiler.fth").read_text()
region = source[source.index("create cc-function-names "):source.index("constant cc-infer-snapshot-bytes")]
# These two arrays contain fixed arithmetic entry identifiers, not parse state.
immutable = {"cc-integer-entries", "cc-wide-entries"}
objects = []
for line in region.splitlines():
    variable = re.fullmatch(r"variable (cc-[\w-]+)", line)
    array = re.fullmatch(r"create (cc-[\w-]+) (.+) allot", line)
    if variable:
        objects.append((variable[1], "cell"))
    elif array:
        objects.append((array[1], array[2]))
    elif line.startswith("create "):
        assert line.split()[1] in immutable, line

program = b""": audit-covered ( address bytes -- ) L{ address bytes }
  cc-state-count @ 0 ?do
    cc-state-addresses i cells + @ cc-state-addresses +
    dup address <= swap cc-state-lengths i cells + @ + address bytes + >= and
    if unloop exit then
  loop ." missing state coverage" cr 2 cs-exit ;
: audit-roundtrip ( -- ) 0 0 L{ before after }
  cc-infer-snapshot-bytes allocate throw 1 (local!)
  cc-infer-snapshot-bytes allocate throw 2 (local!)
  before cc-state-save
  cc-state-count @ 0 ?do
    cc-state-addresses i cells + @ cc-state-addresses +
    cc-state-lengths i cells + @ 165 fill
  loop
  before cc-state-restore after cc-state-save
  before cc-infer-snapshot-bytes after cc-infer-snapshot-bytes compare
  if ." state restoration differs" cr 2 cs-exit then
  before free throw after free throw ;
"""
program += b"\n".join(f"{name} {size} audit-covered".encode() for name, size in objects)
program += b"\naudit-roundtrip .\" OK state snapshot\" cr bye\n"
options.artifacts.mkdir(parents=True, exist_ok=False)
(options.artifacts / "audit.fth").write_bytes(program)
(options.artifacts / "compiler.fth").write_text(source)
result = subprocess.run([str(options.compiler)], input=program, capture_output=True, timeout=30)
(options.artifacts / "stdout.txt").write_bytes(result.stdout)
(options.artifacts / "stderr.txt").write_bytes(result.stderr)
assert result.returncode == 0 and not result.stderr and b"OK state snapshot" in result.stdout, result
(options.artifacts / "evidence.json").write_text(json.dumps({
    "mutable_objects": len(objects), "all_covered": True, "full_restore_equal": True,
    "compiler_sha256": hashlib.sha256(options.compiler.read_bytes()).hexdigest(),
    "forth_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "scope": "native control interpreter; dictionary relocation and all registered bytes checked",
}, indent=2)+"\n")
print(f"OK snapshot: {len(objects)} mutable objects covered; full restore equal")
