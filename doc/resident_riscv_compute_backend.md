# Resident RISC-V Compute Backend

This document defines the compute-backend boundary used by stage `14`.

## Purpose

The purpose of this boundary is to let resident `RISC-V` execute small migration payloads and proof/helper workloads before orchestration is fully moved into copicode.

## Scope

This boundary may:

- run one small migration payload,
- run one proof/helper workload that benefits from resident compute,
- return machine-checkable results,
- keep host helpers bootstrap-only if they are no longer needed.

This boundary may not:

- add new `RISC-V` semantics to `space.*`,
- add orchestration logic to `space.*`,
- change the `space.*` contract,
- turn resident compute into a hidden new host layer.

## Verification Rule

The compute-backend stage is valid only if:

- resident compute is explicitly listed in the migration plan,
- the roadmap has a dedicated stage for compute-backend use,
- the active documentation map names this boundary.
