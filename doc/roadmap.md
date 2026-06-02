# Copy-Space Roadmap

Цель: довести `RISC-V` до состояния, в котором гостевой код реально и доказуемо исполняется *внутри* адресного пространства Copy-Space, а хостовый `space.*` сведен к минимальному контракту: копирование в каналы и из каналов, выполнение `copy` полуинтервалов по инструкциям процессорных слотов, останов пространства и одноразовая загрузка данных в один слот процессора перед первым тактом.

## Правила ведения документа

Этот документ хранит только этапы достижения цели проекта.

1. ✅ Включать только этапы и пункты-действия.
1.1. ✅ Не включать аудит, диагностику, ретроспективу, анализ причин и обзор состояния.
1.2. ✅ Любые результаты проверок и расследований выносить в отдельные документы.

2. ✅ Каждый пункт формулировать как действие.
2.1. ✅ Каждый пункт должен описывать выполненное или запланированное действие.
2.2. ✅ Недопустимы формулировки состояния, проблемы, риска или вывода аудита вместо действия.
2.3. ✅ Предпочтительная форма: `Реализовать`, `Добавить`, `Зафиксировать`, `Переписать`, `Построить`.

3. ✅ Использовать только статусы `✅` и `❌`.
3.1. ✅ `✅` означает завершенное действие.
3.2. ✅ `❌` означает незавершенное или запланированное действие.
3.3. ✅ Пунктов без статуса быть не должно.

4. ✅ Сохранять строгую иерархическую нумерацию.
4.1. ✅ Верхний уровень: `1.`, `2.`, `3.`.
4.2. ✅ Подуровни: `1.1.`, `1.1.1.` и далее.
4.3. ✅ При изменениях перенумеровывать документ вручную без разрывов.

5. ✅ Сохранять назначение и вид документа.
5.1. ✅ Заголовки разделов должны описывать этапы работ.
5.2. ✅ Один пункт должен описывать одно действие.
5.3. ✅ Крупные действия раскладывать на подпункты.
5.4. ✅ Все, что не является действием по достижению цели, выносить из `roadmap`.

## 1. База исполнения

1.1. ✅ Реализовать бит-адресуемую VM-подложку.
1.1.1. ✅ Поддержать активный runtime в `src/vm/space.c`.
1.1.2. ✅ Зафиксировать публичный интерфейс VM в `src/vm/space.h`.
1.1.3. ✅ Сохранить рабочий toolchain сборки/запуска (`vmrun`, `mkimage_std7_fixed`, `forth0c`, `vmprep_forth0`).

1.2. ✅ Реализовать путь сборки образа пространства.
1.2.1. ✅ Поддержать layout/build path в `src/mkimage/std7_fixed/`.
1.2.2. ✅ Подключить таблицы адресов и артефактов в сборку образа.
1.2.3. ✅ Добавить tooling для `rv32m`-образов и загрузки (`scripts/riscv/rv32m_image_builder.py`, `src/tools/rv32m_loader_tool.c`).

1.3. ✅ Реализовать базовые MMIO/channel/watchdog-механизмы.
1.3.1. ✅ Поддержать loader MMIO path в `src/vm/space.c`.
1.3.2. ✅ Поддержать channel ABI entrypoint в `service_channel()`.
1.3.3. ✅ Поддержать bounded-run/watchdog control в runtime.

## 2. Текущий минимум in-space RISC-V

2.1. ✅ Реализовать минимальный runtime ABI внутри VM.
2.1.1. ✅ Поддержать `STATUS`, `LOAD_CODE`, `RUN`, `STEP`, `READ_REGS`, `READ_MEM`, `WRITE_MEM`.
2.1.2. ✅ Добавить C-level harnesses для этих ops в `scripts/tdd/test_rv32_runtime_abi_ops.sh` и `scripts/tdd/test_rv32_guest_run_contract.sh`.

2.2. ✅ Зафиксировать гостевое состояние в пространстве.
2.2.1. ✅ Выделить `G_PC`.
2.2.2. ✅ Выделить `G_REG_BASE`.
2.2.3. ✅ Выделить `G_MEM_BASE`.

2.3. ✅ Реализовать минимальный in-space guest stepper.
2.3.1. ✅ Добавить исполнение `ADDI`.
2.3.2. ✅ Добавить исполнение `LW` и `SW`.
2.3.3. ✅ Добавить исполнение `BEQ`, `BNE`, `JAL`.
2.3.4. ✅ Добавить детерминированную остановку на unsupported instructions.

## 3. Достижение полноценного bootstrap RV32I

3.1. ✅ Реализовать оставшиеся bootstrap RV32I U-type instructions в активном runtime.
3.1.1. ✅ Добавить `LUI`.
3.1.2. ✅ Добавить `AUIPC`.

3.2. ✅ Реализовать оставшиеся bootstrap RV32I compare instructions в активном runtime.
3.2.1. ✅ Добавить `SLTI`.
3.2.2. ✅ Добавить `SLTIU`.
3.2.3. ✅ Добавить `SLT`.
3.2.4. ✅ Добавить `SLTU`.

3.3. ✅ Реализовать оставшиеся bootstrap RV32I boolean instructions в активном runtime.
3.3.1. ✅ Добавить `XORI`.
3.3.2. ✅ Добавить `ORI`.
3.3.3. ✅ Добавить `ANDI`.
3.3.4. ✅ Добавить `XOR`.
3.3.5. ✅ Добавить `OR`.
3.3.6. ✅ Добавить `AND`.

3.4. ✅ Реализовать оставшиеся bootstrap RV32I shift instructions в активном runtime.
3.4.1. ✅ Добавить `SLLI`.
3.4.2. ✅ Добавить `SRLI`.
3.4.3. ✅ Добавить `SRAI`.
3.4.4. ✅ Добавить `SLL`.
3.4.5. ✅ Добавить `SRL`.
3.4.6. ✅ Добавить `SRA`.

3.5. ✅ Реализовать оставшиеся bootstrap RV32I control-flow instructions.
3.5.1. ✅ Добавить `JALR`.
3.5.2. ✅ Добавить `BLT`.
3.5.3. ✅ Добавить `BGE`.
3.5.4. ✅ Добавить `BLTU`.
3.5.5. ✅ Добавить `BGEU`.
3.5.6. ✅ Зафиксировать правило изменения `PC` для sequential path.
3.5.7. ✅ Зафиксировать правило изменения `PC` для branch-taken path.
3.5.8. ✅ Зафиксировать правило изменения `PC` для jump path.

3.6. ✅ Реализовать оставшиеся bootstrap RV32I memory instructions.
3.6.1. ✅ Добавить `LB`.
3.6.2. ✅ Добавить `LBU`.
3.6.3. ✅ Добавить `LH`.
3.6.4. ✅ Добавить `LHU`.
3.6.5. ✅ Добавить `SB`.
3.6.6. ✅ Добавить `SH`.

3.7. ✅ Зафиксировать bootstrap RV32I memory semantics.
3.7.1. ✅ Зафиксировать sign-extension rule для `LB`.
3.7.2. ✅ Зафиксировать sign-extension rule для `LH`.
3.7.3. ✅ Зафиксировать alignment behavior для byte accesses.
3.7.4. ✅ Зафиксировать alignment behavior для halfword accesses.
3.7.5. ✅ Зафиксировать alignment behavior для word accesses.
3.7.6. ✅ Зафиксировать bounds behavior для guest memory accesses.

3.8. ✅ Зафиксировать архитектурные инварианты bootstrap runtime.
3.8.1. ✅ Зафиксировать поведение `x0`.
3.8.2. ✅ Зафиксировать progression `pc`.
3.8.3. ✅ Зафиксировать progression `step`.
3.8.4. ✅ Зафиксировать progression `stop_reason`.
3.8.5. ✅ Зафиксировать deterministic unsupported path.

## 4. Доказательная инфраструктура bootstrap runtime

4.1. ✅ Зафиксировать формат proof-grade trace для bootstrap runtime.
4.1.1. ✅ Зафиксировать запись raw `PC`.
4.1.2. ✅ Зафиксировать запись raw instruction word.
4.1.3. ✅ Зафиксировать запись decoder fields.
4.1.4. ✅ Зафиксировать запись register deltas.
4.1.5. ✅ Зафиксировать запись memory writes.
4.1.6. ✅ Зафиксировать запись stop reason.

4.2. ✅ Добавить извлечение proof-grade trace из активного bootstrap executor.
4.2.1. ✅ Добавить runtime emission trace records.
4.2.2. ✅ Добавить временный bootstrap trace buffer в `space.*`.
4.2.2.1. ✅ Добавить layout временного bootstrap trace buffer.
4.2.2.2. ✅ Добавить запись trace records во временный bootstrap trace buffer.
4.2.3. ✅ Добавить временный bootstrap trace ABI для чтения raw trace artifacts.
4.2.3.1. ✅ Добавить чтение метаданных временного bootstrap trace buffer.
4.2.3.2. ✅ Добавить чтение байт временного bootstrap trace buffer.
4.2.4. ✅ Добавить host-side capture raw trace artifacts.
4.2.5. ✅ Добавить сохранение trace artifacts в repeatable format.

4.3. ✅ Перестроить trace-based validation на raw runtime trace.
4.3.1. ✅ Убрать synthetic trace generation из active proof path.
4.3.2. ✅ Перенести trace diff на raw runtime trace как на единственный источник истины.
4.3.3. ✅ Добавить hard fail при отсутствии raw execution trace.

4.4. ✅ Перестроить state-based validation на ABI-visible assertions.
4.4.1. ✅ Убрать scaffold-only `TESTG` checks из active proof path.
4.4.2. ✅ Добавить failure bundles на основе реального runtime execution.
4.4.3. ✅ Оставить в release path только ABI-visible assertions.

4.5. ✅ Построить directed validation matrix для bootstrap RV32I.
4.5.1. ✅ Добавить directed tests для U-type instructions.
4.5.2. ✅ Добавить directed tests для compare instructions.
4.5.3. ✅ Добавить directed tests для boolean instructions.
4.5.4. ✅ Добавить directed tests для shift instructions.
4.5.5. ✅ Добавить directed tests для control-flow instructions.
4.5.6. ✅ Добавить directed tests для byte/halfword memory instructions.
4.5.7. ✅ Добавить negative tests для alignment faults.
4.5.8. ✅ Добавить negative tests для bounds faults.
4.5.9. ✅ Добавить negative tests для unsupported instructions.
4.5.10. ✅ Добавить deterministic replay checks.

## 5. Очистка bootstrap path

5.1. ✅ Закрепить `LOAD_CODE -> RUN/STEP -> READ_*` как единственный bootstrap closure path.
5.1.1. ✅ Оставить `C3_RUN` только как исследовательскую ветку до появления in-space control plane.
5.1.2. ✅ Исключить host-assisted helpers из bootstrap correctness path.
5.1.3. ✅ Исключить synthetic/scaffold gates из bootstrap release path.

5.2. ✅ Закрыть bootstrap RV32I как доказанный временный контур.
5.2.1. ✅ Зафиксировать bootstrap ABI contract как временный переходный контракт.
5.2.1.1. ✅ Зафиксировать временный bootstrap trace ABI как временный proof-only контракт.
5.2.2. ✅ Зафиксировать bootstrap proof set как достаточный для начала реконструкции `space.*`.
5.2.3. ✅ Зафиксировать запрет на расширение host-side guest logic сверх bootstrap closure.

## 6. Подготовка реконструкции эмулятора пространства

6.1. ❌ Зафиксировать финальный минимальный контракт хостового `space.*`.
6.1.1. ❌ Зафиксировать копирование в каналы и из каналов как единственную channel-функцию хоста.
6.1.2. ❌ Зафиксировать выполнение `copy` полуинтервалов по инструкциям процессорных слотов как единственную compute-функцию хоста.
6.1.3. ❌ Зафиксировать останов пространства как единственную control-функцию хоста.
6.1.4. ❌ Зафиксировать одноразовую загрузку данных в один слот процессора перед первым тактом как единственную bootstrap-функцию хоста.

6.2. ❌ Зафиксировать resident in-space control plane, который заменит bootstrap ABI.
6.2.1. ❌ Зафиксировать resident memory layout control plane.
6.2.1.1. ❌ Зафиксировать размещение resident dispatcher state.
6.2.1.2. ❌ Зафиксировать размещение resident request/response buffers.
6.2.1.3. ❌ Зафиксировать размещение resident service code.
6.2.2. ❌ Зафиксировать resident channel protocol внутри пространства.
6.2.2.1. ❌ Зафиксировать формат resident request.
6.2.2.2. ❌ Зафиксировать формат resident response.
6.2.2.3. ❌ Зафиксировать handshake semantics resident protocol.
6.2.3. ❌ Зафиксировать resident bootstrapping sequence от одного загруженного слота.
6.2.3.1. ❌ Зафиксировать начальную загрузку resident bootstrap payload.
6.2.3.2. ❌ Зафиксировать развертывание resident dispatcher в пространстве.
6.2.3.3. ❌ Зафиксировать переход от bootstrap payload к resident steady-state.
6.2.4. ❌ Зафиксировать resident handoff от bootstrap path к in-space control plane.
6.2.4.1. ❌ Зафиксировать момент завершения bootstrap ABI.
6.2.4.2. ❌ Зафиксировать первый запрос, обслуживаемый resident control plane.
6.2.4.3. ❌ Зафиксировать rollback/fail behavior при срыве handoff.

6.3. ❌ Зафиксировать resident in-space guest runtime, который заменит host-side runtime.
6.3.1. ❌ Зафиксировать resident decode/dispatch contract.
6.3.1.1. ❌ Зафиксировать resident fetch contract.
6.3.1.2. ❌ Зафиксировать resident decode contract.
6.3.1.3. ❌ Зафиксировать resident execute/commit contract.
6.3.2. ❌ Зафиксировать resident guest state contract (`PC`, register file, guest memory).
6.3.2.1. ❌ Зафиксировать resident `PC` layout and ownership.
6.3.2.2. ❌ Зафиксировать resident register file layout and ownership.
6.3.2.3. ❌ Зафиксировать resident guest memory layout and ownership.
6.3.3. ❌ Зафиксировать resident stop/fault contract.
6.3.3.1. ❌ Зафиксировать resident unsupported-instruction behavior.
6.3.3.2. ❌ Зафиксировать resident alignment-fault behavior.
6.3.3.3. ❌ Зафиксировать resident bounds-fault behavior.
6.3.4. ❌ Зафиксировать resident trace/proof contract после удаления host-side executor.
6.3.4.1. ❌ Зафиксировать источник resident trace records.
6.3.4.2. ❌ Зафиксировать способ извлечения resident trace records наружу.
6.3.4.3. ❌ Зафиксировать соответствие resident trace contract bootstrap trace contract.
6.3.4.4. ❌ Зафиксировать замену временного bootstrap trace ABI на resident trace contract.

6.4. ❌ Зафиксировать план миграции доказательной инфраструктуры на финальный контракт.
6.4.1. ❌ Зафиксировать миграцию proof artifacts с bootstrap ABI на final channel-only contract.
6.4.1.1. ❌ Зафиксировать замену bootstrap trace artifacts на resident trace artifacts.
6.4.1.2. ❌ Зафиксировать замену bootstrap state artifacts на resident state artifacts.
6.4.2. ❌ Зафиксировать миграцию validation gates с bootstrap executor на resident executor.
6.4.2.1. ❌ Зафиксировать миграцию directed instruction-family gates.
6.4.2.2. ❌ Зафиксировать миграцию negative/fault gates.
6.4.2.3. ❌ Зафиксировать миграцию replay/determinism gates.
6.4.3. ❌ Зафиксировать критерий готовности к сокращению `space.*`.
6.4.3.1. ❌ Зафиксировать критерий готовности resident control plane.
6.4.3.2. ❌ Зафиксировать критерий готовности resident executor.
6.4.3.3. ❌ Зафиксировать критерий готовности proof gates.

## 7. Построение resident in-space control plane

7.1. ❌ Перенести host-side channel ABI логику внутрь адресного пространства.
7.1.1. ❌ Перенести диспетчеризацию `STATUS` в in-space код.
7.1.2. ❌ Перенести диспетчеризацию `LOAD_CODE` в in-space код.
7.1.3. ❌ Перенести диспетчеризацию `RUN` и `STEP` в in-space код.
7.1.4. ❌ Перенести диспетчеризацию `READ_REGS`, `READ_MEM`, `WRITE_MEM` в in-space код.

7.2. ❌ Перенести host-side execution control внутрь адресного пространства.
7.2.1. ❌ Перенести watchdog control в in-space код.
7.2.2. ❌ Перенести bounded-run control в in-space код.
7.2.3. ❌ Перенести guest lifecycle control в in-space код.

7.3. ❌ Перенести host-side guest execution semantics внутрь адресного пространства.
7.3.1. ❌ Перенести resident fetch/decode path `RISC-V` instructions в in-space код.
7.3.1.1. ❌ Перенести resident fetch path в in-space код.
7.3.1.2. ❌ Перенести resident decode path в in-space код.
7.3.1.3. ❌ Перенести resident dispatch path в in-space код.
7.3.2. ❌ Перенести resident execute/commit path `RISC-V` instructions в in-space код.
7.3.2.1. ❌ Перенести resident arithmetic/logic execution в in-space код.
7.3.2.2. ❌ Перенести resident control-flow execution в in-space код.
7.3.2.3. ❌ Перенести resident memory execution в in-space код.
7.3.3. ❌ Перенести управление `PC` в in-space код.
7.3.3.1. ❌ Перенести sequential `PC` progression в in-space код.
7.3.3.2. ❌ Перенести branch/jump `PC` progression в in-space код.
7.3.4. ❌ Перенести управление register file в in-space код.
7.3.4.1. ❌ Перенести resident register reads в in-space код.
7.3.4.2. ❌ Перенести resident register writes в in-space код.
7.3.4.3. ❌ Перенести resident `x0` invariant в in-space код.
7.3.5. ❌ Перенести управление guest memory в in-space код.
7.3.5.1. ❌ Перенести resident guest loads в in-space код.
7.3.5.2. ❌ Перенести resident guest stores в in-space код.
7.3.5.3. ❌ Перенести resident memory bounds checks в in-space код.
7.3.6. ❌ Перенести stop/fault semantics в in-space код.
7.3.6.1. ❌ Перенести unsupported stop path в in-space код.
7.3.6.2. ❌ Перенести alignment-fault path в in-space код.
7.3.6.3. ❌ Перенести bounds-fault path в in-space код.

7.4. ❌ Перенести доказательную инфраструктуру на resident executor.
7.4.1. ❌ Перенести runtime trace production на resident executor.
7.4.1.1. ❌ Перенести resident trace emission.
7.4.1.2. ❌ Перенести resident trace extraction.
7.4.1.3. ❌ Перенести resident trace artifact persistence.
7.4.2. ❌ Перенести validation gates на resident executor.
7.4.2.1. ❌ Перенести directed instruction-family gates.
7.4.2.2. ❌ Перенести negative/fault gates.
7.4.2.3. ❌ Перенести replay/determinism gates.
7.4.3. ❌ Зафиксировать resident closure path как доказанный.
7.4.3.1. ❌ Зафиксировать resident trace evidence как достаточное.
7.4.3.2. ❌ Зафиксировать resident state evidence как достаточное.
7.4.3.3. ❌ Зафиксировать resident release path как единственный активный path.

## 8. Реконструкция эмулятора пространства

8.1. ❌ Удалить из `space.*` host-side channel ABI после подтверждения resident control plane.
8.1.1. ❌ Удалить host-side dispatch `STATUS`.
8.1.2. ❌ Удалить host-side dispatch `LOAD_CODE`.
8.1.3. ❌ Удалить host-side dispatch `RUN` и `STEP`.
8.1.4. ❌ Удалить host-side dispatch `READ_REGS`, `READ_MEM`, `WRITE_MEM`.

8.2. ❌ Удалить из `space.*` host-side guest runtime после подтверждения resident executor.
8.2.1. ❌ Удалить host-side fetch/decode/dispatch `RISC-V`.
8.2.1.1. ❌ Удалить host-side fetch path.
8.2.1.2. ❌ Удалить host-side decode path.
8.2.1.3. ❌ Удалить host-side dispatch path.
8.2.2. ❌ Удалить host-side execute/commit logic.
8.2.2.1. ❌ Удалить host-side arithmetic/logic execution.
8.2.2.2. ❌ Удалить host-side control-flow execution.
8.2.2.3. ❌ Удалить host-side memory execution.
8.2.3. ❌ Удалить host-side guest state management.
8.2.3.1. ❌ Удалить host-side управление `PC`.
8.2.3.2. ❌ Удалить host-side управление register file.
8.2.3.3. ❌ Удалить host-side управление guest memory.
8.2.4. ❌ Удалить host-side stop/fault semantics.
8.2.4.1. ❌ Удалить host-side unsupported stop path.
8.2.4.2. ❌ Удалить host-side alignment-fault path.
8.2.4.3. ❌ Удалить host-side bounds-fault path.
8.2.5. ❌ Удалить host-side watchdog и bounded-run service logic.
8.2.5.1. ❌ Удалить host-side watchdog service logic.
8.2.5.2. ❌ Удалить host-side bounded-run service logic.
8.2.6. ❌ Удалить из `space.*` временный bootstrap proof/trace layer.
8.2.6.1. ❌ Удалить host-side bootstrap trace buffer.
8.2.6.2. ❌ Удалить host-side bootstrap trace serialization/readback logic.
8.2.6.3. ❌ Удалить временный bootstrap trace ABI ops и metadata path.

8.3. ❌ Сократить `space.*` до минимального хостового эмулятора.
8.3.1. ❌ Оставить в `space.*` только копирование в каналы и из каналов.
8.3.2. ❌ Оставить в `space.*` только выполнение `copy` полуинтервалов по инструкциям процессорных слотов.
8.3.3. ❌ Оставить в `space.*` только останов пространства.
8.3.4. ❌ Оставить в `space.*` только одноразовую загрузку данных в один слот процессора перед первым тактом.

8.4. ❌ Зафиксировать минимальный контракт финального эмулятора пространства.
8.4.1. ❌ Зафиксировать публичный интерфейс `space.h` в виде, близком к `/media/user/PROJECT/bak/demo1/space.h`.
8.4.2. ❌ Зафиксировать поведение `space.c` в виде, близком к `/media/user/PROJECT/bak/demo1/space.c`.
8.4.3. ❌ Добавить proof gates, подтверждающие что хостовый эмулятор выполняет только минимальный контракт.
8.4.4. ❌ Добавить proof gates, подтверждающие отсутствие host-side trace/proof semantics в финальном эмуляторе.

## 9. Нетривиальные guest workloads

9.1. ❌ Переписать SHA acceptance как реальное guest computation proof.
9.1.1. ❌ Загружать обычный guest binary через финальный in-space control plane.
9.1.1.1. ❌ Подготовить честный guest SHA binary без prearranged digest payload.
9.1.1.2. ❌ Загрузить guest SHA binary через финальный in-space control plane.
9.1.2. ❌ Выполнить guest SHA workload через финальный resident executor.
9.1.2.1. ❌ Довести workload до завершения через финальный channel-only contract.
9.1.2.2. ❌ Зафиксировать trace/state evidence реального выполнения workload.
9.1.3. ❌ Получать digest только из финального channel-visible state.
9.1.3.1. ❌ Считать digest только через финальный channel-visible readback.
9.1.3.2. ❌ Сверить digest с host-side reference without payload shortcut.
9.1.4. ❌ Убрать prearranged payload path из active proof.
9.1.4.1. ❌ Удалить acceptance checks, опирающиеся на заранее уложенный digest.
9.1.4.2. ❌ Зафиксировать SHA gate как proof of computation, а не proof of layout.

## 10. Решение по RV32M

10.1. ❌ Принять и зафиксировать контракт по `RV32M` после завершения финального RV32I closure.
10.1.1. ❌ Либо расширить resident executor до требуемого `RV32M`.
10.1.2. ❌ Либо формально заморозить `M` как unsupported в финальном контракте.
