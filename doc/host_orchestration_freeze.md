# Заморозка host orchestration

Этот документ фиксирует значение host orchestration в active path.

## Правило

- Host orchestration - bootstrap-only.
- Host orchestration может подготовить image, запустить первый resident entrypoint и выгрузить результат.
- Host orchestration не должен выбирать jobs после bootstrap.
- Host orchestration не должен запускать tools после resident takeover.
- Host orchestration не должен считаться active execution layer.

## Active path

Active path начинается в resident code после bootstrap и продолжается там.

## Замороженные обязанности host

- загрузка image
- первый bootstrap entry
- bounded run loop
- optional dump
- optional diagnostics

## Не active

- job selection
- tool invocation
- scheduling
- orchestration state machines

Эта заморозка только документальная. Она не меняет семантику `space.*`.
