# План миграции resident copicode

Этот документ задает исполнимый план для этапа `10.2`.

## Цель

Перенести orchestration и toolchain control в resident copicode, не добавляя non-emulator logic в `space.*`.

## Этап 1. Зафиксировать границу resident copicode artifact

- Определить тип resident copicode artifact.
- Определить, как resident workload code представляется во время исполнения.
- Определить, как artifact загружается без изменения поведения `space.*`.

## Этап 2. Зафиксировать границу resident copicode execution

- Определить точку входа resident execution для artifact.
- Определить, как job selection подает данные в точку входа.
- Определить, как tool invocation подает данные в точку входа.
- Определить, как toolchain control подает данные в точку входа.

## Этап 3. Зафиксировать migration shims

- Оставить host bootstrap только для загрузки первого resident artifact.
- Оставить host dump и diagnostics только как наблюдаемость.
- Убрать host-side orchestration из active path после подтверждения takeover.

## Этап 4. Зафиксировать проверки

- Добавить одну проверку на загрузку artifact.
- Добавить одну проверку на handoff в resident entrypoint.
- Добавить одну проверку на takeover toolchain control.
- Добавить одну проверку на удаление host-side orchestration.

## Этап 5. Зафиксировать финальное состояние

- Зафиксировать новую границу resident copicode.
- Зафиксировать host responsibilities, которые остаются bootstrap-only.
- Обновить документацию о структуре под новую границу.

## Правило

Этот план не добавляет orchestration logic в `space.*`.

## Связь с поздними этапами

- Этап `18` задает минимальный resident runtime для copy scheduling.
- Этап `19` задает минимальный resident runtime для test orchestration.
- Этап `21` снимает зависимость от host для resident `RISC-V`.
