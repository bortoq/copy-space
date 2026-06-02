# riscv-external corpus

Папка для внешних RISC-V тестов, используемых в локальном conformance gate.

Минимум:
1. Обновить `manifest_rv32i.json`.
2. Положить `.bin` файлы (flat binaries) и сослаться на них в `binary`.
3. Рекомендуемая структура:
   - `third_party/riscv-external/riscv-tests/*.bin`
   - `third_party/riscv-external/riscv-arch-test/**/**/*.bin`

Запуск:
```bash
sh scripts/tdd/test_rv32i_external_corpus.sh
```

Примечание:
- если бинарник из манифеста отсутствует, кейс помечается как `SKIP` (не блокирует gate);
- реальные падения (`FAIL`) только на семантическом mismatch при запуске существующего кейса.

Текущий активный набор:
- `riscv-tests` generated RV32UI binaries (взяты из открытого зеркала `tinyriscv/tests/isa/generated`).
- `riscv-arch-test` оставлен как следующий слой расширения корпуса после RV32M/S5+.
