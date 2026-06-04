# Resident RISC-V Proof Tools Preparation

This document defines the preparation boundary used by stage `13`.

## Purpose

Prepare `rv32_space_*` proof tools for later resident execution without turning them into resident workloads yet.

## Scope

This preparation boundary may:

- split proof claims into one gate per claim,
- remove mixed claims from a single proof gate,
- remove synthetic-trace dependencies,
- remove host-authored-state dependencies,
- define resident-ready payload formats for later use.

This preparation boundary may not:

- introduce new `RISC-V` semantics,
- move proof execution into resident code yet,
- add orchestration logic to `space.*`,
- change the `space.*` contract.

## Verification Rule

The preparation stage is valid only if:

- the proof tools are described as resident-ready, not resident-executing,
- the documentation map includes this boundary,
- the roadmap marks stage `13` as preparation only.
