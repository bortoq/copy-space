# ABI: std7_fixed artifacts table (ART) — 2026-05-05
_file: doc/abi_artifacts.md_

This document is generated from `src/mkimage/std7_fixed/artifacts.h`.

## How to regenerate
The generator script is:

- `scripts/gen_abi_artifacts_doc.py`

Run `python3 scripts/gen_abi_artifacts_doc.py -h` to see the exact invocation for regeneration.

Consistency is enforced in CI/TDD:
- `scripts/tdd/test_art_doc_sync.sh` runs `scripts/check_art_doc_sync.py --doc doc/abi_artifacts.md`.

## Rules
- ABI is **append-only**: new entries are added only at the end (ART_COUNT increases).
- ART values are **bitaddrs** (bit addresses in `space`).
- Convert to byte offset: `byte = bitaddr / 8`.

## ART base location (std7_fixed)
In std7_fixed tools/tests we treat ART base as:

- `ART = align8(workspace_base + 512)`

I.e. `ART = (workspace_base + 512 + 7) & ~7` (bit address), and ART entries are stored as `ADDR_BITS`-wide values.

## ART table
`ART_COUNT = 70` (valid indices: 0..69)

| Index | Enum name(s) | Meaning |
|---:|---|---|
| ART[0] | `ART_HEAD_CELL` |  |
| ART[1] | `ART_NEXT_IMG` |  |
| ART[2] | `ART_VAR_IP` |  |
| ART[3] | `(reserved)` |  |
| ART[4] | `ART_WORD_SETUP` |  |
| ART[5] | `ART_WORD_INREQ` |  |
| ART[6] | `ART_WORD_OUTREQ` |  |
| ART[7] | `ART_WORD_HALT` |  |
| ART[8] | `(reserved)` |  |
| ART[9] | `(reserved)` |  |
| ART[10] | `(reserved)` |  |
| ART[11] | `(reserved)` |  |
| ART[12] | `(reserved)` |  |
| ART[13] | `(reserved)` |  |
| ART[14] | `(reserved)` |  |
| ART[15] | `(reserved)` |  |
| ART[16] | `(reserved)` |  |
| ART[17] | `(reserved)` |  |
| ART[18] | `(reserved)` |  |
| ART[19] | `(reserved)` |  |
| ART[20] | `ART_VAR_LOOP` |  |
| ART[21] | `ART_WORD_SAVEIP` |  |
| ART[22] | `ART_WORD_JMP` |  |
| ART[23] | `ART_WORD_SETOLEN` |  |
| ART[24] | `ART_WORD_IFGOT0` |  |
| ART[25] | `ART_VAR_N` |  |
| ART[26] | `ART_VAR_DST` |  |
| ART[27] | `ART_VAR_SRC` |  |
| ART[28] | `ART_WORD_LITN` |  |
| ART[29] | `ART_WORD_LITD` |  |
| ART[30] | `ART_WORD_LITS` |  |
| ART[31] | `ART_WORD_COPY` |  |
| ART[32] | `ART_WORD_LITIP` |  |
| ART[33] | `ART_BA` |  |
| ART[34] | `ART_BB` |  |
| ART[35] | `ART_BC` |  |
| ART[36] | `ART_BR` |  |
| ART[37] | `ART_T0` |  |
| ART[38] | `ART_T1` |  |
| ART[39] | `ART_WORD_BNOT` |  |
| ART[40] | `ART_WORD_BAND` |  |
| ART[41] | `ART_CONST1` |  |
| ART[42] | `ART_CONST0` |  |
| ART[43] | `ART_TESTG` | TESTG policy: TESTG == TESTSCR_BASE |
| ART[44] | `ART_WORD_BOR` |  |
| ART[45] | `ART_WORD_BXOR` |  |
| ART[46] | `ART_WORD_ADD24` |  |
| ART[47] | `ART_VAR_A24` |  |
| ART[48] | `ART_VAR_B24` |  |
| ART[49] | `ART_VAR_SUM24` |  |
| ART[50] | `ART_VAR_COUT` |  |
| ART[51] | `ART_WORD_EQ24` |  |
| ART[52] | `ART_VAR_EQ` |  |
| ART[53] | `ART_WORD_LT24` |  |
| ART[54] | `ART_VAR_LT` |  |
| ART[55] | `ART_WORD_LITAP` |  |
| ART[56] | `ART_WORD_LITBP` |  |
| ART[57] | `ART_WORD_LITRP` |  |
| ART[58] | `ART_VAR_AP` |  |
| ART[59] | `ART_VAR_BP` |  |
| ART[60] | `ART_VAR_RP` |  |
| ART[61] | `ART_OFFTAB` |  |
| ART[62] | `ART_WORD_EQ24P` |  |
| ART[63] | `ART_TESTSCR_BASE` | TESTSCR_BASE (standardized test scratch base) |
| ART[64] | `ART_TESTSCR_END` | TESTSCR_END (1 past end) |
| ART[65] | `ART_BUS_BASE` | BUS_BASE (devices bus base) |
| ART[66] | `ART_TERM0_DESC` | TERM0_DESC (terminal device descriptor address) |
| ART[67] | `ART_WORD_LOAD24AP` | WORD_LOAD24AP (block-pointer primitive) |
| ART[68] | `ART_WORD_LOAD24BP` | WORD_LOAD24BP (block-pointer primitive) |
| ART[69] | `ART_WORD_STORE24RP` | WORD_STORE24RP (block-pointer primitive) |

## Notes
- `ART(byte)=...` is printed by `mkimage_std7_fixed` to stderr and is the byte offset of ART in `space`.
- ART entry width is `ADDR_BITS` (typically 24 → 3 bytes per entry).
