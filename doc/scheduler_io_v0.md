# Scheduler I/O v0 (public contract)

v0 is a **volume-based** contract for scheduling **directed full-mesh transfer demands** under a declared
resource model. v0 does NOT model address-level offsets inside endpoints.

Target use cases:
- Pain C: benchmarking / regression tracking for scheduling strategies
- Pain A: CI gating for schedule correctness and performance regressions

Core terms:
- slot: an endpoint participating in transfers
- tick: one discrete time step
- demand: required transfer volume from src_slot to dst_slot
- chunk: scheduled transfer performed within one tick
## Model v0

Resource model: STRICT1
- model = "STRICT1"
- Within a tick: each slot participates at most once total (as src_slot or dst_slot).
- Equivalent view: each tick is a matching over slots.

Bandwidth model:
- Instance defines copy_bw_bits_per_tick (integer > 0).
- Each chunk must satisfy: 0 < len_bits <= copy_bw_bits_per_tick.

## Instance v0 (JSON)

Required fields:
- version: 0
- model: "STRICT1"
- slots: integer > 0
- copy_bw_bits_per_tick: integer > 0
- demands: array (may be empty)

Optional fields:
- id: string
- notes: string

Demand object:
- src_slot: integer, 0 <= src_slot < slots
- dst_slot: integer, 0 <= dst_slot < slots, dst_slot != src_slot
- bits_total: integer > 0

Demands are directed. Multiple demands with the same (src_slot,dst_slot) are allowed, but producers SHOULD merge them.
Example instance:
{
  "version": 0,
  "model": "STRICT1",
  "slots": 6,
  "copy_bw_bits_per_tick": 256,
  "demands": [
    {"src_slot": 0, "dst_slot": 1, "bits_total": 4096},
    {"src_slot": 0, "dst_slot": 2, "bits_total": 2048},
    {"src_slot": 3, "dst_slot": 4, "bits_total": 4096},
    {"src_slot": 2, "dst_slot": 5, "bits_total": 1024}
  ],
  "notes": "example"
}

## Schedule v0 (JSON)

Required fields:
- version: 0
- model: "STRICT1"
- ticks: array of ticks

Tick representation:
- A tick is an array of chunks.

Chunk object:
- src_slot: integer
- dst_slot: integer, dst_slot != src_slot
- len_bits: integer, 0 < len_bits <= copy_bw_bits_per_tick

Example schedule:
{
  "version": 0,
  "model": "STRICT1",
  "ticks": [
    [
      {"src_slot":0,"dst_slot":1,"len_bits":256},
      {"src_slot":2,"dst_slot":5,"len_bits":256}
    ],
    [
      {"src_slot":0,"dst_slot":2,"len_bits":256},
      {"src_slot":3,"dst_slot":4,"len_bits":256}
    ]
  ]
}
## Validation rules (v0)

Structural (always):
- schedule.version == 0
- schedule.model == instance.model == "STRICT1"
- slot bounds: 0 <= src_slot,dst_slot < slots
- src_slot != dst_slot
- bandwidth: 0 < len_bits <= copy_bw_bits_per_tick

STRICT1 (always):
- for each tick: each slot may appear at most once across all src_slot and dst_slot.

Coverage vs demands (v0 default: REQUIRED; prevents “cheating”):
- scheduled_bits(src,dst) = sum(len_bits) over all chunks with (src_slot,dst_slot) == (src,dst)
- for each demand (src,dst,bits_total): scheduled_bits(src,dst) == bits_total
- no extras by default: any scheduled (src,dst) must appear in instance.demands

## Metrics (derived)
- ticks_total = len(ticks)
- bits_total = sum(len_bits over all chunks)
- bits_per_tick = bits_total / ticks_total (0 if ticks_total==0)
- expected_bits_per_tick = floor(slots/2) * copy_bw_bits_per_tick
- utilization = bits_per_tick / expected_bits_per_tick

Interpretation aid (lower bound):
- chunks(src,dst) = ceil(bits_total / copy_bw_bits_per_tick)
- degree(slot) = sum(chunks incident to slot, counting both in+out)
- max_degree_chunks = max_slot degree(slot)
Typically: ticks_total >= max_degree_chunks.

Non-goals (v0): no src_bit/dst_bit; no topology/path selection.