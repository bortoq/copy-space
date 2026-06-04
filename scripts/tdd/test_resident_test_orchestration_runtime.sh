#!/bin/sh
set -eu

grep -F -q 'doc/resident_test_orchestration_runtime.md' README.md
grep -F -q 'doc/resident_test_orchestration_runtime.md' doc/project_structure.md
grep -F -q '## 19. Минимальный resident runtime для test orchestration' doc/roadmap.md
grep -F -q '19.1. ✅ Зафиксировать точку входа и модель состояния test orchestration.' doc/roadmap.md
grep -F -q '19.2. ✅ Зафиксировать минимальные интерфейсы исполнения test orchestration.' doc/roadmap.md
grep -F -q '19.3. ✅ Зафиксировать проверки для test-orchestration runtime.' doc/roadmap.md
grep -F -q '19.4. ✅ Обновить документацию для test-orchestration runtime.' doc/roadmap.md
grep -F -q 'Этап `19` задает минимальный resident runtime для test orchestration' doc/resident_test_orchestration_runtime.md

echo "OK resident test orchestration runtime"
