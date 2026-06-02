# Resident In-Space Guest Runtime Contract

Этот документ фиксирует resident in-space guest runtime, который заменит host-side runtime.

## 1. Resident decode/dispatch contract

resident in-space guest runtime обязан содержать полный resident decode/dispatch contract.

### 1.1. Resident fetch contract

resident fetch contract определяет:

- источник instruction word в resident guest memory;
- ownership текущего guest `PC`;
- чтение instruction bytes без участия host-side executor.

### 1.2. Resident decode contract

resident decode contract определяет:

- разбор opcode и полей инструкции;
- классификацию instruction family;
- передачу decoded form в resident execute path.

### 1.3. Resident execute/commit contract

resident execute/commit contract определяет:

- применение instruction semantics внутри пространства;
- commit register и memory deltas внутри пространства;
- публикацию stop/fault outcomes внутри пространства.

## 2. Resident guest state contract (`PC`, register file, guest memory)

### 2.1. Resident `PC` layout and ownership

resident `PC` layout and ownership должны быть закреплены за resident runtime, а не за хостом.

### 2.2. Resident register file layout and ownership

resident register file layout and ownership должны быть закреплены за resident runtime, а не за хостом.

### 2.3. Resident guest memory layout and ownership

resident guest memory layout and ownership должны быть закреплены за resident runtime, а не за хостом.

## 3. Resident stop/fault contract

### 3.1. Resident unsupported-instruction behavior

resident unsupported-instruction behavior должен давать детерминированную остановку внутри пространства.

### 3.2. Resident alignment-fault behavior

resident alignment-fault behavior должен давать детерминированную fault-семантику внутри пространства.

### 3.3. Resident bounds-fault behavior

resident bounds-fault behavior должен давать детерминированную fault-семантику внутри пространства.

## 4. Resident trace/proof contract после удаления host-side executor

### 4.1. Источник resident trace records

источник resident trace records должен находиться внутри resident runtime, а не в хостовом `space.*`.

### 4.2. Способ извлечения resident trace records наружу

способ извлечения resident trace records наружу должен использовать final channel-only contract или resident protocol поверх него.

### 4.3. Соответствие resident trace contract bootstrap trace contract

соответствие resident trace contract bootstrap trace contract должно сохранять доказуемость `PC`, instruction word, decoder fields, register deltas, memory writes и stop reason.

### 4.4. Замену временного bootstrap trace ABI на resident trace contract

замену временного bootstrap trace ABI на resident trace contract необходимо выполнить до удаления bootstrap proof layer из `space.*`.
