#!/usr/bin/env python3
# file: scripts/gen_abi_artifacts_doc.py
# date: 2026-05-05
# purpose: generate doc/abi_artifacts.md from src/mkimage/std7_fixed/artifacts.h

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


def strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


def find_enum_bodies(txt: str) -> list[str]:
    t = strip_c_comments(txt)
    pat = re.compile(r"\benum\b[^{}]*\{(.*?)\}\s*[^;]*;", flags=re.S)
    return [m.group(1) for m in pat.finditer(t)]


def parse_art_enum(art_h_text: str) -> tuple[int, dict[int, list[str]]]:
    t = strip_c_comments(art_h_text)

    m = re.search(r"\bART_COUNT\s*=\s*(0x[0-9a-fA-F]+|\d+)\b", t)
    if not m:
        raise ValueError("cannot find 'ART_COUNT = <num>' in artifacts.h")
    art_count = int(m.group(1), 0)

    bodies = find_enum_bodies(art_h_text)
    if not bodies:
        raise ValueError("cannot find any enum block in artifacts.h")

    body = None
    for b in bodies:
        if "ART_COUNT" in b or re.search(r"\bART_[A-Za-z0-9_]+\b", b):
            body = b
            break
    if body is None:
        raise ValueError("found enum blocks, but none contain ART_* or ART_COUNT")

    items = [x.strip() for x in body.split(",")]
    items = [x for x in items if x]

    idx_to_names: dict[int, list[str]] = {}
    cur_val: int | None = None

    for it in items:
        m = re.match(r"^([A-Za-z_]\w*)(?:\s*=\s*(0x[0-9a-fA-F]+|\d+))?\s*$", it)
        if not m:
            continue
        name = m.group(1)
        if name == "ART_COUNT":
            continue
        if not name.startswith("ART_"):
            continue

        if m.group(2) is not None:
            cur_val = int(m.group(2), 0)
        else:
            cur_val = 0 if cur_val is None else (cur_val + 1)

        idx_to_names.setdefault(cur_val, []).append(name)

    return art_count, idx_to_names


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate artifact ABI doc from artifacts.h")
    ap.add_argument("--art-h", default=None, help="path to artifacts.h")
    ap.add_argument("--out", default=None, help="output markdown path")
    ap.add_argument("--date", default=None, help="date YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    art_h = Path(args.art_h) if args.art_h else (repo / "src/mkimage/std7_fixed/artifacts.h")
    outp = Path(args.out) if args.out else (repo / "doc/abi_artifacts.md")

    dstr = args.date if args.date else date.today().isoformat()

    htxt = art_h.read_text(encoding="utf-8", errors="replace")
    art_count, idx_to_names = parse_art_enum(htxt)

    meanings_by_idx = {
        43: "TESTG policy: TESTG == TESTSCR_BASE",
        63: "TESTSCR_BASE (standardized test scratch base)",
        64: "TESTSCR_END (1 past end)",
        65: "BUS_BASE (devices bus base)",
        66: "TERM0_DESC (terminal device descriptor address)",
        67: "WORD_LOAD24AP (block-pointer primitive)",
        68: "WORD_LOAD24BP (block-pointer primitive)",
        69: "WORD_STORE24RP (block-pointer primitive)",
    }

    lines: list[str] = []
    lines.append(f"# doc/abi_artifacts.md — ABI: std7_fixed artifacts table (ART) — {dstr}")
    lines.append("")
    lines.append("This document is generated from `src/mkimage/std7_fixed/artifacts.h`.")
    lines.append("")
    lines.append("## Rules")
    lines.append("- ABI is **append-only**: new entries are added only at the end (ART_COUNT increases).")
    lines.append("- ART values are **bitaddrs** (bit addresses in `space`).")
    lines.append("- Convert to byte offset: `byte = bitaddr / 8`.")
    lines.append("")
    lines.append("## ART table")
    lines.append(f"`ART_COUNT = {art_count}` (valid indices: 0..{art_count - 1})")
    lines.append("")
    lines.append("| Index | Enum name(s) | Meaning |")
    lines.append("|---:|---|---|")

    for i in range(art_count):
        names = idx_to_names.get(i, [])
        names_str = ", ".join(names) if names else "(reserved)"
        meaning = meanings_by_idx.get(i, "")
        # IMPORTANT: keep literal "ART[i]" for scripts/check_art_doc_sync.py
        lines.append(f"| ART[{i}] | `{names_str}` | {meaning} |")

    lines.append("")
    lines.append("## Notes")
    lines.append("- `ART(byte)=...` is printed by `mkimage_std7_fixed` to stderr and is the byte offset of ART in `space`.")
    lines.append("- ART entry width is `ADDR_BITS` (typically 24 → 3 bytes per entry).")

    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: wrote {outp} (ART_COUNT={art_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
