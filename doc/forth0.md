# Forth0 (host-compiled) — std7_fixed workflow

_file: doc/forth0.md_

Forth0 in this repository means **host-side compilation** of `.f0` text programs into a binary token stream (`.tok`),
which is then compiled and executed inside the VM.

Recommended development style:
- add new logic/tests/benches as `.f0` + harness scripts,
- avoid changing VM/mkimage/ART unless you really need a new primitive.

---

## Pipeline

1) Build a base image:

- `build/bin/mkimage_std7_fixed --out std7.bin`

2) Compile `.f0` → `.tok`:

- `build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok`

3) VM compile phase:

- `build/bin/vmrun --image std7.bin --life <L> --dump compiled_space.bin < prog.tok`

4) Prepare for run:

- `build/bin/vmprep_forth0 --image compiled_space.bin`

5) VM run phase:

- `build/bin/vmrun --image compiled_space.bin --life <L> --dump after.bin < /dev/null`

Debug helper:

- `scripts/forth0/run_f0.sh --in <file.f0> --dump-testg N [--expect-hex HEX] [--keep]`

---

## `.f0` syntax (`forth0c`)

- comments: `# ...` or `\ ...` to end of line
- include: `include "path.f0"` (relative to current file)
- directives:
  - `const`, `emit`
  - `copybits`, `setbit`, `setbyte`, `set24`
- macros:
  - `macro NAME(p1,...) ... endmacro`
  - call: `NAME(expr,...)`
- compile-time loops:
  - `for i a b ... endfor` (inclusive)

Expressions support `+ - * /` and parentheses `(...)`.

---

## Alignment contract (block pointers)

Block pointers must be 32-bit aligned:

- `bitaddr % 32 == 0`

`forth0c` can enforce this for pointer literals:

- `F0C_STRICT_ALIGN32=1 build/bin/forth0c ...` → error if `LITAP/LITBP/LITRP` immediate is unaligned.

---

## Where things live

- libs: `src/forth0/lib/`
- tests: `src/forth0/tests/`
- host compiler implementation (included into the tool): `src/forth0/host/`
- tool wrapper: `src/tools/forth0c.c`

