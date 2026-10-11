# Resident copicode migration

Этот документ объединяет этапы `10.1-10.3`.

## Назначение

Документ фиксирует миграцию orchestration и toolchain control в resident copicode без добавления non-emulator logic в `space.*`.

## Граница runtime

- resident runtime boundary определяет entrypoints, state model, interfaces и verification hooks;
- `space.*` остается только эмулятором адресного пространства;
- resident code получает orchestration/toolchain behavior через явный handoff.
`doc/resident_execution_boundary.md` задает runtime boundary для stages `15-19`.

## Artifact and handoff

- resident copicode artifact определяет формат resident workload code;
- resident copicode handoff определяет, как подготовленный artifact становится resident-ready;
- decision records, toolchain control records и launch-completion records фиксируют состояния этой миграции.

## Transition rules

- Host bootstrap only prepares the first artifact and bounded diagnostics.
- Host-side orchestration is removed from the active path after takeover.
- No orchestration logic is added to `space.*`.

## Проверяемая граница

Миграция считается корректной только если:

- artifact boundary существует отдельно,
- handoff boundary существует отдельно,
- execution boundary существует отдельно,
- host responsibilities остаются bootstrap-only.
