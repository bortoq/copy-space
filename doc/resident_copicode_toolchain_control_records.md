# Resident Copicode Toolchain Control Records

This document defines the toolchain control record used by stage `10.3.4`.

## Purpose

The control record captures resident toolchain control without adding toolchain logic to `space.*`.

## Record Format

The control record is a fixed-size opaque payload:

- `artifact_id`
- `toolchain_id`
- `control_id`
- `stage`
- `mode`
- `status`

All fields are stored as 32-bit little-endian words.

## Status Values

- `0` - prepared
- `1` - control-recorded
- `2` - materialized

## Contract

- The control record must be copyable as a blob.
- The control record must survive state transitions unchanged except for `status`.
- The control record must be visible to resident code.
- The contract must not add toolchain logic to `space.*`.

## Stage 10.3.4 Meaning

This step proves that toolchain control can be represented as resident copicode records before the launch-completion migration.
