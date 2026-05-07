# Roadmap / TODO

_file: doc/roadmap.md_

For current done items and test coverage: see `doc/status.md`.

## Next (high priority)

1) Bench CSV schema + harness  
Unify benchmark output into a stable CSV schema + tooling (parse/plot/summarize).

2) Layer scheduler / replication trees  
Scheduling under vertex-disjoint constraints; broadcast via replication trees (reduce depth to ~log2(K)).

## Later

- Devices/channels evolution (see `doc/devices.md`)
- More control-flow / branching primitives (if needed)
- Raw bit pointers (deferred; block pointers are baseline now)

