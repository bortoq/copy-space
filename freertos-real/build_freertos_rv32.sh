#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/freertos-real/out"
mkdir -p "$OUT_DIR"

CC="riscv-none-elf-gcc"
CFLAGS=(
  -march=rv32im_zicsr -mabi=ilp32 -mcmodel=medany
  -O2 -g -ffreestanding -fno-builtin -fdata-sections -ffunction-sections
  -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers
  -I"$ROOT/freertos-real/include"
  -I"$ROOT/third_party/FreeRTOS-Kernel/include"
  -I"$ROOT/freertos-real/portable/GCC/RISC-V"
  -DprojCOVERAGE_TEST=0
)

SRCS=(
  "$ROOT/freertos-real/src/main.c"
  "$ROOT/freertos-real/src/platform.c"
  "$ROOT/third_party/FreeRTOS-Kernel/tasks.c"
  "$ROOT/third_party/FreeRTOS-Kernel/list.c"
  "$ROOT/third_party/FreeRTOS-Kernel/queue.c"
  "$ROOT/third_party/FreeRTOS-Kernel/timers.c"
  "$ROOT/freertos-real/portable/MemMang_heap_4.c"
  "$ROOT/freertos-real/portable/GCC/RISC-V/port.c"
  "$ROOT/freertos-real/portable/GCC/RISC-V/mpu_wrappers_v2_asm.c"
  "$ROOT/freertos-real/portable/GCC/RISC-V/mpu_wrappers_template.c"
)

ASMS=(
  "$ROOT/freertos-real/src/startup.S"
  "$ROOT/freertos-real/portable/GCC/RISC-V/portASM.S"
)

OBJS=()
for s in "${SRCS[@]}"; do
  o="$OUT_DIR/$(basename "${s%.*}").o"
  "$CC" "${CFLAGS[@]}" -c "$s" -o "$o"
  OBJS+=("$o")
done
for s in "${ASMS[@]}"; do
  o="$OUT_DIR/$(basename "${s%.*}").o"
  "$CC" "${CFLAGS[@]}" -x assembler-with-cpp -c "$s" -o "$o"
  OBJS+=("$o")
done

ELF="$OUT_DIR/rtos.elf"
BIN="$OUT_DIR/rtos.bin"
RV32M="$OUT_DIR/rtos.rv32m"

"$CC" -nostartfiles -Wl,--gc-sections -T "$ROOT/freertos-real/src/linker.ld" \
  -o "$ELF" "${OBJS[@]}"

riscv-none-elf-objcopy -O binary "$ELF" "$BIN"

python3 "$ROOT/scripts/riscv/rv32m_image_builder.py" build \
  --payload "$BIN" --output "$RV32M" --entry 0 --processor-bits "$(( $(stat -c%s "$BIN") * 8 ))" >/dev/null

echo "Built: $ELF"
echo "Built: $BIN"
echo "Built: $RV32M"
