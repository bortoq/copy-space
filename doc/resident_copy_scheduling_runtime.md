# Минимальный resident runtime для copy scheduling

Этап `18` задает минимальный resident runtime для copy scheduling.

## Область

Это самый маленький resident-owned scheduling loop, который может управлять fixed-slot копиями после старта orchestration execution runtime.

Он включает только:

- решения по копированию fixed-slot,
- учет запуска и завершения,
- минимальный channel service, нужный для copy scheduling,
- проверяемые gate'ы.

## Форма scheduling

Runtime намеренно маленький:

1. Прочитать resident scheduling state.
2. Выбрать, какое fixed-slot копирование нужно сейчас.
3. Выполнить минимальное копирование.
4. Записать состояние запуска или завершения.
5. Передать или прочитать минимальные channel words для этого шага.
6. Продолжать до bounded stop condition.

## Обязанности host

На этом этапе host остается bootstrap-only:

- подготовить startup payload,
- запустить первый resident tick,
- забрать bounded results только если это нужно.

Host не может:

- принимать решения по copy scheduling после bootstrap,
- владеть состоянием запуска и завершения,
- обрабатывать resident channel для copy scheduling,
- добавлять семантику `space.*`.

## Что не входит

Этот runtime не включает:

- изменения семантики `space.*`,
- поддержку нового guest ISA,
- семантику `forth0`,
- восстановление legacy `C3_RUN`,
- полный перенос test orchestration,
- снятие зависимости от host.

## Проверки

Runtime должен быть защищен проверяемыми gate'ами на:

- форму fixed-slot scheduling,
- отделение от `space.*`,
- host-only обязанности bootstrap,
- минимальное поведение copy/channel/bookkeeping.

## Связь с соседними этапами

- Этап `17` задает минимальный resident runtime для orchestration.
- Этап `19` переносит минимальный test orchestration в resident copicode.
- Этап `20` задает контракт на минимальное снятие зависимости от host.
- Этап `21` снимает зависимость от host для resident `RISC-V`.
