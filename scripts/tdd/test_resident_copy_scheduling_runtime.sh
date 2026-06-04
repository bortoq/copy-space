#!/bin/sh
set -eu

grep -F -q 'doc/resident_copy_scheduling_runtime.md' README.md
grep -F -q 'doc/resident_copy_scheduling_runtime.md' doc/project_structure.md
grep -F -q '## 18. Минимальный resident runtime для copy scheduling' doc/roadmap.md
grep -F -q '18.1. ✅ Зафиксировать форму и состояние fixed-slot scheduling.' doc/roadmap.md
grep -F -q '18.2. ✅ Зафиксировать учет запуска и завершения для copy scheduling.' doc/roadmap.md
grep -F -q '18.3. ✅ Зафиксировать минимальный channel service для copy scheduling.' doc/roadmap.md
grep -F -q '18.4. ✅ Обновить документацию для copy scheduling runtime.' doc/roadmap.md
grep -F -q 'Этап `18` задает минимальный resident runtime для copy scheduling' doc/resident_copy_scheduling_runtime.md

echo "OK resident copy scheduling runtime"
