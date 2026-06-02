# External RISC-V Tests (RV32I/RV32M)

Цель: подключить общеизвестные внешние тест-наборы к текущему C3/C2 пайплайну, чтобы проверять совместимость при развитии `RV32IM`.

## Поддерживаемые источники

1. `riscv-software-src/riscv-tests` (ISA tests: `rv32ui`, `rv32um`, `rv32mi`).
2. `riscv-non-isa/riscv-arch-test` (архитектурные compliance tests).

## Локальный контракт для репозитория

1. Внешние ELF/flat-binary тесты кладутся в `third_party/riscv-external/rv32i/` и `third_party/riscv-external/rv32m/`.
2. Манифест прогона: `third_party/riscv-external/manifest_rv32i.json`.
3. Каждый кейс запускается через `scripts/riscv/rv32i_mvp_check.py --binary ...` (trace + step diff + VM reg-check).

## Быстрый запуск

```bash
sh scripts/tdd/test_rv32i_external_corpus.sh
```

Если внешний корпус не подготовлен, gate возвращает `SKIP` (rc=0) и не блокирует основной pipeline.

## Зачем это нужно

1. Снижает риск “локально зелёно, но не совместимо с общепринятыми тестами”.
2. Даёт повторяемую базу для перехода от `RV32I` к `RV32M`.
3. Ускоряет диагностику регрессий при добавлении `mul/div/rem`.
