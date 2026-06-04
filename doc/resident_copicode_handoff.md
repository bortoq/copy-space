# Resident Copicode Handoff

This document defines the handoff contract used by stage `10.3.2`.

## Purpose

The handoff contract defines how a prepared resident copicode artifact becomes resident handoff-ready without adding orchestration logic to `space.*`.

## Handoff Record

The handoff record is a fixed-size opaque payload:

- `artifact_id`
- `entry`
- `handoff_id`
- `generation`
- `status`

All fields are stored as 32-bit little-endian words.

## Status Values

- `0` - prepared
- `1` - loading
- `2` - handoff-ready

## Contract

- The handoff record must be copyable as a blob.
- The handoff record must survive state transitions unchanged except for `status`.
- The handoff record must be visible to resident code.
- The contract must not add orchestration logic to `space.*`.

## Stage 10.3.2 Meaning

This step proves the handoff boundary between artifact preparation and resident-ready execution.
