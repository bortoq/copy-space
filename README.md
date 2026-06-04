# Copy-Space

Этот репозиторий сведен к антикризисному минимуму.

Текущая цель:
- довести resident `RV32I` proof-closure в `space.c`
- завершить перенос orchestration и toolchain control в resident code
- использовать resident `RISC-V` как вычислительную опору для переноса других частей проекта
- считать `host` только временной bootstrap-обвязкой вокруг `space.*`

Активный baseline:
- `src/vm/space.c`
- `src/vm/space.h`
- `src/vm/rv32.c`
- `src/vm/rv32.h`
- `src/vm/bitcpy.c`
- `src/tools/vmrun.c`
- активные `scripts/tdd/` gates
- активная документация:
  - `doc/project_structure.md`
  - `doc/roadmap.md`
  - `doc/anticrisis_plan.md`
  - `doc/space_contract.md`
  - `doc/glossary.md`
  - `doc/legacy_inventory.md`
  - `doc/resident_copicode_runtime_boundary.md`
  - `doc/resident_copicode_migration_plan.md`
  - `doc/resident_orchestration_runtime_boundary.md`
  - `doc/resident_startup_contract.md`
  - `doc/resident_orchestration_execution_runtime.md`
  - `doc/resident_copy_scheduling_runtime.md`
  - `doc/resident_test_orchestration_runtime.md`
  - `doc/resident_host_dependency_collapse_contract.md`
  - `doc/resident_host_independent_launch_slice.md`
  - `doc/resident_launch_control_ownership.md`
  - `doc/resident_copy_scheduling_ownership.md`
  - `doc/resident_completion_bookkeeping_ownership.md`
  - `doc/resident_job_selection_tool_dispatch_ownership.md`
  - `doc/resident_control_plane_assembly_plan.md`
  - `doc/resident_copicode_artifact.md`
  - `doc/resident_copicode_handoff.md`
  - `doc/resident_copicode_decision_records.md`
  - `doc/resident_copicode_toolchain_control_records.md`
  - `doc/resident_copicode_launch_completion.md`
  - `doc/riscv_migration_plan.md`
  - `doc/resident_riscv_boundary_freeze.md`
  - `doc/resident_riscv_extraction_boundary.md`
  - `doc/resident_riscv_compute_backend.md`
  - `doc/resident_riscv_proof_tools_preparation.md`

Единственный допустимый активный путь доказательства:
- resident `RV32I` путь через `space.c`
- проверки fault/trace/control для resident-кода

Быстрый старт:

```sh
make bins
sh scripts/tdd/run_all.sh
```

План:
- [doc/anticrisis_plan.md](/home/user/work/copy-space/doc/anticrisis_plan.md:1)
- [doc/roadmap.md](/home/user/work/copy-space/doc/roadmap.md:1)
- [doc/legacy_inventory.md](/home/user/work/copy-space/doc/legacy_inventory.md:1)

Исторический материал заморожен в legacy inventory и при необходимости восстанавливается из git.
