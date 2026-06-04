# Resident Orchestration Boundary

This document defines the boundary for stage `9.4`.

## Scope

Resident orchestration means:

- starting resident jobs,
- selecting resident workloads,
- passing job metadata to resident code,
- collecting job completion status,
- coordinating resident tool invocations that already live inside the address space.

Toolchain means:

- build-time generation of resident artifacts,
- translation or lowering steps that prepare resident workloads,
- launch-time bootstrap only when strictly required to enter the resident path.

## Target State

The target is a resident-controlled orchestration layer where:

- the host only boots the first resident entrypoint,
- resident code schedules and launches follow-on resident work,
- resident code owns the job lifecycle after bootstrap,
- host-side orchestration becomes bootstrap-only and then removable.

## Not In Scope

This boundary does not include:

- changes to `space.*` semantics,
- new ISA support,
- new proof goals for `space.c`,
- legacy `C3_RUN` recovery,
- `forth0` language semantics,
- unrelated service tracks,
- full compiler redesign.

## Rule

If a change is about choosing, launching, or coordinating resident work after bootstrap, it belongs here or in a child plan, not inside `space.*`.
