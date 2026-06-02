# FreeRTOS RV32 Minimal Port Layer (Stage 46.5.2)

## Scope
This stage defines and verifies a minimal scheduler-capable RV32 port slice executed only through the in-space emulator path.

## 46.5.2.1 Context-switch primitives contract
Minimal required primitive semantics for the current emulator profile:
- `pxPortInitialiseStack`: creates initial task frame and start PC in guest memory layout.
- `vPortYield`: explicit cooperative context switch request path.
- Critical sections: scheduler-safe enter/exit contract (`portENTER_CRITICAL`/`portEXIT_CRITICAL`) mapped to deterministic interrupt-mask state in guest-visible control memory.

For this stage, behavior is validated by guest-observable state transitions in an RV32 smoke image:
- scheduler-start marker set,
- first-task marker set,
- yield marker incremented.

## 46.5.2.2 Tick source binding contract
Tick progression must be driven by runtime/emulator execution budget (`RUN`/`STEP`) only. No host helper loop is allowed to emulate guest semantics.

## 46.5.2.3 Trap/exception glue contract
Trap path must remain scheduler-safe and deterministic:
- guest stop/trap state is surfaced via existing channel status path,
- no undefined host-side recovery path may mutate guest state.

## 46.5.2.4 Acceptance gate
`scripts/tdd/test_rv32_freertos_port_smoke.sh` must pass and prove:
- guest RV32 binary is loaded by `LOAD_CODE`,
- executed via `RUN` only,
- scheduler/first-task/yield markers are observed through `READ_MEM`,
- results are deterministic across repeated runs.
