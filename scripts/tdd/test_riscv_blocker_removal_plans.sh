#!/bin/sh
set -eu

grep -F -q '## 9.5. План устранения блокеров 1-4' doc/roadmap.md
grep -F -q '9.5.1. ✅ Зафиксировать границу `space.*` для следующей миграции.' doc/roadmap.md
grep -F -q '9.5.2. ✅ Выделить resident `RISC-V` в отдельный source boundary.' doc/roadmap.md
grep -F -q '9.5.3. ✅ Подготовить proof tools для resident execution.' doc/roadmap.md
grep -F -q '9.5.4. ✅ Использовать resident `RISC-V` как compute backend.' doc/roadmap.md
grep -F -q 'Этот план отражен в `doc/roadmap.md` как этап `9.5` и этапы `11-27`.' doc/riscv_migration_plan.md

echo "OK riscv blocker removal plans"
