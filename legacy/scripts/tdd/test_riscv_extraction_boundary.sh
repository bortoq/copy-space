#!/bin/sh
set -eu

grep -F -q 'src/vm/rv32.c' doc/project_structure.md
grep -F -q 'src/vm/rv32.h' doc/project_structure.md
grep -F -q 'resident execution core and trace helpers' doc/project_structure.md
grep -F -q '## 12. Extract resident `RISC-V` implementation into isolated source' doc/roadmap.md
grep -F -q 'Перенести resident execution logic `RISC-V` в отдельные исходники' doc/riscv_migration_plan.md
grep -F -q 'Использовать `doc/resident_riscv_migration.md` как границу этого этапа.' doc/riscv_migration_plan.md
grep -F -q 'doc/resident_riscv_migration.md' README.md

echo "OK riscv extraction boundary"
