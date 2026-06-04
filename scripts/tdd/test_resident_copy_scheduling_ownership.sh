#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_collapse_plan.md' README.md
grep -F -q 'doc/resident_host_collapse_plan.md' doc/project_structure.md
grep -F -q '## 23. Контракт на владение minimal copy scheduling' doc/roadmap.md
grep -F -q '23.1. ✅ Зафиксировать, что resident runtime владеет minimal copy scheduling.' doc/roadmap.md
grep -F -q '23.2. ✅ Зафиксировать, что host после bootstrap не принимает copy decisions.' doc/roadmap.md
grep -F -q '23.3. ✅ Обновить документацию под copy scheduling ownership.' doc/roadmap.md
grep -F -q 'Этап `23` задает минимальный контракт' doc/resident_host_collapse_plan.md

echo "OK resident copy scheduling ownership"
