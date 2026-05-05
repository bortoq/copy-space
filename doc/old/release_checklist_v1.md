# doc/release_checklist_v1.md — Release checklist v1 — 2026-05-05

Этот чеклист фиксирует, что считается “готовым v1” для baseline Copy-Space / Forth0 (std7_fixed),
в режиме “вертикальные срезы + тесты”, без бесконтрольного роста ABI.

## 1) Сборка и тесты (обязательно)
- [x] `make` PASS
- [x] `make test` PASS
- [x] `make tdd` PASS
- [x] `scripts/check_art_doc_sync.py` PASS

## 2) ABI/документация (обязательно)
- [x] `doc/abi_std7_fixed_artifacts.md` актуален и соответствует `ART_COUNT`
- [x] Scratch ABI зафиксирован:
  - [x] `ART[43]=TESTG == TESTSCR_BASE`
  - [x] `ART[64]=TESTSCR_END` (1 past end)
- [x] Bus/TERM0 публикация через ART:
  - [x] `ART[65]=BUS_BASE`
  - [x] `ART[66]=TERM0_DESC`

## 3) todo B (указатели, block pointers) — “достаточно для алгоритмов” (обязательно)
- [x] `LITAP/LITBP/LITRP` работают
- [x] block-pointer primitives:
  - [x] `LOAD24AP` (ART[67])
  - [x] `LOAD24BP` (ART[68])
  - [x] `STORE24RP` (ART[69])
- [x] есть end-to-end тест “ADD24 по указателям пишет результат по RP” (`mktok_test_add24p_via_prims`)
- [x] есть тест “LT24 по указателям” (`mktok_test_lt24p_via_prims`)
- [x] pointer arithmetic добавлен “как макросы” (без новых слов/ABI): используется в token-tests (AP/BP/RP += 32)

Контракт:
- [x] block pointers: `bitaddr % 32 == 0`
- [x] 24-bit data лежит в `[base..base+23]` внутри 32-bit блока

## 4) todo D (устройства/каналы) — минимальный доказательный кусок (обязательно)
- [x] self-describing TERM0 device (descriptor + 3 channel headers) размещён в bus region
- [x] публикация через ART `BUS_BASE` и `TERM0_DESC`
- [x] TDD-регресс-тест `scripts/tdd/test_term0_desc_abi.sh` проверяет:
  - [x] `CDEV` magic/version/type/port_count
  - [x] 3 порта (stdin/stdout/stderr)
  - [x] `chan_base` указывает на `CHN1`

## 5) todo C.0 (измеримость/CSV) — минимально (желательно, но сильно усиливает демонстрацию)
- [x] `scripts/vmrep_to_csv.py` конвертирует vmrep-блок из лога в unified CSV schema v1
- [x] “одна команда → CSV” обёртки:
  - [x] `scripts/bench_pack_csv.sh`
  - [x] `scripts/bench_permute_csv.sh`
  - [x] `scripts/bench_bulkcopy_csv.sh`
- [ ] `moved_bits_total` (семантическая метрика бенча) пока оставлена пустой (не блокирует v1)

## 6) Неблокирующие улучшения (после v1)
- [ ] ускорение bitcpy fast-path (byte-aligned → memmove, n==1)
- [ ] унифицировать bench-обёртки в один `bench_csv.sh`
- [ ] расширение pointer arithmetic (если потребуется)
- [ ] channel manager / guest isolation (следующие этапы todo D/E)
