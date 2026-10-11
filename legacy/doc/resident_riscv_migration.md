# Resident RISC-V migration

Этот документ объединяет этапы `11-14`.

## Назначение

Документ фиксирует путь, по которому resident `RISC-V` выделяется в отдельную границу, затем используется как compute backend для миграции других частей проекта.

## Часть 1. Freeze boundary

- `space.*` остается только эмулятором адресного пространства.
- Новые `RISC-V` semantics в `space.*` не добавляются.
- `RISC-V` execution state живет вне host-side `space.*` functionality.

## Часть 2. Extraction boundary

- resident `RISC-V` execution живет в `src/vm/rv32.c` и `src/vm/rv32.h`;
- `src/tools/vmrun.c` остается transition-only bootstrap helper;
- host wrapper и resident execution responsibilities разделяются.

## Часть 3. Proof-tools preparation

- proof gates делятся по одному claim на один gate;
- synthetic traces и host-authored state уходят из active proofs;
- proof tools становятся resident-ready, но не resident-executing.
Prepare `rv32_space_*` proof tools for later resident execution.
resident-ready, not resident-executing.

## Часть 4. Compute backend usage

- resident `RISC-V` исполняет маленькие migration payloads;
- resident `RISC-V` исполняет proof/helper workloads, если это уменьшает host dependency;
- host helpers остаются bootstrap-only или удаляются из active path.
Использовать resident `RISC-V` для одного маленького migration payload.
Использовать resident `RISC-V` для одного proof/helper workload, которому полезен resident compute.

## Проверяемая граница

Миграция считается корректной только если:

- boundary freeze зафиксирован,
- resident `RISC-V` выделен,
- proof tools подготовлены,
- compute backend usage доказан машинно-проверяемыми gate'ами.
