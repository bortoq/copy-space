"""Compile pinned pForth and its built-in dictionary into an RV32I IN stream."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from common import ROOT, PORT, REVISION, sources, flags

sys.path.insert(0, str(ROOT / "scripts/rv32i"))
from build import build as build_rv32i


def build(output, compiler=None, optimization="-O2", stream=True):
    header = PORT / "pfdicdat.h"
    if not header.is_file():
        raise ValueError("built-in dictionary missing; run python3 scripts/pforth/prepare.py")
    prepared = json.loads(header.with_name(header.name+".json").read_text())
    if hashlib.sha256(header.read_bytes()).hexdigest() != prepared["header_sha256"]:
        raise ValueError("built-in dictionary checksum mismatch")
    manifest = build_rv32i(sources(), output, optimization, compiler,
                           stream=stream, extra_cflags=flags())
    manifest.update({"pforth_revision": REVISION, "pforth_dictionary": prepared})
    output.resolve().with_name(output.name+".json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "tmp/pforth.stream")
    parser.add_argument("--compiler")
    parser.add_argument("--optimization", choices=["O0", "O1", "O2", "Os"], default="O2")
    parser.add_argument("--core", action="store_true", help="produce a raw initial image instead of an IN stream")
    args = parser.parse_args()
    try:
        manifest = build(args.output, args.compiler, "-"+args.optimization, not args.core)
        print(f"pForth RV32I: {args.output} ({manifest['guest_memory_bytes']} guest bytes)")
    except (OSError, ValueError) as error:
        parser.exit(1, str(error)+"\n")


if __name__ == "__main__":
    main()
