#!/bin/bash
# run_riscv_f0.sh — полный пайплайн C2: RISC-V binary → .f0 → VM run
# Usage: ./run_riscv_f0.sh [riscv_binary] [--expect-hex HEX] [--dump-testg N] [--max-instr N]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RISCV_BIN=""
EXPECT_HEX=""
DUMP_TESTG=0
MAX_INSTR=256

# Parse args
while [ $# -gt 0 ]; do
    case "$1" in
        --expect-hex) EXPECT_HEX="$2"; shift 2 ;;
        --dump-testg) DUMP_TESTG="$2"; shift 2 ;;
        --max-instr) MAX_INSTR="$2"; shift 2 ;;
        *)
            if [ -z "$RISCV_BIN" ]; then
                RISCV_BIN="$1"
            fi
            shift
            ;;
    esac
done

echo "=== C2: RISC-V in Copy-Space ==="
echo "RISC-V binary: ${RISCV_BIN:-demo}"

# Step 1: Generate .f0 from RISC-V binary (or use demo)
F0_FILE="$SCRIPT_DIR/generated.f0"
if [ -n "$RISCV_BIN" ] && [ -f "$RISCV_BIN" ]; then
    echo "[1] Generating .f0 from $RISCV_BIN..."
    python3 "$SCRIPT_DIR/riscv_trace_to_f0.py" \
        --binary "$RISCV_BIN" \
        --max-instr "$MAX_INSTR" \
        --out "$F0_FILE"
else
    echo "[1] Using demo program (addi x1, 42; add x2, x1, x1; sw x2, 0)..."
    python3 "$SCRIPT_DIR/riscv_trace_to_f0.py" \
        --max-instr "$MAX_INSTR" \
        --out "$F0_FILE"
fi

echo "[1] Generated $(wc -l < "$F0_FILE") lines of .f0"

# Step 2: Build project tools if needed
echo "[2] Checking build..."
if [ ! -x "$REPO_DIR/build/bin/forth0c" ]; then
    echo "Building project..."
    cd "$REPO_DIR"
    make bins 2>&1 || echo "Warning: build may have partial failures"
    cd "$SCRIPT_DIR"
fi

# Step 3: Run in VM via canonical run_f0 pipeline (compiles + executes)
echo "[3] Running in VM..."
if [ -x "$REPO_DIR/scripts/forth0/run_f0.sh" ]; then
    EXTRA_ARGS=""
    if [ -n "$EXPECT_HEX" ]; then
        EXTRA_ARGS="$EXTRA_ARGS --expect-hex $EXPECT_HEX"
    fi
    if [ "$DUMP_TESTG" -gt 0 ]; then
        EXTRA_ARGS="$EXTRA_ARGS --dump-testg $DUMP_TESTG"
    fi
    "$REPO_DIR/scripts/forth0/run_f0.sh" \
        --in "$F0_FILE" \
        $EXTRA_ARGS 2>&1
else
    echo "[3] run_f0.sh not available — cannot execute in VM"
fi

echo ""
echo "=== Done ==="
