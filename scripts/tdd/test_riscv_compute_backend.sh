#!/bin/sh
set -eu

grep -F -q 'doc/resident_riscv_migration.md' README.md
grep -F -q 'doc/resident_riscv_migration.md' doc/project_structure.md
grep -F -q '## 14. Use resident `RISC-V` as a migration compute backend' doc/roadmap.md
grep -F -q 'Использовать resident `RISC-V` для одного маленького migration payload.' doc/riscv_migration_plan.md
grep -F -q 'Использовать resident `RISC-V` для одного proof/helper workload, которому полезен resident compute.' doc/riscv_migration_plan.md

echo "OK riscv compute backend"
