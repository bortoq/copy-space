# Resident Tool Invocation

This document defines the first resident-visible tool invocation contract used by stage `9.4.7`.

## Purpose

Tool invocation is the transition from a selected job to a launched job and back to a completed job record.

## Invocation Record

The invocation record is a fixed-size opaque payload:

- `job_id`
- `tool_id`
- `entry`
- `arg0`
- `arg1`
- `status`

All fields are stored as 32-bit little-endian words.

## Status Values

- `0` - prepared
- `1` - launched
- `2` - completed

## Contract

- The invocation record must be copyable as a blob.
- The invocation record must survive launch/complete transitions unchanged except for `status`.
- The record must be visible to resident code.
- The contract must not add orchestration logic to `space.*`.

## Stage 9.4.7 Meaning

This step proves the data boundary for tool invocation before moving any invocation logic into resident code.
