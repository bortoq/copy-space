# RV32 Service Quickstart

1. Validate ABI and loader:
   - `sh scripts/tdd/test_rv32_service_abi_contract.sh`
   - `sh scripts/tdd/test_rv32_service_loader_e2e.sh`
2. Run smoke conformance:
   - `sh scripts/tdd/test_rv32_service_external_smoke.sh`
3. Run full release gate:
   - `sh scripts/tdd/test_rv32_service_release_gate.sh`

All limits are tick-based (`max_ticks`, `watchdog_ticks`).
