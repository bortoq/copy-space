# Resident Job Descriptor

This document defines the first resident orchestration payload used by stage `9.4.5`.

## Purpose

A resident job descriptor is the smallest unit of orchestration metadata that can be passed through the current resident-visible boundary without involving `space.*` semantics beyond copying.

## Format

The descriptor is a fixed-size opaque record:

- `kind` - identifies the job class
- `entry` - resident entrypoint or target address
- `arg0` - first argument
- `arg1` - second argument
- `flags` - control bits for future scheduling behavior

All fields are stored as 32-bit little-endian words.

## Contract

- The descriptor must be copyable as a single blob.
- The descriptor must survive transport through resident-visible memory unchanged.
- The descriptor must remain a data format only.
- No orchestration logic belongs inside `space.*`.

## Stage 9.4.5 Meaning

This descriptor is the first executable boundary for orchestration migration:

- host code may prepare it during bootstrap,
- resident code will later consume it,
- the current gate only proves the transport and format boundary.
