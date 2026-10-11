#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_collapse_plan.md' README.md
grep -F -q 'doc/resident_host_collapse_plan.md' doc/project_structure.md
grep -F -q '## 26. План сборки resident control plane' doc/roadmap.md
grep -F -q '26.1. ✅ Зафиксировать один общий resident state для control plane.' doc/roadmap.md
grep -F -q '26.2. ✅ Связать launch control и copy scheduling.' doc/roadmap.md
grep -F -q '26.3. ✅ Связать completion bookkeeping, job selection и tool dispatch.' doc/roadmap.md
grep -F -q '26.4. ✅ Оставить host только bootstrap-only.' doc/roadmap.md
grep -F -q '26.5. ✅ Обновить документацию.' doc/roadmap.md
grep -F -q 'Этап `26` задает один конкретный технический план' doc/resident_host_collapse_plan.md

echo "OK resident control plane assembly"
