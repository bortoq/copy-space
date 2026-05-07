# Forth0 (host-compiled) — std7_fixed workflow

Forth0 в этом репозитории — это host-side компиляция текстовых `.f0` программ в бинарный поток токенов `.tok`,
который затем компилируется/исполняется внутри VM.

Рекомендуемый стиль разработки: новые тесты/логика/бенчи добавляются в виде `.f0` + harness-скриптов, без правок VM/mkimage.

---

## Pipeline

1) mkimage:
- `build/bin/mkimage_std7_fixed --out std7.bin`

2) compile `.f0` → `.tok`:
- `build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok`

3) VM compile phase:
- `build/bin/vmrun --image std7.bin --life <L> --dump compiled_space.bin < prog.tok`

4) prepare for run:
- `build/bin/vmprep_forth0 --image compiled_space.bin`

5) VM run phase:
- `build/bin/vmrun --image compiled_space.bin --life <L> --dump after.bin < /dev/null`

Отладочный раннер:
- `scripts/forth0/run_f0.sh --in <file.f0> --dump-testg N [--expect-hex HEX] [--keep]`

---

## `.f0` syntax (forth0c)

- comments: `# ...` or `\ ...` (to end of line)
- include: `include "path.f0"` (relative to current file)
- directives: `const`, `emit`, `copybits`, `setbit/setbyte/set24`
- macros: `macro NAME(p1,...) ... endmacro`, call `NAME(expr,...)`
- compile-time loops: `for i a b ... endfor` (inclusive)

Expressions support `+ - * /` and parentheses `(...)`.

---

## Alignment contract (block pointers)

Для block pointers адрес должен быть выровнен на 32 бита: `bitaddr % 32 == 0`.

`forth0c` может это проверять строго:

- `F0C_STRICT_ALIGN32=1 build/bin/forth0c ...`  → error при невыровненном `LITAP/LITBP/LITRP`.

---

## Где лежат библиотеки и тесты

- libs: `src/forth0/lib/`
- tests: `src/forth0/tests/`
- host compiler implementation: `src/forth0/host/` (включается в `src/tools/forth0c.c`)
