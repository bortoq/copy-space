"""Fast structural check of the bulk-synchronous schedule (roadmap 8.10).

Builds the base-profile image and relies on the generator's built-in
invariants (pairwise-disjoint copies per tick, processor region untouched,
patch at least two layers before its instruction) plus the budget and
format relations; no emulator needed. The io/report profiles and the
channel adapter are not part of this milestone.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
from rv32i import Layout
from rv32i_bulk import BulkImage

SPACE_BYTES = 8 * 1024 * 1024
layout = Layout(SPACE_BYTES)
image, manifest = BulkImage(memory_bytes=65536, layout=layout).build().encode(b"")
assert manifest["code_end_bit"] < layout.memory_bit, manifest["code_end_bit"]
assert manifest["instruction_bits"] == 3 * layout.address_bits - 1
assert manifest["layer_bits"] == 256 * manifest["instruction_bits"]
assert manifest["layer_count"] == manifest["code_end_bit"] // manifest["layer_bits"]
print(f"ok: bulk schedule: {manifest['layer_count']} layers, a={manifest['address_bits']}, "
      f"isz={manifest['instruction_bits']}, {len(image)} bytes")
print("OK bulk RV32I schedule invariants")
