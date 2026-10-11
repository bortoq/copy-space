# Resident host collapse plan

Этот документ объединяет планы и контракты для этапов `20-27`.

## Назначение

Документ фиксирует путь от minimal host-dependency contract до удаления `vmrun` из active path и сведения `space.*` к чистому эмулятору адресного пространства.

## Часть 1. Контракт перед снятием зависимости

- Host остается bootstrap-only during migration.
- Active path должен описываться через resident execution control, resident copy scheduling, resident test orchestration и стабильный контракт `space.*`.
- Проверки должны подтверждать bootstrap-only поведение host и отсутствие новых семантик `space.*`.

## Часть 2. Минимальный host-independent launch slice

- Host только загружает image и запускает первый tick.
- Resident runtime владеет launch/completion и minimal copy scheduling.
- Host не выбирает jobs after bootstrap.

## Часть 3. Владение resident control plane

Resident code должен отдельно владеть:

- launch control,
- minimal copy scheduling,
- completion bookkeeping,
- job selection,
- tool dispatch.

## Часть 4. Assembly plan

Resident control plane собирается в один resident-owned control loop:

- `rv_control_plane_step()` вызывает launch control,
- `rv_control_plane_step()` вызывает copy scheduling,
- `rv_control_plane_step()` вызывает completion bookkeeping,
- `rv_control_plane_step()` вызывает job selection,
- `rv_control_plane_step()` вызывает tool dispatch.

## Часть 5. Финальное снятие зависимости

`vmrun` выводится из active path.

`space.*` остается только эмулятором адресного пространства.

`space.*` не несет active control semantics и не принимает orchestration decisions.

## Проверяемая граница

Финальное состояние считается достигнутым только если:

- `vmrun` не участвует в active path,
- `space.*` остается единственным проектным executable boundary на стороне ОС,
- resident control plane является единственным источником active control after bootstrap.

## Compatibility notes

Этап `21` задает первый маленький путь запуска.
Этап `22` задает минимальный контракт.
Этап `23` задает минимальный контракт.
Этап `24` задает минимальный контракт.
Этап `25` задает минимальный контракт.
Этапы `22-25` задают безопасные контракты владения перед снятием зависимости.
Этап `26` собирает resident control plane.
Этап `27` выполняет настоящее снятие зависимости от host.
Этап `26` задает один конкретный технический план.
