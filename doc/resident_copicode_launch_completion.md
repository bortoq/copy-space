# Resident Copicode Launch Completion

This document defines the launch-completion record used by stage `10.3.5`.

## Purpose

The launch-completion record captures the final resident launch state without adding launch logic to `space.*`.

## Record Format

The launch-completion record is a fixed-size opaque payload:

- `artifact_id`
- `launch_id`
- `completion_id`
- `entry`
- `status`

All fields are stored as 32-bit little-endian words.

## Status Values

- `0` - prepared
- `1` - launched
- `2` - completed

## Contract

- The record must be copyable as a blob.
- The record must survive launch transitions unchanged except for `status`.
- The record must be visible to resident code.
- The contract must not add launch logic to `space.*`.

## Stage 10.3.5 Meaning

This step proves that resident launch completion can be represented as copicode data before any execution logic is migrated.
