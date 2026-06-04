# Контракт на владение minimal copy scheduling

Этап `23` задает минимальный контракт, по которому resident runtime владеет minimal copy scheduling после bootstrap.

## Назначение

Этот контракт нужен, чтобы resident code сам решал простые копирования, нужные для запуска и продолжения resident-пути.

## Область

Контракт требует, чтобы resident runtime:

- хранил минимальное состояние copy scheduling;
- выбирал нужные копирования;
- выполнял копирования полуинтервалов;
- фиксировал результат copy decision.

## Host

Host на этом этапе остается только bootstrap-обвязкой:

- подготавливает startup payload;
- запускает первый tick;
- может дать bounded diagnostics.

Host не решает, какие копирования нужны после bootstrap.

## Что не входит

Контракт не включает:

- полный host collapse;
- перенос launch control;
- перенос completion bookkeeping;
- перенос job selection и tool dispatch;
- изменение семантики `space.*`.

## Проверки

Контракт должен быть защищен проверяемыми gate'ами на:

- наличие resident copy scheduling;
- отсутствие host-side copy decision after bootstrap;
- отделение от `space.*`.

## Связь с соседними этапами

- Этап `22` задает minimal resident launch control.
- Этап `24` задает minimal resident completion bookkeeping.
- Этап `26` выполняет полное снятие зависимости от host.
