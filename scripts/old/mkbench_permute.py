#!/usr/bin/env python3
import argparse, sys, random

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

def compute_layout(space_bytes: int, processor_n: int):
    space_bits = space_bytes * 8
    raw = ceil_log2(space_bits)
    addr_bits = round_up_to_8(raw)
    if addr_bits < 8: addr_bits = 8
    n_bits = addr_bits
    instr_bits = 3 * addr_bits
    instr_bytes = instr_bits // 8

    processor_bits = processor_n * instr_bits
    p = processor_bits
    p += 1*4; p += addr_bits; p += n_bits; p += n_bits
    p += 1*3; p += addr_bits; p += n_bits; p += n_bits
    p += 1
    mmio_end = (p + 7) & ~7
    workspace_base = mmio_end
    return addr_bits, instr_bytes, processor_bits, workspace_base

def bitrev(x: int, bits: int) -> int:
    y = 0
    for _ in range(bits):
        y = (y << 1) | (x & 1)
        x >>= 1
    return y

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--space-bytes", type=int, default=524288)
    ap.add_argument("--processor-n", type=int, default=64)

    ap.add_argument("--copies", type=int, default=32)
    ap.add_argument("--chunk-bytes", type=int, default=2048)
    ap.add_argument("--pad-bytes", type=int, default=4096)

    ap.add_argument("--mode", choices=["identity","reverse","random","bitrev"], default="reverse")
    ap.add_argument("--seed", type=int, default=1)

    args = ap.parse_args()

    space_bytes = args.space_bytes
    processor_n = args.processor_n
    space_bits = space_bytes * 8

    addr_bits, instr_bytes, processor_bits, workspace_base = compute_layout(space_bytes, processor_n)
    w = addr_bits // 8

    K = args.copies
    if K < 1 or K > processor_n:
        raise SystemExit("--copies must be in [1..processor_n]")

    chunk_bits = args.chunk_bytes * 8
    pad_bits = args.pad_bytes * 8

    # src contiguous, dst contiguous
    src_base = (workspace_base + pad_bits + 7) & ~7
    dst_base = (src_base + K*chunk_bits + pad_bits + 7) & ~7

    last = dst_base + K*chunk_bits
    if last > space_bits:
        raise SystemExit("out of space (reduce copies/chunk or increase space)")

    perm = list(range(K))
    if args.mode == "reverse":
        perm = list(reversed(perm))
    elif args.mode == "random":
        rng = random.Random(args.seed)
        rng.shuffle(perm)
    elif args.mode == "bitrev":
        # only makes sense when K is power-of-two; otherwise map by bitrev mod K
        bits = (K-1).bit_length()
        perm = [bitrev(i, bits) % K for i in range(K)]

    data = bytearray(space_bytes)
    with open(args.image, "rb") as f:
        b = f.read()
    data[:min(len(b), space_bytes)] = b[:space_bytes]

    proc_bytes = processor_bits // 8
    data[0:proc_bytes] = b"\x00" * proc_bytes

    # init src, clear dst, write instructions
    for i in range(K):
        src_i = perm[i]
        src = src_base + src_i*chunk_bits
        dst = dst_base + i*chunk_bits
        sb = src//8
        db = dst//8

        for j in range(args.chunk_bytes):
            data[sb + j] = (src_i*7 + j) & 0xFF
            data[db + j] = 0

        ins = uN_to_be_bytes(chunk_bits, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
        off = i * instr_bytes
        data[off:off+instr_bytes] = ins

    with open(args.out, "wb") as f:
        f.write(data)

    sys.stderr.write(f"mkbench_permute: mode={args.mode} seed={args.seed}\n")
    sys.stderr.write(f"mkbench_permute: addr_bits={addr_bits} instr_bytes={instr_bytes}\n")
    sys.stderr.write(f"mkbench_permute: workspace_base(bit)={workspace_base}\n")
    sys.stderr.write(f"mkbench_permute: K={K} chunk_bytes={args.chunk_bytes}\n")
    sys.stderr.write(f"mkbench_permute: src_base(byte)={src_base//8} dst_base(byte)={dst_base//8}\n")
    sys.stderr.write(f"mkbench_permute: expected_bits_per_tick={K*chunk_bits}\n")
    sys.stderr.write(f"mkbench_permute: perm[0:16]={perm[:16]}\n")

if __name__ == "__main__":
    main()