# doc/35_bench_csv_schema.md — todo C.0: Unified bench CSV schema (v1) — 2026-05-05

## 1. Цель
Все throughput-бенчи (bulk/pack/permute/… и будущие) должны печатать результаты в **едином CSV формате**, чтобы:
- сравнивать прогоны между бенчами и после оптимизаций,
- строить графики одной утилитой,
- легко хранить историю результатов.

Схема расширяется **append-only** (добавлением новых колонок в конец).

## 2. Формат вывода
- CSV в stdout.
- Первая строка: заголовок (header) с именами колонок.
- Далее одна или несколько строк результатов (по sweep параметров).

Рекомендуется всегда печатать:
- `schema_version=1` в отдельной колонке.

## 3. Колонки (v1, минимальный обязательный набор)
Обязательные колонки:

1) `schema_version` — число, сейчас `1`
2) `bench` — строка: `bulkcopy|pack|permute|...`
3) `mode` — строка (например `reverse|random|stride|...`), либо пусто
4) `seed` — число или пусто

Конфигурация VM/образа:
5) `space_bytes`
6) `processor_n`
7) `addr_bits`

Основные метрики исполнения:
8) `ticks_total` — число тиков до завершения
9) `moved_bits_total` — полезная оценка “сколько данных описано/перенесено” (см. примечания)
10) `vmrep_bits_sum_total`
11) `vmrep_bits_uniq_dst_total`
12) `vmrep_avg_bits_sum_per_tick`
13) `vmrep_avg_bits_uniq_dst_per_tick`

Throughput window (если используется):
14) `thr_from`
15) `thr_len`
16) `thr_avg_bits_sum_per_tick`
17) `thr_avg_bits_uniq_dst_per_tick`

Опционально (но очень полезно):
18) `notes` — короткая строка без запятых (или в кавычках)

## 4. Единицы измерения
- `*_bits_*` — в битах.
- `space_bytes` — байты.
- `ticks_*` — тики VM.

Если бенч считает “мoved bytes”, он должен конвертировать в `moved_bits_total = moved_bytes_total * 8`.

## 5. Примечания по `moved_bits_total`
`moved_bits_total` в идеале означает “сколько полезных бит было перенесено” (семантическая метрика бенча).
Для VM-уровня дополнительно есть `vmrep_bits_sum_total` (сумма n по copy) и `vmrep_bits_uniq_dst_total` (реальная запись без overlap).

## 6. Пример
```csv
schema_version,bench,mode,seed,space_bytes,processor_n,addr_bits,ticks_total,moved_bits_total,vmrep_bits_sum_total,vmrep_bits_uniq_dst_total,vmrep_avg_bits_sum_per_tick,vmrep_avg_bits_uniq_dst_per_tick,thr_from,thr_len,thr_avg_bits_sum_per_tick,thr_avg_bits_uniq_dst_per_tick,notes
1,permute,reverse,,524288,64,24,20000,536870912,1234567890,987654321,61728.39,49382.71,1000,5000,65000.00,52000.00,baseline