# Граница resident runtime для orchestration

Этот документ задает resident runtime boundary для этапа `15`.

## Область

Resident orchestration runtime - это resident execution layer, который после bootstrap владеет orchestration.

Он включает:

- точки входа resident orchestration,
- модель состояния resident orchestration,
- переходы между состояниями resident orchestration,
- интерфейсы resident для job selection, invocation и completion,
- проверочные точки для отделения resident runtime.

## Bootstrap handoff

Host может передать только самый маленький bootstrap payload, который нужен, чтобы войти в resident runtime.

Во время bootstrap:

- host остается bootstrap-only,
- host не принимает active scheduling decisions,
- host не владеет job lifecycle после bootstrap,
- host не реализует семантику resident orchestration.

## Что не входит

Эта граница не включает:

- изменения семантики `space.*`,
- поддержку нового guest ISA,
- восстановление legacy `C3_RUN`,
- семантику `forth0`,
- другие служебные треки,
- расширение host orchestration.

## Правило

Если изменение касается resident orchestration entry, state, lifecycle или интерфейсов после bootstrap, оно относится сюда или в дочерний план, а не в `space.*`.

## Связь с startup contract и execution runtime

Этап `16` задает минимальный startup contract, который передает управление resident runtime. Этап `16` покрывает только fixed slots, bootstrap payload и первый handoff.

Этап `17` задает минимальный resident orchestration execution runtime, который владеет первым циклом orchestration после handoff. Эта граница покрывает точку входа, состояние, интерфейсы и проверки для этого runtime.
