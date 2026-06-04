# Copy-Space Roadmap

Цель: довести `resident RV32I` executor в `space.c` до честного proof-closure, затем перенести request/response control plane в пространство и только после этого сократить хостовый `space.*` до минимального контракта.

## Правила ведения документа

Этот документ хранит только этапы достижения цели проекта.

1. ✅ Включать только этапы и пункты-действия.
1.1. ✅ Не включать аудит, диагностику, ретроспективу и выводы расследований.
1.2. ✅ Любые результаты проверок выносить в отдельные документы.

2. ✅ Каждый пункт формулировать как действие.
2.1. ✅ Каждый пункт должен описывать выполненное или запланированное действие.
2.2. ✅ Недопустимы формулировки состояния, риска или проблемы вместо действия.

3. ✅ Использовать только статусы `✅` и `❌`.
3.1. ✅ `✅` означает завершенное действие.
3.2. ✅ `❌` означает незавершенное или запланированное действие.

4. ✅ Сохранять строгую иерархическую нумерацию.
4.1. ✅ Верхний уровень: `1.`, `2.`, `3.`.
4.2. ✅ Подуровни: `1.1.`, `1.1.1.` и далее.

5. ✅ Сохранять назначение документа.
5.1. ✅ Один пункт должен описывать одно действие.
5.2. ✅ Крупные действия раскладывать на подпункты.
5.3. ✅ Все, что не помогает достижению цели, выносить из `roadmap`.

## 1. Сведение проекта к антикризисному baseline

1.1. ✅ Оставить `space.c` resident executor единственным active runtime baseline.
1.1.1. ✅ Исключить synthetic traces из active proof path.
1.1.2. ✅ Исключить scaffold-only `TESTG` paths из active proof path.
1.1.3. ✅ Исключить `rv32m`, `service`, `SHA`, `FreeRTOS` и external-corpus tracks из active proof path.

1.2. ✅ Сохранить `C3_RUN` только как legacy proof artifact вне active baseline.
1.2.1. ✅ Не использовать `C3_RUN` как источник истины для active proof path.
1.2.2. ✅ Не использовать `C3_RUN` gates при определении progress по цели проекта.

1.3. ✅ Оставить минимальный toolchain для real resident proof.
1.3.1. ✅ Сохранить `std7_fixed` image builder.
1.3.2. ✅ Сохранить host-side `forth0` compiler/launcher только как bootstrap toolchain.
1.3.3. ✅ Сохранить минимальные `scripts/tdd` gates только для active baseline.

1.4. ✅ Зафиксировать антикризисный план в отдельном документе.
1.4.1. ✅ Зафиксировать единственный active path.
1.4.2. ✅ Зафиксировать допустимую единицу прогресса.
1.4.3. ✅ Зафиксировать порядок работ.
1.4.4. ✅ Зафиксировать kill criteria.
1.4.5. ✅ Зафиксировать frozen legacy inventory отдельным документом.

## 2. Построение resident baseline proof

2.1. ✅ Зафиксировать resident `space.c` executor contract как active baseline.
2.1.1. ✅ Зафиксировать host ABI и guest-state layout для resident `RV32I`.
2.1.2. ✅ Зафиксировать допустимую единицу progress как real-proof gate из `space.c`.

2.2. ✅ Построить первый real resident proof-slice через `space.c`.
2.2.1. ✅ Добавить real-proof gate resident `ADDI` execution.
2.2.2. ✅ Добавить real-proof gate sequential `PC` progression на resident `ADDI` path.
2.2.3. ✅ Добавить real-proof gate записи `x1` на resident `ADDI` path.

2.3. ✅ Выделить resident baseline gates в отдельный active smoke path.
2.3.1. ✅ Добавить отдельный smoke-runner baseline resident proof path.

## 3. Достижение resident RV32I proof-closure

3.1. ✅ Добавить real-proof gate real unsupported stop path в `space.c`.
3.2. ✅ Добавить real-proof gate real `SW/LW` path в `space.c`.
3.3. ✅ Добавить real-proof gate real branch/jump path в `space.c`.
3.3.1. ✅ Доказать full `JAL` link-write через resident `space.c`.
3.4. ✅ Добавить real-proof gate real `guest_steps` и stop-state layout в `space.c`.

## 4. Доведение resident stop/fault semantics

4.1. ✅ Добавить real-proof gate resident unsupported stop-state в `space.c`.
4.2. ✅ Добавить real-proof gate resident alignment fault path.
4.3. ✅ Добавить real-proof gate resident bounds fault path.

## 5. Построение resident trace/state proof path

5.1. ✅ Добавить resident trace evidence path без synthetic trace из `space.c`.
5.2. ✅ Добавить gate извлечения resident trace records из реального исполнения `space.c`.
5.3. ✅ Добавить gate согласованности resident trace и resident state из `space.c`.

## 6. Построение resident request/response control plane

6.1. ✅ Реализовать resident request layout внутри `space.c`.
6.2. ✅ Реализовать resident response layout внутри `space.c`.
6.3. ✅ Реализовать resident handshake path внутри `space.c`.
6.4. ✅ Добавить real-proof gate первого resident request/response roundtrip.

## 7. Подтверждение resident closure

7.1. ✅ Добавить closure runner, который использует только resident proof path из `space.c`.
7.2. ✅ Исключить bootstrap-only proof path из closure criteria.

## 8. Реконструкция хостового эмулятора пространства

8.1. ✅ Удалить из `space.*` host-side channel ABI semantics после переноса в `space.c`.
8.2. ✅ Удалить из `space.*` host-side guest runtime semantics после переноса в `space.c`.
8.3. ✅ Свести `space.*` к минимальному контракту хоста.

## 9. Подготовка следующей resident migration

9.1. ✅ Зафиксировать контракт `space.*` как стабильный boundary.
9.2. ✅ Зафиксировать план миграции `RISC-V` в resident copicode.
9.3. ✅ Выделить resident `RISC-V` implementation в отдельный source boundary.
9.4. ✅ Зафиксировать boundary миграции orchestration and toolchain into copicode.
9.4.1. ✅ Зафиксировать scope resident orchestration.
9.4.2. ✅ Зафиксировать scope bootstrap-only toolchain.
9.4.3. ✅ Зафиксировать out-of-scope items for `space.*`.
9.4.4. ✅ Зафиксировать execution plan migration for orchestration and toolchain.
9.4.5. ✅ Добавить resident job descriptor format.
9.4.6. ✅ Зафиксировать resident job selection contract.
9.4.7. ✅ Зафиксировать resident tool invocation contract.
9.4.8. ✅ Заморозить host orchestration как bootstrap-only.
9.4.9. ✅ Зафиксировать resident toolchain control contract.
9.4.10. ✅ Зафиксировать final resident orchestration boundary.

## 10. Resident Copicode Runtime Boundary

10.1. ✅ Зафиксировать resident copicode runtime boundary.
10.1.1. ✅ Определить resident runtime entrypoints for orchestration.
10.1.2. ✅ Определить resident runtime state model for job/tool lifecycle.
10.1.3. ✅ Определить resident runtime interfaces for job selection, invocation and toolchain control.
10.1.4. ✅ Зафиксировать resident runtime verification gates.
10.2. ✅ Зафиксировать resident copicode migration plan.
10.2.1. ✅ Определить resident copicode artifact boundary.
10.2.2. ✅ Определить resident copicode execution boundary.
10.2.3. ✅ Определить migration shims for host bootstrap and diagnostics.
10.2.4. ✅ Определить verification gates for copicode migration.
10.2.5. ✅ Зафиксировать final state for copicode migration.
10.3. ❌ Мигрировать orchestration and toolchain into copicode.
10.3.1. ✅ Зафиксировать resident copicode artifact format.
10.3.2. ✅ Зафиксировать resident copicode handoff contract.
10.3.3. ❌ Перенести orchestration decision records into copicode.
10.3.4. ❌ Перенести toolchain control records into copicode.
10.3.5. ❌ Перенести resident launch completion into copicode.
