# Минимальный resident runtime для test orchestration

Этап `19` задает минимальный resident runtime для test orchestration.

## Область

Это самый маленький resident-owned loop, который может управлять test-oriented resident work после появления orchestration execution runtime и copy scheduling runtime.

Он включает только:

- dispatch выбора job,
- dispatch запуска tools, когда это помогает переносу,
- dispatch управления toolchain, когда это уменьшает bootstrap,
- учет job / invocation / control,
- проверяемые gate'ы.

## Форма исполнения

Runtime намеренно маленький:

1. Прочитать resident orchestration state.
2. Выбрать следующую resident job.
3. Прочитать или обновить invocation record для этой job.
4. Применить минимальный toolchain control record для этой job.
5. Записать состояние запуска или завершения.
6. Продолжать до bounded stop condition.

## Обязанности host

На этом этапе host остается bootstrap-only:

- подготовить startup payload,
- запустить первый resident tick,
- забрать bounded results только если это нужно.

Host не может:

- выбирать job после bootstrap,
- запускать tools после takeover,
- владеть job / invocation / control records после takeover,
- добавлять семантику `space.*`.

## Что не входит

Этот runtime не включает:

- изменения семантики `space.*`,
- поддержку нового guest ISA,
- семантику `forth0`,
- восстановление legacy `C3_RUN`,
- полное снятие зависимости от host.

## Проверки

Runtime должен быть защищен проверяемыми gate'ами на:

- форму job-selection dispatch,
- форму tool-invocation dispatch, когда она нужна,
- форму toolchain-control dispatch, когда она нужна,
- отделение от `space.*`,
- host-only обязанности bootstrap.

## Связь с соседними этапами

- Этап `17` задает минимальный resident runtime для orchestration.
- Этап `18` задает минимальный resident runtime для copy scheduling.
- Этап `20` задает контракт на минимальное снятие зависимости от host.
- Этап `21` снимает зависимость от host для resident `RISC-V`.
