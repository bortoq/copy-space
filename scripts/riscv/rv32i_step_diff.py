#!/usr/bin/env python3
"""Step-by-step consistency checker for RV32I trace artifacts.

Checks that trace step fields (pc/pc_after/rd_value/mem_write) match
an independent replay of the same binary in RISCVEmulator.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "riscv-port"))

from riscv_emulator import RISCVEmulator  # noqa: E402
from riscv_trace_to_f0 import decode_rv32i  # noqa: E402


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def digest_trace(trace):
    h = hashlib.sha256()
    for e in trace:
        h.update(json.dumps(e, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Validate RV32I trace step fields")
    ap.add_argument("--binary", required=True)
    ap.add_argument("--trace-json", required=True)
    ap.add_argument("--entry-point", type=lambda s: int(s, 0), default=0)
    args = ap.parse_args()

    program = Path(args.binary).read_bytes()
    trace = json.loads(Path(args.trace_json).read_text(encoding="utf-8"))

    emu = RISCVEmulator()
    emu.load_program(program, base=args.entry_point)

    for i, exp in enumerate(trace):
        pc = emu.pc
        if pc != exp.get("pc"):
            return fail(f"step {i}: pc mismatch got={pc} exp={exp.get('pc')}")

        instr = int.from_bytes(emu.memory[pc:pc + 4], "little")
        name, rd, rs1, rs2, imm = decode_rv32i(instr, pc)
        if name != exp.get("instr_name"):
            return fail(f"step {i}: name mismatch got={name} exp={exp.get('instr_name')}")

        pre_rs1 = emu.regs[rs1] & 0xFFFFFFFF if rs1 else 0
        pre_rs2 = emu.regs[rs2] & 0xFFFFFFFF if rs2 else 0
        mem_write = None
        if name == "sw":
            mem_write = {"addr": (pre_rs1 + imm) & 0xFFFFFFFF, "size": 4, "value": pre_rs2}

        emu.pc += 4
        emu.execute(instr)

        got_pc_after = emu.pc
        if got_pc_after != exp.get("pc_after"):
            return fail(f"step {i}: pc_after mismatch got={got_pc_after} exp={exp.get('pc_after')}")

        got_rd_value = (emu.regs[rd] & 0xFFFFFFFF) if rd else None
        if got_rd_value != exp.get("rd_value"):
            return fail(f"step {i}: rd_value mismatch got={got_rd_value} exp={exp.get('rd_value')}")

        if mem_write != exp.get("mem_write"):
            return fail(f"step {i}: mem_write mismatch got={mem_write} exp={exp.get('mem_write')}")

    print("OK: rv32i_step_diff")
    print(f"  steps={len(trace)}")
    print(f"  digest={digest_trace(trace)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
