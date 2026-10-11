#!/bin/sh
set -eu

grep -F -q 'должен оставаться только эмулятором адресного пространства' doc/space_contract.md
grep -F -q 'doc/resident_riscv_migration.md' README.md
grep -F -q 'doc/riscv_migration_plan.md' doc/project_structure.md
grep -F -q '## 11. Freeze the `space.*` boundary for the next migration' doc/roadmap.md
grep -F -q '## 12. Extract resident `RISC-V` implementation into isolated source' doc/roadmap.md
grep -F -q '## 13. Prepare proof tools for resident execution' doc/roadmap.md
grep -F -q '## 14. Use resident `RISC-V` as a migration compute backend' doc/roadmap.md
grep -F -q '## 15. Define the resident orchestration runtime boundary' doc/roadmap.md
grep -F -q '## 16. Implement the minimal resident startup contract' doc/roadmap.md
grep -F -q '## 17. Минимальный resident runtime для orchestration' doc/roadmap.md
grep -F -q '## 18. Минимальный resident runtime для copy scheduling' doc/roadmap.md
grep -F -q '## 19. Минимальный resident runtime для test orchestration' doc/roadmap.md
grep -F -q '## 20. Контракт на минимальное снятие зависимости от host' doc/roadmap.md
grep -F -q '## 21. Минимальный resident launch slice без host decision' doc/roadmap.md
grep -F -q '## 22. Контракт на владение запуском resident code' doc/roadmap.md
grep -F -q '## 23. Контракт на владение minimal copy scheduling' doc/roadmap.md
grep -F -q '## 24. Контракт на владение completion bookkeeping' doc/roadmap.md
grep -F -q '## 25. Контракт на владение job selection и tool dispatch после bootstrap' doc/roadmap.md
grep -F -q '## 26. План сборки resident control plane' doc/roadmap.md
grep -F -q '## 27. Сделать `space.*` единственным проектным executable boundary на стороне ОС' doc/roadmap.md
grep -F -q '27.2. ✅ Свести `space.*` к чистому эмулятору адресного пространства.' doc/roadmap.md
grep -F -q '27.2.1. ✅ Оставить в `space.*` только эмуляцию адресного пространства и минимальный host bootstrap contract.' doc/roadmap.md
grep -F -q '27.2.2. ✅ Удалить из `space.*` всю остаточную управляющую логику, не нужную эмулятору.' doc/roadmap.md
grep -F -q '27.2.3. ✅ Запретить рост host-side orchestration semantics в `space.*`.' doc/roadmap.md
grep -F -q 'Финальная граница проекта на стороне ОС такова:' doc/space_contract.md

echo "OK riscv boundary freeze"
