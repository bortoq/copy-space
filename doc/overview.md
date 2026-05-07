# Overview

_file: doc/overview.md_

Copy-Space (DPF — Deterministic Data Movement Fabric) is a small research VM where the main execution primitive is a scheduled copy:

    copy(n, dst, src)

The goal is not to replace existing DB engines or ML accelerators.
The goal is to provide a clear and deterministic model for data movement and scheduling,
with a path to hardware-friendly execution (ASIC/FPGA feasibility discussions).

---

## Core execution model (very short)

### Memory model
- There is one memory array called `space`.
- Addressing is **bit-based** (`bitaddr`), so memory is bit-addressable.

### Instruction model
Each instruction slot is a copy:

    copy(n, dst, src)

Meaning: copy `n` bits from `src` to `dst` inside `space`.

A VM tick executes a fixed number of instruction slots (processor slots).

### Determinism and conflicts
Given the same initial image and the same input, results are deterministic.
However, deterministic does not mean “safe”: same-tick write conflicts can hide bugs.

See:
- `semantics.md`

---

## Baseline image: std7_fixed and ART (ABI)
The baseline image publishes key addresses through an artifacts table (ART).
ART is the ABI contract for tools and programs.

See:
- `abi_artifacts.md`

---

## Forth0-first workflow (recommended)
Most tests and higher-level logic in this repo are written as `.f0` programs compiled by `forth0c`.

See:
- `forth0.md`
- `forth0_howto.md`
- `testing.md`

---

## Current gap: flow control / scheduling layer partitioner
Today, Forth0 is used mainly as a *host-compiled DSL* to build specific schedules and tests.

What is still missing (design work):
- A “copy-flow manager” / control layer that owns higher-level copy plans.
- Automatic partitioning of copies into tick-layers under a constraint such as:
  “within one tick/layer, each space index participates at most once”
  (vertex-disjoint / no-overlap dst, and usually no overlap src).
- Replication trees for broadcast (one source → many destinations) under fanout constraints.

This is a major upcoming design step and should be implemented *using Forth0* (not by expanding ART),
but it needs a clear interface and a stable layer model.

---

## Stability / guarantees
See:
- `stability.md`

---

## Quickstart
See:
- `quickstart.md`

---

## Why DB/analytics may care (high-level)
Many pipelines are dominated by moving bytes, not computing:
- compaction after filter (selection vectors)
- reorder / partition (hash partitioning, sort preparation, materialization)
- bulk buffer movement (DMA-like)

The repo includes benchmarks (`benchmarks.md`) that output CSV metrics.

