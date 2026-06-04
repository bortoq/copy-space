# План сборки resident control plane

Этап `26` задает один конкретный технический план, который собирает launch control, copy scheduling, completion bookkeeping, job selection и tool dispatch в один resident control plane.

## Назначение

Этот план нужен, чтобы получить один resident-owned путь управления после bootstrap. Он не снимает зависимость от host сам по себе. Он подготавливает один общий resident control plane, который потом можно использовать для снятия зависимости безопасно.

## Область

План состоит только из маленьких действий:

- собрать один общий resident state для launch control, copy scheduling, completion bookkeeping, job selection и tool dispatch;
- связать эти части через один resident entrypoint;
- оставить host только bootstrap-only;
- зафиксировать machine-checkable проверки для каждого шага;
- не менять семантику `space.*`.

## Файлы

### `src/vm/rv32.c`

Добавить или объединить следующие функции:

- `rv_launch_control_step()`
- `rv_copy_scheduling_step()`
- `rv_completion_bookkeeping_step()`
- `rv_job_selection_step()`
- `rv_tool_dispatch_step()`
- `rv_control_plane_step()`

Эти функции должны работать только с resident state и не должны принимать решения за host.

### `src/vm/rv32.h`

Добавить декларации для resident control plane state и для функций из `rv32.c`.

### `src/vm/space.c`

Оставить только вызов resident control plane из active runtime path.
Не добавлять новую orchestration semantics в `space.*`.

### `src/tools/vmrun.c`

Оставить только bootstrap wrapper behavior:

- загрузка image;
- bounded run;
- optional dump;
- без execution decisions после bootstrap.

### `scripts/tdd/`

Добавить отдельные gates для:

- launch control step;
- copy scheduling step;
- completion bookkeeping step;
- job selection step;
- tool dispatch step;
- combined control plane step.

## Маленькие задания

### Task 1: Зафиксировать один общий resident state

**Files:**
- Modify: `src/vm/rv32.h`
- Modify: `src/vm/rv32.c`
- Test: `scripts/tdd/test_resident_control_plane_assembly.sh`

- [ ] **Step 1: Write the failing test**

Проверить, что roadmap и документация уже называют этот этап `26`, а функции control plane перечислены в `rv32.h`.

- [ ] **Step 2: Run test to verify it fails**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: fail because control plane symbols are not yet present.

- [ ] **Step 3: Write minimal implementation**

Добавить минимальный resident control plane state в `rv32.h` и только объявления функций.

- [ ] **Step 4: Run test to verify it passes**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: pass.

### Task 2: Связать launch control и copy scheduling

**Files:**
- Modify: `src/vm/rv32.c`
- Modify: `scripts/tdd/test_resident_control_plane_assembly.sh`

- [ ] **Step 1: Write the failing test**

Проверить, что `rv_control_plane_step()` вызывает `rv_launch_control_step()` и `rv_copy_scheduling_step()`.

- [ ] **Step 2: Run test to verify it fails**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: fail until the call chain exists.

- [ ] **Step 3: Write minimal implementation**

Добавить минимальную связку между launch control и copy scheduling.

- [ ] **Step 4: Run test to verify it passes**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: pass.

### Task 3: Связать completion bookkeeping, job selection и tool dispatch

**Files:**
- Modify: `src/vm/rv32.c`
- Modify: `scripts/tdd/test_resident_control_plane_assembly.sh`

- [ ] **Step 1: Write the failing test**

Проверить, что `rv_control_plane_step()` вызывает `rv_completion_bookkeeping_step()`, `rv_job_selection_step()` и `rv_tool_dispatch_step()`.

- [ ] **Step 2: Run test to verify it fails**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: fail until the call chain exists.

- [ ] **Step 3: Write minimal implementation**

Добавить минимальную связку этих шагов в один resident control plane.

- [ ] **Step 4: Run test to verify it passes**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: pass.

### Task 4: Оставить host только bootstrap-only

**Files:**
- Modify: `src/tools/vmrun.c`
- Modify: `scripts/tdd/test_resident_control_plane_assembly.sh`

- [ ] **Step 1: Write the failing test**

Проверить, что `vmrun` не принимает orchestration decisions после bootstrap.

- [ ] **Step 2: Run test to verify it fails**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: fail until host-side decisions are removed from the active path.

- [ ] **Step 3: Write minimal implementation**

Оставить в `vmrun` только bootstrap wrapper behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: pass.

### Task 5: Обновить документацию

**Files:**
- Modify: `doc/roadmap.md`
- Modify: `doc/project_structure.md`
- Modify: `README.md`
- Modify: `doc/resident_host_dependency_collapse_contract.md`

- [ ] **Step 1: Write the failing test**

Проверить, что все документы ссылаются на этот план как на этап `26`, а настоящая зависимость от host перенесена на `27`.

- [ ] **Step 2: Run test to verify it fails**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: fail until docs are synced.

- [ ] **Step 3: Write minimal implementation**

Обновить документы и сдвинуть actual host-dependency collapse на `27`.

- [ ] **Step 4: Run test to verify it passes**

Run: `sh scripts/tdd/test_resident_control_plane_assembly.sh`
Expected: pass.
