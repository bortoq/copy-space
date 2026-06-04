# План миграции RISC-V

Цель: перенести все оставшиеся host-side части, связанные с `RISC-V`, в resident copicode с минимальным риском и при этом сохранить `space.*` как контракт эмулятора адресного пространства.

Этот план отражен в `doc/roadmap.md` как этап `9.5` и этапы `11-27`.

## Этап 1. Зафиксировать границу

- Заморозить `src/vm/space.*` для функциональных изменений.
- Оставить там только улучшения производительности, переносимости, надежности, диагностики и сопровождаемости.
- Держать `space.c` только как эмулятор адресного пространства.
- Эта граница поддерживается `space_contract.md` и картой активной документации.

## Этап 2. Выделить resident реализацию RISC-V в отдельный source boundary

- Перенести resident execution logic `RISC-V` в отдельные исходники и оставить понятные интерфейсы к `space.*`.
- Развести host wrapper и resident execution responsibilities.
- Сделать extraction механически проверяемым текущими gate'ами.
- Не расширять ISA на этом этапе.
- Использовать `doc/resident_riscv_extraction_boundary.md` как границу этого этапа.

## Этап 3. Подготовить proof tools для resident execution

- Перевести текущие `rv32_space_*` proof tools в resident-ready workloads или resident-controlled tests.
- Оставить один machine-checkable gate на один proof slice.
- Убрать зависимость от synthetic traces и host-authored state.
- Не смешивать доказательства между разными утверждениями.

## Этап 4. Использовать resident RISC-V как compute backend для переноса

- Использовать resident `RISC-V` для одного маленького migration payload.
- Использовать resident `RISC-V` для одного proof/helper workload, которому полезен resident compute.
- Оставить host-side helpers только как bootstrap-only, если они уже не нужны.
- Держать scope маленьким и измеримым.
- Использовать `doc/resident_riscv_compute_backend.md` как границу этого этапа.

## Этап 5. Зафиксировать minimal resident runtime для orchestration

- Зафиксировать resident execution runtime для orchestration.
- Ограничить runtime моделью состояния, интерфейсами и проверками.
- Не переносить execution дальше на этом этапе.
- Использовать `doc/resident_orchestration_runtime_boundary.md` как границу этого этапа.
- Использовать `doc/resident_orchestration_execution_runtime.md` как контракт этого этапа.

## Этап 6. Зафиксировать minimal resident runtime для copy scheduling

- Зафиксировать minimal resident copy scheduling runtime.
- Ограничить runtime fixed-slot scheduling, учетом и минимальным channel service.
- Не переносить более широкую orchestration.
- Использовать `doc/resident_copy_scheduling_runtime.md` как контракт этого этапа.

## Этап 7. Зафиксировать minimal resident runtime для test orchestration

- Зафиксировать minimal resident test orchestration runtime.
- Ограничить runtime выбором job, запуском tools, toolchain control и учетом записей.
- Не переносить host-dependency collapse на этом этапе.
- Использовать `doc/resident_test_orchestration_runtime.md` как контракт этого этапа.

## Этап 8. Зафиксировать контракт на минимальное снятие зависимости от host

- Зафиксировать минимальный loader, resident execution control и границу host-only.
- Зафиксировать минимальный copy scheduling, test orchestration и completion ownership.
- Зафиксировать безопасные контракты владения запуском, копированием, завершением, выбором job и передачей tool перед снятием зависимости.
- Зафиксировать стабильную границу зависимости `space.*`.
- Использовать `doc/resident_host_dependency_collapse_contract.md` как контракт этого этапа.

## Этап 9. Снять зависимость от host для resident RISC-V

- Убрать remaining bootstrap shims из active `RISC-V` path.
- Сделать resident copicode единственным источником execution control.
- Убрать `space.*` как active runtime dependency для resident `RISC-V`.
- Обновить документацию после снятия зависимости.

## Правило

Этот план не добавляет orchestration logic в `space.*`.
