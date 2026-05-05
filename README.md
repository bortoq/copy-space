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

## Tests

Run all tests:

    make test
    make tdd

---

## Documentation

See:

    doc/README.md

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
