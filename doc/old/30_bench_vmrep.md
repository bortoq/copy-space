Бенчмарки и отчёт vmrep (Latency/Throughput) — 2026-05-04
# Бенчмарки и отчёт vmrep (Latency/Throughput)

Этот документ описывает “измеритель толщины” работы VM (`vmrep`) и набор вспомогательных бенчей (bulkcopy/pack/permute), которые позволяют быстро оценивать:
- сколько бит реально копируется за тик,
- насколько “толстые” операции генерирует программа,
- как выглядит steady-state throughput (модель конвейера).

## 1) Что измеряем и зачем

### 1.1 Tick
В copyspace 1 **tick** = выполнение всех `PROCESSOR_N` слотов в `vm_tick()`.

### 1.2 Метрики
`vmrep` считает две ключевые метрики на tick:

1) `bits_sum`  
Сумма `n` по всем `copy(n,dst,src)` за tick:
- быстро,
- верхняя оценка “сколько работы запланировано”.

2) `bits_uniq_dst`  
Длина объединения всех dst-интервалов `[dst, dst+n)` за tick:
- показывает “реальный объём записи” (если есть overlap по dst, то `uniq < sum`),
- удобная диагностика конфликтов/перезаписей.

**Интерпретация:**
- `sum == uniq` → нет overlap по dst в этом тике (хорошо для модели “параллельных слоёв”).
- `sum >> uniq` → много перекрытий по dst (часть работы “перетирает” себя же).

> Примечание: `vmrep` не проверяет конфликты чтения (src). Это отдельная задача планировщика слоёв.

## 2) Режимы отчёта

### 2.1 Latency mode
Отчёт по всему прогону (всем тикам), включая:
- `ticks_total`
- `bits_sum_total`, `bits_uniq_dst_total`
- `avg_bits_*_per_tick` (среднее за прогон)

### 2.2 Throughput mode (steady-state / pipeline window)
Отчёт по окну тиков `[FROM .. FROM+LEN)`:
- позволяет исключить “прогрев/эпилог” и измерить steady-state throughput,
- удобен для моделирования конвейера: «каждый тик подаём новый такт работы».

Окно задаётся переменными окружения:
- `COPYSPACE_REPORT_FROM` (0-based tick index)
- `COPYSPACE_REPORT_LEN` (кол-во тиков)

Если `LEN=0`, throughput-часть отчёта не печатается.

## 3) Как включить vmrep

`vmrep` включается через переменные окружения (stderr `vmrun`):

- `COPYSPACE_REPORT=1` — включить отчёт
- `COPYSPACE_REPORT_FROM=<N>` — начало окна throughput (опционально)
- `COPYSPACE_REPORT_LEN=<L>` — длина окна throughput (опционально)
- `COPYSPACE_REPORT_HZ=<hz>` — если задано, печатается оценка Gb/s:
  - `Gb/s ≈ avg_bits_per_tick * hz / 1e9`

Примеры:
```sh
# latency only
COPYSPACE_REPORT=1 scripts/test_all.sh

# throughput window (steady-state)
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 scripts/test_all.sh

# с переводом в Gb/s (условная частота)
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 COPYSPACE_REPORT_HZ=1000000000 scripts/test_all.sh

4) Где искать вывод (важно)
vmrep пишет в stderr процесса vmrun.

В scripts/test_all.sh stderr vmrun редиректится в:

tmp/compile.log (этап компиляции токенов)
tmp/run.log (этап выполнения compiled_space)
Поэтому:

либо читай tmp/run.log,
либо добавь в scripts/test_all.sh функцию, печатающую блок [vmrep]..VMREP_END в консоль.
Быстрый просмотр отчёта из лога:

Shell

sed -n '/^\[vmrep\]/,/VMREP_END/p' tmp/run.log
5) Удобный запуск для текущих тестов
Если в проекте есть враппер scripts/vmrep.sh, он запускает тесты и включает vmrep автоматически.

Примеры:

Shell

# один тест (если ONLY поддерживается в test_all.sh)
ONLY=eq24p COPYSPACE_REPORT=1 scripts/test_all.sh

# через враппер (если добавлен)
scripts/vmrep.sh eq24p --from 2000 --len 5000
scripts/vmrep.sh all  --from 0    --len 999999999
6) “Толстые” throughput-бенчи (data movement)
Эти бенчи создают отдельный образ, в котором первые K слотов выполняют большие копирования диапазонов каждый тик. Это демонстрация “толстых интервалов” и верхней пропускной способности модели ISA при заданном PROCESSOR_N.

6.1 bulkcopy
Один большой copy(n,dst,src) в slot0 каждый тик.

Ожидаемо:

avg_bits_uniq_dst_per_tick ≈ len_bytes * 8
Запуск (пример):

Shell

scripts/bench_bulkcopy.sh
LEN_BYTES=65536 LIFE=20000 FROM=1000 LEN=5000 scripts/bench_bulkcopy.sh
6.2 pack (gather → pack)
Много слотов копируют чанки из “разреженного” src (stride) в “плотный” dst.

Ожидаемо:

avg_bits_uniq_dst_per_tick ≈ COPIES * CHUNK_BYTES * 8 (если dst не пересекается)
Запуск (пример):

Shell

COPIES=64 CHUNK_BYTES=1024 SRC_STRIDE_BYTES=4096 scripts/bench_pack.sh
COPIES=64 CHUNK_BYTES=1024 SRC_STRIDE_BYTES=4096 RANDOMIZE=1 SEED=42 scripts/bench_pack.sh
6.3 permute (chunk permutation)
Src и dst плотные, но чанки копируются по перестановке (reverse/random/bitrev).

Запуск (пример):

Shell

COPIES=64 CHUNK_BYTES=1024 MODE=reverse scripts/bench_permute.sh
COPIES=64 CHUNK_BYTES=1024 MODE=random SEED=7 scripts/bench_permute.sh
7) Как интерпретировать результаты бенчей
Если при PACK/PERMUTE/BULKCOPY ты видишь одинаковый avg_bits_uniq_dst_per_tick, это обычно означает:

ты достиг потолка COPIES * CHUNK_BYTES * 8 (ограничение “сколько данных описано инструкциями за тик”),
перестановка чанков стоит столько же, сколько и перенос такого же объёма (важный тезис deterministic permutation fabric на уровне ISA).
8) Типичные проблемы
bits_* == 0, но ticks_total > 0
Обычно значит, что:
все слоты NOP (n==0), или
vmrep_note_copy() не вставлен в vm_tick().
Throughput-окно пустое (thr_ticks == 0)
Значит FROM больше, чем число тиков до завершения программы.

sum > uniq
Значит overlap по dst внутри одного tick. Это может быть:

баг планировщика/упаковщика,
или сознательная перезапись (но тогда uniq — более честная метрика).
9) Рекомендуемый минимальный набор отчётов для проекта
Для каждого нового слова/бенча:

latency average (avg_bits_*_per_tick)
throughput window (steady-state), например FROM=1000 LEN=5000 (если прогон длинный)
сравнить “тонкие слова” (EQ24P) против “толстых” (bulk/pack/permute)
Это помогает быстро увидеть, где архитектура упирается в “мелкие копии” и где нужен fusion/оптимизация/переход на bulk операции.
