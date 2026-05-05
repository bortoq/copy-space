# Overview

Copy-Space (DPF — Deterministic Data Movement Fabric) is a small research VM where the main execution primitive is a scheduled copy:

    copy(n, dst, src)

- Memory is **bit-addressable**.
- A VM tick executes a fixed number of copy slots.
- Programs are built by composing copy operations into higher-level behavior.

This repository is focused on:
- **measurable data movement** (pack/permute/bulkcopy benchmarks),
- stable baseline images (std7_fixed),
- reproducible results and regression tests.

The goal is not to replace existing DB engines or ML accelerators.
The goal is to provide a clear and deterministic model for data movement and scheduling,
with a path to hardware-friendly execution (ASIC/FPGA feasibility discussions).

