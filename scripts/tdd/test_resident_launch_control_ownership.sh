#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_collapse_plan.md' README.md
grep -F -q 'doc/resident_host_collapse_plan.md' doc/project_structure.md
grep -F -q '## 22. Контракт на владение запуском resident code' doc/roadmap.md
grep -F -q '22.1. ✅ Зафиксировать, что resident runtime владеет решением о запуске после bootstrap.' doc/roadmap.md
grep -F -q '22.2. ✅ Зафиксировать, что host после bootstrap не принимает launch decisions.' doc/roadmap.md
grep -F -q '22.3. ✅ Обновить документацию под launch control ownership.' doc/roadmap.md
grep -F -q 'Этап `22` задает минимальный контракт' doc/resident_host_collapse_plan.md

echo "OK resident launch control ownership"
