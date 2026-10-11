#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_collapse_plan.md' README.md
grep -F -q 'doc/resident_host_collapse_plan.md' doc/project_structure.md
grep -F -q '## 20. Контракт на минимальное снятие зависимости от host' doc/roadmap.md
grep -F -q '20.1. ✅ Зафиксировать минимальный loader, resident execution control и границу host-only.' doc/roadmap.md
grep -F -q '20.2. ✅ Зафиксировать минимальный copy scheduling, test orchestration и ownership завершения.' doc/roadmap.md
grep -F -q '20.3. ✅ Зафиксировать стабильную границу зависимости `space.*`.' doc/roadmap.md
grep -F -q '20.4. ✅ Обновить документацию под контракт снятия зависимости.' doc/roadmap.md
grep -F -q 'Этапы `22-25` задают безопасные контракты владения перед снятием зависимости.' doc/resident_host_collapse_plan.md
grep -F -q '27.3. ✅ Оставить resident control plane единственным источником active control после bootstrap.' doc/roadmap.md
grep -F -q '27.3.1. ✅ Перевести launch control в resident code.' doc/roadmap.md
grep -F -q '27.3.2. ✅ Перевести minimal copy scheduling в resident code.' doc/roadmap.md
grep -F -q '27.3.3. ✅ Перевести completion bookkeeping в resident code.' doc/roadmap.md
grep -F -q '27.3.4. ✅ Перевести job selection и tool dispatch в resident code.' doc/roadmap.md
grep -F -q '27.4. ✅ Обновить документацию и gates после удаления `vmrun` из active path.' doc/roadmap.md
grep -F -q '27.4.4. ✅ Добавить gate на отсутствие `vmrun` в active path.' doc/roadmap.md
grep -F -q '27.4.5. ✅ Добавить gate на то, что `space.*` остается единственным проектным executable boundary на стороне ОС.' doc/roadmap.md
grep -F -q 'Этап `26` собирает resident control plane.' doc/resident_host_collapse_plan.md
grep -F -q 'Этап `27` выполняет настоящее снятие зависимости от host.' doc/resident_host_collapse_plan.md

echo "OK resident host dependency collapse contract"
