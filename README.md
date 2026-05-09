# Copy-Space / Deterministic Data Movement Fabric (DPF)

_file: README.md_

**Pitch (short):** Copy-Space is a tiny deterministic VM for *measuring and reasoning about data movement*.
It treats computation as scheduled bit-copies executed in fixed ticks, making throughput and scheduling constraints explicit.
This is useful for workloads dominated by memory movement (compaction, reorder/permute, partition/materialization).

The core operation is:

    copy(n, dst, src)

All higher-level behavior is built by composing this primitive (plus a small baseline image: `std7_fixed`).

## What’s inside (high-level)

- A minimal bit-addressable VM (`space`, ticks, copy slots)
- A baseline image builder: `mkimage_std7_fixed`
- A host-side `.f0` compiler: `forth0c` (Forth0-first workflow)
- A deterministic testing pipeline (`make test`, `make tdd`, CI)
- Benchmarks and vmrep-based throughput metrics (CSV)

---

## Quick Demo (DB / Analytics Focus)

Build tools:

    make bins

Run demo (produces CSV):

    scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
    cat tmp/demo.csv

Key metric in CSV:

    vmrep_avg_bits_uniq_dst_per_tick

This is effective unique destination bits written per tick (useful write throughput).

---

## Forth0-first workflow (recommended)

This repo uses **host-compiled Forth0** for most tests and higher-level logic:

- `.f0` text program → `build/bin/forth0c` → `.tok` stream
- VM compile phase (`vmrun`) → `vmprep_forth0` → VM run phase (`vmrun`)

Docs:

- `doc/forth0.md`

Run a `.f0` program and dump `TESTG`:

    scripts/forth0/run_f0.sh --in src/forth0/tests/test_eq24.f0 --dump-testg 4

Strict alignment check for block pointers (`LITAP/LITBP/LITRP` immediates must be 32-bit aligned):

    F0C_STRICT_ALIGN32=1 build/bin/forth0c --image std7.bin --in prog.f0 --out prog.tok

---

## Tests

Run all tests:

    make test
    make tdd

Legacy C token-generators (`build/bin/mktok_test_*`) are **optional**:

    make tok
    # or
    make TOK=1 bins

---

## Documentation

Start here:

- `doc/README.md`

Status / roadmap:

- `doc/status.md`
- `doc/roadmap.md`

---

## License

MIT — see LICENSE  
Third-party notes — see THIRD_PARTY.md

---

## Contact

Dmitri Bortoq  
Email: bortoq@gmail.com  
Telegram: @the_arctium  
GitHub repo: https://github.com/bortoq/copy-space
