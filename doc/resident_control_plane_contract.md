# Resident In-Space Control Plane Contract

Этот документ фиксирует resident in-space control plane, который заменит bootstrap ABI.

## 1. Resident memory layout control plane

В пространстве должны быть зафиксированы отдельные области для:

- resident dispatcher state;
- resident request/response buffers;
- resident service code.

resident dispatcher state хранит фазу control plane, ownership активного запроса и данные handoff.

resident request/response buffers содержат сериализованные запросы и ответы resident channel protocol.

resident service code содержит resident dispatcher, resident service handlers и resident handoff logic.

## 2. Resident channel protocol внутри пространства

Необходимо зафиксировать resident channel protocol внутри пространства как replacement для bootstrap ABI.

### 2.1. Формат resident request

формат resident request должен включать:

- код операции;
- область аргументов;
- признак владения запросом;
- признак готовности запроса к обработке.

### 2.2. Формат resident response

формат resident response должен включать:

- код завершения;
- область полезного результата;
- признак готовности ответа;
- признак завершения handoff в resident steady-state.

### 2.3. Handshake semantics resident protocol

handshake semantics resident protocol должны определять:

- момент принятия resident request;
- момент публикации resident response;
- момент освобождения буферов;
- запрет на одновременное владение одним запросом хостом и resident dispatcher.

## 3. Resident bootstrapping sequence от одного загруженного слота

### 3.1. Начальную загрузку resident bootstrap payload

Необходимо зафиксировать начальную загрузку resident bootstrap payload через единственный разрешенный bootstrap path хоста.

### 3.2. Развертывание resident dispatcher в пространстве

Необходимо зафиксировать развертывание resident dispatcher в пространстве из bootstrap payload.

### 3.3. Переход от bootstrap payload к resident steady-state

Необходимо зафиксировать переход от bootstrap payload к resident steady-state без возврата к расширенному host-side ABI.

## 4. Resident handoff от bootstrap path к in-space control plane

### 4.1. Момент завершения bootstrap ABI

Необходимо зафиксировать момент завершения bootstrap ABI как точку, после которой запросы больше не интерпретируются хостовым dispatcher.

### 4.2. Первый запрос, обслуживаемый resident control plane

Необходимо зафиксировать первый запрос, обслуживаемый resident control plane, как observable proof of handoff.

### 4.3. Rollback/fail behavior при срыве handoff

Необходимо зафиксировать rollback/fail behavior при срыве handoff.

Если resident dispatcher не развернут или resident protocol не вошел в steady-state, bootstrap path должен завершаться детерминированной ошибкой, а не неявным возвратом к постоянному host-side сервису.
