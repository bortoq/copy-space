#!/bin/sh
set -eu

DOC="doc/roadmap.md"
[ -f "$DOC" ] || { echo "FAIL: missing $DOC"; exit 1; }

for s in \
  '## 6. Подготовка реконструкции эмулятора пространства' \
  '6.1. ✅ Зафиксировать финальный минимальный контракт хостового `space.*`.' \
  '6.2. ✅ Зафиксировать resident in-space control plane, который заменит bootstrap ABI.' \
  '6.3. ✅ Зафиксировать resident in-space guest runtime, который заменит host-side runtime.' \
  '6.4. ✅ Зафиксировать план миграции доказательной инфраструктуры на финальный контракт.'
do
  rg -n --fixed-strings "$s" "$DOC" >/dev/null
done

echo "OK rv32 stage6 roadmap sync"
