# doc/done.md — Definition of Done (DoD) + текущий прогресс — 2026-05-05

Этот документ фиксирует “что считается готовым” для изменений в репозитории Copy-Space / Forth0, чтобы проект оставался устойчивым и не деградировал от рефакторингов.

## 0) Термины
- **Baseline**: состояние репозитория, которое собирается и проходит тесты.
- **ABI**: контракт адресов/артефактов/структур в `space`.
- **ART**: таблица артефактов (bitaddr), публикуемая mkimage.
- **Append-only ABI**: новые поля/индексы добавляются только в конец, старые не меняются.

## 1) Definition of Done — общий (для любого изменения)
Изменение считается “Done”, если выполнены все пункты:

### 1.1 Сборка и тесты
- [ ] `make` проходит без ошибок (warnings допускаются только если осознанно и документировано; лучше — 0).
- [ ] `make test` PASS.
- [ ] `scripts/test_all.sh` PASS.
- [ ] `scripts/tdd/run_all.sh` PASS (если TDD-набор присутствует в ветке).

### 1.2 Регрессия и отладка
- [ ] Если изменение затрагивает диагностику/ABI/бенчи — добавлен или обновлён тест (token-test или scripts/tdd/*).
- [ ] При падении тестов формируется fail bundle (если сценарий поддерживает).
- [ ] В логе можно найти vmrep блоки (если включены env), и они корректны.

### 1.3 ABI / Документация
- [ ] Если меняется ABI (ART/адреса/layout/структуры), изменения **append-only** и отражены в документации:
  - [ ] `doc/abi_std7_fixed_artifacts.md` обновлён/сгенерен.
  - [ ] `scripts/check_art_doc_sync.py` PASS.
- [ ] Документы имеют заголовок формата:  
  `doc/<name>.md — <title> — YYYY-MM-DD`

### 1.4 Код-организация (минимум)
- [ ] Новые модули добавлены в сборку (Makefile) и реально используются/покрыты тестом.
- [ ] Нет “гигантских блоков” write-инструкций в legacy: по возможности выносить в модули (пример: artifacts/layout/devices).

## 2) Definition of Done — для изменений mkimage/std7_fixed
Дополнительно к общему DoD:

- [ ] mkimage печатает диагностические строки layout/ABI (если это принято как стандарт: ART(byte), TESTSCR_BASE/SIZE).
- [ ] Overlap-check защищает:
  - scratch region
  - pool region
  - bus/devices region (если вводится)
- [ ] Если добавлены новые ART индексы:
  - [ ] обновлён enum `ART_*` + `ART_COUNT`
  - [ ] обновлён writer в `artifacts.c`
  - [ ] обновлена документация ABI и прошёл `check_art_doc_sync.py`

## 3) Definition of Done — для новых слов/микрокода (words_*)
- [ ] Добавлен token-test (src/tokens/mktok_test_*.c) или эквивалентная проверка.
- [ ] Добавлен токен в tokcomp (если слово должно быть доступно через токены).
- [ ] Слово включено в образ mkimage (legacy/orchestrator).
- [ ] Результат проверяется через TESTSCR/TESTG (стандартизированный scratch).

## 4) Definition of Done — для бенчей / vmrep (todo C)
- [ ] bench запускается одним скриптом из `scripts/bench_*.sh` и печатает метрики в стабильном формате.
- [ ] (todo C.0) При появлении unified CSV schema: бенч печатает CSV строго по схеме.

## 5) Текущий статус (что уже сделано на 2026-05-05)

### 5.1 Инженерные улучшения (todo A)
- [x] A.1 VM_ERR диагностика (tick/slot/n/dst/src/kind/space_bits), vmrun возвращает nonzero.
- [x] A.2 Scratch ABI стандартизирован, mkimage печатает TESTSCR/ART; ART содержит TESTSCR_BASE/END.
- [x] A.3 vmrep tools + fail bundles + FORCE_BAD_EXP, TDD тесты на это.

### 5.2 Рефакторинг mkimage/vm (реализация уменьшения legacy)
- [x] vmrep вынесен в `src/vm/diag/vmrep.c`.
- [x] mkimage_std7_fixed: wrapper main + legacy вынесен в `src/mkimage/std7_fixed/legacy.c`.
- [x] PASS2.1: layout вынесен в `layout.c/.h`, overlap-check усилен.

### 5.3 Устройства/каналы MVP (todo D, ранний кусок)
- [x] Добавлен bus region и self-describing terminal device (descriptor + 3 channel headers).
- [x] ART расширен append-only до:
  - [x] ART[65] = BUS_BASE
  - [x] ART[66] = TERM0_DESC

### 5.4 Контроль документа ABI ART
- [x] `scripts/check_art_doc_sync.py` добавлен и используется для проверки упоминаний ART индексов в doc.
- [x] (если применено) генерация `doc/abi_std7_fixed_artifacts.md` из кода — через `scripts/gen_abi_artifacts_doc.py`.

### 5.5 Указатели (todo B)
- [~] Старт 2b сделан: EQ24P + LITAP/LITBP/LITRP + VAR_AP/BP/RP + OFFTAB.
- [ ] Осталось для “приготавливаемости”: LT24P/ADD24P/store по RP/ptr arith + тесты.

## 6) TODO: ближайшие документы-спеки (рекомендуемые)
- [ ] doc/??_ptrs_block_pointers.md — ABI/семантика block pointers (todo B)
- [ ] doc/??_bench_csv_schema.md — unified CSV schema (todo C.0)
- [ ] doc/??_term0_descriptor_abi.md — фиксированный layout CDEV/CHN1 (если хотите жёсткий контракт)