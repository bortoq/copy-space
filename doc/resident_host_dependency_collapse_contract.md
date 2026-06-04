# Контракт на снятие зависимости от host

Этап `20` задает минимальный контракт на снятие зависимости от host.

## Назначение

Этот контракт фиксирует последнюю границу перед тем, как зависимость от host можно будет убрать из активного resident `RISC-V` пути.

Контракт не выполняет само снятие зависимости. Он задает минимальный набор условий, которые должны быть истинны, чтобы снять зависимость безопасно.

## Область

Контракт требует, чтобы active path можно было описать только через:

- минимальный loader для запуска resident `RISC-V`,
- resident execution control после bootstrap,
- resident copy scheduling после bootstrap,
- resident test orchestration после bootstrap,
- стабильный контракт эмулятора `space.*`.

## Обязанности host

На этом этапе host остается bootstrap-only:

- подготовить startup payload,
- запустить первый resident entrypoint,
- оставить только bounded diagnostics,
- не принимать active orchestration control после bootstrap.

## Что не входит

Этот контракт не включает:

- удаление последнего bootstrap shim,
- превращение resident copicode в единственный controller,
- удаление `space.*` как runtime dependency,
- финальную фиксацию документации после снятия зависимости.

## Проверки

Контракт должен быть защищен проверяемыми gate'ами на:

- bootstrap-only поведение host,
- минимальные active обязанности host,
- resident-owned границы execution control,
- отсутствие новых семантик `space.*`.

## Связь с соседними этапами

- Этап `19` задает минимальный resident runtime для test orchestration.
- Этап `21` задает минимальный resident launch slice без host decision.
- Этапы `22-25` задают безопасные контракты владения перед снятием зависимости.
- Этап `26` собирает resident control plane.
- Этап `27` выполняет настоящее снятие зависимости от host.
