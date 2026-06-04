# Resident execution boundary

Этот документ объединяет границы resident execution для этапов `15-19`.

## Назначение

Документ фиксирует одну общую границу: после bootstrap resident code владеет execution entrypoint, состоянием, launch/control, copy scheduling, channel service и test orchestration.

## Состав границы

Граница включает только минимальные части:

- resident execution entrypoint,
- resident runtime state,
- startup handoff,
- minimal copy scheduling,
- minimal channel service,
- job selection и tool dispatch там, где они нужны после bootstrap,
- completion bookkeeping,
- проверяемые gates для отделения от `space.*`.

## Что не входит

Эта граница не включает:

- изменения семантики `space.*`,
- support for new guest ISA,
- legacy `C3_RUN`,
- `forth0` semantics,
- host-side orchestration decisions after bootstrap.

## Связь со стадиями

- Stage `15` задает runtime boundary.
- Stage `16` задает minimal startup contract.
- Stage `17` задает minimal execution runtime.
- Stage `18` задает minimal copy scheduling runtime.
- Stage `19` задает minimal test orchestration runtime.

## Правило

Если изменение касается resident entrypoint, state, lifecycle, launch, copy scheduling, channel service, job selection, tool dispatch или completion after bootstrap, оно относится сюда или в более узкий дочерний контракт, а не в `space.*`.

## Compatibility notes

Этот документ задает resident runtime boundary для этапа `15`.
Этап `16` задает минимальный startup contract.
Этап `17` задает минимальный resident runtime для orchestration.
Этап `18` задает минимальный resident runtime для copy scheduling.
Этап `19` задает минимальный resident runtime для test orchestration.
