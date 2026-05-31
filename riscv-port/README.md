# RISC-V Port (C2)

Current scope is the narrow RV32I MVP path (`trace -> .f0 -> VM`).

## Main Commands

- Generate and run demo via C2 pipeline:
  - `riscv-port/run_riscv_f0.sh`
- Generate from a raw binary:
  - `riscv-port/run_riscv_f0.sh path/to/program.bin --max-instr 256`
- Emit artifacts only (`.f0` + JSON trace):
  - `python3 riscv-port/riscv_trace_to_f0.py --binary path/to/program.bin --out tmp/program.f0 --trace-json tmp/trace.json`

## MVP Contract

See `doc/rv32i_mvp.md` for goals, limits, acceptance gates, and metrics.
