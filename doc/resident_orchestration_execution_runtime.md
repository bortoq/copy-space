# Минимальный resident runtime для orchestration

Этап `17` задает минимальный resident runtime для orchestration.

## Область

Это самый маленький resident-owned цикл исполнения, который может взять на себя orchestration после bootstrap.

Он включает только:

- одну точку входа resident execution,
- одну модель состояния orchestration,
- минимальный copy scheduling,
- минимальный channel service,
- минимальный учет запуска и завершения.

## Форма исполнения

Runtime намеренно маленький:

1. Прочитать startup state.
2. Выбрать текущую resident job.
3. Выполнить минимальные fixed-slot копирования для этой job.
4. Передать или прочитать минимальные channel words для этой job.
5. Записать состояние запуска или завершения.
6. Продолжать до bounded stop condition.

## Обязанности host

На этом этапе host остается bootstrap-only:

- подготовить startup payload,
- запустить первый resident tick,
- забрать bounded results только если это нужно.

Host не может:

- принимать orchestration решения после bootstrap,
- владеть resident lifecycle state,
- реализовывать resident copy scheduling,
- реализовывать resident channel service,
- реализовывать учет запуска и завершения.

## Что не входит

Этот runtime не включает:

- изменения семантики `space.*`,
- поддержку нового guest ISA,
- семантику `forth0`,
- восстановление legacy `C3_RUN`,
- полный перенос toolchain,
- снятие зависимости от host.

## Проверки

Runtime должен быть защищен проверяемыми gate'ами на:

- форму resident execution entrypoint,
- отделение от `space.*`,
- host-only обязанности bootstrap,
- минимальное поведение copy/channel/bookkeeping.

## Связь с соседними этапами

- Этап `16` задает минимальный startup contract, который передает управление этому runtime.
- Этап `18` задает минимальный resident copy scheduling runtime.
- Этап `19` переносит минимальный test orchestration в resident copicode.
- Этап `20` задает контракт на минимальное снятие зависимости от host.
