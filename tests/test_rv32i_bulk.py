"""Differential check of the bulk-synchronous RV32I generator (roadmap
8.10) against the independent oracle, on the real new emulator.

The image is generated once (the code layout does not depend on the
program); each case patches only the initial registers, PC, guest memory
and program, runs the new emulator with --core and compares the final
state frame and the guest memory with rv32i_reference.execute.
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules"))
sys.path.insert(0, str(ROOT / "tests"))
from rv32i import Layout, REGS, PC, STATUS
from rv32i_bulk import BulkImage
from rv32i_reference import execute

EMULATOR = os.environ.get("SPACE_EMULATOR", "/home/user/work/positional addressing/space-dev")
SPACE_BYTES = 8 * 1024 * 1024
MEMORY_BYTES = 65536
layout = Layout(SPACE_BYTES)
BASE, MANIFEST = BulkImage(memory_bytes=MEMORY_BYTES, layout=layout).build().encode(b"")
MEM_BIT = MANIFEST["guest_memory_bit"]
assert MANIFEST["code_end_bit"] < MEM_BIT, MANIFEST["code_end_bit"]
ROOTDIR = Path("tmp/space-tests/rv32i-bulk")
ROOTDIR.mkdir(parents=True, exist_ok=True)
case_count = 0


def iword(f3=0, rd=3, rs1=1, imm=0, op=0x13):
    return ((imm & 4095) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def rword(f3=0, rd=3, rs1=1, rs2=2, f7=0):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x33


def sword(f3=2, rs1=1, rs2=2, imm=0):
    imm &= 4095
    return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm & 31) << 7) | 0x23


def bword(f3=0, rs1=1, rs2=2, offset=8):
    offset &= 8191
    return (((offset >> 12) & 1) << 31) | (((offset >> 5) & 63) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (((offset >> 1) & 15) << 8) | (((offset >> 11) & 1) << 7) | 0x63


def jword(rd=1, offset=8):
    offset &= (1 << 21)-1
    return (((offset >> 20) & 1) << 31) | (((offset >> 1) & 1023) << 21) | (((offset >> 11) & 1) << 20) | (((offset >> 12) & 255) << 12) | (rd << 7) | 0x6f


def write_bits(data, address, value):
    for i in range(32):
        mask = 1 << (7-(address+i) % 8)
        at = (address+i)//8
        data[at] = (data[at] & ~mask) | (mask if (value >> i) & 1 else 0)


def read_frame(raw):
    return [sum(((raw[(REGS+j*32+i)//8] >> (7-(REGS+j*32+i) % 8)) & 1) << i
                for i in range(32)) for j in range(34)]


def run_case(name, words, registers=None, entry=0, memory=None, expected_status=None):
    global case_count
    program = b"".join(word.to_bytes(4, "little") for word in words)
    registers = {2: 65520} if registers is None else registers
    expected, expected_memory, _ = execute(program, registers, entry, memory,
                                           memory_bytes=MEMORY_BYTES)
    if expected_status is not None:
        assert expected[-1][-1] == expected_status, (name, expected[-1][-1])
    core = bytearray(BASE)
    for register in range(32):
        write_bits(core, REGS+register*32, registers.get(register, 0) if register else 0)
    write_bits(core, PC, entry)
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
                            capture_output=True, timeout=120)
    assert result.returncode == 0, (name, result.stderr[:200])
    raw = dump_path.read_bytes()
    actual = read_frame(raw)
    assert actual == expected[-1], (
        name, {i: (expected[-1][i], actual[i]) for i in range(34) if expected[-1][i] != actual[i]})
    assert raw[MEM_BIT//8:MEM_BIT//8+MEMORY_BYTES] == expected_memory, name
    assert raw[:MANIFEST["layer_bits"]//8] == bytes(MANIFEST["layer_bits"]//8), name
    case_count += 1
    print(f"OK bulk RV32I {name}")


# arithmetic and upper immediates
run_case("first", [iword(rd=1, rs1=0, imm=1), iword(rd=2, rs1=0, imm=2), rword(), 0x73])
run_case("carry32", [rword(), 0x73], {1: 0xffffffff, 2: 1})
values = [0, 1, 0x7fffffff, 0x80000000, 0xffffffff, 0x55555555, 0xaaaaaaaa]
for index, value in enumerate(values):
    words = []
    for immediate in [-2048, -1, 0, 1, 2047]:
        words += [iword(f3=f3, rd=3+f3, imm=immediate) for f3 in (0, 2, 3, 4, 6, 7)]
    words += [rword(f3=f3, rd=3+f3) for f3 in range(8)]
    words += [rword(rd=11, f7=32), rword(f3=5, rd=12, f7=32), 0x73]
    run_case(f"arithmetic-{index}", words, {1: value, 2: values[-1-index]})
for value in [0x80000001, 0xffffffff, 0x7fffffff]:
    words = []
    for amount in range(32):
        words += [iword(1, rd=3, imm=amount), iword(5, rd=4, imm=amount),
                  iword(5, rd=5, imm=1024+amount), iword(rd=2, rs1=0, imm=amount),
                  rword(1, rd=6), rword(5, rd=7), rword(5, rd=8, f7=32)]
    run_case(f"shifts-{value:08x}", words+[0x73], {1: value})
run_case("shift-mask", [rword(1), rword(5, rd=4), rword(5, rd=5, f7=32), 0x73],
         {1: 0x87654321, 2: 0xfffffffe})
run_case("upper", [0x123451b7, 0x80000237, 0xfffff297, 0x00000317, 0x73])
run_case("aliases-x0", [rword(rd=1), rword(rd=2), rword(rd=0),
                        iword(rd=0, imm=-1), rword(rd=3, rs1=0, rs2=0), 0x73], {1: 7, 2: 9})
for f3 in [0, 1, 4, 5, 6, 7]:
    for tag, a, b in [("equal", 1, 1), ("signed", 0xffffffff, 1), ("less", 0, 0xffffffff)]:
        run_case(f"branch-{f3}-{tag}", [bword(f3), iword(rd=3, rs1=0, imm=17),
                                       iword(rd=4, rs1=0, imm=23), 0x73], {1: a, 2: b})
run_case("backward-loop", [iword(rd=1, rs1=0, imm=8), iword(rd=3, rs1=0, imm=0),
                           rword(rd=3, rs1=3, rs2=1), iword(rd=1, imm=-1),
                           bword(1, rs1=1, rs2=0, offset=-8), 0x73])
run_case("calls", [jword(offset=12), iword(rd=4, rs1=0, imm=23), 0x73,
                   iword(rd=3, rs1=0, imm=17), iword(rd=0, rs1=1, op=0x67)])
run_case("jalr-alias-bit0", [iword(rd=1, rs1=1, imm=1, op=0x67), 0x73], {1: 4})
run_case("jal-zero", [jword(rd=0, offset=4), 0x73])
run_case("jal-negative", [0x73, jword(rd=0, offset=-4)], entry=4)
for offset in [2048, 4096, 32768, 65532]:
    run_case(f"jal-offset-{offset}", [jword(offset=offset)], memory={offset: b"\x73\0\0\0"})
run_case("branch-offset-2048", [bword(offset=2048)], {1: 1, 2: 1}, memory={2048: b"\x73\0\0\0"})
run_case("jalr-wrap", [iword(op=0x67, rd=1, imm=5), 0x73], {1: 0xffffffff})
memory_program = [sword(f3=2), iword(f3=2, rd=3, op=3), iword(f3=0, rd=4, op=3),
                  iword(f3=4, rd=5, op=3), iword(f3=1, rd=6, op=3), iword(f3=5, rd=7, op=3),
                  sword(f3=0, imm=5), sword(f3=1, imm=6), iword(f3=2, rd=8, imm=4, op=3), 0x73]
run_case("memory", memory_program, {1: 1024, 2: 0x8765fedc})
run_case("negative-offset", [sword(imm=-4), iword(f3=2, imm=-4, op=3), 0x73], {1: 1028, 2: 0x12345678})
run_case("memory-last-byte", [sword(f3=0), iword(f3=0, op=3), iword(f3=4, rd=4, op=3), 0x73],
         {1: 65535, 2: 255})
run_case("memory-last-word", [sword(), iword(f3=2, op=3), 0x73], {1: 65532, 2: 0xffffffff})
run_case("self-modifying-guest", [sword(imm=4), 0, 0x73], {1: 0, 2: iword(rd=3, rs1=0, imm=42)})
run_case("fence-hints", [0x0ff0000f, 0x8330000f, 0x0ff0808f, 0x13, 0x73])
run_case("ebreak", [0x100073], expected_status=2)
illegal = [0, 0xffffffff, rword(f7=1), rword(f3=1, f7=32), iword(f3=1, imm=32),
           iword(f3=5, imm=32), iword(op=0x67, f3=1), bword(f3=2),
           iword(op=3, f3=3), sword(f3=3), 0x100f, 0x1073, 0x200073, 0x80000073]
for index, word in enumerate(illegal):
    run_case(f"illegal-{index}", [word], {1: 1024, 2: 123}, expected_status=3)
for f3, width in [(0, 1), (1, 2), (2, 4), (4, 1), (5, 2)]:
    run_case(f"load-access-{f3}", [iword(op=3, f3=f3, rd=0)], {1: 65536}, expected_status=6)
    if width > 1:
        run_case(f"load-align-{f3}", [iword(op=3, f3=f3)], {1: 1025}, expected_status=7)
for f3 in [0, 1, 2]:
    run_case(f"store-access-{f3}", [sword(f3=f3)], {1: 0xffffffff, 2: 0x87654321}, expected_status=8)
    if f3:
        run_case(f"store-align-{f3}", [sword(f3=f3)], {1: 1025, 2: 0x87654321}, expected_status=9)
run_case("fetch-align", [0x73], entry=2, expected_status=5)
run_case("fetch-access", [0x73], entry=65536, expected_status=4)
run_case("jal-align", [jword(offset=2)], {1: 99}, expected_status=5)
run_case("jalr-align", [iword(op=0x67, rd=1)], {1: 3}, expected_status=5)
run_case("branch-align-taken", [bword(offset=2)], {1: 1, 2: 1}, expected_status=5)
run_case("branch-align-untaken", [bword(offset=2), 0x73], {1: 1, 2: 2}, expected_status=1)
run_case("jump-outside", [jword(offset=-4)], expected_status=4)
run_case("pc-last-instruction", [], entry=65532, memory={65532: b"\x13\0\0\0"}, expected_status=4)
rng = random.Random(20261011)
for stream in range(8):
    words = []
    for _ in range(60):
        rd, rs1, rs2 = [rng.randrange(32) for _ in range(3)]
        f3 = rng.randrange(8)
        if rng.randrange(2):
            f7 = rng.choice([0, 32]) if f3 in (0, 5) else 0
            words.append(rword(f3, rd, rs1, rs2, f7))
        else:
            imm = rng.randrange(-2048, 2048)
            if f3 in (1, 5):
                imm = rng.randrange(32) + (1024 if f3 == 5 and rng.randrange(2) else 0)
            words.append(iword(f3, rd, rs1, imm))
    run_case(f"random-{stream}", words+[0x73], {i: rng.getrandbits(32) for i in range(1, 32)})
(ROOTDIR / "manifest.json").write_text(json.dumps(MANIFEST, indent=2)+"\n")
print(f"OK bulk RV32I: {case_count} programs checked against the oracle on the new emulator")
