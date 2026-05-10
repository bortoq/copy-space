# STRICT1 model v0 — formal baseline

_file: doc/strict1_model_v0.md_

This document defines the baseline resource model used by Copy-Space scheduler v0.

Related contract:
- doc/scheduler_io_v0.md

----------------------------------------------------------------

## 1. Objects

### Slot
A slot is an endpoint that can participate in transfers.

Slots are identified by integers:

    0 <= slot < slots

where slots is declared by the instance.

### Demand
A demand is a directed transfer volume:

    (src_slot, dst_slot, bits_total)

Validity requirements:

    0 <= src_slot < slots
    0 <= dst_slot < slots
    src_slot != dst_slot
    bits_total > 0

Multiple demands with the same (src_slot, dst_slot) are allowed by the v0 JSON contract.
For model-level reasoning, they are treated as one aggregated demand:

    demand_bits_total(src,dst) = sum(bits_total for all demands with the same src,dst)

### Chunk
A chunk is one scheduled transfer performed within one tick:

    (src_slot, dst_slot, len_bits)

Validity requirements:

    0 <= src_slot < slots
    0 <= dst_slot < slots
    src_slot != dst_slot
    0 < len_bits <= copy_bw_bits_per_tick

### Tick
A tick is one discrete time step.

A schedule consists of an ordered list of ticks:

    ticks[0], ticks[1], ..., ticks[T-1]

where each tick is a list of chunks.

----------------------------------------------------------------

## 2. Resource model: STRICT1

STRICT1 means:

  Within a single tick, each slot may participate at most once total,
  either as a source or as a destination.

Equivalently, each tick is a matching over slots.

Formal statement: for every tick k, for any two distinct chunks a and b in that tick:

    {a.src_slot, a.dst_slot} ∩ {b.src_slot, b.dst_slot} = ∅

This forbids, within the same tick:
- two outgoing transfers from the same slot
- two incoming transfers to the same slot
- one incoming and one outgoing transfer involving the same slot

----------------------------------------------------------------

## 3. Bandwidth model

The instance declares:

    copy_bw_bits_per_tick > 0

Every scheduled chunk must satisfy:

    0 < len_bits <= copy_bw_bits_per_tick

There is no separate per-direction or global fabric bandwidth limit in v0 beyond STRICT1 and per-chunk bandwidth.

----------------------------------------------------------------

## 4. Schedule validity (instance + schedule)

A schedule is valid for an instance if all of the following hold.

### 4.1 Structural validity

    schedule.version == 0
    schedule.model == instance.model == "STRICT1"
    all slots are in bounds
    all chunks have src_slot != dst_slot
    all chunks satisfy bandwidth bounds

### 4.2 STRICT1 validity
Every tick satisfies the STRICT1 matching constraint.

### 4.3 Coverage validity (v0 default)
For every directed pair (src,dst):

    scheduled_bits(src,dst) = sum(len_bits for all chunks with that src,dst)

The v0 default contract requires exact coverage:

    scheduled_bits(src,dst) == demand_bits_total(src,dst)

for every demanded pair.

It also forbids extras:

    scheduled_bits(src,dst) > 0  =>  demand_bits_total(src,dst) > 0

----------------------------------------------------------------

## 5. Derived metrics

### Basic metrics

    ticks_total = number of ticks
    bits_total = sum(len_bits over all chunks)
    bits_per_tick = bits_total / ticks_total   (0 if ticks_total == 0)
    expected_bits_per_tick = floor(slots / 2) * copy_bw_bits_per_tick
    utilization = bits_per_tick / expected_bits_per_tick

### Lower bound

For each aggregated demand:

    chunks(src,dst) = ceil(demand_bits_total(src,dst) / copy_bw_bits_per_tick)

For each slot:

    degree(slot) = sum(chunks incident to slot, counting both in+out)

The STRICT1 lower bound is:

    lower_bound_ticks = max_slot degree(slot)

Any valid STRICT1 schedule must satisfy:

    ticks_total >= lower_bound_ticks

### Gap to lower bound

    gap_ticks = ticks_total - lower_bound_ticks
    gap_to_lower_bound = gap_ticks / lower_bound_ticks

If lower_bound_ticks == 0, then:

    gap_to_lower_bound = 0

Interpretation: gap_to_lower_bound is a deterministic model-level metric for how far the schedule is from the lower bound.

----------------------------------------------------------------

## 6. Non-goals in v0

STRICT1 v0 does not model:
- address-level offsets inside endpoints (src_bit, dst_bit)
- topology/path selection
- broadcast/fanout within one tick
- "1 read + 1 write per tick" endpoint semantics
- global optimality claims
