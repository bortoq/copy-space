Документация (doc/) — 2026-05-04
# Документация (doc/)

## Порядок чтения
1) `00_about.md` — общая идея проекта + принцип “всё внешнее = устройство, доступ через каналы”.
2) `10_state_std7_fixed.md` — текущий baseline (std7_fixed + 2a + старт 2b).
3) `30_bench_vmrep.md` — vmrep отчёт и throughput-бенчи (bulk/pack/permute).
4) `40_devices_channels.md` — дизайн устройств/каналов/менеджера (зафиксированная архитектура взаимодействия модулей/гестов).
5) `20_todo.md` — планы.
6) `abi_std7_fixed_artifacts.md` — ABI

## Быстрые ссылки
- регрессия: `scripts/test_all.sh`
- логи тестов: `tmp/compile.log`, `tmp/run.log`
- образы: `out/img_fixed_pool_small.bin`, `out/img_fixed_pool_big.bin`

## Artifact ABI (индексы)
см. `doc/10_state_std7_fixed.md` и/или поддерживаемый список в mkimage.

## Принципы
- VM минимальна: copy + MMIO.
- Устройства/гесты оформляются как device objects, доступ через каналы.
- Менеджер каналов отделяется от прикладной логики.
- Детерминизм обеспечивается тем, что состояние каналов — часть `space` и/или протоколы могут быть записаны/воспроизведены.

## License
- License: MIT (see `LICENSE`).
- Third-party notes: see `THIRD_PARTY.md`.
