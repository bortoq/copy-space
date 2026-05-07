# Semantics (reference)

_file: doc/semantics.md_

This document describes the intended *reference semantics* of the Copy-Space VM execution model.

The project focuses on deterministic, measurable data movement.
Determinism is easiest to reason about when programs avoid same-tick write conflicts.

---

## Terms

- **space**: one bit-addressable memory array.
- **bitaddr**: bit address inside `space`.
- **tick**: one VM cycle.
- **slot**: one instruction slot executed per tick.
- **instruction**: `copy(n, dst, src)` (copy `n` bits from `src` to `dst`).

---

## Tick execution model

A tick executes a fixed number of slots (configured by `processor_n`).

**Reference implementation behavior:**
- slots are executed in a fixed, deterministic order (by slot index),
- effects of earlier slots are visible to later slots within the same tick.

This makes the model deterministic for a given initial image and inputs.

---

## Same-tick write conflicts

A **write conflict** happens when two (or more) slots write to the same destination bit range in the same tick.

- The behavior is deterministic in the reference implementation (due to fixed slot order),
  but it is usually *undesirable* because it hides bugs and is not hardware-friendly.

**Recommended rule for programs/benchmarks (strongly suggested):**
- design schedules so that within a tick, destination ranges do not overlap.

This is also the basis for “layer” constraints (vertex-disjoint copies per tick/layer).

---

## Source/destination overlap within a single copy

If `src` and `dst` ranges overlap within the same `copy(n, dst, src)`, the result depends on the exact copy algorithm.

**Recommendation:** treat overlapping `src`/`dst` as *unsupported / avoid it* unless explicitly documented and tested.

---

## Practical scheduling guidance

For deterministic and hardware-realistic schedules:
- avoid any overlap between destinations within a tick,
- ideally also avoid using the same index as both `src` and `dst` within a tick.

Broadcast constraints (one source → many destinations) can be handled by replication trees
(spread to intermediate relays across ticks/layers).

