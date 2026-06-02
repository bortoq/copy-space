# RV32M Runtime Loop Contract v1

## Scope

This document defines the universal fetch/decode/execute loop that runs in the
Copy-Space VM processor. It replaces curated slice dependencies with a single,
watchdog-protected runtime path.

## Loop architecture

```
┌─────────────────────────────────────────────────┐
│  Tick N:                                         │
│   1. MMIO services (IN, OUT, LOADER, CHANNEL)    │
│   2. Watchdog update                              │
│   3. HALT check                                   │
│   4. Execute processor slots (fetch→decode→exec)  │
│   5. Tick counter++                               │
└─────────────────────────────────────────────────┘
```

The processor executes all 64 slots each tick. Each slot is a `copy(n, dst, src)`
instruction. The runtime loop lays out these copy instructions to implement
fetch/decode/execute of the target ISA (RV32I).

## Bounded-step mode (watchdog)

The watchdog is enabled via MMIO registers:

| Register | Width | Description |
|----------|-------|-------------|
| `wd_enable` | 1 | Set to 1 to enable watchdog |
| `wd_fired` | 1 | Set by VM when limit reached |
| `wd_limit` | N_BITS | Max ticks while enabled |
| `wd_ticks` | N_BITS | Observed ticks (incremented each tick) |

When `wd_enable=1`:
1. Each tick increments `wd_ticks`.
2. If `wd_ticks >= wd_limit` (and `wd_limit > 0`):
   - `wd_fired` is set to 1
   - `halt` is set to 1 (VM stops on next HALT check)

## State snapshot points

At each snapshot point, the runtime writes current state to a reserved area:

| Offset | Field | Size |
|--------|-------|------|
| TESTG + 0 | stop_reason | 1 byte |
| TESTG + 1 | guest_pc | 4 bytes |
| TESTG + 5 | instr | 4 bytes |
| TESTG + 9 | fault_addr | 4 bytes |
| TESTG + 13 | guest_steps | 4 bytes |
| TESTG + 17 | reserved | 3 bytes |

Snapshots are taken:
- On stop (HALT/reason)
- On watchdog fire
- On error (memory fault, illegal instruction, arithmetic fault)

## Slice independence

The universal loop does not depend on curated C3 slices. Instead:
1. Loader→runtime handoff: The loader sets `entry_bitaddr` and triggers the MMIO
   loader channel. The runtime loop starts executing from that entry point.
2. The runtime loop reads instructions from the code area (not from a slice table).
3. Fallback mode (under feature flag `RV32M_UNIVERSAL_LOOP_V1=0`) reverts to
   the legacy slice-based execution.

## Stop/trap ABI

Reasons (compatible with C3 Stop Contract):
- 1: HALT reached
- 2: step budget exhausted (watchdog)
- 3: illegal instruction
- 4: memory fault
- 5: arithmetic fault

## Validation gates

- `test_rv32m_loop_smoke.sh` — basic loop execution, stop ABI, snapshot
- `test_rv32m_loop_watchdog.sh` — bounded-step mode (watchdog fires correctly)
- `test_rv32m_unified_entrypoint.sh` — loader→runtime handoff
- `test_rv32m_slice_independence.sh` — execution without curated slices
- `test_rv32m_e2e_universal_loop.sh` — full e2e: code→execution→stop
