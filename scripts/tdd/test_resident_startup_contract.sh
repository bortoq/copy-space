#!/bin/sh
set -eu

grep -F -q 'doc/resident_execution_boundary.md' README.md
grep -F -q 'doc/resident_execution_boundary.md' doc/project_structure.md
grep -F -q '## 16. Implement the minimal resident startup contract' doc/roadmap.md
grep -F -q '16.1. ✅ Зафиксировать fixed boot slots and resident entrypoint payload.' doc/roadmap.md
grep -F -q '16.2. ✅ Зафиксировать minimal copy/channel responsibilities for startup.' doc/roadmap.md
grep -F -q '16.3. ✅ Зафиксировать verification gates for the startup contract.' doc/roadmap.md
grep -F -q '16.4. ✅ Обновить документацию под startup contract.' doc/roadmap.md
grep -F -q 'Этот документ задает resident runtime boundary для этапа `15`.' doc/resident_execution_boundary.md
grep -F -q 'Этап `16` задает минимальный startup contract' doc/resident_execution_boundary.md

echo "OK resident startup contract"
