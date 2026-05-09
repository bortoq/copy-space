#!/usr/bin/env python3
import json, os, random

SEED = 42
random.seed(SEED)

out_dir = "scripts/scheduler/tests/ref_pack"
os.makedirs(out_dir, exist_ok=True)

def write(name, obj):
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")

def inst(slots, bw, demands, notes=""):
    return {
        "version": 0,
        "model": "STRICT1",
        "slots": slots,
        "copy_bw_bits_per_tick": bw,
        "demands": demands,
        "notes": notes,
    }

# Keep the original 3 small examples (useful for sanity)
write("00_sparse.json", inst(8, 256, [
    {"src_slot": 0, "dst_slot": 1, "bits_total": 1024},
    {"src_slot": 2, "dst_slot": 3, "bits_total": 512},
    {"src_slot": 4, "dst_slot": 5, "bits_total": 768},
], "sparse"))

write("01_dense_star.json", inst(6, 256,
    [{"src_slot": 0, "dst_slot": i, "bits_total": 512} for i in range(1, 6)] +
    [{"src_slot": i, "dst_slot": 0, "bits_total": 256} for i in range(1, 6)],
    "dense star"
))

demands = []
for _ in range(15):
    s, t = random.sample(range(8), 2)
    demands.append({"src_slot": s, "dst_slot": t, "bits_total": random.choice([256, 512, 1024])})
write("02_random_med.json", inst(8, 256, demands, "random medium"))

# Many random instances (fixed seed, deterministic)
# We intentionally generate a moderate-size multigraph to expose order-sensitivity in maximal matching decomposition.
N = 80
SLOTS = 20
BW = 256
DEM_N = 120
BITS_CHOICES = [256, 512, 768, 1024]  # multiples of 256 except 768 => creates varied chunking patterns

for k in range(N):
    demands = []
    for _ in range(DEM_N):
        s, t = random.sample(range(SLOTS), 2)
        bits = random.choice(BITS_CHOICES)
        demands.append({"src_slot": s, "dst_slot": t, "bits_total": bits})
    # shuffle demands list: baseline is order-sensitive, greedy less so
    random.shuffle(demands)
    write(f"10_rand_{k:03d}.json", inst(SLOTS, BW, demands, f"rand seed={SEED} k={k}"))

print(f"Generated {N+3} instances in {out_dir} (seed={SEED})")
