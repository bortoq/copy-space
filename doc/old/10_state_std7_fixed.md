Текущее состояние: std7_fixed (подробности реализации) — 2026-05-04
# Текущее состояние: std7_fixed (подробности реализации)

Документ фиксирует актуальный baseline, который должен собираться и проходить тесты через:
- `make`
- `scripts/test_all.sh`

## 1) Конфигурация VM (по умолчанию)
- `SPACE_BYTES = 524288` (512 KiB)
- `PROCESSOR_N = 64`

Производные величины (для 512 KiB):
- `SPACE_BITS = SPACE_BYTES * 8 = 2^22`
- `ADDR_BITS = 24` (выводится из space_bits, округляется вверх до кратности 8)
- `N_BITS = 24` (== ADDR_BITS)
- `INSTR_BITS = 72` (3 * 24) => 9 байт на инструкцию
- `PROCESSOR_BITS = 4608`

Инструкция VM (`n,dst,src`):
- если `n > 0`: копируется `n` бит из `src` в `dst`
- если `n == 0`: **NOP** (в текущей VM нет спец.семантики для n==0)

Копирование делает `bitcpy.c` (MSB-first, overlap-safe).

## 2) MMIO (текущие “устройства” VM)
MMIO реализует handshake для stdin/stdout и HALT:
- IN: `in_req/in_done/in_eof/in_err`, `in_dst`, `in_len`, `in_got`
- OUT: `out_req/out_done/out_err`, `out_src`, `out_len`, `out_got`
- CONTROL: `halt`

MMIO обслуживается в начале каждого тика (out, потом in), затем проверяется halt, затем исполняются слоты.

Требование MMIO: операции IN/OUT byte-aligned (`dst/src/len` кратны 8 бит).

## 3) Loader 3B (переключение страниц как копикод)
Переключение страниц реализовано копикодом (не логикой VM):

- `slot0`: NOP, но `dst` хранит `next_layer_ptr`
- `patch_slot = PROCESSOR_N-2`: патчит src-field `load_slot` из dst-field `slot0`
- `load_slot = PROCESSOR_N-1`: копирует `PROCESSOR_BITS` бит следующей страницы в область процессора

Helper: `vm_build_boot_loader_layer()`.

## 4) Forth0 (threaded code)
- Программа — список cells `(code_ptr,next_ptr)`.
- NEXT_IMG грузит слово по `code_ptr`, обновляет IP на `next_ptr`, и слово возвращается обратно в NEXT.

## 5) std7_fixed: фиксированные адреса слов
В `mkimage_std7_fixed.c` страницы слов размещаются в фиксированном регионе near end-of-space:
- адреса `WORD_*` не зависят от `POOL_CELLS`,
- токены, сгенерированные на small pool image, корректно работают на big pool image (регрессией).

## 6) Библиотека слов: базовые + 2a + старт 2b
### 6.1 2a (24-bit fixed operands/results)
Добавлены `WORD_ADD24/WORD_EQ24/WORD_LT24` и переменные `VAR_A24/VAR_B24/VAR_SUM24/VAR_COUT/VAR_EQ/VAR_LT`.

### 6.2 2b (указатели, старт)
Добавлены `VAR_AP/VAR_BP/VAR_RP`, `OFFTAB`, `WORD_LITAP/LITBP/LITRP`, `WORD_EQ24P`.

Alignment requirement: `VAR_AP/VAR_BP` должны быть 32-bit aligned: `bitaddr % 32 == 0`.

## 7) Artifact ABI
см. doc/abi_std7_fixed_artifacts.md

## 8) Two-pass workflow тестов
`scripts/test_all.sh`:
1) mkimage small/big
2) tokgen (small)
3) compile (big) -> `compiled_space.bin`
4) vmprep
5) run -> `after.bin`
6) compare expected bytes at TESTG

## 9) Тесты
Проходят:
- fulladder, add8
- eq24/lt24/add24 (2a)
- eq24p (2b)

## 10) Инструменты измерения throughput (vmrep)
В VM добавлен репорт vmrep:
- `bits_sum` и `bits_uniq_dst` per tick
- latency и throughput window (FROM/LEN)
- вывод пишется в stderr `vmrun` и обычно попадает в `tmp/compile.log` и `tmp/run.log`

См. `doc/30_bench_vmrep.md`.

## 11) Зафиксированное направление дизайна (не полностью реализовано в baseline)
Проект фиксирует направление: “всё внешнее — устройство, доступ через каналы”, с отдельным channel/device manager и self-describing devices.

Это относится к будущей архитектуре взаимодействия модулей/гестов/ОС и не обязано быть полностью реализовано в std7_fixed baseline.

См. `doc/40_devices_channels.md`.
