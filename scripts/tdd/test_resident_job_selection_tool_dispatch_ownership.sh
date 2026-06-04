#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_collapse_plan.md' README.md
grep -F -q 'doc/resident_host_collapse_plan.md' doc/project_structure.md
grep -F -q '## 25. Контракт на владение job selection и tool dispatch после bootstrap' doc/roadmap.md
grep -F -q '25.1. ✅ Зафиксировать, что resident runtime владеет job selection после bootstrap.' doc/roadmap.md
grep -F -q '25.2. ✅ Зафиксировать, что resident runtime владеет tool dispatch, когда он нужен после bootstrap.' doc/roadmap.md
grep -F -q '25.3. ✅ Зафиксировать, что host после bootstrap не выбирает jobs и не dispatch'\''ит tools.' doc/roadmap.md
grep -F -q '25.4. ✅ Обновить документацию под job selection и tool dispatch ownership.' doc/roadmap.md
grep -F -q 'Этап `25` задает минимальный контракт' doc/resident_host_collapse_plan.md

echo "OK resident job selection and tool dispatch ownership"
