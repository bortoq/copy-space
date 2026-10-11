#!/bin/sh
set -eu

grep -F -q 'doc/resident_execution_boundary.md' README.md
grep -F -q 'doc/resident_execution_boundary.md' doc/project_structure.md
grep -F -q '## 15. Define the resident orchestration runtime boundary' doc/roadmap.md
grep -F -q '15.1. ✅ Зафиксировать resident orchestration runtime entrypoint and state model.' doc/roadmap.md
grep -F -q '15.2. ✅ Зафиксировать resident orchestration interfaces and bootstrap handoff.' doc/roadmap.md
grep -F -q '15.3. ✅ Зафиксировать verification gates for the orchestration runtime boundary.' doc/roadmap.md
grep -F -q '15.4. ✅ Обновить документацию под runtime boundary.' doc/roadmap.md
grep -F -q 'doc/resident_execution_boundary.md' doc/resident_copicode_migration.md

echo "OK resident orchestration runtime boundary"
