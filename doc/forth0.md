# Forth0 (host-compiled) — std7_fixed workflow

Forth0 в этом репозитории — это host-side компиляция текстовых `.f0` программ в бинарный поток токенов `.tok`,
который затем компилируется/исполняется внутри VM.

## Pipeline

1) mkimage:
- build/bin/mkimage_std7_fixed --out std7.bin

2) compile .f0 -> .tok:
- build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok

3) VM compile phase:
- build/bin/vmrun --image std7.bin --life <L> --dump compiled_space.bin < prog.tok

4) prepare for run:
- build/bin/vmprep_forth0 --image compiled_space.bin

5) VM run phase:
- build/bin/vmrun --image compiled_space.bin --life <L> --dump after.bin < /dev/null

## .f0 syntax (forth0c)

- comments: `# ...` or `\ ...` (to end of line)
- include: `include "path.f0"` (relative to current file)
- directives: `const`, `emit`, `copybits`, `setbit/setbyte/set24`
- macros: `macro NAME(p1,...) ... endmacro`, call `NAME(expr,...)`
- compile-time loops: `for i a b ... endfor` (inclusive)
