#!/usr/bin/env python3
import json
from pathlib import Path

U32 = 0xFFFFFFFF
INT_MIN = -0x80000000


def u32(x: int) -> int:
    return x & U32


def s32(x: int) -> int:
    x &= U32
    return x if x < 0x80000000 else x - 0x100000000


def mul(a: int, b: int) -> int:
    return u32(s32(a) * s32(b))


def mulh(a: int, b: int) -> int:
    p = s32(a) * s32(b)
    return u32((p >> 32) & U32)


def mulhu(a: int, b: int) -> int:
    p = u32(a) * u32(b)
    return u32((p >> 32) & U32)


def mulhsu(a: int, b: int) -> int:
    p = s32(a) * u32(b)
    return u32((p >> 32) & U32)


def div_s(a: int, b: int) -> int:
    sa, sb = s32(a), s32(b)
    if sb == 0:
        return U32
    if sa == INT_MIN and sb == -1:
        return u32(INT_MIN)
    return u32(int(sa / sb))


def div_u(a: int, b: int) -> int:
    ua, ub = u32(a), u32(b)
    if ub == 0:
        return U32
    return u32(ua // ub)


def rem_s(a: int, b: int) -> int:
    sa, sb = s32(a), s32(b)
    if sb == 0:
        return u32(sa)
    if sa == INT_MIN and sb == -1:
        return 0
    q = int(sa / sb)
    return u32(sa - q * sb)


def rem_u(a: int, b: int) -> int:
    ua, ub = u32(a), u32(b)
    if ub == 0:
        return ua
    return u32(ua % ub)


CASES = [
    # core and prior critical cases
    (0x00000000, 0x00000000),
    (0x00000001, 0x00000001),
    (0xFFFFFFFF, 0x00000002),
    (0x80000000, 0xFFFFFFFF),
    (0x7FFFFFFF, 0x00000002),
    (0x12345678, 0x9ABCDEF0),
    (0xFFFFFFFF, 0x00000000),
    (0x80000000, 0x00000000),
    # extra edge-heavy cases for mulhsu/div/rem
    (0x80000000, 0x00000001),
    (0x80000000, 0x00000002),
    (0x7FFFFFFF, 0xFFFFFFFF),
    (0x00000003, 0xFFFFFFFE),
    (0xFFFFFFFD, 0x00000002),
    (0xFFFFFFFE, 0xFFFFFFFF),
    (0x40000000, 0x00000003),
    (0xC0000000, 0x00000003),
    (0x00000007, 0x00000003),
    (0xFFFFFFF9, 0x00000003),
    (0x80000001, 0x00000002),
    (0x7FFFFFFE, 0x00000003),
]


def row(a: int, b: int) -> dict:
    return {
        "a": u32(a),
        "b": u32(b),
        "mul": mul(a, b),
        "mulh": mulh(a, b),
        "mulhu": mulhu(a, b),
        "mulhsu": mulhsu(a, b),
        "div": div_s(a, b),
        "divu": div_u(a, b),
        "rem": rem_s(a, b),
        "remu": rem_u(a, b),
    }


def main() -> int:
    out = {
        "contract": "rv32m-v1",
        "cases": [row(a, b) for a, b in CASES],
    }
    p = Path("tmp/rv32m_vectors.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"OK rv32m vectors -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
