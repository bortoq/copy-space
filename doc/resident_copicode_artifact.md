# Resident Copicode Artifact

This document defines the first artifact format used by stage `10.3.1`.

## Purpose

The artifact is the resident-ready blob that carries copicode payloads through the bootstrap boundary.

## Format

The artifact is a fixed-size opaque record:

- `artifact_id`
- `payload_id`
- `entry`
- `size`
- `flags`
- `status`

All fields are stored as 32-bit little-endian words.

## Status Values

- `0` - prepared
- `1` - loaded
- `2` - handoff-ready

## Contract

- The artifact must be copyable as a blob.
- The artifact must survive load/handoff transitions unchanged except for `status`.
- The artifact must be visible to resident code.
- The artifact must not add orchestration logic to `space.*`.

## Stage 10.3.1 Meaning

This step proves the artifact boundary for resident copicode before any execution migration work begins.
