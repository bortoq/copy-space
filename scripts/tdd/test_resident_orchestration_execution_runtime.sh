#!/bin/sh
set -eu

grep -F -q 'doc/resident_execution_boundary.md' README.md
grep -F -q 'doc/resident_execution_boundary.md' doc/project_structure.md
grep -F -q '## 17. Минимальный resident runtime для orchestration' doc/roadmap.md
grep -F -q '17.1. ✅ Зафиксировать точку входа и модель состояния resident runtime.' doc/roadmap.md
grep -F -q '17.2. ✅ Зафиксировать минимальные интерфейсы исполнения orchestration.' doc/roadmap.md
grep -F -q '17.3. ✅ Зафиксировать проверки для execution runtime.' doc/roadmap.md
grep -F -q '17.4. ✅ Обновить документацию для execution runtime.' doc/roadmap.md
grep -F -q 'Этап `17` задает минимальный resident runtime для orchestration' doc/resident_execution_boundary.md

echo "OK resident orchestration execution runtime"
