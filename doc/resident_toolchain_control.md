# Resident Toolchain Control

This document defines the first resident-visible toolchain control contract used by stage `9.4.9`.

## Purpose

Toolchain control is the preparation step that turns build-time artifacts into a resident-ready workload record.

## Workload Control Record

The control record is a fixed-size opaque payload:

- `artifact_id`
- `workload_id`
- `input_id`
- `output_id`
- `mode`
- `status`

All fields are stored as 32-bit little-endian words.

## Status Values

- `0` - prepared
- `1` - accepted
- `2` - materialized

## Contract

- The control record must be copyable as a blob.
- The control record must survive preparation transitions unchanged except for `status`.
- The record must be visible to resident code.
- Build-time generation stays separate from runtime orchestration.
- No toolchain control logic belongs inside `space.*`.

## Stage 9.4.9 Meaning

This step proves the data boundary for toolchain control before moving any preparation logic into resident code.
