# Copy-Space Anticrisis Plan

Цель этого плана: не пытаться сразу довести весь проект до финальной архитектуры, а доказать `resident RV32I closure first` в `space.c`.

## 1. Единственный active path

Единственный допустимый active runtime path на время антикризисного плана:

- `std7_fixed` image builder
- `forth0` host toolchain только как bootstrap compiler/launcher
- `space.c` resident executor как единственный active runtime baseline

Недопустимо считать active proof path:

- synthetic traces;
- scaffold-only `TESTG` dumps;
- `rv32m`/`service`/`FreeRTOS`/`SHA` tracks;
- external corpora;
- legacy host-assisted runtime paths.

`C3_RUN` сохраняется только как legacy proof artifact и не участвует в active baseline.

## 2. Рабочая единица прогресса

Единственная допустимая единица прогресса: один real-proof gate, который:

- запускает реальный resident path в `space.c`;
- читает реальное resident state после исполнения;
- не подменяет результат заранее записанным `TESTG`;
- не использует synthetic trace как источник истины.

Если новый шаг не дает такого gate, он не считается прогрессом.

## 3. Последовательность работ

Работы выполняются только в таком порядке:

1. Довести `space.c` до honest resident RV32I proof-closure.
2. Довести resident stop/fault semantics.
3. Довести resident trace/state proof path.
4. Построить resident request/response control plane.
5. Только после этого сокращать `space.*`.

Запрещено начинать `resident protocol handoff` или `space.*` reconstruction до завершения пунктов `1-3`.

## 4. Minimal Closure Backlog

Обязательная последовательность ближайших proof-slices:

1. real unsupported stop path in `space.c`
2. real `SW/LW` path in `space.c`
3. real branch/jump path in `space.c`
4. real `guest_steps` / stop-state layout in `space.c`
5. resident trace evidence
6. resident request/response protocol

Переход к следующему пункту допускается только после machine-checkable gate для предыдущего.

## 5. Kill Criteria

Проект нужно заморозить и переоценить, если выполняется хотя бы одно условие:

1. После нескольких узких итераций подряд не удается закрыть real unsupported path.
2. После нескольких узких итераций подряд не удается закрыть real `SW/LW` path.
3. После нескольких узких итераций подряд не удается закрыть real branch/jump path.
4. Для движения вперед снова требуется возвращаться к scaffold-only доказательствам.
5. Для progress по resident executor приходится наращивать постоянную host-side семантику в `space.*` вместо переноса в `space.c`.

## 6. Success Criteria

Антикризисный план считается успешным только если:

1. `space.c` доказывает resident `RV32I` execution через real-proof gates.
2. resident stop/fault state доказан без scaffold-подмен.
3. resident trace/state evidence становится единственным источником истины.
4. только после этого начинается resident control plane.

До выполнения этих условий проект не считается вернувшимся в устойчивое состояние.
