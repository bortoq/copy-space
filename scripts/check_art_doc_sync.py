#!/usr/bin/env python3
# file: scripts/check_art_doc_sync.py
# date: 2026-05-05
# purpose: ensure doc/abi_artifacts.md matches src/mkimage/std7_fixed/artifacts.h (ART_COUNT and indices)

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def die(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(code)


def compress_ranges(nums: list[int]) -> str:
    if not nums:
        return ""
    nums = sorted(set(nums))
    out: list[str] = []
    a = b = nums[0]
    for x in nums[1:]:
        if x == b + 1:
            b = x
        else:
            out.append(f"{a}" if a == b else f"{a}-{b}")
            a = b = x
    out.append(f"{a}" if a == b else f"{a}-{b}")
    return ",".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check that artifact ABI doc contains exactly ART[0..ART_COUNT-1]."
    )
    ap.add_argument(
        "--art-h",
        default=None,
        help="Path to artifacts.h (default: repo src/mkimage/std7_fixed/artifacts.h)",
    )
    ap.add_argument(
        "--doc",
        default=None,
        help="Path to ABI doc (default: repo doc/abi_artifacts.md)",
    )
    ap.add_argument(
        "--allow-extra",
        action="store_true",
        help="Do not fail if doc mentions ART[i] for i >= ART_COUNT (warn only).",
    )
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    art_h = Path(args.art_h) if args.art_h else (repo / "src/mkimage/std7_fixed/artifacts.h")
    doc = Path(args.doc) if args.doc else (repo / "doc/abi_artifacts.md")

    if not art_h.exists():
        die(f"missing {art_h}")
    if not doc.exists():
        die(f"missing {doc}")

    htxt = art_h.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\bART_COUNT\s*=\s*(\d+)\b", htxt)
    if not m:
        die(f"cannot find 'ART_COUNT = <num>' in {art_h}")

    art_count = int(m.group(1))
    if art_count <= 0:
        die(f"bad ART_COUNT={art_count} in {art_h}")

    dtxt = doc.read_text(encoding="utf-8", errors="replace")

    missing = [i for i in range(art_count) if f"ART[{i}]" not in dtxt]
    if missing:
        die(
            f"{doc} missing indices: {compress_ranges(missing)} "
            f"(expected full range 0..{art_count-1})"
        )

    mentioned = [int(x) for x in re.findall(r"ART\[(\d+)\]", dtxt)]
    if mentioned:
        extra = sorted({i for i in mentioned if i >= art_count})
        if extra:
            msg = (
                f"{doc} mentions ART indices >= ART_COUNT ({art_count}): "
                f"{compress_ranges(extra)}"
            )
            if args.allow_extra:
                print(f"WARN: {msg}", file=sys.stderr)
            else:
                die(msg)

    print(f"OK: {doc} covers ART[0..{art_count-1}] (ART_COUNT={art_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
