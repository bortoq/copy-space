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
    # IN
    p += 1*4
    p += addr_bits
    p += n_bits
    p += n_bits
    # OUT
    p += 1*3
    p += addr_bits
    p += n_bits
    p += n_bits
    # HALT
    p += 1
    mmio_end = (p + 7) & ~7
    workspace_base = mmio_end
    return addr_bits, instr_bytes, processor_bits, workspace_base

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--space-bytes", type=int, default=524288)
    ap.add_argument("--processor-n", type=int, default=64)

    ap.add_argument("--copies", type=int, default=32)          # how many active slots
    ap.add_argument("--chunk-bytes", type=int, default=2048)   # bytes per copy
    ap.add_argument("--src-stride-bytes", type=int, default=8192)
    ap.add_argument("--pad-bytes", type=int, default=4096)

    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--src-randomize", action="store_true",
                    help="pick random src chunk indices (still non-overlapping if stride>=chunk)")

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
    src_stride_bits = args.src_stride_bytes * 8
    pad_bits = args.pad_bytes * 8

    # layout:
    # src_base: K chunks placed with src_stride (sparse)
    # dst_base: K chunks placed contiguously (packed)
    src_base = (workspace_base + pad_bits + 7) & ~7
    dst_base = (src_base + K*src_stride_bits + pad_bits + 7) & ~7

    # bounds (worst case)
    last_src = src_base + (K-1)*src_stride_bits + chunk_bits
    last_dst = dst_base + K*chunk_bits
    if last_src > space_bits: raise SystemExit("src out of space (increase space or reduce K/stride/chunk)")
    if last_dst > space_bits: raise SystemExit("dst out of space (increase space or reduce K/chunk)")

    data = bytearray(space_bytes)
    with open(args.image, "rb") as f:
        b = f.read()
    data[:min(len(b), space_bytes)] = b[:space_bytes]

    # clear processor bytes
    proc_bytes = processor_bits // 8
    data[0:proc_bytes] = b"\x00" * proc_bytes

    # choose mapping dst_i <- src_{perm[i]}
    perm = list(range(K))
    if args.src_randomize:
        rng = random.Random(args.seed)
        rng.shuffle(perm)

    # init src chunks (patterns) and clear dst
    for i in range(K):
        src_idx = perm[i]
        src = src_base + src_idx*src_stride_bits
        dst = dst_base + i*chunk_bits
        sb = src // 8
        db = dst // 8

        # fill src with identifiable bytes, clear dst
        for j in range(args.chunk_bytes):
            data[sb + j] = (src_idx*13 + j) & 0xFF
            data[db + j] = 0

        # instruction in slot i: copy(chunk_bits, dst, src)
        ins = uN_to_be_bytes(chunk_bits, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
        off = i * instr_bytes
        data[off:off+instr_bytes] = ins

    with open(args.out, "wb") as f:
        f.write(data)

    sys.stderr.write(f"mkbench_pack: addr_bits={addr_bits} instr_bytes={instr_bytes}\n")
    sys.stderr.write(f"mkbench_pack: workspace_base(bit)={workspace_base}\n")
    sys.stderr.write(f"mkbench_pack: K={K} chunk_bytes={args.chunk_bytes} src_stride_bytes={args.src_stride_bytes}\n")
    sys.stderr.write(f"mkbench_pack: src_base(byte)={src_base//8} dst_base(byte)={dst_base//8}\n")
    sys.stderr.write(f"mkbench_pack: expected_bits_per_tick={K*chunk_bits}\n")
    if args.src_randomize:
        sys.stderr.write(f"mkbench_pack: perm[0:16]={perm[:16]}\n")

if __name__ == "__main__":
    main()