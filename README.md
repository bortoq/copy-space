# Copy-Space / Deterministic Data Movement Fabric (DPF)

Copy-Space is a minimal deterministic execution model focused on data movement.

The core operation is a scheduled memory copy:

    copy(n, dst, src)

All higher-level behavior (compaction, reorder, gather/scatter, arithmetic) is built on top of this primitive.

---

## Quick Demo (DB / Analytics Focus)

Build tools:

    make bins

Run demo (produces CSV):

    scripts/demo_db.sh > /dev/null 2> tmp/demo.stderr
    cat tmp/demo.csv

Key metric in CSV:

    vmrep_avg_bits_uniq_dst_per_tick

This shows effective unique destination bits written per tick (useful write throughput).

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

See:

- `doc/README.md`
- `doc/forth0.md`
- `doc/21_todo_status.md` (status/progress)

---

## License

MIT — see LICENSE  
Third-party notes — see THIRD_PARTY.md

---

## Contact

Dmitri Bortoq  
Email: bortoq@gmail.com  
Telegram: @the_arctium  
GitHub: https://github.com/bortoq/parallel-computing
