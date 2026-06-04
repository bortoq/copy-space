#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_collapse_plan.md' README.md
grep -F -q 'doc/resident_host_collapse_plan.md' doc/project_structure.md
grep -F -q '## 24. Контракт на владение completion bookkeeping' doc/roadmap.md
grep -F -q '24.1. ✅ Зафиксировать, что resident runtime владеет completion bookkeeping.' doc/roadmap.md
grep -F -q '24.2. ✅ Зафиксировать, что host после bootstrap не владеет completion records.' doc/roadmap.md
grep -F -q '24.3. ✅ Обновить документацию под completion bookkeeping ownership.' doc/roadmap.md
grep -F -q 'Этап `24` задает минимальный контракт' doc/resident_host_collapse_plan.md

echo "OK resident completion bookkeeping ownership"
