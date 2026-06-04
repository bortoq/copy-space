#!/bin/sh
set -eu

grep -F -q 'doc/resident_host_dependency_collapse_contract.md' README.md
grep -F -q 'doc/resident_host_dependency_collapse_contract.md' doc/project_structure.md
grep -F -q '## 20. Контракт на минимальное снятие зависимости от host' doc/roadmap.md
grep -F -q '20.1. ✅ Зафиксировать минимальный loader, resident execution control и границу host-only.' doc/roadmap.md
grep -F -q '20.2. ✅ Зафиксировать минимальный copy scheduling, test orchestration и ownership завершения.' doc/roadmap.md
grep -F -q '20.3. ✅ Зафиксировать стабильную границу зависимости `space.*`.' doc/roadmap.md
grep -F -q '20.4. ✅ Обновить документацию под контракт снятия зависимости.' doc/roadmap.md
grep -F -q 'Этапы `22-25` задают безопасные контракты владения перед снятием зависимости.' doc/resident_host_dependency_collapse_contract.md
grep -F -q 'Этап `26` собирает resident control plane.' doc/resident_host_dependency_collapse_contract.md
grep -F -q 'Этап `27` выполняет настоящее снятие зависимости от host.' doc/resident_host_dependency_collapse_contract.md

echo "OK resident host dependency collapse contract"
