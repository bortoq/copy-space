#!/bin/sh
set -eu

HOST_DOC="doc/space_minimal_host_contract.md"
CP_DOC="doc/resident_control_plane_contract.md"
RT_DOC="doc/resident_runtime_contract.md"
MIG_DOC="doc/resident_proof_migration.md"

for doc in "$HOST_DOC" "$CP_DOC" "$RT_DOC" "$MIG_DOC"; do
  [ -f "$doc" ] || { echo "FAIL: missing $doc"; exit 1; }
done

for s in \
  'финальный минимальный контракт хостового `space.*`' \
  'копирование в каналы и из каналов' \
  'выполнение `copy` полуинтервалов по инструкциям процессорных слотов' \
  'останов пространства' \
  'одноразовая загрузка данных в один слот процессора перед первым тактом' \
  '/media/user/PROJECT/bak/demo1/space.c' \
  '/media/user/PROJECT/bak/demo1/space.h' \
  'Запрещено сохранять в хостовом `space.*` channel ABI, guest runtime, proof runtime и guest-state semantics.'
do
  rg -n --fixed-strings "$s" "$HOST_DOC" >/dev/null
done

for s in \
  'resident in-space control plane' \
  'resident dispatcher state' \
  'resident request/response buffers' \
  'resident service code' \
  'формат resident request' \
  'формат resident response' \
  'handshake semantics resident protocol' \
  'начальную загрузку resident bootstrap payload' \
  'развертывание resident dispatcher в пространстве' \
  'переход от bootstrap payload к resident steady-state' \
  'момент завершения bootstrap ABI' \
  'первый запрос, обслуживаемый resident control plane' \
  'rollback/fail behavior при срыве handoff'
do
  rg -n --fixed-strings "$s" "$CP_DOC" >/dev/null
done

for s in \
  'resident in-space guest runtime' \
  'resident fetch contract' \
  'resident decode contract' \
  'resident execute/commit contract' \
  'resident `PC` layout and ownership' \
  'resident register file layout and ownership' \
  'resident guest memory layout and ownership' \
  'resident unsupported-instruction behavior' \
  'resident alignment-fault behavior' \
  'resident bounds-fault behavior' \
  'источник resident trace records' \
  'способ извлечения resident trace records наружу' \
  'соответствие resident trace contract bootstrap trace contract' \
  'замену временного bootstrap trace ABI на resident trace contract'
do
  rg -n --fixed-strings "$s" "$RT_DOC" >/dev/null
done

for s in \
  'миграцию proof artifacts с bootstrap ABI на final channel-only contract' \
  'замену bootstrap trace artifacts на resident trace artifacts' \
  'замену bootstrap state artifacts на resident state artifacts' \
  'миграцию validation gates с bootstrap executor на resident executor' \
  'миграцию directed instruction-family gates' \
  'миграцию negative/fault gates' \
  'миграцию replay/determinism gates' \
  'критерий готовности resident control plane' \
  'критерий готовности resident executor' \
  'критерий готовности proof gates'
do
  rg -n --fixed-strings "$s" "$MIG_DOC" >/dev/null
done

echo "OK rv32 stage6 docs sync"
