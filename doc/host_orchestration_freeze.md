# Host Orchestration Freeze

This document freezes the active-path meaning of host orchestration.

## Rule

- Host orchestration is bootstrap-only.
- Host orchestration may prepare images, launch the first resident entrypoint, and dump results.
- Host orchestration must not select jobs after bootstrap.
- Host orchestration must not launch tools after resident takeover.
- Host orchestration must not be treated as an active execution layer.

## Active Path

The active path begins in resident code after bootstrap and continues there.

## Frozen Host Responsibilities

- image loading
- first-entry bootstrap
- bounded run loop
- optional dump
- optional diagnostics

## Not Active

- job selection
- tool invocation
- scheduling
- orchestration state machines

This freeze is a documentation boundary only. It does not change `space.*` semantics.
