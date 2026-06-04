# Resident Job Selection

This document defines the first resident-visible selection rule used by stage `9.4.6`.

## Purpose

Job selection is the rule that chooses which descriptor from a resident-visible table becomes the next active job.

## Selection Rule

- Scan the table in order.
- Skip descriptors with `kind == 0`.
- Select the first descriptor whose `flags & 1u` is non-zero.
- If no descriptor matches, return `none`.

## Contract

- The selection rule must be deterministic.
- The selection rule must operate on resident-visible data only.
- The selection rule must not introduce orchestration semantics into `space.*`.
- The selection rule must be encoded as data-contract behavior first, then later as resident execution.

## Stage 9.4.6 Meaning

This step proves the contract boundary for selection before moving selection logic into resident code.
