# Контракт на владение job selection и tool dispatch после bootstrap

Этап `25` задает минимальный контракт, по которому resident runtime владеет job selection и tool dispatch после bootstrap.

## Назначение

Этот контракт нужен, чтобы выбор следующей задачи и передача ее в инструмент больше не решались host после bootstrap.

## Область

Контракт требует, чтобы resident runtime:

- хранил минимальное состояние job selection;
- выбирал следующий resident job path;
- хранил минимальное состояние tool dispatch;
- передавал выбранную задачу в нужный tool;
- фиксировал факт dispatch.

## Host

Host на этом этапе остается только bootstrap-обвязкой:

- загружает image;
- запускает первый tick;
- может дать bounded diagnostics.

Host не выбирает jobs и не dispatch'ит tools после bootstrap.

## Что не входит

Контракт не включает:

- полный host collapse;
- перенос launch control;
- перенос copy scheduling;
- перенос completion bookkeeping;
- изменение семантики `space.*`.

## Проверки

Контракт должен быть защищен проверяемыми gate'ами на:

- наличие resident job selection;
- наличие resident tool dispatch;
- отсутствие host-side selection и dispatch after bootstrap;
- отделение от `space.*`.

## Связь с соседними этапами

- Этап `24` задает minimal resident completion bookkeeping.
- Этап `26` выполняет полное снятие зависимости от host.
