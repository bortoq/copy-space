# Semantics (reference)

_file: doc/semantics.md_

This document describes the intended *reference semantics* of the Copy-Space execution model.

The project focuses on deterministic, measurable data movement.
In practice, determinism is easiest to reason about when programs avoid same-tick write conflicts.

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

### Reference implementation note
The current VM implementation executes slots in a fixed, deterministic way.
However, **programs should not rely on same-tick conflict resolution** as a feature.

The recommended programming model is to treat same-tick write conflicts as "invalid schedule".

---

## Same-tick write conflicts

A **write conflict** happens when two (or more) slots write to the same destination bit range in the same tick.

- The reference implementation may have deterministic behavior for conflicts,
  but conflicts are usually *undesirable* because they hide bugs and are not hardware-friendly.

### Recommended rule for programs/benchmarks
Design schedules so that within a tick:
- destination ranges do not overlap.

This is also the basis for “layer” constraints (vertex-disjoint copies per tick/layer).

---

## Source/destination overlap within a single copy

If `src` and `dst` ranges overlap within the same `copy(n, dst, src)`, the result depends on the exact copy algorithm.

### Recommendation
Treat overlapping `src`/`dst` as *unsupported / avoid it* unless explicitly documented and tested.

---

## Practical scheduling guidance

For deterministic and hardware-realistic schedules:
- avoid any overlap between destinations within a tick,
- ideally also avoid using the same index as both `src` and `dst` within a tick.

Broadcast constraints (one source → many destinations) can be handled by replication trees
(spread to intermediate relays across ticks/layers).

