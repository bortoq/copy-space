# Overview

_file: doc/overview.md_

Copy-Space is a deterministic toolkit for validated scheduling of data movement.

This repository contains two layers:

1) Scheduler v0 toolkit (pilot-facing, recommended)
- Purpose: correctness gating and reproducible metrics for transfer schedules under a strict resource model.
- Interfaces:
  - CLI: copyspace-validate, copyspace-solve, copyspace-pilot
  - Contracts: doc/scheduler_io_v0.md, doc/strict1_model_v0.md
  - Partner path: doc/partners/quickstart_pilot.md and doc/partners/ci_gate_recipe.md

2) DPF VM and toolchain (under the hood)
- Purpose: a small research VM for deterministic data-movement experiments and hardware-feasibility discussion.
- Includes: baseline image (std7_fixed), native tools, Forth0-first test workflow, and VM-level benchmarks.

If you are evaluating Copy-Space as a validated scheduling tool for CI gating or regression tracking,
start with the Scheduler v0 toolkit and the partner docs. You do not need to build the VM toolchain to start.

------------------------------------------------------------

## Scheduler v0 (recommended for pilots)

Scheduler v0 solves and validates schedules for directed transfer demands:

- Input: instance.json (directed demands src_slot -> dst_slot with bits_total)
- Output: schedule.json plus a validator report with metrics

The model is STRICT1:
- each slot may participate in at most one copy per tick (as src or dst)

See:
- doc/scheduler_io_v0.md
- doc/strict1_model_v0.md
- doc/partners/quickstart_pilot.md

------------------------------------------------------------

## DPF VM (under the hood)

The DPF VM is a small deterministic execution model where the main primitive is a scheduled copy:

    copy(n, dst, src)

Very short model sketch:

Memory model
- One memory array called space (bit-addressable).
- Addressing is bit-based (bitaddr).

Instruction model
- Each instruction slot is a copy(n, dst, src).
- A VM tick executes a fixed number of instruction slots (copy slots).

Determinism and conflicts
- Given the same initial image and the same input, results are deterministic.
- Deterministic does not mean safe: same-tick write conflicts can hide bugs.

See:
- doc/semantics.md
- doc/stability.md

------------------------------------------------------------

## Baseline image: std7_fixed and ART (ABI)

The baseline image publishes key addresses through an artifacts table (ART).
ART is the ABI contract for tools and programs.

See:
- doc/abi_artifacts.md
- doc/memory_layout.md
- doc/devices.md

------------------------------------------------------------

## Forth0-first workflow (under the hood)

Most VM-level tests and higher-level logic in this repository are written as Forth0 programs compiled by forth0c.

See:
- doc/forth0.md
- doc/forth0_howto.md
- doc/testing.md
