# Copy-Space Roadmap

Цель: довести `resident RV32I` executor в `space.c` до честного proof-closure, затем перенести минимальный resident startup и orchestration path в resident code, и только после этого сократить временный bootstrap wrapper вокруг `space.*` до минимального контракта.

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

## 9.5. План устранения блокеров 1-4

9.5.1. ✅ Зафиксировать границу `space.*` для следующей миграции.
9.5.2. ✅ Выделить resident `RISC-V` в отдельный source boundary.
9.5.3. ✅ Подготовить proof tools для resident execution.
9.5.4. ✅ Использовать resident `RISC-V` как compute backend.

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
10.3. ✅ Мигрировать orchestration and toolchain into copicode.
10.3.1. ✅ Зафиксировать resident copicode artifact format.
10.3.2. ✅ Зафиксировать resident copicode handoff contract.
10.3.3. ✅ Перенести orchestration decision records into copicode.
10.3.4. ✅ Перенести toolchain control records into copicode.
10.3.5. ✅ Перенести resident launch completion into copicode.

## 11. Freeze the `space.*` boundary for the next migration

11.1. ✅ Зафиксировать `space.*` как неизменяемую функционально границу.
11.1.1. ✅ Сформулировать перечень допустимых изменений для `space.*`.
11.1.2. ✅ Сформулировать перечень запрещенных изменений для `space.*`.
11.1.3. ✅ Зафиксировать правило, что новые `RISC-V` semantics не добавляются в `space.*`.

11.2. ✅ Зафиксировать интерфейс между `space.*` и resident `RISC-V` boundary.
11.2.1. ✅ Определить минимальный host/resident handoff.
11.2.2. ✅ Зафиксировать, какие состояния читает и пишет resident `RISC-V` boundary.
11.2.3. ✅ Зафиксировать, какие проверки остаются вне `space.*`.

11.3. ✅ Зафиксировать verification gates для boundary freeze.
11.3.1. ✅ Добавить gate на отсутствие новых `space.*` semantics.
11.3.2. ✅ Добавить gate на сохранение текущих active `space.*` contracts.
11.3.3. ✅ Добавить gate на отсутствие host-side `RISC-V` expansion.

11.4. ✅ Обновить documentation map под frozen boundary.
11.4.1. ✅ Синхронизировать `README.md`.
11.4.2. ✅ Синхронизировать `doc/project_structure.md`.
11.4.3. ✅ Синхронизировать `doc/space_contract.md`.

## 12. Extract resident `RISC-V` implementation into isolated source

12.1. ✅ Выделить resident `RISC-V` entrypoint в отдельный source boundary.
12.1.1. ✅ Определить `RISC-V` runtime state ownership.
12.1.2. ✅ Определить `RISC-V` instruction execution ownership.
12.1.3. ✅ Определить `RISC-V` trace/state ownership.

12.2. ✅ Разделить host wrapper и resident execution responsibilities.
12.2.1. ✅ Убрать `RISC-V` execution semantics из host wrapper.
12.2.2. ✅ Оставить host wrapper только как bootstrap loader and dumper.
12.2.3. ✅ Зафиксировать минимальные interface points between wrapper and resident core.

12.3. ✅ Сделать extraction mechanically verifiable.
12.3.1. ✅ Добавить one-step proof gate for extracted resident `RISC-V` source.
12.3.2. ✅ Добавить one-step proof gate for preserved resident state layout.
12.3.3. ✅ Добавить one-step proof gate for preserved host wrapper behavior.

12.4. ✅ Обновить source tree map after extraction.
12.4.1. ✅ Синхронизировать `doc/project_structure.md`.
12.4.2. ✅ Синхронизировать `README.md`.

## 13. Prepare proof tools for resident execution

13.1. ✅ Выделить `rv32_space_*` proof tools как resident-ready workloads.
13.1.1. ✅ Перевести fault proofs в resident-ready форму.
13.1.2. ✅ Перевести trace/state proofs в resident-ready форму.
13.1.3. ✅ Перевести control plane proofs в resident-ready форму.

13.2. ✅ Зафиксировать один machine-checkable gate на каждый proof-slice.
13.2.1. ✅ Убрать multi-purpose proof gates where they hide different claims.
13.2.2. ✅ Разнести evidence per slice and per contract.

13.3. ✅ Удалить dependency on synthetic traces and host-authored state.
13.3.1. ✅ Убрать synthetic trace sources from active proofs.
13.3.2. ✅ Убрать host-authored state from active proofs.
13.3.3. ✅ Зафиксировать resident state as the single proof source.

13.4. ✅ Обновить proof orchestration documentation.
13.4.1. ✅ Синхронизировать `README.md`.
13.4.2. ✅ Синхронизировать `doc/project_structure.md`.
13.4.3. ✅ Синхронизировать `doc/roadmap.md`.

## 14. Use resident `RISC-V` as a migration compute backend

14.1. ✅ Зафиксировать resident `RISC-V` как compute backend для последующих переносов.
14.1.1. ✅ Определить минимальные classes of work, которые уже можно выполнять resident-side.
14.1.2. ✅ Зафиксировать интерфейс between переносимыми assets and resident execution.
14.1.3. ✅ Зафиксировать rule that host-side helpers are no longer the default compute path.

14.2. ✅ Перенести один небольшой переносимый workload на resident compute path.
14.2.1. ✅ Выбрать один tiny payload, suitable for resident execution.
14.2.2. ✅ Запустить payload через resident `RISC-V` boundary.
14.2.3. ✅ Зафиксировать machine-checkable result of resident execution.

14.3. ✅ Перенести proof/helper logic that benefits from resident compute.
14.3.1. ✅ Выбрать один proof/helper path that can be executed resident-side.
14.3.2. ✅ Перенести its computation into resident code.
14.3.3. ✅ Убедиться, что host-side equivalent stays bootstrap-only or is removed.

14.4. ✅ Обновить documentation and gates for resident compute usage.
14.4.1. ✅ Update `README.md`.
14.4.2. ✅ Update `doc/project_structure.md`.
14.4.3. ✅ Update `doc/riscv_migration_plan.md`.

## 15. Define the resident orchestration runtime boundary

15.1. ✅ Зафиксировать resident orchestration runtime entrypoint and state model.
15.1.1. ✅ Определить resident orchestration runtime entrypoint.
15.1.2. ✅ Определить resident orchestration state model.
15.1.3. ✅ Определить resident orchestration lifecycle transitions.

15.2. ✅ Зафиксировать resident orchestration interfaces and bootstrap handoff.
15.2.1. ✅ Определить resident orchestration interface to job selection, invocation, and completion.
15.2.2. ✅ Определить the smallest bootstrap payload.
15.2.3. ✅ Определить the data passed at bootstrap.
15.2.4. ✅ Определить what stays host-only during bootstrap.

15.3. ✅ Зафиксировать verification gates for the orchestration runtime boundary.
15.3.1. ✅ Добавить gate on resident entrypoint shape.
15.3.2. ✅ Добавить gate on resident lifecycle ownership.
15.3.3. ✅ Добавить gate on host bootstrap-only behavior.
15.3.4. ✅ Добавить gate on orchestration/runtime separation.

15.4. ✅ Обновить документацию под runtime boundary.
15.4.1. ✅ Update `doc/resident_execution_boundary.md`.
15.4.2. ✅ Update `doc/resident_execution_boundary.md`.
15.4.3. ✅ Update `doc/resident_copicode_migration.md`.
15.4.4. ✅ Update `doc/project_structure.md`.

## 16. Implement the minimal resident startup contract

16.1. ✅ Зафиксировать fixed boot slots and resident entrypoint payload.
16.1.1. ✅ Определить fixed positions for boot payload and resident state.
16.1.2. ✅ Определить one resident entrypoint payload.
16.1.3. ✅ Определить minimal bootstrap data passed at launch.

16.2. ✅ Зафиксировать minimal copy/channel responsibilities for startup.
16.2.1. ✅ Определить which copies the bootstrap wrapper performs before the first tick.
16.2.2. ✅ Определить which channel words belong to bootstrap-only setup.
16.2.3. ✅ Определить what resident code must continue after the first tick.

16.3. ✅ Зафиксировать verification gates for the startup contract.
16.3.1. ✅ Добавить gate on fixed-slot startup layout.
16.3.2. ✅ Добавить gate on one-entrypoint bootstrap handoff.
16.3.3. ✅ Добавить gate on bootstrap wrapper limited to copy-and-launch responsibilities.
16.3.4. ✅ Добавить gate on resident continuation after first tick.

16.4. ✅ Обновить документацию под startup contract.
16.4.1. ✅ Update `doc/resident_execution_boundary.md`.
16.4.2. ✅ Update `doc/resident_execution_boundary.md`.
16.4.3. ✅ Update `doc/project_structure.md`.
16.4.4. ✅ Update `README.md`.

## 17. Минимальный resident runtime для orchestration

17.1. ✅ Зафиксировать точку входа и модель состояния resident runtime.
17.1.1. ✅ Определить точку входа resident orchestration runtime.
17.1.2. ✅ Определить модель состояния resident orchestration runtime.
17.1.3. ✅ Определить переходы между состояниями resident orchestration runtime.

17.2. ✅ Зафиксировать минимальные интерфейсы исполнения orchestration.
17.2.1. ✅ Определить интерфейс минимального copy scheduling.
17.2.2. ✅ Определить интерфейс минимального channel service.
17.2.3. ✅ Определить интерфейс минимального учета запуска и завершения.

17.3. ✅ Зафиксировать проверки для execution runtime.
17.3.1. ✅ Добавить проверку формы resident execution runtime.
17.3.2. ✅ Добавить проверку отделения от `space.*`.
17.3.3. ✅ Добавить проверку того, что host остается bootstrap-only.

17.4. ✅ Обновить документацию для execution runtime.
17.4.1. ✅ Обновить `doc/resident_execution_boundary.md`.
17.4.2. ✅ Обновить `doc/resident_execution_boundary.md`.
17.4.3. ✅ Обновить `doc/resident_copicode_migration.md`.
17.4.4. ✅ Обновить `doc/project_structure.md`.

## 18. Минимальный resident runtime для copy scheduling

18.1. ✅ Зафиксировать форму и состояние fixed-slot scheduling.
18.1.1. ✅ Определить решения по копированию boot payload.
18.1.2. ✅ Определить решения по копированию resident state.
18.1.3. ✅ Определить форму проверки bootstrap copy.

18.2. ✅ Зафиксировать учет запуска и завершения для copy scheduling.
18.2.1. ✅ Определить учет launch record.
18.2.2. ✅ Определить учет completion record.
18.2.3. ✅ Определить учет bounded handoff.

18.3. ✅ Зафиксировать минимальный channel service для copy scheduling.
18.3.1. ✅ Определить обработку bootstrap channel.
18.3.2. ✅ Определить доставку resident request/response для scheduling.
18.3.3. ✅ Оставить channel semantics минимальными и измеримыми.

18.4. ✅ Обновить документацию для copy scheduling runtime.
18.4.1. ✅ Обновить `doc/resident_execution_boundary.md`.
18.4.2. ✅ Обновить `doc/project_structure.md`.
18.4.3. ✅ Обновить `doc/resident_copicode_migration.md`.

## 19. Минимальный resident runtime для test orchestration

19.1. ✅ Зафиксировать точку входа и модель состояния test orchestration.
19.1.1. ✅ Определить точку входа job-selection dispatch.
19.1.2. ✅ Определить модель состояния test orchestration.
19.1.3. ✅ Определить переходы между состояниями test orchestration.

19.2. ✅ Зафиксировать минимальные интерфейсы исполнения test orchestration.
19.2.1. ✅ Определить интерфейс job selection dispatch.
19.2.2. ✅ Определить интерфейс tool invocation dispatch, когда он помогает переносу.
19.2.3. ✅ Определить интерфейс toolchain control dispatch, когда он уменьшает bootstrap.

19.3. ✅ Зафиксировать проверки для test-orchestration runtime.
19.3.1. ✅ Добавить проверку формы job-selection dispatch.
19.3.2. ✅ Добавить проверку формы tool-invocation dispatch, когда это нужно.
19.3.3. ✅ Добавить проверку формы toolchain-control dispatch, когда это нужно.
19.3.4. ✅ Добавить проверку отделения от `space.*`.

19.4. ✅ Обновить документацию для test-orchestration runtime.
19.4.1. ✅ Обновить `doc/resident_execution_boundary.md`.
19.4.2. ✅ Обновить `doc/resident_copicode_migration.md`.
19.4.3. ✅ Обновить `doc/project_structure.md`.

## 20. Контракт на минимальное снятие зависимости от host

20.1. ✅ Зафиксировать минимальный loader, resident execution control и границу host-only.
20.1.1. ✅ Оставить только минимальный loader для запуска resident `RISC-V`.
20.1.2. ✅ Зафиксировать resident execution control после bootstrap как требование контракта.
20.1.3. ✅ Зафиксировать host как bootstrap-only после первого entrypoint.

20.2. ✅ Зафиксировать минимальный copy scheduling, test orchestration и ownership завершения.
20.2.1. ✅ Требовать, чтобы minimal copy scheduling жило в resident code.
20.2.2. ✅ Требовать, чтобы minimal test orchestration жило в resident code.
20.2.3. ✅ Требовать, чтобы completion bookkeeping жило в resident code.

20.3. ✅ Зафиксировать стабильную границу зависимости `space.*`.
20.3.1. ✅ Оставить `space.*` только эмулятором адресного пространства.
20.3.2. ✅ Запретить новые семантики `space.*` через этот контракт.
20.3.3. ✅ Заморозить все оставшееся bootstrap-visible поведение как временное.

20.4. ✅ Обновить документацию под контракт снятия зависимости.
20.4.1. ✅ Обновить `README.md`.
20.4.2. ✅ Обновить `doc/project_structure.md`.
20.4.3. ✅ Обновить `doc/legacy_inventory.md`.

## 21. Минимальный resident launch slice без host decision

21.1. ✅ Зафиксировать один tiny resident-controlled launch path.
21.1.1. ✅ Зафиксировать, что host только загружает image и запускает первый tick.
21.1.2. ✅ Зафиксировать, что resident runtime владеет launch/completion.
21.1.3. ✅ Зафиксировать, что resident runtime владеет minimal copy scheduling.

21.2. ✅ Зафиксировать один tiny resident job decision path.
21.2.1. ✅ Зафиксировать, что host не выбирает jobs после bootstrap.
21.2.2. ✅ Зафиксировать, что resident runtime выбирает следующий tiny job path.
21.2.3. ✅ Зафиксировать, что path завершается bounded stop condition.

21.3. ✅ Зафиксировать проверку host-independent launch slice.
21.3.1. ✅ Добавить проверку на отсутствие host-side orchestration decision after bootstrap.
21.3.2. ✅ Добавить проверку на отделение от `space.*`.
21.3.3. ✅ Добавить проверку на bootstrap-only host responsibilities.

21.4. ✅ Обновить документацию под host-independent launch slice.
21.4.1. ✅ Обновить `doc/resident_host_collapse_plan.md`.
21.4.2. ✅ Обновить `doc/project_structure.md`.
21.4.3. ✅ Обновить `README.md`.

## 22. Контракт на владение запуском resident code

22.1. ✅ Зафиксировать, что resident runtime владеет решением о запуске после bootstrap.
22.1.1. ✅ Определить минимальную модель состояния launch control.
22.1.2. ✅ Определить минимальные проверки launch control.

22.2. ✅ Зафиксировать, что host после bootstrap не принимает launch decisions.
22.2.1. ✅ Оставить host только для загрузки, первого tick и bounded diagnostics.
22.2.2. ✅ Запретить host-side execution control для launch path после bootstrap.

22.3. ✅ Обновить документацию под launch control ownership.
22.3.1. ✅ Обновить `doc/resident_host_collapse_plan.md`.
22.3.2. ✅ Обновить `doc/project_structure.md`.
22.3.3. ✅ Обновить `README.md`.

## 23. Контракт на владение minimal copy scheduling

23.1. ✅ Зафиксировать, что resident runtime владеет minimal copy scheduling.
23.1.1. ✅ Определить минимальную модель состояния copy scheduling.
23.1.2. ✅ Определить минимальные проверки copy scheduling.

23.2. ✅ Зафиксировать, что host после bootstrap не принимает copy decisions.
23.2.1. ✅ Оставить host только для первого загрузочного пути.
23.2.2. ✅ Запретить host-side scheduling control для copy path после bootstrap.

23.3. ✅ Обновить документацию под copy scheduling ownership.
23.3.1. ✅ Обновить `doc/resident_host_collapse_plan.md`.
23.3.2. ✅ Обновить `doc/project_structure.md`.
23.3.3. ✅ Обновить `README.md`.

## 24. Контракт на владение completion bookkeeping

24.1. ✅ Зафиксировать, что resident runtime владеет completion bookkeeping.
24.1.1. ✅ Определить минимальную модель состояния completion bookkeeping.
24.1.2. ✅ Определить минимальные проверки completion bookkeeping.

24.2. ✅ Зафиксировать, что host после bootstrap не владеет completion records.
24.2.1. ✅ Оставить host только для bounded results.
24.2.2. ✅ Запретить host-side ownership завершения после bootstrap.

24.3. ✅ Обновить документацию под completion bookkeeping ownership.
24.3.1. ✅ Обновить `doc/resident_host_collapse_plan.md`.
24.3.2. ✅ Обновить `doc/project_structure.md`.
24.3.3. ✅ Обновить `README.md`.

## 25. Контракт на владение job selection и tool dispatch после bootstrap

25.1. ✅ Зафиксировать, что resident runtime владеет job selection после bootstrap.
25.1.1. ✅ Определить минимальную модель состояния job selection.
25.1.2. ✅ Определить минимальные проверки job selection.

25.2. ✅ Зафиксировать, что resident runtime владеет tool dispatch, когда он нужен после bootstrap.
25.2.1. ✅ Определить минимальную модель состояния tool dispatch.
25.2.2. ✅ Определить минимальные проверки tool dispatch.

25.3. ✅ Зафиксировать, что host после bootstrap не выбирает jobs и не dispatch'ит tools.
25.3.1. ✅ Оставить host только как bootstrap wrapper.
25.3.2. ✅ Запретить host-side job selection после bootstrap.
25.3.3. ✅ Запретить host-side tool dispatch после bootstrap.

25.4. ✅ Обновить документацию под job selection и tool dispatch ownership.
25.4.1. ✅ Обновить `doc/resident_host_collapse_plan.md`.
25.4.2. ✅ Обновить `doc/project_structure.md`.
25.4.3. ✅ Обновить `README.md`.

## 26. План сборки resident control plane

26.1. ✅ Зафиксировать один общий resident state для control plane.
26.1.1. ✅ Определить минимальный resident state для launch control, copy scheduling, completion bookkeeping, job selection и tool dispatch.
26.1.2. ✅ Зафиксировать минимальные проверки resident state.

26.2. ✅ Связать launch control и copy scheduling.
26.2.1. ✅ Зафиксировать, что `rv_control_plane_step()` вызывает `rv_launch_control_step()`.
26.2.2. ✅ Зафиксировать, что `rv_control_plane_step()` вызывает `rv_copy_scheduling_step()`.

26.3. ✅ Связать completion bookkeeping, job selection и tool dispatch.
26.3.1. ✅ Зафиксировать, что `rv_control_plane_step()` вызывает `rv_completion_bookkeeping_step()`.
26.3.2. ✅ Зафиксировать, что `rv_control_plane_step()` вызывает `rv_job_selection_step()`.
26.3.3. ✅ Зафиксировать, что `rv_control_plane_step()` вызывает `rv_tool_dispatch_step()`.

26.4. ✅ Оставить host только bootstrap-only.
26.4.1. ✅ Зафиксировать, что `vmrun` не принимает orchestration decisions после bootstrap.
26.4.2. ✅ Зафиксировать, что `vmrun` остается только bootstrap wrapper.

26.5. ✅ Обновить документацию.
26.5.1. ✅ Обновить `doc/resident_host_collapse_plan.md`.
26.5.2. ✅ Обновить `doc/project_structure.md`.
26.5.3. ✅ Обновить `README.md`.

## 27. Сделать `space.*` единственным проектным executable boundary на стороне ОС

27.1. ✅ Вывести `vmrun` из active path и оставить `space.*` как единственную проектную точку запуска. Финальная граница описана в `doc/space_contract.md`.
27.1.1. ✅ Оставить `space.*` запускаемым напрямую в ОС через `src/tools/space.c`.
27.1.2. ✅ Перевести `vmrun` в legacy inventory.
27.1.3. ✅ Убрать `vmrun` из active documentation and gates.

27.2. ✅ Свести `space.*` к чистому эмулятору адресного пространства.
27.2.1. ✅ Оставить в `space.*` только эмуляцию адресного пространства и минимальный host bootstrap contract.
27.2.2. ✅ Удалить из `space.*` всю остаточную управляющую логику, не нужную эмулятору.
27.2.3. ✅ Запретить рост host-side orchestration semantics в `space.*`.

27.3. ✅ Оставить resident control plane единственным источником active control после bootstrap.
27.3.1. ✅ Перевести launch control в resident code.
27.3.2. ✅ Перевести minimal copy scheduling в resident code.
27.3.3. ✅ Перевести completion bookkeeping в resident code.
27.3.4. ✅ Перевести job selection и tool dispatch в resident code.

27.4. ✅ Обновить документацию и gates после удаления `vmrun` из active path.
27.4.1. ✅ Обновить `README.md`.
27.4.2. ✅ Обновить `doc/project_structure.md`.
27.4.3. ✅ Обновить `doc/legacy_inventory.md`.
27.4.4. ✅ Добавить gate на отсутствие `vmrun` в active path.
27.4.5. ✅ Добавить gate на то, что `space.*` остается единственным проектным executable boundary на стороне ОС.
