# Glossary

_file: doc/glossary.md_

A minimal terminology index for this repo.

- **space**: the single VM memory array (bit-addressable).
- **bitaddr**: bit address inside `space`.
- **byte offset**: `byte = bitaddr / 8`.
- **tick**: one VM cycle.
- **slot**: one copy instruction slot executed within a tick.
- **copy(n, dst, src)**: copy `n` bits from `src` bitaddr to `dst` bitaddr.
- **processor_n**: number of slots executed per tick (fixed per VM configuration).
- **ART**: artifacts table (ABI surface) publishing addresses of baseline objects (words/vars/consts/devices).
- **std7_fixed**: the baseline image/ABI used by tools and tests in this repo.
- **TESTSCR**: standardized test scratch region `[TESTSCR_BASE .. TESTSCR_END)`, published via ART.
- **TESTG**: conventional output window base (policy: `TESTG == TESTSCR_BASE`).
- **block pointer**: a bitaddr aligned to 32 bits (`bitaddr % 32 == 0`), used as a base of a 32-bit block.
- **ptrprims**: pointer primitives (e.g. `LOAD24AP`, `STORE24RP`) operating on block pointers.
- **Forth0**: a host-compiled `.f0` language producing `.tok` token streams, executed via VM compile/run pipeline.
- **forth0c**: host compiler for `.f0`.
- **vmrun**: runs the VM on an image, can dump the resulting `space`.
- **vmprep_forth0**: prepares a compiled image for the run phase (boot + VAR_IP setup).
- **vmrep**: VM report emitted by diagnostic tooling; includes throughput-related metrics.
- **fail bundle**: a directory under `tmp/fail/` capturing artifacts/logs for a failing test run.

