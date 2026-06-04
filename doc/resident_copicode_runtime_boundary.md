# Граница resident copicode runtime

Этот документ задает границу resident runtime для этапа `10.1`.

## Область

Resident copicode runtime - это resident execution layer, который в итоге будет владеть:

- точками входа orchestration,
- состоянием job lifecycle,
- интерфейсами job selection,
- интерфейсами tool invocation,
- интерфейсами toolchain control,
- проверками runtime.

## Целевое состояние

Целевое состояние - это resident runtime boundary, который может нести orchestration и toolchain control behavior без добавления non-emulator logic в `space.*`.

## Что не входит

Эта граница не включает:

- изменения семантики `space.*`,
- поддержку нового guest ISA,
- расширение host orchestration,
- proof logic внутри эмулятора,
- восстановление `C3_RUN`,
- другие служебные треки.

## Правила

- Runtime entrypoints должны принадлежать resident.
- Runtime state должен принадлежать resident.
- Runtime interfaces должны быть явными и machine-checkable.
- Verification gates должны подтвердить границу до переноса исполнения.
- `space.*` остается только эмулятором адресного пространства.

## Связь с другими документами

- `doc/resident_orchestration_boundary.md` задает scope orchestration.
- `doc/resident_boundary_final.md` фиксирует границу между host и resident.
- `doc/resident_orchestration_execution_runtime.md` задает минимальный resident orchestration execution runtime для этапа `17`.
- Этот документ задает runtime layer, который стоит за этими границами.
