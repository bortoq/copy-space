# doc/05_demo_quick.md — Copy-Space (Copymachine): что это и как быстро посмотреть демо — 2026-05-05

## 1) Суть проекта (простыми словами)
Copy-Space — это экспериментальная вычислительная модель, где базовая операция — **копирование битов** в общей памяти.

- Есть одна большая память (`space`), которая адресуется **по битам**.
- “Процессор” — это набор слотов, в каждом слоте записана инструкция вида:  
  `copy(n, dst, src)` = скопировать `n` бит из `src` в `dst`.
- VM делает “тик”: выполняет все слоты, затем следующий тик, и так до остановки.

Идея проекта: показать, что многие задачи можно выразить как **перемещение данных** (перестановки, упаковка, сборка/разборка), а вычислительная “сложность” может быть вынесена в то, как мы планируем эти копирования.

## 2) Что тут “вау”
1) **Минимальная VM**: почти всё — это копирования в памяти.
2) **Детерминированность**: при одном и том же образе `space` и одном и том же входе результат воспроизводим.
3) **Измеримость**: есть отчёт `vmrep`, который считает “сколько бит реально копируется за тик”.
4) **Устройства как данные**: терминал оформлен как объект “device descriptor + каналы” в памяти `space`, и это проверяется тестом (без логики в эмуляторе).

---

## 3) Быстрое демо, которое можно показать сегодня (3 команды)
Ниже — демо “data movement throughput” (похоже на операции в больших данных: gather/scatter, compaction, reorder).

### 3.1 Сборка
```sh
make bins

3.2 PACK (модель compaction после фильтра)
Shell

COPIES=64 CHUNK_BYTES=64 SRC_STRIDE_BYTES=4096 \
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 \
scripts/bench_pack_csv.sh
Вывод: одна CSV-строка с метриками. Важное поле:

vmrep_avg_bits_uniq_dst_per_tick — сколько бит реально записывается в тик (полезный объём записи).
3.3 PERMUTE (модель reorder/перестановки блоков)
Shell

COPIES=64 CHUNK_BYTES=64 MODE=random SEED=1 \
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 \
scripts/bench_permute_csv.sh
3.4 BULKCOPY (максимально “толстая” копия)
Shell

LEN_BYTES=65536 LIFE=20000 \
COPYSPACE_REPORT=1 COPYSPACE_REPORT_FROM=1000 COPYSPACE_REPORT_LEN=5000 \
scripts/bench_bulkcopy_csv.sh
4) Мини-демо “устройства как данные в space” (device≠channel)
Это короткий тест, который проверяет:

что в ART опубликованы BUS_BASE и TERM0_DESC,
что по TERM0_DESC лежит descriptor "CDEV" и 3 порта,
что каждый порт указывает на заголовок канала "CHN1".
Запуск:

Shell

make tdd
Ищите строку:

OK: term0 descriptor ABI
5) Что означают числа в CSV (коротко)
ticks_total — сколько тиков исполнялось.
vmrep_bits_sum_total — сумма n по всем copy за весь прогон (сколько “запланировали копировать”).
vmrep_bits_uniq_dst_total — сколько уникальных бит реально записали (без двойной перезаписи в те же места).
vmrep_avg_bits_uniq_dst_per_tick — средний полезный объём записи за тик.
thr_* — то же самое, но только на окне steady-state (например, тики 1000..5999).
6) Где смотреть логи
Обычно бенчи пишут логи в tmp/*.log.
Если нужно вручную посмотреть vmrep-блок:

Shell

sed -n '/^\[vmrep\]/,/VMREP_END/p' tmp/bench_pack.log
7) Ссылки на термины (если нужно)
Forth (язык/идея threaded code): https://en.wikipedia.org/wiki/Forth_(programming_language)
Sorting network (сортирующие сети, compare-exchange слои): https://en.wikipedia.org/wiki/Sorting_network
Gather/scatter (переупаковка/сборка-разборка данных): https://en.wikipedia.org/wiki/Gather/scatter_(vector_addressing)
Determinism (детерминизм): https://en.wikipedia.org/wiki/Deterministic_system
FPGA (если говорить о возможной аппаратной реализации): https://en.wikipedia.org/wiki/Field-programmable_gate_array
