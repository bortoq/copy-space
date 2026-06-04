# Контракт на владение completion bookkeeping

Этап `24` задает минимальный контракт, по которому resident runtime владеет completion bookkeeping после bootstrap.

## Назначение

Этот контракт нужен, чтобы resident code сам записывал факт завершения и его результат.

## Область

Контракт требует, чтобы resident runtime:

- хранил минимальное состояние completion bookkeeping;
- записывал completion record;
- фиксировал bounded result;
- завершал tiny resident path понятным способом.

## Host

Host на этом этапе остается только bootstrap-обвязкой:

- запускает первый tick;
- может читать bounded diagnostics;
- не владеет completion records после bootstrap.

## Что не входит

Контракт не включает:

- полный host collapse;
- перенос launch control;
- перенос copy scheduling;
- перенос job selection и tool dispatch;
- изменение семантики `space.*`.

## Проверки

Контракт должен быть защищен проверяемыми gate'ами на:

- наличие resident completion bookkeeping;
- отсутствие host-side ownership завершения after bootstrap;
- отделение от `space.*`.

## Связь с соседними этапами

- Этап `23` задает minimal resident copy scheduling.
- Этап `25` задает resident job selection и tool dispatch после bootstrap.
- Этап `26` выполняет полное снятие зависимости от host.
