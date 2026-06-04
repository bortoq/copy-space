# План миграции RISC-V

Этот документ задает исполнимый план для переноса resident `RISC-V` и последующего снятия зависимости от `host`.

## Цель

Перенести все оставшиеся host-side части, связанные с `RISC-V`, в resident code с минимальным риском и сохранить `space.*` как контракт эмулятора адресного пространства.

## Опорные документы

- `doc/resident_riscv_migration.md` - единая сводка по стадиям `11-14`.
- `doc/resident_copicode_migration.md` - единая сводка по стадиям `10.1-10.3`.
- `doc/resident_execution_boundary.md` - единая сводка по стадиям `15-19`.
- `doc/resident_host_collapse_plan.md` - единая сводка по стадиям `20-27`.
- `doc/space_contract.md` - контракт на `space.*`.

## План

1. Сначала freeze/extract resident `RISC-V`.
2. Потом подготовить proof tools и resident compute backend.
3. Потом перевести orchestration и toolchain control в resident copicode.
4. Потом собрать resident execution boundary, startup, scheduling и test orchestration в один resident-owned путь.
5. Потом собрать host collapse plan.
6. Потом вывести `vmrun` из active path и оставить `space.*` единственным project executable boundary на стороне ОС через `src/tools/space.c`.
7. Использовать `doc/resident_riscv_migration.md` как границу этого этапа.
8. Перенести resident execution logic `RISC-V` в отдельные исходники.
9. Использовать resident `RISC-V` для одного маленького migration payload.
10. Использовать resident `RISC-V` для одного proof/helper workload, которому полезен resident compute.

Этот план отражен в `doc/roadmap.md` как этап `9.5` и этапы `11-27`.

## Правило

Этот план не добавляет orchestration logic в `space.*`.
