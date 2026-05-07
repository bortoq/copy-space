# Status / прогресс — std7_fixed + forth0 — 2026-05-07

Этот документ — **статус/прогресс** (что уже сделано и чем проверяется), а не “план на будущее”.
План/идеи: `doc/roadmap.md` (и пока `doc/old/20_todo.md`).

Легенда:
- `[x]` — сделано и есть устойчивые проверки/использование
- `[~]` — частично / есть, но стоит усилить
- `[ ]` — не сделано / отложено

---

## A) Инженерные улучшения / стабильность baseline

- [x] Диагностика `VM_ERR`: TDD `scripts/tdd/test_vmerr_diag.sh`
- [x] Стандартизированный test scratch:
  - [x] policy `ART_TESTG == ART_TESTSCR_BASE`
  - [x] `ART_TESTSCR_BASE/ART_TESTSCR_END` (ART[63..64])
  - [x] TDD: `scripts/tdd/test_scratch_abi.sh`, `scripts/tdd/test_scratch_artifacts.sh`
- [x] Fail bundles: TDD `scripts/tdd/test_fail_bundle.sh`
- [x] vmrep tooling selftest: TDD `scripts/tdd/test_vmrep_tools.sh`
- [x] ABI doc sync: TDD `scripts/tdd/test_art_doc_sync.sh` (`scripts/check_art_doc_sync.py --doc doc/abi_artifacts.md`)
- [x] CI: `.github/workflows/ci.yml` (make bins / make test / make tdd / art doc sync)

---

## B) 2b pointers (Block pointers) — пригодность без расширения ART

### 2b базовые указатели / ptrprims
- [x] `LITAP/LITBP/LITRP`, `VAR_AP/VAR_BP/VAR_RP` (ART[55..60])
- [x] `LOAD24AP/LOAD24BP/STORE24RP` (ART[67..69])
- [x] Padding semantics — Forth0/TDD: `src/forth0/tests/test_ptrprims_padding.f0` (через `scripts/tdd/test_forth0_ptrprims.sh`)

### derived pointer arithmetic (без новых ART)
- [x] `INC_PTR32` (derived) — Forth0/TDD: `src/forth0/tests/test_incptr32.f0` (`scripts/tdd/test_forth0_ptr32.sh`)
- [x] `ADD_PTR_CONST32` (derived) — Forth0/TDD: `src/forth0/tests/test_addptr_const32.f0` (`scripts/tdd/test_forth0_ptr32.sh`)

### derived “P-слова” через примитивы
- [x] `ADD24P` via prims — Forth0/TDD: `src/forth0/tests/test_add24p_via_prims.f0` (`scripts/tdd/test_forth0_add24p.sh`)
- [x] `LT24P` via prims — Forth0/TDD: `src/forth0/tests/test_lt24p_via_prims.f0` (`scripts/tdd/test_forth0_lt24p.sh`)
- [x] `EQ24P` — Forth0/TDD: `src/forth0/tests/test_eq24p.f0` (`scripts/tdd/test_forth0_ptrprims.sh`)

### Alignment contract
- [x] Host-side strict check (optional): `F0C_STRICT_ALIGN32=1` + TDD `scripts/tdd/test_forth0c_strict.sh`
- [ ] Runtime-check в VM (не обязателен для baseline; можно добавить позже при необходимости)

### Отложено
- [ ] Raw bit pointers / bit pointers — отложено (не блокирует block pointers baseline)

---

## Forth0 (цель: разрабатывать через `.f0`, минимально трогая codebase)

- [x] Host-компилятор: `build/bin/forth0c` (wrapper: `src/tools/forth0c.c`, реализация: `src/forth0/host/`)
- [x] Pipeline исполнения: `mkimage_std7_fixed` → `vmrun` (compile) → `vmprep_forth0` → `vmrun` (run)
- [x] `forth0c` поддерживает:
  - [x] `include`, `const`, `emit`
  - [x] директивы `copybits`, `setbit/setbyte/set24`
  - [x] макросы `macro ... endmacro` + вызовы `NAME(expr,...)`
  - [x] compile-time цикл `for i start end ... endfor`
- [x] `make test` и `make tdd` используют `.f0`-тесты (forth0-first)
- [x] Legacy C token-generators опциональны: `make tok` / `make TOK=1 bins`

---

## 2a арифметика (закрепление baseline)

- [x] Forth0/TDD:
  - [x] `ADD24`: `src/forth0/tests/test_add24.f0`
  - [x] `EQ24`:  `src/forth0/tests/test_eq24.f0`
  - [x] `LT24`:  `src/forth0/tests/test_lt24.f0`
  - (через `scripts/tdd/test_forth0_2a.sh`)

---

## Следующие шаги (кратко)

- [ ] (Doc) Привести roadmap (`doc/roadmap.md`) к актуальному виду (без дублирования со status)
- [ ] (C) Bench CSV schema + harness
- [ ] (C) Layer scheduler / replication trees (broadcast under vertex-disjoint constraint)
