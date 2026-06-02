# RV32M div-family slice contract (14.20.3.2)

Источник семантики: `doc/rv32m_m_semantics_contract.md`.

Покрытие slice:
1. `div`  (signed)
2. `divu` (unsigned)
3. `rem`  (signed)
4. `remu` (unsigned)

Обязательные corner-cases в slice truth:
1. обычный signed/unsigned случай;
2. `div-by-zero`: `div/divu -> 0xFFFFFFFF`, `rem/remu -> dividend`;
3. stop-contract: final step `stop_reason=1`.

Гейты:
1. `scripts/tdd/test_c3_m_div4.sh`
2. `scripts/tdd/test_c3_m_div4_trace_diff.sh`
3. `scripts/tdd/test_c3_m_div4_run_diff.sh`
4. `scripts/tdd/test_c3_m_div4_budget.sh`
