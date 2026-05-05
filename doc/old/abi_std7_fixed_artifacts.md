# doc/abi_std7_fixed_artifacts.md — ABI: std7_fixed artifacts table (ART) — 2026-05-05

Этот документ фиксирует таблицу артефактов `ART` для `std7_fixed`.

## Правила
- ABI **append-only**: новые индексы добавляются только в конец (увеличивается `ART_COUNT`).
- Значения в ART — это **bitaddr** (битовые адреса в `space`).
- Byte-адрес: `byte = bitaddr / 8`.
- `mkimage_std7_fixed` печатает `ART(byte)=...` (byte-адрес начала таблицы ART в `space`).

`ART_COUNT = 70` (валидные индексы: `ART[0]..ART[69]`).

## Таблица ART

| Index | Name | Meaning |
|---:|---|---|
| ART[0] | ART_HEAD_CELL | head cell address |
| ART[1] | ART_NEXT_IMG | NEXT image page |
| ART[2] | ART_VAR_IP | IP variable |
| ART[3] | (reserved) |  |
| ART[4] | ART_WORD_SETUP | word: setup/echo |
| ART[5] | ART_WORD_INREQ | word: inreq |
| ART[6] | ART_WORD_OUTREQ | word: outreq |
| ART[7] | ART_WORD_HALT | word: halt |
| ART[8] | (reserved) |  |
| ART[9] | (reserved) |  |
| ART[10] | (reserved) |  |
| ART[11] | (reserved) |  |
| ART[12] | (reserved) |  |
| ART[13] | (reserved) |  |
| ART[14] | (reserved) |  |
| ART[15] | (reserved) |  |
| ART[16] | (reserved) |  |
| ART[17] | (reserved) |  |
| ART[18] | (reserved) |  |
| ART[19] | (reserved) |  |
| ART[20] | ART_VAR_LOOP | loop variable |
| ART[21] | ART_WORD_SAVEIP | word: saveip |
| ART[22] | ART_WORD_JMP | word: jmp |
| ART[23] | ART_WORD_SETOLEN | word: setolen |
| ART[24] | ART_WORD_IFGOT0 | word: ifgot0 |
| ART[25] | ART_VAR_N | VAR_N |
| ART[26] | ART_VAR_DST | VAR_DST |
| ART[27] | ART_VAR_SRC | VAR_SRC |
| ART[28] | ART_WORD_LITN | word: litn |
| ART[29] | ART_WORD_LITD | word: litd |
| ART[30] | ART_WORD_LITS | word: lits |
| ART[31] | ART_WORD_COPY | word: copy |
| ART[32] | ART_WORD_LITIP | word: litip |
| ART[33] | ART_BA | BA scratch |
| ART[34] | ART_BB | BB scratch |
| ART[35] | ART_BC | BC scratch |
| ART[36] | ART_BR | BR scratch |
| ART[37] | ART_T0 | T0 scratch |
| ART[38] | ART_T1 | T1 scratch |
| ART[39] | ART_WORD_BNOT | word: bnot |
| ART[40] | ART_WORD_BAND | word: band |
| ART[41] | ART_CONST1 | CONST1 base |
| ART[42] | ART_CONST0 | CONST0 base |
| ART[43] | ART_TESTG | policy: TESTG == TESTSCR_BASE |
| ART[44] | ART_WORD_BOR | word: bor |
| ART[45] | ART_WORD_BXOR | word: bxor |
| ART[46] | ART_WORD_ADD24 | word: add24 (2a) |
| ART[47] | ART_VAR_A24 | VAR_A24 |
| ART[48] | ART_VAR_B24 | VAR_B24 |
| ART[49] | ART_VAR_SUM24 | VAR_SUM24 |
| ART[50] | ART_VAR_COUT | VAR_COUT |
| ART[51] | ART_WORD_EQ24 | word: eq24 (2a) |
| ART[52] | ART_VAR_EQ | VAR_EQ |
| ART[53] | ART_WORD_LT24 | word: lt24 (2a) |
| ART[54] | ART_VAR_LT | VAR_LT |
| ART[55] | ART_WORD_LITAP | word: litap (2b) |
| ART[56] | ART_WORD_LITBP | word: litbp (2b) |
| ART[57] | ART_WORD_LITRP | word: litrp (2b) |
| ART[58] | ART_VAR_AP | VAR_AP |
| ART[59] | ART_VAR_BP | VAR_BP |
| ART[60] | ART_VAR_RP | VAR_RP |
| ART[61] | ART_OFFTAB | OFFTAB (5-bit offsets table) |
| ART[62] | ART_WORD_EQ24P | word: eq24p (2b) |
| ART[63] | ART_TESTSCR_BASE | standardized test scratch base |
| ART[64] | ART_TESTSCR_END | standardized test scratch end (1 past end) |
| ART[65] | ART_BUS_BASE | devices bus base |
| ART[66] | ART_TERM0_DESC | TERM0 device descriptor address |
| ART[67] | ART_WORD_LOAD24AP | word: load24ap (block pointer primitive) |
| ART[68] | ART_WORD_LOAD24BP | word: load24bp (block pointer primitive) |
| ART[69] | ART_WORD_STORE24RP | word: store24rp (block pointer primitive) |

## Примечания
- Если вы добавляете новые артефакты, обновляйте `ART_COUNT` и дописывайте их **только в конец**.
- `scripts/check_art_doc_sync.py` должен проходить (проверяет, что в документе упомянуты все `ART[i]`).
