# Resident Copicode Decision Records

This document defines the orchestration decision record used by stage `10.3.3`.

## Purpose

The decision record captures the resident orchestration choice without adding orchestration logic to `space.*`.

## Record Format

The decision record is a fixed-size opaque payload:

- `artifact_id`
- `job_id`
- `decision_id`
- `selector`
- `status`

All fields are stored as 32-bit little-endian words.

## Status Values

- `0` - prepared
- `1` - recorded
- `2` - committed

## Contract

- The decision record must be copyable as a blob.
- The decision record must survive state transitions unchanged except for `status`.
- The decision record must be visible to resident code.
- The contract must not add orchestration logic to `space.*`.

## Stage 10.3.3 Meaning

This step proves that orchestration decisions can be represented as resident copicode records before migration of the execution logic itself.
