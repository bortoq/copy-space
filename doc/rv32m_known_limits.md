# RV32M Known Limits

Status: frozen.
Date: 2026-06-01.

1. Coverage is bounded by frozen RV32M MVP test set (`doc/rv32m_mvp_test_set.md`).
2. Trace truth for staged/diff is based on deterministic known cases.
3. Repro bundle writes `stop_dump.bin` placeholder on mismatch path.
4. Performance baseline is environment-dependent; degradation is controlled by percentage gates.
5. No claim of full platform/privileged/CSR/interrupt architectural completeness.
