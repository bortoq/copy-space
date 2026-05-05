# Devices and Channels (device ≠ channel)

## Principle
A **device** is a single object with identity and a set of ports.
A **channel** is a port endpoint with a protocol.

This repo follows the design rule:

- device ≠ channel

Meaning:
- a terminal is one device (with stdin/stdout/stderr ports),
  not "three unrelated channels".

## TERM0 (terminal device)
The terminal is published as a self-describing structure inside `space` and referenced via ART:

- ART[65] = BUS_BASE
- ART[66] = TERM0_DESC

The descriptor uses magic "CDEV".
Channel headers use magic "CHN1".

## Test
TERM0 descriptor ABI is validated by:

- `scripts/tdd/test_term0_desc_abi.sh`

