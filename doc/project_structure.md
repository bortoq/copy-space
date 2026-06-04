# Copy-Space Project Structure

Этот документ описывает текущее устройство проекта: что активно, что переходно, что заморожено как legacy.

## Текущее состояние

Активный проект сейчас сведен к четырем основным опорам:

- `src/vm/space.c` - источник истины для resident `RV32I` execution.
- `src/vm/space.h` - layout состояния, stop reasons, trace records и объект VM.
- `src/vm/rv32.c` / `src/vm/rv32.h` - отдельная resident execution boundary.
- `src/tools/space.c` - активная точка запуска проекта на стороне ОС.
- `scripts/tdd/*` - активные proof gates.

Переходные и вспомогательные части:

- `src/tools/vmrun.c` - legacy bootstrap helper, выведенный из active path.
- `doc/legacy_inventory.md` - реестр замороженного legacy.

## Активная документация

- `README.md`
- `doc/glossary.md`
- `doc/roadmap.md`
- `doc/space_contract.md`
- `doc/riscv_migration_plan.md`
- `doc/legacy_inventory.md`
- `doc/audit.md`
- `doc/resident_execution_boundary.md`
- `doc/resident_host_collapse_plan.md`
- `doc/resident_copicode_migration.md`
- `doc/resident_riscv_migration.md`

## Роли файлов

### `src/vm/space.c`

- реализует эмулятор адресного пространства;
- вызывает resident `RV32I` execution;
- держит стабильные host-visible state transitions.

### `src/vm/space.h`

- определяет VM object;
- определяет guest-state addresses, stop reasons и trace layouts;
- определяет MMIO/channel layout.

### `src/vm/rv32.c`

- реализует resident `RV32I` execution;
- resident execution core and trace helpers;
- владеет guest load, step, stop, trace emission и control-plane behavior;
- владеет resident trace/state proof path;
- владеет resident request/response control plane.

### `src/tools/vmrun.c`

- загружает image в `vm->space`;
- запускает VM на bounded ticks;
- optionally dumps final space image.

Это legacy bootstrap helper, выведенный из active path; active launcher теперь `src/tools/space.c`.

### `scripts/tdd/*`

- содержит активные проверяемые ворота;
- должен подтверждать только active path.

## Документы

### `doc/space_contract.md`

- задает контракт `space.*`;
- фиксирует, что `space.*` остается только эмулятором адресного пространства;
- запрещает накапливать в нем чужую семантику.

### `doc/resident_execution_boundary.md`

- объединяет границы resident execution для этапов `15-19`;
- описывает startup, orchestration execution, copy scheduling и test orchestration как один минимальный resident runtime контур.

### `doc/resident_host_collapse_plan.md`

- объединяет план снятия зависимости от `host` для этапов `20-27`;
- описывает boundary contract, launch slice, ownership contracts, control plane assembly и final collapse.

### `doc/resident_copicode_migration.md`

- объединяет миграцию `10.1-10.3`;
- описывает runtime boundary, artifact boundary, handoff contract и related records.

### `doc/resident_riscv_migration.md`

- объединяет миграцию `RISC-V` для этапов `11-14`;
- описывает freeze boundary, extraction boundary, proof-tools preparation и compute-backend usage.

### `doc/roadmap.md`

- содержит только этапы действий;
- не содержит аудита и диагностики.

### `doc/legacy_inventory.md`

- фиксирует все, что намеренно выведено из active path;
- список должен быть источником истины для legacy.

## Что active

- resident execution в `space.c`
- resident trace/state proof
- resident fault semantics
- resident request/response control plane
- active proof gates в `scripts/tdd`

## Что transitional

- `src/tools/vmrun.c`
- любые bootstrap-only loading/dumping path, которые существуют только до того, как `space.*` станет единственным проектным executable boundary на стороне ОС

## Что legacy

- `C3_RUN` как runtime path
- `c3_addi_proof` как active proof mechanism
- scaffold-only и synthetic-trace-based paths
- любые host-side guest semantics beyond the transition-only bootstrap helper contract
