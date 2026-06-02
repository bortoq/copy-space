# RV32 Service Runbook

## Preflight
- Run `sh scripts/tdd/test_rv32_service_abi_contract.sh`.
- Run `sh scripts/tdd/test_rv32_service_runtime_path.sh`.

## Full release
- Run `sh scripts/tdd/run_rv32_service_release.sh`.
- Require 3/3 green runs.

## Troubleshooting
- If `ERR_BUDGET`, increase `max_ticks` only if deterministic replay still passes.
- If `ERR_PROTOCOL`, re-check ABI version and required fields.
