# RV32 Bootstrap Closure

Этот документ фиксирует активный bootstrap closure path для `RISC-V` до появления resident in-space control plane.

## 1. Активный bootstrap closure path

Единственный активный bootstrap closure path:

`LOAD_CODE -> RUN/STEP -> READ_REGS/READ_MEM -> TRACE_INFO/TRACE_READ`

Этот путь считается единственным источником доказательств для bootstrap `RV32I`.

## 2. Временный bootstrap ABI contract

Временный bootstrap ABI включает только операции:

- `STATUS`
- `LOAD_CODE`
- `RUN`
- `STEP`
- `READ_REGS`
- `READ_MEM`
- `WRITE_MEM`

Этот ABI является временным переходным контрактом.

## 3. Временный bootstrap trace ABI

Временный bootstrap trace ABI включает только:

- `TRACE_INFO`
- `TRACE_READ`

Этот trace ABI является временным `proof-only` контрактом.
Он нужен только для bootstrap proof path и должен быть удален из `space.*` на этапе реконструкции эмулятора пространства.

## 4. Достаточный bootstrap proof set

Bootstrap proof set считается достаточным для начала реконструкции `space.*`, если проходят:

- `scripts/tdd/test_rv32_runtime_abi_ops.sh`
- `scripts/tdd/test_rv32_guest_run_contract.sh`
- `scripts/tdd/test_rv32_stage3_rv32i_runtime.sh`
- `scripts/tdd/test_rv32_stage4_trace_runtime.sh`
- `scripts/tdd/test_rv32_stage4_bootstrap_proof.sh`

Сводный runner этого proof set:

- `scripts/tdd/run_rv32_bootstrap_closure.sh`

## 5. Неактивные proof paths

До появления resident in-space control plane следующие пути не входят в bootstrap correctness path:

- `C3_RUN`
- synthetic trace generation
- scaffold-only gates
- `TESTG`-based closure assertions
- host-assisted `forth0`/translation/emitter paths
- SHA, FreeRTOS и external corpus gates

Они могут оставаться только как исследовательские или legacy-пути.

## 6. Ограничение на host-side guest logic

До реконструкции `space.*` запрещено расширять host-side guest logic сверх bootstrap closure.

Разрешено:

- поддерживать текущий bootstrap executor;
- поддерживать временный bootstrap trace ABI;
- исправлять дефекты, блокирующие bootstrap proof path.

Запрещено:

- расширять active release path назад в `C3_RUN` или synthetic/scaffold gates;
- делать host-assisted proof paths обязательными для bootstrap closure;
- считать legacy release runners источником истины для bootstrap `RISC-V`.
