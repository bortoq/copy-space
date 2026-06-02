# Gate Policy

1. Primary release gate: `scripts/tdd/run_c3_staged.sh`.
2. Primary engineering gate: `scripts/tdd/run_c3_minimal.sh`.
3. Secondary safety gate: `scripts/tdd/run_rv32i_minimal.sh`.
4. RV32M preflight gate: `scripts/tdd/run_rv32m_preflight.sh`.
5. External corpus gate: `scripts/tdd/test_rv32i_external_corpus.sh`.
