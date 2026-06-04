# Контракт на владение запуском resident code

Этап `22` задает минимальный контракт, по которому resident runtime владеет решением о запуске после bootstrap.

## Назначение

Этот контракт нужен, чтобы запуск resident-пути больше не решался host после bootstrap.

## Область

Контракт требует, чтобы resident runtime:

- хранил минимальное состояние launch control;
- принимал решение о запуске после bootstrap;
- писал launch record;
- завершал tiny launch path bounded образом.

## Host

Host на этом этапе остается только bootstrap-обвязкой:

- загружает image;
- запускает первый tick;
- может дать bounded diagnostics.

Host не решает, запускать ли следующий resident path.

## Что не входит

Контракт не включает:

- полный host collapse;
- перенос copy scheduling;
- перенос completion bookkeeping;
- перенос job selection и tool dispatch;
- изменение семантики `space.*`.

## Проверки

Контракт должен быть защищен проверяемыми gate'ами на:

- наличие resident launch control;
- отсутствие host-side launch decision after bootstrap;
- отделение от `space.*`.

## Связь с соседними этапами

- Этап `21` задает первый маленький resident launch slice.
- Этап `23` задает minimal resident copy scheduling.
- Этап `26` выполняет полное снятие зависимости от host.
