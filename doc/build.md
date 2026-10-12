# Сборка и зависимости

Для `make bins` нужны Make и компилятор C99 (GCC или Clang).
Для `make test` дополнительно нужны Python 3.8 или новее, Git и Linux:
проверки ошибок каналов используют `/dev/full`, чтение каталога и
`fopencookie`. Python использует только стандартную библиотеку; `xxd`
не требуется. `make clean` также требует Python и Git, чтобы сохранить
отслеживаемые файлы. Для `make test-sanitize` компилятор должен поддерживать
AddressSanitizer и UndefinedBehaviorSanitizer.

```sh
make bins
make test
make test-sanitize
```

## CMake

Альтернативная сборка использует CMake 3.16 или новее:

```sh
cmake -S . -B build/cmake -DCMAKE_BUILD_TYPE=Debug
cmake --build build/cmake
(cd build/cmake && ctest --output-on-failure)
```

Программы находятся в `build/cmake/bin`. CTest проверяет bitcopy,
возобновление исполнения и границу вместимости ассемблера. Полный набор
проверок образов пространства запускается через `make test`.
Без Python можно собрать только программы и библиотеки:

```sh
cmake -S . -B build/cmake-native -DBUILD_TESTING=OFF
cmake --build build/cmake-native
```

## C и pForth на RV32I

Для `make test-rv32i-c`, `make pforth`, `make pforth-job`,
`make test-pforth` и `make test-file-job` нужен RISC-V GCC с поддержкой
`-march=rv32i -mabi=ilp32`, соответствующие binutils (as, ld, objcopy,
objdump) и совместимая библиотека libgcc. Гостевая libc не требуется.
Компилятор `riscv64-unknown-elf-gcc` подходит при наличии варианта libgcc
для RV32I/ILP32; имя с `riscv64` не означает запрет 32-битной сборки.

Компилятор выбирается по `--compiler` (для команд сборки), затем `RISCV_CC`,
затем из PATH. Если его нет, проверяется локальная установка
`tmp/rv32i-toolchain/root/usr/bin/riscv64-unknown-elf-gcc`.
Пути objcopy/objdump выводятся из имени компилятора или задаются явно:

```sh
export RISCV_CC=/path/to/bin/riscv64-unknown-elf-gcc
export RISCV_OBJCOPY=/path/to/bin/riscv64-unknown-elf-objcopy
export RISCV_OBJDUMP=/path/to/bin/riscv64-unknown-elf-objdump
"$RISCV_CC" -print-multi-lib
"$RISCV_CC" -march=rv32i -mabi=ilp32 -print-libgcc-file-name
make test-rv32i-c
make test-file-job
```

Последние две диагностические команды показывают выбор библиотек;
сквозные тесты проверяют, что настоящий C-образ собирается и исполняется.
Отсутствие компилятора останавливает проверки с сообщением об ошибке,
а не засчитывается как успешный запуск.

Обычная сборка pForth использует сохранённый словарь и исходники
`third_party/pforth`, сеть не нужна. Повторная подготовка словаря требует
отдельных условий i386, описанных в [pforth.md](pforth.md).
Прямой запуск готового задания `space < job.in > result.out` требует
только собранного space и файла задания.

Сырые результаты тестов находятся в `tmp/space-tests`; очистка —
[make clean](cleanup.md). Лицензии перечислены в [LICENSING.md](../LICENSING.md).

Компилятор C → копирования собирается отдельной целью `make copy-c`;
она также создаёт `build/bin/space-64m` для среды компилятора.
`make bins-large` собирает только этот вариант того же эмулятора.
Прямой результат C пока исполняется обычным `build/bin/space`.
Для первой подготовки нужен также GCC с генерацией i386. Команды
двух запусков, подмножество C и проверки — в [copy_c.md](copy_c.md).
