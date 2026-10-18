# Миграция copy-space на новое пространство

Цель: **полностью исключить старый эмулятор** (`src/space*.c`, `build/bin/space*`).
Все исполняемые артефакты (rv32i, pforth, copy-c, GCC, Linux) должны исполняться
на новом эмуляторе (`positional addressing`, `space-dev`) через SYS и
пред-привязанные каналы данных. Всё, что старый эмулятор делал на хосте,
воспроизводится **копикодом внутри пространства**.

Основание: `positional addressing/doc/roadmap.md` §8–§13 (эмулятор — минимальный
субстрат; протокол SYS принадлежит in-space драйверу; прочее — приложение в
пространстве).

## 1. Что даёт новый эмулятор (дано, менять нельзя)

- Запуск: `-s <space_bits>`, `-p <proc_n>`, `-t <ticks>`, `--core FILE`,
  `--dump-space FILE` (сборка `SPACE_DEV`), `SPACE_TICKS=1` (диагностика).
- Такт **bulk-synchronous**: все инструкции читаются в начале такта, все
  копирования коммитятся вместе, самомодификация и патч поля видны не раньше
  следующего такта (инвариант P1: патч в слое L виден слою M при `M >= L+2`).
- Формат: `a = bit_length(space_nbits)`, `nfield = a-1`, `isz = 3a-1`.
- Позиции каналов: `SYS = space_nbits`, данные — `stdin = space_nbits+1`,
  `stdout = space_nbits+2` (по таблице `XDEV`).
- Протокол SYS (временный, владелец — in-space драйвер):
  запрос `op(8) chan(ADDR) flags(16) arg(32) off(64)`;
  ответ `op(8) status(8) flags(16) size(64) moved(NF) eof(1)`;
  операции `NONE/CLOSE/SEEK/FSTAT/IOCTL/EXEC`.
- Копирование, затрагивающее канал данных, переносит до `ceil(n/8)` байт; число
  перенесённых байт, `eof` и статус читаются через SYS `FSTAT`.
- Нет: трассировки, `--restore`, `report_status`, потоковой загрузки, нескольких
  сборок под размер пространства.

## 2. Что давал старый эмулятор (инвентарь)

1. Размер пространства и `PROCESSOR_N` на этапе компиляции (2/64/256 МиБ).
2. `--core` — загрузка сырого образа пространства.
3. Потоковая загрузка: пакет `RVS1` (`encode_stream`), устанавливаемый ядром
   через IN.
4. Такт с **немедленной видимостью** записей и самомодификацией в том же такте.
5. Каналы-инструкции на слотах 1 (IN) и 2 (OUT): `n`, индекс буфера, индекс
   результата; результат `2*перенесённых_бит + причина` (`0=EOF`, `1=ошибка`),
   виден инструкциям того же такта; выравнивание по байтам; потоковые биты
   продолжаются между операциями; канальная инструкция не делает внутреннего
   копирования; при неполной операции исполнение продолжается.
6. `--ticks N`; причины остановки `idle/limit/error`.
7. `--dump-space FILE` — полный сырой дамп пространства.
8. `--trace FILE` (все копирования и каналы) и `--trace-channels FILE`
   (каналы и счётчики).
9. Профили генератора `report_status` / `state_output` — терминальная запись в
   пространстве.
10. Инфраструктура тестов: `tests/space_segments.py` (дампы, курсоры, счёт
    событий), `tests/space_trace_audit.py`, `tests/space_archive.py`.

## 3. Разрыв: недостающие ключи/фичи и копикод-замена

| # | Что было у старого | Что делаем на новом | Где |
|---|---|---|---|
| R1 | IN/OUT на слотах 1/2, статус `2*moved+reason` в том же такте | **Канальный адаптер**: копия данных через `stdin`/`stdout`, затем SYS `FSTAT`; `moved` на успехе, `-5` при ошибке потока; сохраняем выравнивание, курсор, порядок OUT→IN | `modules/rv32i_channels.py` |
| R2 | `report_status` / `state_output` | **Терминальный слой**: `STATUS`/`EXIT_CODE` уже лежат в пространстве; хост читает их из дампа; для длинных заданий — терминальная запись в отдельный канал | `modules/rv32i_terminal.py` |
| R3 | Потоковая загрузка `RVS1` (`encode_stream`), ядро через IN | **Загрузчик в пространстве**: читает самоописывающийся образ из `stdin`, раскладывает по позициям (самоперезапись/trampoline); хост-примитив `--core` | `modules/rv32i_loader.py` |
| R4 | `--resume-segments`, курсоры | **Install/restore + граница такта**: дамп → `--core`; восстановление курсоров через SYS `SEEK`; хост задаёт границу такта | `modules/rv32i_install.py`, `tests/space_segments.py` |
| R5 | `--trace`, `--trace-channels` | **Трассировщик в пространстве**: события `copy/channel/stop`, отдельный отладочный канал, счётчик тактов; порт `space_trace_audit.py` | `modules/rv32i_tracer.py` |
| R6 | Компиляционные размеры | **Runtime `-s/-p`**; зафиксировать `space_bytes`, `proc_n` и прокинуть в генератор | `modules/space_model.py` |
| R7 | Видимость в такте | **Сборочное расписание** (bulk, `rv32i_bulk.py`) для ВСЕХ генераторов, не только rv32i | `modules/rv32i_bulk.py` |
| R8 | Протоколы `RVS1/CCFILES1/GCCJOB1/GCCOUT1`, задание pforth | Сохранить формат, транспорт — через адаптер (R1) | `modules/rv32i_loading.py`, `scripts/*` |

Официальная позиция: **ни один несущий механизм не остаётся на хосте**, кроме
примитива «вставить образ + запустить + граница такта» (roadmap нового
эмулятора §8.2, §8.9.2).

## 4. Целевая структура файлов

```
modules/
  space_model.py      # НОВОЕ: единый формат нового пространства (-s/-p, позиции SYS/устройств)
  rv32i_proto.py      # НОВОЕ: владелец SYS-протокола: упаковка/распаковка записей (хост+гость)
  rv32i_channels.py   # НОВОЕ: канальный адаптер IN/OUT/SEEK/CLOSE поверх SYS+data
  rv32i_terminal.py   # НОВОЕ: терминальный слой статуса
  rv32i_loader.py     # НОВОЕ: загрузчик RVS1 в пространстве
  rv32i_install.py    # НОВОЕ: install/restore + сегментация
  rv32i_tracer.py     # НОВОЕ: трассировщик в пространстве
  rv32i.py            # frontend (API не меняется)
  rv32i_bulk.py       # backend/планировщик нового такта (base+io+ новых профилей)
  rv32i_toolchain.py  # без изменений
  rv32i_stream.py     # УДАЛИТЬ (старая потоковая загрузка)
scripts/
  rv32i/{build.py,run.py}   # bulk-only, --core, новый статус
  pforth/{build.py,run.py}  # build есть; добавить run.py
  copy_c/{build.py,run.py}  # добавить run.py (core-runner)
  gcc/{prepare_image.py,run_job.py}  # bulk + адаптер + loader/segments
runtime/rv32i/        # cs_read/cs_write/cs_exit — без изменения ABI
tests/
  space_runner.py     # НОВОЕ: хост-раннер нового эмулятора
  space_segments.py   # портировать на space_runner + in-space tracer
  space_trace_audit.py
src/                  # УДАЛИТЬ целиком (старый эмулятор)
```

## 5. Интерфейсы

### 5.1 Хост-раннер (`tests/space_runner.py`, общий и для scripts)
```python
RunResult = namedtuple("RunResult", "returncode stdout dump_path ticks")

def run(image: Path, *, space_bytes: int, proc_n: int = 256, ticks: int | None = None,
        stdin: bytes = b"", forward: bool = True, dump: Path | None = None,
        emulator: Path = SPACE_EMULATOR, timeout: float | None = None) -> RunResult
```
Инварианты: запускает `emulator -s space_bytes*8-4 -p proc_n -t ticks --core image
[--dump-space dump]`; `stdin` — полезная нагрузка; `dump` — сырое пространство.
Предусловие: `space_bytes*8-4` даёт ту же `a`, что у генератора.
Постусловие: `returncode` разобран по `STATUS`/`EXIT_CODE` из дампа.

### 5.2 SYS-драйвер / владелец протокола (`modules/rv32i_proto.py`)
```python
def pack_req(op, chan, flags=0, arg=0, off=0) -> bytes   # раскладка полей low-bit-first
def unpack_rsp(raw: bytes, nfield_bits: int) -> dict     # op/status/flags/size/moved/eof
```
Инварианты: раскладка совпадает с `proto.def`; запись целиком в пространстве; буфер
данных не пересекается с записями каналов (roadmap §10).

### 5.3 Канальный адаптер (`modules/rv32i_channels.py`)
Гостевой ABI не меняется: `cs_read(buf,n)->int`, `cs_write(buf,n)->int`,
`cs_exit(code)`.
```
pre:  a7=63/64/93 (иначе ENOSYS=-38); a0-дескриптор 0=stdin/1=stdout (иначе EBADF=-9);
      диапазон [a1, a1+a2) внутри гостевой памяти (иначе EFAULT=-14)
post: read: данные в [a1,a1+moved); a0 = moved (>=0) | -5 при статусе потока
      write: байты [a1,a1+a2) выведены; a0 = moved | -5
      exit: STATUS=10, EXIT_CODE=a0, остановка
```
Реализация: копирование данных в отдельный блок (свой такт), затем SYS `FSTAT`
для `moved`/`status`.

### 5.4 Терминальный слой (`modules/rv32i_terminal.py`)
Запись `{STATUS, EXIT_CODE, ticks}` в фиксированные позиции; при `forward` —
потоковая выдача на отдельный канал. Постусловие: хост-обёртка читает статус без
`report_status`.

### 5.5 Загрузчик (`modules/rv32i_loader.py`)
```
pre:  канал stdin содержит образ с заголовком (магия, версия, размеры, раскладка)
post: образ разложен по позициям, включая собственную область (самоперезапись),
      управление передано точке входа
```
Заменяет `encode_stream` (R3). Применяется, когда образ больше seed.

### 5.6 Install/restore + сегментация (`modules/rv32i_install.py`)
```
pre:  дамп пространства + запись курсора
post: состояние восстановлено, курсоры каналов reopen/SEEK, исполнение продолжено
```
Хост даёт границу такта (`-t`), восстановление — в пространстве.

### 5.7 Трассировщик (`modules/rv32i_tracer.py`)
Резидентная библиотека/программа: читает `PROCESSOR`, пишет
`copy tick slot n dst src`, `channel ...`, `stop <reason>` в отдельный канал;
пропускает собственные слоты; сам считает такты. Порт `space_trace_audit.py`.

## 6. Data Flow

1. **Обычный запуск.** `build --new-emulator` → bulk-образ (frontend+планировщик+
   адаптер+терминал) → хост `--core` → такт: SYS/данные → гостевые syscall'ы →
   `STATUS/EXIT_CODE` → `space_runner` разбирает дамп.
2. **Длинное задание (copy-c/GCC).** Образ с загрузчиком → задание через
   `stdin` → гость читает задание, компилирует/линкует в пространстве → ответ
   через `stdout`; сегментация: `-t` + дамп → restore (`--core` + SEEK).
3. **Трассировка.** Образ с трассировщиком → события в отладочный канал →
   хост-аудит.

## 7. Инварианты и риски

- **Не полагаться на видимость в такте** (roadmap §8.3.1): адаптер и слои — только
  копикод с `+2` headroom.
- **Один `SYS`, два канала**: старые IN/OUT сводятся к копиям через data-каналы;
  порядок OUT→IN и выравнивание воспроизводятся точно.
- **Производительность**: доступ к каналу — обычная инструкция; большие операции
  переносят много бит за раз. Полный трейс — только на коротких участках.
- **Формат изображений** для всех генераторов нужно регенерировать (R6, R7).
- **Нет защиты**: диапазоны гарантирует программа (roadmap §9).
- **Опасность scope creep**: не строить общий транслятор расписаний (§8.9.1
  отложен) — только сборочное расписание §8.10.

## 8. Порядок миграции (фазы)

0. Зафиксировать `space_model.py` (единый формат), `space_runner.py`, `-s/-p`.
1. `rv32i_proto.py` + `rv32i_channels.py` (полный адаптер) на bulk.
2. `rv32i_terminal.py` (замена `report_status`/`state_output`).
3. `rv32i_loader.py` (замена `encode_stream`).
4. `rv32i_install.py` + порт `space_segments.py`.
5. `rv32i_tracer.py` + порт `space_trace_audit.py`.
6. rv32i: полный профиль (base+io+schedule+новые слои).
7. pforth: раннер + протокол задания.
8. copy-c: core-runner + упаковка задания.
9. GCC: `prepare_image`/`run_job` + сегментация + терминальный статус.
10. Linux: транзитивно через GCC.
11. Переключить `tests/*` и `Makefile`; дифференциальные проверки.
12. Удалить `src/`, `rv32i_stream.py`, `bins`/`bins-large`, старые доки.
