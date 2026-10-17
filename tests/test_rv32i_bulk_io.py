"""Differential check of the bulk-synchronous RV32I io adapter against the
oracle, on the real new emulator.

Old IN/OUT (ECALL read/write/exit) are mapped to the new data channels and
SYS FSTAT (roadmap 8.1): the observable contract is stdout bytes, the a0
result and the exit status. Contract: same output, registers and status as
rv32i_reference.execute(io=...). The old same-tick channel-status bit is not
a contract (roadmap 8.3).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
sys.path.insert(0, str(ROOT / "tests"))
from rv32i import Layout, REGS, PC
from rv32i_bulk import BulkImage
from rv32i_reference import execute

EMULATOR = os.environ.get("SPACE_EMULATOR", "/home/user/work/positional addressing/space-dev")
SPACE_BYTES = 8 * 1024 * 1024
MEMORY_BYTES = 65536
layout = Layout(SPACE_BYTES)
BASE, MANIFEST = BulkImage(io=True, memory_bytes=MEMORY_BYTES,
                           layout=layout).build().encode(b"")
MEM_BIT = MANIFEST["guest_memory_bit"]
assert MANIFEST["code_end_bit"] < MEM_BIT, MANIFEST["code_end_bit"]
ROOTDIR = Path("tmp/space-tests/rv32i-bulk-io")
ROOTDIR.mkdir(parents=True, exist_ok=True)
case_count = 0

ECALL, EBREAK = 0x00000073, 0x00100073


def iword(f3=0, rd=3, rs1=1, imm=0, op=0x13):
    return ((imm & 4095) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def li(register, value):
    """Load any 32-bit constant with lui/addi (addi sign-extends)."""
    value &= 0xffffffff
    upper = (value + 0x800) >> 12
    lower = value - (upper << 12)
    words = []
    if upper:
        words.append(((upper & 0xfffff) << 12) | (register << 7) | 0x37)
    words.append(iword(rd=register, rs1=register if upper else 0, imm=lower & 0xfff))
    return words


def sycall(a0, a1, a2, a7):
    words = []
    for register, value in ((10, a0), (11, a1), (12, a2), (17, a7)):
        words += li(register, value)
    words.append(ECALL)
    return words


def setreg(register, value):
    return li(register, value)


def write_bits(data, address, value):
    for i in range(32):
        mask = 1 << (7-(address+i) % 8)
        at = (address+i)//8
        data[at] = (data[at] & ~mask) | (mask if (value >> i) & 1 else 0)


def read_frame(raw):
    return [sum(((raw[(REGS+j*32+i)//8] >> (7-(REGS+j*32+i) % 8)) & 1) << i
                for i in range(32)) for j in range(34)]


def run_case(name, words, registers, memory=None, input_data=b"", expect_output=None,
             expect_exit=None):
    global case_count
    program = b"".join(word.to_bytes(4, "little") for word in words)
    registers = dict(registers)
    registers.setdefault(2, 65520)
    io = {"input": input_data, "output": b""}
    expected, expected_memory, _ = execute(program, registers, 0, memory,
                                           memory_bytes=MEMORY_BYTES, io=io)
    if expect_output is not None:
        assert io["output"] == expect_output, (name, io["output"], expect_output)
    if expect_exit is not None:
        assert io.get("exit_code") == expect_exit, (name, io.get("exit_code"))
    core = bytearray(BASE)
    for register in range(32):
        write_bits(core, REGS+register*32, registers.get(register, 0) if register else 0)
    write_bits(core, PC, 0)
    for address, data in (memory or {}).items():
        core[MEM_BIT//8+address:MEM_BIT//8+address+len(data)] = data
    core[MEM_BIT//8:MEM_BIT//8+len(program)] = program
    folder = ROOTDIR / name
    folder.mkdir(exist_ok=True)
    core_path, dump_path = folder / "core.bin", folder / "space.bin"
    core_path.write_bytes(core)
    result = subprocess.run([EMULATOR, "--core", str(core_path),
                             "-s", str(SPACE_BYTES*8-4), "-p", "256", "-t", "0",
                             "--dump-space", str(dump_path)],
                            input=input_data, capture_output=True, timeout=240)
    assert result.returncode == 0, (name, result.stderr[:300])
    raw = dump_path.read_bytes()
    actual = read_frame(raw)
    assert actual == expected[-1], (
        name, {i: (expected[-1][i], actual[i]) for i in range(34) if expected[-1][i] != actual[i]})
    assert raw[MEM_BIT//8:MEM_BIT//8+MEMORY_BYTES] == expected_memory, name
    assert result.stdout == io["output"], (name, result.stdout, io["output"])
    case_count += 1
    print(f"OK bulk RV32I io {name}")


def exit_seq(code=0):
    return setreg(17, 93) + setreg(10, code) + [ECALL]


# write(1, 1024, 5) -> "hello", then exit(0)
run_case("write", sycall(1, 1024, 5, 64) + exit_seq(), {10: 1, 11: 1024, 12: 5, 17: 64},
         memory={1024: b"hello"}, expect_output=b"hello", expect_exit=0)
# write with a two-call sequence: "abc" then "xyz"
run_case("write-twice",
         sycall(1, 1024, 3, 64) + sycall(1, 1028, 3, 64) + exit_seq(7),
         {10: 1, 11: 1024, 12: 3, 17: 64}, memory={1024: b"abc", 1028: b"xyz"},
         expect_output=b"abcxyz", expect_exit=7)
# write zero bytes -> a0 = 0, no output
run_case("write-zero", sycall(1, 1024, 0, 64) + exit_seq(), {10: 1, 11: 1024, 12: 0, 17: 64})
# read(0, 2048, 3) -> a0 = 3, memory "abc"
run_case("read", sycall(0, 2048, 3, 63) + exit_seq(), {10: 0, 11: 2048, 12: 3, 17: 63},
         input_data=b"abcdef", expect_exit=0)
# read past EOF -> a0 = 2
run_case("read-eof", sycall(0, 2048, 5, 63) + exit_seq(), {10: 0, 11: 2048, 12: 5, 17: 63},
         input_data=b"xy")
# write then read: order and independent cursors
run_case("write-read", sycall(1, 1024, 2, 64) + sycall(0, 2048, 4, 63) + exit_seq(),
         {10: 1, 11: 1024, 12: 2, 17: 64}, memory={1024: b"OK"},
         input_data=b"wxyz", expect_output=b"OK")
# exit(42)
run_case("exit", exit_seq(42), {}, expect_exit=42)
# unknown syscall -> a0 = -38
run_case("enosys", sycall(0, 0, 0, 7) + exit_seq(), {10: 0, 11: 0, 12: 0, 17: 7})
# bad descriptor -> a0 = -9
run_case("ebadf", sycall(2, 1024, 4, 64) + exit_seq(), {10: 2, 11: 1024, 12: 4, 17: 64})
# out of range -> a0 = -14
run_case("efault", sycall(1, 65535, 4, 64) + exit_seq(), {10: 1, 11: 65535, 12: 4, 17: 64})
# read bad descriptor -> a0 = -9
run_case("read-ebadf", sycall(1, 2048, 4, 63) + exit_seq(), {10: 1, 11: 2048, 12: 4, 17: 63})
# read zero -> a0 = 0
run_case("read-zero", sycall(0, 2048, 0, 63) + exit_seq(), {10: 0, 11: 2048, 12: 0, 17: 63})

(ROOTDIR / "manifest.json").write_text(json.dumps(MANIFEST, indent=2)+"\n")
print(f"OK bulk RV32I io: {case_count} programs checked against the oracle on the new emulator")
