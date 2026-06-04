# Контракт resident startup

Этот документ задает минимальный resident startup contract для этапа `16`.
Этап `16` задает минимальный startup contract.

## Область

Startup contract - это самый маленький набор копирований и фиксированных позиций, который нужен, чтобы передать управление resident code.

Он включает:

- fixed boot slots в address space,
- один resident entrypoint payload,
- минимальное resident state для начала исполнения,
- минимальные channel bootstrap data,
- bounded tick limit, который передан при запуске.

## Обязанности host

Host может только:

- скопировать startup payload в фиксированные позиции пространства,
- скопировать минимальное состояние в фиксированные позиции пространства,
- передать initial channel/bootstrap words,
- запустить первый tick,
- остановиться после заданного tick budget.

Host не может:

- реализовывать orchestration semantics,
- реализовывать resident scheduling policy,
- реализовывать resident toolchain policy,
- добавлять новые семантики `space.*`.

## Обязанности resident

После первого tick resident code владеет:

- чтением своего startup state,
- продолжением copy/channel flow, который принадлежит resident code,
- продвижением минимального job lifecycle,
- записью observable completion state.

## Что не входит

Этот контракт не включает:

- полный перенос orchestration,
- полный перенос toolchain,
- поддержку нового `RISC-V` ISA,
- изменения семантики `space.*`,
- восстановление `C3_RUN`,
- семантику `forth0`.
