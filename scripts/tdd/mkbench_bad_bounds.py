#!/usr/bin/env python3
import argparse, sys

def ceil_log2(x: int) -> int:
    k = 0
    p = 1
    while p < x:
        p <<= 1
        k += 1
    return k

def round_up_to_8(x: int) -> int:
    return (x + 7) & ~7

def uN_to_be_bytes(v: int, nbytes: int) -> bytes:
    return v.to_bytes(nbytes, "big", signed=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--space-bytes", type=int, default=524288)
    ap.add_argument("--processor-n", type=int, default=64)
    args = ap.parse_args()

    space_bytes = args.space_bytes
    space_bits = space_bytes * 8

    raw = ceil_log2(space_bits)
    addr_bits = round_up_to_8(raw)
    if addr_bits < 8: addr_bits = 8
    instr_bits = 3 * addr_bits
    instr_bytes = instr_bits // 8
    processor_bits = args.processor_n * instr_bits
    proc_bytes = processor_bits // 8
    w = addr_bits // 8

    data = bytearray(space_bytes)
    with open(args.image, "rb") as f:
        b = f.read()
    data[:min(len(b), space_bytes)] = b[:space_bytes]

    # Clear processor area
    data[0:proc_bytes] = b"\x00" * proc_bytes

    # Make slot0: copy(n=64, dst=space_bits-16, src=0) => dst+n > space_bits => VM_ERR
    n = 64
    dst = space_bits - 16
    src = 0

    ins0 = uN_to_be_bytes(n, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
    data[0:instr_bytes] = ins0

    with open(args.out, "wb") as f:
        f.write(data)

    sys.stderr.write(f"mkbench_bad_bounds: addr_bits={addr_bits} instr_bytes={instr_bytes}\n")
    sys.stderr.write(f"mkbench_bad_bounds: n={n} dst={dst} src={src} (should fail bounds)\n")

if __name__ == "__main__":
    main()