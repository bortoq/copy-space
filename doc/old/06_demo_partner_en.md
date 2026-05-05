# doc/06_demo_partner_en.md — Copy-Space: Deterministic Data Movement Engine — Quick Demo — 2026-05-05

## What is this?
Copy-Space is a deterministic data-movement engine.  
The only instruction: `copy(n, dst, src)` — move `n` bits from `src` to `dst` in a shared bit-addressable memory (`space`).

There is no ALU. All computation is expressed as **planned data movement**: permutations, gather/scatter, packing/compaction.

## Why it matters
Many real workloads in databases, analytics, and networking spend most of their time **moving data**, not computing:
- filter → compact surviving rows,
- reorder/partition by key,
- gather/scatter columns.

Copy-Space models this directly and measures it precisely (**bits moved per tick**), giving a foundation for hardware-oriented data-movement accelerators (Deterministic Permutation Fabric).

## Quick demo (3 commands)

### 0. Build
```sh
make bins
1. PACK — filter + compaction
Shell

COPIES=64 CHUNK_BYTES=64 SRC_STRIDE_BYTES=4096 \
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 \
scripts/bench_pack_csv.sh
2. PERMUTE — reorder / partition
Shell

COPIES=64 CHUNK_BYTES=64 MODE=random SEED=1 \
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 \
scripts/bench_permute_csv.sh
3. BULKCOPY — sustained bulk move
Shell

LEN_BYTES=65536 LIFE=20000 \
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 \
scripts/bench_bulkcopy_csv.sh
Each command prints one CSV row (unified schema v1).

Benchmark ↔ DB/Analytics mapping
Benchmark	DB / Analytics operation	What it measures
PACK	Selection scan → compaction of surviving rows/values	Gather from sparse source into dense output (like applying a selection vector)
PERMUTE	Reorder / hash-partition / sort materialization	Chunk-level permutation (reverse, random, bitrev)
BULKCOPY	Large memcpy / column copy / materialization	Peak sustained data movement (single large interval per tick)
Key metric to look at
vmrep_avg_bits_uniq_dst_per_tick — unique bits actually written per tick (steady-state throughput of useful data movement, excluding any dst-overlap / rewrites).

For PACK with COPIES=64, CHUNK_BYTES=64:
expected ≈ 64 × 64 × 8 = 32768 bits/tick — and that is exactly what the engine delivers.

Bonus: self-describing devices in memory
The engine publishes a terminal device descriptor ("CDEV" + 3 channel headers "CHN1") as data structures inside space, proving that "3 channels = 1 device" without any emulator logic.

Shell

make tdd    # look for: "OK: term0 descriptor ABI"
Links
Gather/scatter
Sorting network (used in parallel addressing demo vm1)
Selection (DB)
FPGA (potential hardware target)