# Copy-Space

Этот репозиторий сведен к антикризисному минимуму.

## Текущая цель

- довести resident `RV32I` proof-closure в `space.c`
- использовать resident `RISC-V` как вычислительную опору для переноса других частей проекта
- свести `host` к ОС/железу как среде исполнения; финальная граница описана в `doc/space_contract.md`

## Активный минимум

- `src/vm/space.c`
- `src/vm/space.h`
- `src/vm/rv32.c`
- `src/vm/rv32.h`
- `src/vm/bitcpy.c`
- `src/tools/space.c`
- активные `scripts/tdd/` gates
- активная документация:
  - `doc/project_structure.md`
  - `doc/roadmap.md`
  - `doc/anticrisis_plan.md`
  - `doc/space_contract.md`
  - `doc/glossary.md`
  - `doc/legacy_inventory.md`
  - `doc/audit.md`
  - `doc/resident_execution_boundary.md`
  - `doc/resident_host_collapse_plan.md`
  - `doc/resident_copicode_migration.md`
  - `doc/resident_riscv_migration.md`
  - `doc/riscv_migration_plan.md`

## Допустимое active доказательство

- resident `RV32I` путь через `space.c`
- проверки fault/trace/control для resident-кода

## Быстрый старт

```sh
make bins
sh scripts/tdd/run_all.sh
```

## План и архив

- `doc/anticrisis_plan.md`
- `doc/roadmap.md`
- `doc/legacy_inventory.md`

Исторический материал заморожен в legacy inventory и при необходимости восстанавливается из git.

## Legacy helper

- `src/tools/vmrun.c` (legacy helper; активная точка запуска теперь `src/tools/space.c`)
