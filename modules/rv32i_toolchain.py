"""Discover and invoke a freestanding GCC toolchain; no execution of guest code."""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Toolchain:
    def __init__(self, compiler=None):
        requested = compiler or os.environ.get("RISCV_CC")
        local = ROOT / "tmp/rv32i-toolchain/root/usr/bin/riscv64-unknown-elf-gcc"
        candidate = requested or shutil.which("riscv64-unknown-elf-gcc")
        if not candidate and local.is_file():
            candidate = str(local)
        if not candidate:
            raise ValueError("RISC-V GCC not found; set RISCV_CC")
        resolved = str(Path(candidate).resolve()) if Path(candidate).is_file() else shutil.which(candidate)
        if not resolved:
            raise ValueError("RISC-V GCC not found: " + candidate)
        self.compiler = resolved
        prefix = resolved[:-3] if resolved.endswith("gcc") else "riscv64-unknown-elf-"
        self.objcopy = os.environ.get("RISCV_OBJCOPY", prefix+"objcopy")
        self.objdump = os.environ.get("RISCV_OBJDUMP", prefix+"objdump")
        triple = Path(prefix).name.rstrip("-")
        tools = Path(resolved).parent.parent / "lib" / triple / "bin"
        self.flags = ["-B"+str(tools)+"/"] if (tools / "as").is_file() else []

    def command(self, optimization):
        return [self.compiler] + self.flags + [
            optimization, "-std=c99", "-march=rv32i", "-mabi=ilp32", "-mno-relax",
            "-msmall-data-limit=0", "-ffreestanding", "-fno-pic", "-fno-stack-protector",
            "-nostdlib", "-nostartfiles", "-Wall", "-Wextra", "-Werror", "-Wl,--build-id=none",
        ]
