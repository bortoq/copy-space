# TODO / статус работ — std7_fixed + forth0 (status) — 2026-05-07

Этот документ — **статус/прогресс** (что уже сделано и чем проверяется), а не “план на будущее”.
План/идеи могут жить отдельно (например `doc/20_todo.md`).

Легенда:
- `[x]` — сделано и есть устойчивые проверки/использование
- `[~]` — частично / есть, но стоит усилить
- `[ ]` — не сделано / отложено

---

## A) Инженерные улучшения / стабильность baseline

- [x] Диагностика `VM_ERR`: есть TDD `scripts/tdd/test_vmerr_diag.sh`, в выводе присутствуют tick/slot/n/dst/src и др.
- [x] Стандартизированный test scratch:
  - [x] policy `ART_TESTG == ART_TESTSCR_BASE`
  - [x] `ART_TESTSCR_BASE/ART_TESTSCR_END` (ART[63..64])
  - [x] TDD: `scripts/tdd/test_scratch_abi.sh`, `scripts/tdd/test_scratch_artifacts.sh`
- [x] Fail bundles: TDD `scripts/tdd/test_fail_bundle.sh`
- [x] vmrep tooling selftest: TDD `scripts/tdd/test_vmrep_tools.sh`
- [x] TDD runner устойчивый:
  - [x] `scripts/tdd/run_all.sh` без dead code, корректно учитывает rc каждого теста
  - [x] bash-тест `scripts/tdd/test_ptrprims.sh` запускается через `bash`

---

## B) 2b pointers (Block pointers) — пригодность без расширения ART

### 2b базовые указатели / ptrprims
- [x] `LITAP/LITBP/LITRP`, `VAR_AP/VAR_BP/VAR_RP` (ART[55..60])
- [x] `LOAD24AP/LOAD24BP/STORE24RP` (ART[67..69])
- [x] Padding semantics:
  - [x] C/TDD: `mktok_test_ptrprims_padding` (через `scripts/tdd/test_ptrprims.sh`)
  - [x] Forth0/TDD: `src/forth0/tests/test_ptrprims_padding.f0` (через `scripts/tdd/test_forth0_ptrprims.sh`)

### derived pointer arithmetic (без новых ART)
- [x] `INC_PTR32` (derived) — покрыто в:
  - [x] C: `mktok_test_incptr32` (через `scripts/tdd/test_ptrprims.sh`)
  - [x] Forth0: `src/forth0/tests/test_incptr32.f0` (через `scripts/tdd/test_forth0_ptr32.sh`)
- [x] `ADD_PTR_CONST32` (derived) — покрыто в:
  - [x] C: `mktok_test_addptr_const32` (через `scripts/tdd/test_ptrprims.sh`)
  - [x] Forth0: `src/forth0/tests/test_addptr_const32.f0` (через `scripts/tdd/test_forth0_ptr32.sh`)

### derived “P-слова” через примитивы
- [x] `ADD24P` via prims:
  - [x] C/TDD: `mktok_test_add24p_via_prims`
  - [x] Forth0/TDD: `src/forth0/tests/test_add24p_via_prims.f0` + `scripts/tdd/test_forth0_add24p.sh`
- [x] `LT24P` via prims:
  - [x] C/TDD: `mktok_test_lt24p_via_prims`
  - [x] Forth0/TDD: `src/forth0/tests/test_lt24p_via_prims.f0` + `scripts/tdd/test_forth0_lt24p.sh`

### EQ24P
- [x] `WORD_EQ24P` (ART[62]) присутствует в baseline
- [x] Forth0/TDD: `src/forth0/tests/test_eq24p.f0` (через `scripts/tdd/test_forth0_ptrprims.sh`)

### Остатки/опционально по B
- [~] Alignment contract (AP/BP/RP low5=0): контракт описан, но нет отдельной явной проверки/теста “сломай выравнивание”.
- [ ] Raw bit pointers / bit pointers — сознательно отложено (не блокирует block pointers baseline).

---

## Forth0 (цель: разрабатывать через `.f0`, минимально трогая codebase)

- [x] Host-компилятор: `build/bin/forth0c` (из `src/tools/forth0c.c`, реализация вынесена в `src/forth0/host/*.inc`)
- [x] Pipeline исполнения: `mkimage_std7_fixed` → `vmrun` (compile) → `vmprep_forth0` → `vmrun` (run)
- [x] `forth0c` поддерживает:
  - [x] `include`, `const`, `emit`
  - [x] директивы `copybits`, `setbit/setbyte/set24`
  - [x] макросы `macro ... endmacro` + вызовы `NAME(expr,...)`
  - [x] compile-time цикл `for i start end ... endfor`
- [x] Структура программ: `src/forth0/...`
- [x] Smoke/TDD: `scripts/tdd/test_forth0c.sh` (проверяет include+macro+for)

---

## 2a арифметика (закрепление baseline)

- [x] Forth0/TDD:
  - [x] `ADD24`: `src/forth0/tests/test_add24.f0`
  - [x] `EQ24`:  `src/forth0/tests/test_eq24.f0`
  - [x] `LT24`:  `src/forth0/tests/test_lt24.f0`
  - (через `scripts/tdd/test_forth0_2a.sh`)

---

## Документация / ABI синхронизация

- [x] ABI doc sync: `scripts/tdd/test_art_doc_sync.sh` запускает `scripts/check_art_doc_sync.py --doc doc/abi_artifacts.md`

---

## CI

- [x] GitHub Actions: `.github/workflows/ci.yml` гоняет `make bins`, `check_art_doc_sync.py`, `make test`, `make tdd`

---

## Следующие шаги (кратко)

- [ ] (Doc) Обновить README/документацию под “forth0-first” workflow: как писать `.f0` тесты, как запускать pipeline.
- [ ] (B) Явная проверка/тест alignment контракта для block pointers (low5=0).
- [ ] (Policy) Решить роль `src/tokens/mktok_test_*.c`: оставить как legacy/страховку или постепенно перестать добавлять новые.
