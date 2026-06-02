# Resident Proof Migration Contract

Этот документ фиксирует план миграции доказательной инфраструктуры на финальный контракт.

## 1. Миграцию proof artifacts с bootstrap ABI на final channel-only contract

Необходимо зафиксировать миграцию proof artifacts с bootstrap ABI на final channel-only contract.

### 1.1. Замену bootstrap trace artifacts на resident trace artifacts

Необходимо зафиксировать замену bootstrap trace artifacts на resident trace artifacts.

### 1.2. Замену bootstrap state artifacts на resident state artifacts

Необходимо зафиксировать замену bootstrap state artifacts на resident state artifacts.

## 2. Миграцию validation gates с bootstrap executor на resident executor

Необходимо зафиксировать миграцию validation gates с bootstrap executor на resident executor.

### 2.1. Миграцию directed instruction-family gates

Необходимо зафиксировать миграцию directed instruction-family gates.

### 2.2. Миграцию negative/fault gates

Необходимо зафиксировать миграцию negative/fault gates.

### 2.3. Миграцию replay/determinism gates

Необходимо зафиксировать миграцию replay/determinism gates.

## 3. Критерий готовности к сокращению `space.*`

### 3.1. Критерий готовности resident control plane

критерий готовности resident control plane: resident dispatcher обслуживает запросы через resident protocol без обязательного host-side ABI.

### 3.2. Критерий готовности resident executor

критерий готовности resident executor: guest execution semantics, guest state ownership и stop/fault behavior подтверждены внутри пространства без обязательного host-side executor.

### 3.3. Критерий готовности proof gates

критерий готовности proof gates: trace/state evidence извлекаются через финальный resident path и покрывают directed, negative и replay/determinism validation без bootstrap proof-only ABI.
