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

    ap.add_argument("--copies", type=int, default=8, help="number of active slots (<=processor_n)")
    ap.add_argument("--chunk-bytes", type=int, default=8192, help="bytes copied per slot")
    ap.add_argument("--src-stride-bytes", type=int, default=16384, help="distance between src chunks")
    ap.add_argument("--pad-bytes", type=int, default=4096)

    args = ap.parse_args()

    space_bytes = args.space_bytes
    space_bits = space_bytes * 8

    raw = ceil_log2(space_bits)
    addr_bits = round_up_to_8(raw)
    if addr_bits < 8: addr_bits = 8
    n_bits = addr_bits
    instr_bits = 3 * addr_bits
    instr_bytes = instr_bits // 8
    assert instr_bits % 8 == 0

    processor_bits = args.processor_n * instr_bits
    # MMIO layout exactly like vm_compute_mmio_layout()
    p = processor_bits
    p += 1*4            # in_req,in_done,in_eof,in_err
    p += addr_bits      # in_dst
    p += n_bits         # in_len
    p += n_bits         # in_got
    p += 1*3            # out_req,out_done,out_err
    p += addr_bits      # out_src
    p += n_bits         # out_len
    p += n_bits         # out_got
    p += 1              # halt
    mmio_end = (p + 7) & ~7
    workspace_base = mmio_end

    copies = args.copies
    if copies < 1 or copies > args.processor_n:
        raise SystemExit("--copies must be in [1..processor_n]")

    chunk_bits = args.chunk_bytes * 8
    pad_bits = args.pad_bytes * 8
    src_stride_bits = args.src_stride_bytes * 8

    # layout: src_base ... scattered chunks ... gap ... dst_base ... packed chunks
    src_base = (workspace_base + pad_bits + 7) & ~7
    dst_base = (src_base + copies * src_stride_bits + pad_bits + 7) & ~7

    # bounds check
    last_src = src_base + (copies-1)*src_stride_bits + chunk_bits
    last_dst = dst_base + copies*chunk_bits
    if last_src > space_bits: raise SystemExit("src out of space")
    if last_dst > space_bits: raise SystemExit("dst out of space")

    # load base image
    data = bytearray(space_bytes)
    with open(args.image, "rb") as f:
        b = f.read()
    data[:min(len(b), space_bytes)] = b[:space_bytes]

    # clear processor area
    proc_bytes = processor_bits // 8
    for i in range(proc_bytes):
        data[i] = 0

    w = addr_bits // 8

    # init src patterns and clear dst
    for i in range(copies):
        src = src_base + i*src_stride_bits
        dst = dst_base + i*chunk_bits
        sb = src//8
        db = dst//8

        # src: different pattern per chunk
        for j in range(args.chunk_bytes):
            data[sb + j] = (i*17 + j) & 0xFF
            data[db + j] = 0

        # write slot i instruction: n,dst,src
        ins = uN_to_be_bytes(chunk_bits, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
        off = i * instr_bytes
        data[off:off+instr_bytes] = ins

    with open(args.out, "wb") as f:
        f.write(data)

    sys.stderr.write(f"mkbench_multicopy: addr_bits={addr_bits} instr_bytes={instr_bytes}\n")
    sys.stderr.write(f"mkbench_multicopy: workspace_base(bit)={workspace_base}\n")
    sys.stderr.write(f"mkbench_multicopy: copies={copies} chunk_bytes={args.chunk_bytes} src_stride_bytes={args.src_stride_bytes}\n")
    sys.stderr.write(f"mkbench_multicopy: src_base(byte)={src_base//8} dst_base(byte)={dst_base//8}\n")
    sys.stderr.write(f"mkbench_multicopy: expected_bits_per_tick={copies*chunk_bits}\n")

if __name__ == "__main__":
    main()