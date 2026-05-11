from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


COLS = [
    "schema_version",
    "bench",
    "mode",
    "seed",
    "space_bytes",
    "slots",
    "addr_bits",
    "ticks_total",
    "moved_bits_total",
    "vmrep_bits_sum_total",
    "vmrep_bits_uniq_dst_total",
    "vmrep_avg_bits_sum_per_tick",
    "vmrep_avg_bits_uniq_dst_per_tick",
    "thr_from",
    "thr_len",
    "thr_avg_bits_sum_per_tick",
    "thr_avg_bits_uniq_dst_per_tick",
    "notes",
    "git_rev",
    "copies_total",
    "expected_bits_per_tick",
]


def sh(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def try_git_rev() -> str:
    try:
        return sh(["git", "rev-parse", "--short", "HEAD"])
    except Exception:
        return ""


def parse_list_str(s: str) -> List[str]:
    out: List[str] = []
    for p in s.replace(",", " ").split():
        if p:
            out.append(p)
    return out


def parse_list_int(s: str, name: str) -> List[int]:
    xs = []
    for p in parse_list_str(s):
        try:
            xs.append(int(p, 0))
        except ValueError:
            raise SystemExit(f"ERROR: cannot parse int in {name}: {p}")
    if not xs:
        raise SystemExit(f"ERROR: empty list for {name}")
    return xs


def parse_list_mode(s: str) -> List[str]:
    xs = parse_list_str(s)
    if not xs:
        raise SystemExit("ERROR: empty list for --mode-list")
    for m in xs:
        if m not in ["identity", "reverse", "random", "bitrev"]:
            raise SystemExit("ERROR: unsupported mode in --mode-list: " + m)
    return xs


def find_bin(bin_dir: str, name: str) -> str:
    p = Path(bin_dir) / name
    if p.is_file():
        return str(p)
    p2 = Path(bin_dir) / (name + ".exe")
    if p2.is_file():
        return str(p2)
    raise SystemExit(f"ERROR: missing binary: {p} (run make bins, or use released native tools)")


def ceil_log2_u64(x: int) -> int:
    k = 0
    p = 1
    while p < x:
        p <<= 1
        k += 1
    return k


def round_up_to_8(x: int) -> int:
    return (x + 7) & ~7


def uN_to_be_bytes(v: int, nbytes: int) -> bytes:
    return int(v).to_bytes(nbytes, "big", signed=False)


def compute_layout(space_bytes: int, processor_n: int) -> Tuple[int, int, int, int]:
    space_bits = space_bytes * 8
    raw = ceil_log2_u64(space_bits)
    addr_bits = round_up_to_8(raw)
    if addr_bits < 8:
        addr_bits = 8
    instr_bits = 3 * addr_bits
    instr_bytes = instr_bits // 8
    processor_bits = processor_n * instr_bits

    p = processor_bits
    p += 1 * 4
    p += addr_bits
    p += addr_bits
    p += addr_bits
    p += 1 * 3
    p += addr_bits
    p += addr_bits
    p += addr_bits
    p += 1
    mmio_end = (p + 7) & ~7
    workspace_base = mmio_end
    return addr_bits, instr_bytes, processor_bits, workspace_base


def ensure_base_image(mkimage: str, base_img: str, pool_cells: int) -> None:
    p = Path(base_img)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file():
        return
    subprocess.check_call([mkimage, "--out", base_img, "--pool-cells", str(pool_cells)], stdout=subprocess.DEVNULL)


def load_image_exact(path: str, space_bytes: int) -> bytearray:
    b = Path(path).read_bytes()
    if len(b) != space_bytes:
        raise SystemExit(f"ERROR: base image size mismatch: got={len(b)} expected={space_bytes} path={path}")
    return bytearray(b)


def clear_processor(data: bytearray, processor_bits: int) -> None:
    proc_bytes = processor_bits // 8
    data[0:proc_bytes] = b"\x00" * proc_bytes


def gen_pack_image(
    base_img: str,
    out_img: str,
    space_bytes: int,
    processor_n: int,
    copies: int,
    chunk_bytes: int,
    src_stride_bytes: int,
    pad_bytes: int,
) -> None:
    addr_bits, instr_bytes, processor_bits, workspace_base = compute_layout(space_bytes, processor_n)
    w = addr_bits // 8

    if copies < 1 or copies > processor_n:
        raise SystemExit("ERROR: copies must be in [1..processor_n]")

    space_bits = space_bytes * 8
    chunk_bits = chunk_bytes * 8
    stride_bits = src_stride_bytes * 8
    pad_bits = pad_bytes * 8

    src_base = (workspace_base + pad_bits + 7) & ~7
    dst_base = (src_base + copies * stride_bits + pad_bits + 7) & ~7

    last_src = src_base + (copies - 1) * stride_bits + chunk_bits
    last_dst = dst_base + copies * chunk_bits
    if last_src > space_bits:
        raise SystemExit("ERROR: src out of space")
    if last_dst > space_bits:
        raise SystemExit("ERROR: dst out of space")

    data = load_image_exact(base_img, space_bytes)
    clear_processor(data, processor_bits)

    for i in range(copies):
        src = src_base + i * stride_bits
        dst = dst_base + i * chunk_bits
        sb = src // 8
        db = dst // 8

        for j in range(chunk_bytes):
            data[sb + j] = (i * 13 + j) & 0xFF
            data[db + j] = 0

        ins = uN_to_be_bytes(chunk_bits, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
        off = i * instr_bytes
        data[off : off + instr_bytes] = ins

    Path(out_img).write_bytes(bytes(data))


def bitrev(x: int, bits: int) -> int:
    y = 0
    for _ in range(bits):
        y = (y << 1) | (x & 1)
        x >>= 1
    return y


def gen_permute_image(
    base_img: str,
    out_img: str,
    space_bytes: int,
    processor_n: int,
    copies: int,
    chunk_bytes: int,
    pad_bytes: int,
    mode: str,
    seed: int,
) -> None:
    import random

    addr_bits, instr_bytes, processor_bits, workspace_base = compute_layout(space_bytes, processor_n)
    w = addr_bits // 8

    if copies < 1 or copies > processor_n:
        raise SystemExit("ERROR: copies must be in [1..processor_n]")

    space_bits = space_bytes * 8
    chunk_bits = chunk_bytes * 8
    pad_bits = pad_bytes * 8

    src_base = (workspace_base + pad_bits + 7) & ~7
    dst_base = (src_base + copies * chunk_bits + pad_bits + 7) & ~7

    last = dst_base + copies * chunk_bits
    if last > space_bits:
        raise SystemExit("ERROR: out of space")

    perm = list(range(copies))
    if mode == "reverse":
        perm = list(reversed(perm))
    elif mode == "random":
        rng = random.Random(seed)
        rng.shuffle(perm)
    elif mode == "bitrev":
        bits = (copies - 1).bit_length()
        perm = [bitrev(i, bits) % copies for i in range(copies)]
    elif mode == "identity":
        pass
    else:
        raise SystemExit("ERROR: unknown mode: " + mode)

    data = load_image_exact(base_img, space_bytes)
    clear_processor(data, processor_bits)

    for i in range(copies):
        src_i = perm[i]
        src = src_base + src_i * chunk_bits
        dst = dst_base + i * chunk_bits
        sb = src // 8
        db = dst // 8

        for j in range(chunk_bytes):
            data[sb + j] = (src_i * 7 + j) & 0xFF
            data[db + j] = 0

        ins = uN_to_be_bytes(chunk_bits, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
        off = i * instr_bytes
        data[off : off + instr_bytes] = ins

    Path(out_img).write_bytes(bytes(data))


def gen_bulkcopy_image(
    base_img: str,
    out_img: str,
    space_bytes: int,
    processor_n: int,
    len_bytes: int,
    pad_bytes: int,
) -> None:
    addr_bits, instr_bytes, processor_bits, workspace_base = compute_layout(space_bytes, processor_n)
    w = addr_bits // 8

    space_bits = space_bytes * 8
    pad_bits = pad_bytes * 8
    len_bits = len_bytes * 8

    src = (workspace_base + pad_bits + 7) & ~7
    dst = (src + len_bits + pad_bits + 7) & ~7

    if src + len_bits > space_bits:
        raise SystemExit("ERROR: src out of space")
    if dst + len_bits > space_bits:
        raise SystemExit("ERROR: dst out of space")

    data = load_image_exact(base_img, space_bytes)
    clear_processor(data, processor_bits)

    sb = src // 8
    db = dst // 8
    for i in range(len_bytes):
        data[sb + i] = i & 0xFF
        data[db + i] = 0

    chunk = uN_to_be_bytes(len_bits, w) + uN_to_be_bytes(dst, w) + uN_to_be_bytes(src, w)
    data[0:instr_bytes] = chunk

    Path(out_img).write_bytes(bytes(data))


def extract_vmrep_block(text: str) -> str:
    lines = text.splitlines()
    end_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if "VMREP_END" in lines[i]:
            end_idx = i
            break
    if end_idx is None:
        raise SystemExit("ERROR: cannot find VMREP_END in log")

    start_idx = end_idx
    while start_idx > 0 and lines[start_idx - 1].lstrip().startswith("[vmrep]"):
        start_idx -= 1
    if not lines[start_idx].lstrip().startswith("[vmrep]"):
        raise SystemExit("ERROR: cannot find [vmrep] prefix before VMREP_END")
    return "\n".join(lines[start_idx : end_idx + 1])


def parse_vmrep_kv(block: str) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for raw in block.splitlines():
        s = raw.strip()
        if not s.startswith("[vmrep]"):
            continue
        s = s[len("[vmrep]") :].strip()
        if not s:
            continue
        parts = s.split()
        for p in parts:
            if "=" not in p:
                continue
            k, v = p.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv


def run_vmrun_collect_log(
    vmrun: str,
    bench_img: str,
    space_bytes: int,
    processor_n: int,
    life: int,
    thr_from: int,
    thr_len: int,
    log_path: str,
    dump_path: str,
) -> None:
    env = os.environ.copy()
    env["COPYSPACE_REPORT"] = "1"
    env["COPYSPACE_REPORT_FROM"] = str(thr_from)
    env["COPYSPACE_REPORT_LEN"] = str(thr_len)

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(dump_path).parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as logf:
        p = subprocess.run(
            [
                vmrun,
                "--image",
                bench_img,
                "--space-bytes",
                str(space_bytes),
                "--processor-n",
                str(processor_n),
                "--life",
                str(life),
                "--dump",
                dump_path,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=logf,
            env=env,
            text=True,
        )
    if p.returncode != 0:
        # keep going: vmrun may exit non-zero but still emit vmrep
        pass

    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    if "[vmrep]" not in text or "VMREP_END" not in text:
        raise SystemExit("ERROR: no vmrep block in log: " + log_path)


def make_row_base(bench: str, mode: str, seed: str, space_bytes: int, processor_n: int) -> Dict[str, str]:
    space_bits = space_bytes * 8
    addr_bits = round_up_to_8(ceil_log2_u64(space_bits))
    if addr_bits < 8:
        addr_bits = 8

    row: Dict[str, str] = {c: "-" for c in COLS}
    row["schema_version"] = "csv.v0"
    row["bench"] = bench
    row["mode"] = mode
    row["seed"] = seed
    row["space_bytes"] = str(space_bytes)
    row["slots"] = str(processor_n)
    row["addr_bits"] = str(addr_bits)
    row["git_rev"] = try_git_rev()
    return row


def fill_row_from_vmrep(row: Dict[str, str], log_path: str, notes: str, copies_total: int, expected_bpt: int) -> None:
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    block = extract_vmrep_block(text)
    kv = parse_vmrep_kv(block)

    row["ticks_total"] = kv.get("ticks_total", "-")
    row["vmrep_bits_sum_total"] = kv.get("bits_sum_total", "-")
    row["vmrep_bits_uniq_dst_total"] = kv.get("bits_uniq_dst_total", "-")
    row["vmrep_avg_bits_sum_per_tick"] = kv.get("avg_bits_sum_per_tick", "-")
    row["vmrep_avg_bits_uniq_dst_per_tick"] = kv.get("avg_bits_uniq_dst_per_tick", "-")

    row["thr_from"] = kv.get("thr_from", "-")
    row["thr_len"] = kv.get("thr_len", "-")
    row["thr_avg_bits_sum_per_tick"] = kv.get("thr_avg_bits_sum_per_tick", "-")
    row["thr_avg_bits_uniq_dst_per_tick"] = kv.get("thr_avg_bits_uniq_dst_per_tick", "-")

    moved = kv.get("moved_bits_total", "") or kv.get("bits_sum_total", "")
    row["moved_bits_total"] = moved if moved else "-"

    row["notes"] = notes
    row["copies_total"] = str(copies_total)
    row["expected_bits_per_tick"] = str(expected_bpt)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Core benches (pack/permute/bulkcopy) -> unified CSV v0 (Python-first).")
    ap.add_argument("--bench", required=True, choices=["pack", "permute", "bulkcopy", "all"])
    ap.add_argument("--out", required=True, help="output CSV path (overwritten)")
    ap.add_argument("--repeat", type=int, default=1)

    ap.add_argument("--bin-dir", default="build/bin")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--tmp-dir", default="tmp")
    ap.add_argument("--pool-cells", type=int, default=32768)

    ap.add_argument("--space-bytes", type=int, default=524288)
    ap.add_argument("--processor-n", type=int, default=64)

    ap.add_argument("--thr-from", type=int, default=1000)
    ap.add_argument("--thr-len", type=int, default=5000)

    ap.add_argument("--copies-list", default="64")
    ap.add_argument("--chunk-bytes-list", default="64")
    ap.add_argument("--src-stride-bytes-list", default="4096")
    ap.add_argument("--mode-list", default="random")
    ap.add_argument("--seed-list", default="1")
    ap.add_argument("--len-bytes-list", default="65536")
    ap.add_argument("--life-list", default="20000")
    args = ap.parse_args(argv)

    if args.repeat <= 0:
        raise SystemExit("ERROR: --repeat must be > 0")
    if args.space_bytes <= 0 or args.processor_n <= 0:
        raise SystemExit("ERROR: --space-bytes and --processor-n must be > 0")

    mkimage = find_bin(args.bin_dir, "mkimage_std7_fixed")
    vmrun = find_bin(args.bin_dir, "vmrun")

    base_img = str(Path(args.out_dir) / "img_fixed_pool_big.bin")
    ensure_base_image(mkimage, base_img, args.pool_cells)

    copies_list = parse_list_int(args.copies_list, "--copies-list")
    chunk_list = parse_list_int(args.chunk_bytes_list, "--chunk-bytes-list")
    stride_list = parse_list_int(args.src_stride_bytes_list, "--src-stride-bytes-list")
    mode_list = parse_list_mode(args.mode_list)
    seed_list = parse_list_int(args.seed_list, "--seed-list")
    len_list = parse_list_int(args.len_bytes_list, "--len-bytes-list")
    life_list = parse_list_int(args.life_list, "--life-list")

    Path(os.path.dirname(args.out) or ".").mkdir(parents=True, exist_ok=True)

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLS)

        def write_row(row: Dict[str, str]) -> None:
            w.writerow([row.get(c, "-") for c in COLS])

        if args.bench in ["pack", "all"]:
            for copies in copies_list:
                for chunk_bytes in chunk_list:
                    for stride_bytes in stride_list:
                        for seed in seed_list:
                            for _ in range(args.repeat):
                                bench_img = str(Path(args.tmp_dir) / "bench_pack.bin")
                                log_path = str(Path(args.tmp_dir) / "bench_pack.log")
                                dump_path = str(Path(args.tmp_dir) / "after_pack.bin")

                                gen_pack_image(
                                    base_img=base_img,
                                    out_img=bench_img,
                                    space_bytes=args.space_bytes,
                                    processor_n=args.processor_n,
                                    copies=copies,
                                    chunk_bytes=chunk_bytes,
                                    src_stride_bytes=stride_bytes,
                                    pad_bytes=4096,
                                )

                                life = life_list[0]
                                run_vmrun_collect_log(
                                    vmrun=vmrun,
                                    bench_img=bench_img,
                                    space_bytes=args.space_bytes,
                                    processor_n=args.processor_n,
                                    life=life,
                                    thr_from=args.thr_from,
                                    thr_len=args.thr_len,
                                    log_path=log_path,
                                    dump_path=dump_path,
                                )

                                copies_total = copies
                                expected_bpt = copies * chunk_bytes * 8
                                notes = (
                                    f"COPIES={copies} CHUNK_BYTES={chunk_bytes} SRC_STRIDE_BYTES={stride_bytes} "
                                    f"SEED={seed} COPIES_TOTAL={copies_total} EXPECTED_BITS_PER_TICK={expected_bpt}"
                                )

                                row = make_row_base("pack", "pack", str(seed), args.space_bytes, args.processor_n)
                                fill_row_from_vmrep(row, log_path, notes, copies_total, expected_bpt)
                                write_row(row)

        if args.bench in ["permute", "all"]:
            for copies in copies_list:
                for chunk_bytes in chunk_list:
                    for mode in mode_list:
                        for seed in seed_list:
                            for _ in range(args.repeat):
                                bench_img = str(Path(args.tmp_dir) / "bench_permute.bin")
                                log_path = str(Path(args.tmp_dir) / "bench_permute.log")
                                dump_path = str(Path(args.tmp_dir) / "after_permute.bin")

                                gen_permute_image(
                                    base_img=base_img,
                                    out_img=bench_img,
                                    space_bytes=args.space_bytes,
                                    processor_n=args.processor_n,
                                    copies=copies,
                                    chunk_bytes=chunk_bytes,
                                    pad_bytes=4096,
                                    mode=mode,
                                    seed=seed,
                                )

                                life = life_list[0]
                                run_vmrun_collect_log(
                                    vmrun=vmrun,
                                    bench_img=bench_img,
                                    space_bytes=args.space_bytes,
                                    processor_n=args.processor_n,
                                    life=life,
                                    thr_from=args.thr_from,
                                    thr_len=args.thr_len,
                                    log_path=log_path,
                                    dump_path=dump_path,
                                )

                                copies_total = copies
                                expected_bpt = copies * chunk_bytes * 8
                                notes = (
                                    f"COPIES={copies} CHUNK_BYTES={chunk_bytes} MODE={mode} SEED={seed} "
                                    f"COPIES_TOTAL={copies_total} EXPECTED_BITS_PER_TICK={expected_bpt}"
                                )

                                row = make_row_base("permute", mode, str(seed), args.space_bytes, args.processor_n)
                                fill_row_from_vmrep(row, log_path, notes, copies_total, expected_bpt)
                                write_row(row)

        if args.bench in ["bulkcopy", "all"]:
            for len_bytes in len_list:
                for life in life_list:
                    for _ in range(args.repeat):
                        bench_img = str(Path(args.tmp_dir) / "bench_bulkcopy.bin")
                        log_path = str(Path(args.tmp_dir) / "bench_bulkcopy.log")
                        dump_path = str(Path(args.tmp_dir) / "after_bulkcopy.bin")

                        gen_bulkcopy_image(
                            base_img=base_img,
                            out_img=bench_img,
                            space_bytes=args.space_bytes,
                            processor_n=args.processor_n,
                            len_bytes=len_bytes,
                            pad_bytes=4096,
                        )

                        run_vmrun_collect_log(
                            vmrun=vmrun,
                            bench_img=bench_img,
                            space_bytes=args.space_bytes,
                            processor_n=args.processor_n,
                            life=life,
                            thr_from=args.thr_from,
                            thr_len=args.thr_len,
                            log_path=log_path,
                            dump_path=dump_path,
                        )

                        copies_total = 1
                        expected_bpt = len_bytes * 8
                        notes = f"LEN_BYTES={len_bytes} LIFE={life} COPIES_TOTAL={copies_total} EXPECTED_BITS_PER_TICK={expected_bpt}"

                        row = make_row_base("bulkcopy", "", "", args.space_bytes, args.processor_n)
                        fill_row_from_vmrep(row, log_path, notes, copies_total, expected_bpt)
                        write_row(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
