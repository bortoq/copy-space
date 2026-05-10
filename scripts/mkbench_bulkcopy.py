#!/usr/bin/env python3
import argparse, math, sys

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
    ap.add_argument("--image", required=True, help="base image (std7_fixed big)")
    ap.add_argument("--out", required=True, help="output bench image")
    ap.add_argument("--space-bytes", type=int, default=524288)
    ap.add_argument("--processor-n", type=int, default=64)
    ap.add_argument("--len-bytes", type=int, default=65536)
    ap.add_argument("--pad-bytes", type=int, default=4096)
    args = ap.parse_args()

    space_bytes = args.space_bytes
    space_bits = space_bytes * 8

    # match vm_init() logic
    raw = ceil_log2(space_bits)
    addr_bits = round_up_to_8(raw)
    if addr_bits < 8: addr_bits = 8
    n_bits = addr_bits
    instr_bits = 3 * addr_bits
    instr_bytes = instr_bits // 8
    assert instr_bits % 8 == 0

    processor_bits = args.processor_n * instr_bits
    # compute mmio layout exactly like vm_compute_mmio_layout()
    p = processor_bits
    mmio_base = p
    p += 1*4                    # in_req,in_done,in_eof,in_err
    p += addr_bits              # in_dst
    p += n_bits                 # in_len
    p += n_bits                 # in_got
    p += 1*3                    # out_req,out_done,out_err
    p += addr_bits              # out_src
    p += n_bits                 # out_len
    p += n_bits                 # out_got
    p += 1                      # halt
    mmio_end = (p + 7) & ~7
    workspace_base = mmio_end

    pad_bits = args.pad_bytes * 8
    len_bits = args.len_bytes * 8

    # choose src/dst in workspace
    src = workspace_base + pad_bits
    src = (src + 7) & ~7
    dst = src + len_bits + pad_bits
    dst = (dst + 7) & ~7

    if src + len_bits > space_bits: raise SystemExit("src out of space")
    if dst + len_bits > space_bits: raise SystemExit("dst out of space")

    # load base
    data = bytearray(space_bytes)
    with open(args.image, "rb") as f:
        b = f.read()
    data[:min(len(b), space_bytes)] = b[:space_bytes]

    # clear processor area (all NOPs)
    proc_bytes = (processor_bits // 8)
    for i in range(proc_bytes):
        data[i] = 0

    # init src pattern + clear dst
    src_b = src // 8
    dst_b = dst // 8
    for i in range(args.len_bytes):
        data[src_b + i] = i & 0xFF
        data[dst_b + i] = 0

    # write slot0 instruction bytes: n,dst,src (each addr_bits wide, big-endian)
    w = addr_bits // 8
    ins0 = uN_to_be_bytes(len_bits, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
    assert len(ins0) == instr_bytes
    data[0:instr_bytes] = ins0

    with open(args.out, "wb") as f:
        f.write(data)

    sys.stderr.write(f"mkbench_bulkcopy.py: space_bytes={space_bytes} processor_n={args.processor_n}\n")
    sys.stderr.write(f"mkbench_bulkcopy.py: addr_bits={addr_bits} instr_bytes={instr_bytes}\n")
    sys.stderr.write(f"mkbench_bulkcopy.py: workspace_base(bit)={workspace_base}\n")
    sys.stderr.write(f"mkbench_bulkcopy.py: src(byte)={src_b} dst(byte)={dst_b} len_bytes={args.len_bytes}\n")
    sys.stderr.write(f"mkbench_bulkcopy.py: slot0={data[0:instr_bytes].hex()}\n")

if __name__ == "__main__":
    main()