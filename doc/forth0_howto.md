# Forth0 HOWTO (recipes)

_file: doc/forth0_howto.md_

This is a practical guide for writing `.f0` programs and adding new tests.

See also:
- `doc/forth0.md` (syntax + pipeline)
- `doc/testing.md` (tests, fail bundles, debugging)

---

## 1) Where to write data (scratch + TESTG)

Use standardized scratch:

- `TESTG` is the conventional output base (policy: `TESTG == TESTSCR_BASE`).
- `std7_fixed` guarantees scratch size is at least **8 KiB** (see `doc/memory_layout.md`).
- Place temporary buffers at fixed offsets from `TESTG`, e.g.:

    const A_base   (TESTG + 256*8)
    const B_base   (TESTG + 320*8)
    const RES_base (TESTG + 384*8)

Stay inside `[TESTSCR_BASE .. TESTSCR_END)`.

(Reference: `doc/memory_layout.md`.)

---

## 2) Common patterns

### Write bytes / 24-bit values
- `setbyte <byte_bitaddr> <u8>`
- `set24 <base_bitaddr> <u24>` (big-endian)

Example:
    setbyte TESTG 0x80
    set24 VAR_A24 0x123456

### Copy raw bit ranges
- `copybits <n> <dst> <src>`

Example (copy 24 bits into output):
    copybits 24 TESTG VAR_SUM24

---

## 3) Use macros and compile-time loops

Macros:
    macro M(a, b)
      setbyte a b
    endmacro

Call:
    M(TESTG, 0x80)

Loops:
    for i 0 7
      setbyte (TESTG + i*8) (0x10 + i)
    endfor

---

## 4) Pointer literals and alignment

Block pointers must be 32-bit aligned (`bitaddr % 32 == 0`).

Strict checking:
    F0C_STRICT_ALIGN32=1 build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok

---

## 5) Running a `.f0` program manually

Dump `TESTG`:
    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4

With expected bytes:
    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4 --expect-hex 80008000

Keep logs/artifacts:
    scripts/forth0/run_f0.sh --in src/forth0/tests/test_add24p_via_prims.f0 --dump-testg 64 --keep

---

## 6) Adding a new regression test (recommended template)

1) Create `src/forth0/tests/test_<name>.f0`
2) Create a TDD harness `scripts/tdd/test_forth0_<name>.sh` that:
   - mkimage
   - forth0c compile
   - vmrun compile
   - vmprep_forth0
   - vmrun run
   - read `TESTG` bytes and compare to expected hex
3) Add the new script to `scripts/tdd/run_all.sh`
4) Ensure `make tdd` is green, commit, push.

Tip: for small tests you can reuse an existing harness style (see `scripts/tdd/test_forth0_2a.sh`).

