# Минимальный resident launch slice без host decision

Этап `21` задает первый маленький путь запуска, где host только загружает image и запускает первый tick.

## Цель

Этот этап нужен, чтобы показать один tiny path, в котором:

- host не выбирает jobs после bootstrap,
- resident runtime владеет launch/completion,
- resident runtime владеет minimal copy scheduling,
- `space.*` остается только эмулятором адресного пространства.

## Область

Этап включает только:

- один resident-controlled launch path,
- одну resident-visible job decision,
- один minimal copy decision,
- один completion record,
- machine-checkable proof gate.

## Форма пути

1. Host подготавливает startup payload.
2. Host запускает первый tick.
3. Resident runtime выбирает следующий tiny job path.
4. Resident runtime выполняет minimal copies, если они нужны.
5. Resident runtime пишет launch/completion record.
6. Path завершается bounded stop condition.

## Host

Host на этом этапе остается bootstrap-only:

- загрузка image,
- запуск первого tick,
- bounded dump или diagnostics при необходимости.

Host не может:

- выбирать jobs после bootstrap,
- запускать tools после takeover,
- принимать orchestration decisions после bootstrap.

## Что не входит

Этот этап не включает:

- полный collapse host dependency,
- удаление последнего bootstrap shim,
- изменение семантики `space.*`,
- поддержку нового guest ISA,
- семантику `forth0`.

## Проверка

Этап считается выполненным только если есть machine-checkable gate, который подтверждает:

- один tiny resident-controlled launch path,
- отсутствие host-side orchestration decision после bootstrap,
- отделение от `space.*`,
- bootstrap-only host responsibilities.

## Связь с соседними этапами

- Этап `20` задает контракт на минимальное снятие зависимости от host.
- Этап `22` задает минимальный resident launch control.
- Этап `27` выполняет настоящее снятие зависимости от host для resident `RISC-V`.
