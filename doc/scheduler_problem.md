# Scheduler problem (copy-flow / layer partitioning)

_file: doc/scheduler_problem.md_

This document describes the next major missing piece in the project:
a **copy-flow manager / scheduler** that turns a higher-level copy plan into valid tick-layers.

Today, most `.f0` programs/tests manually build schedules.
The long-term goal is to generate these schedules automatically.

---

## Problem statement

Input:
- a set of required copy operations (edges), conceptually of the form:

    src -> dst

or more generally interval copies:

    [src, src+n) -> [dst, dst+n)

Goal:
- partition the work into a sequence of **layers** (ticks),
- where each layer is valid under the execution constraints,
- and total depth / total work is small.

---

## Layer validity constraint

A layer should be **hardware-realistic**.

For the basic model, the strongest useful rule is:

- within one layer, each index of `space` participates at most once

In graph terms (for 1-bit copies):
- a layer is a set of **vertex-disjoint** directed edges

For interval copies:
- source intervals must not overlap,
- destination intervals must not overlap,
- and in practice it is best to keep `src` and `dst` disjoint inside a layer as well.

See also:
- `doc/semantics.md`

---

## Why this matters

Without a scheduler, `.f0` code must manually decide:
- which copies can happen in the same tick,
- how to avoid conflicts,
- how to implement broadcast/fanout.

This is manageable for small tests, but not for serious workloads.

A scheduler is the missing step between:
- **high-level copy intent**
and
- **valid low-level tick schedule**

---

## Broadcast / fanout problem

A common pattern is:

- one source value is needed by many destinations

Naive schedule:
- do one copy per layer
- depth = `K` for fanout `K`

Better schedule:
- build a **replication tree**
- use already-created copies as relays in later layers

This reduces depth to about:

- `ceil(log2(K+1))`

This is the key idea behind “broadcast under vertex-disjoint constraints”.

---

## Desired outputs of the scheduler

At minimum, the scheduler should produce:

1) a sequence of layers
2) each layer contains conflict-free copies
3) metadata / diagnostics:
   - layer count
   - copies per layer
   - fanout groups detected
   - relay nodes used

Optional future output:
- direct `.f0` generation,
- CSV / report for benchmark comparison,
- visual graph/layer dump.

---

## Scope for the first implementation

A good MVP would be:

1) work on simple 1-bit or fixed-size block copies
2) detect fanout groups
3) build replication trees
4) greedily pack non-conflicting edges into layers
5) emit a machine-readable schedule

This is enough to evaluate:
- schedule depth,
- bandwidth use,
- usefulness of replication trees.

---

## Non-goals for the first version

- perfect global optimality
- full support for every overlap case
- VM/ART changes

The preferred path is:
- implement the scheduler **on top of the existing forth0-first toolchain**
- keep VM/mkimage stable unless a real bottleneck is found

---

## Relation to current docs

- `doc/overview.md` mentions this as the current major gap
- `doc/semantics.md` defines the conflict model
- `doc/bench_csv_schema.md` is the natural target format for scheduler evaluation runs

