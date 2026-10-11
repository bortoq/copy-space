#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_collapse_plan.md' README.md
grep -F -q 'doc/resident_host_collapse_plan.md' doc/project_structure.md
grep -F -q '## 21. Минимальный resident launch slice без host decision' doc/roadmap.md
grep -F -q '21.1. ✅ Зафиксировать один tiny resident-controlled launch path.' doc/roadmap.md
grep -F -q '21.2. ✅ Зафиксировать один tiny resident job decision path.' doc/roadmap.md
grep -F -q '21.3. ✅ Зафиксировать проверку host-independent launch slice.' doc/roadmap.md
grep -F -q '21.4. ✅ Обновить документацию под host-independent launch slice.' doc/roadmap.md
grep -F -q 'Этап `21` задает первый маленький путь запуска' doc/resident_host_collapse_plan.md

echo "OK resident host independent launch slice"
