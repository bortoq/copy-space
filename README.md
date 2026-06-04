# Copy-Space

Этот репозиторий сведен к антикризисному минимуму.

Текущая цель:
- довести resident `RV32I` proof-closure в `space.c`

Активный baseline:
- `src/vm/space.c`
- `src/vm/space.h`
- `src/vm/rv32.c`
- `src/vm/rv32.h`
- `src/vm/bitcpy.c`
- `src/tools/vmrun.c`
- активные `scripts/tdd/` gates
- активная документация:
  - `doc/project_structure.md`
  - `doc/roadmap.md`
  - `doc/anticrisis_plan.md`
  - `doc/space_contract.md`
  - `doc/legacy_inventory.md`

Единственный допустимый active proof path:
- resident `RV32I` proof path через `space.c`
- resident fault/trace/control gates

Быстрый старт:

```sh
make bins
sh scripts/tdd/run_all.sh
```

План:
- [doc/anticrisis_plan.md](/home/user/work/copy-space/doc/anticrisis_plan.md:1)
- [doc/roadmap.md](/home/user/work/copy-space/doc/roadmap.md:1)
- [doc/legacy_inventory.md](/home/user/work/copy-space/doc/legacy_inventory.md:1)

Исторический материал заморожен в legacy inventory и при необходимости восстанавливается из git.
