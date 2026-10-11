"""Compare every RV32I state frame and final memory with a separate oracle."""
import json
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules"))
from rv32i import Image
from rv32i_reference import execute

ROOT = Path("tmp/space-tests/rv32i")
ROOT.mkdir(parents=True, exist_ok=True)
REG_BASE, MEMORY_BASE = 131072, 8388608
PC_BIT = REG_BASE+1024
BASE, MANIFEST = Image(True, memory_bytes=65536).build().encode()
(ROOT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2)+"\n")
assert MANIFEST["layer_count"] > 0 and MANIFEST["code_end_bit"] < MEMORY_BASE
case_count = frame_count = 0
coverage = set()


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
        mask = 1 << (7-(address+i)%8)
        at = (address+i)//8
        data[at] = (data[at] & ~mask) | (mask if (value >> i) & 1 else 0)


def read_frame(raw):
    assert len(raw) == 136
    return [sum(((raw[j*4+i//8] >> (7-i%8)) & 1) << i for i in range(32)) for j in range(34)]


def run_case(name, words, registers=None, entry=0, memory=None, expected_status=None):
    global case_count, frame_count
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    program = b"".join(word.to_bytes(4, "little") for word in words)
    registers = {2: 65520} if registers is None else registers
    expected, expected_memory, fetches = execute(program, registers, entry, memory, coverage=coverage)
    if expected_status is not None:
        assert expected[-1][-1] == expected_status
    core = bytearray(BASE)
    for register in range(32):
        write_bits(core, REG_BASE+register*32, registers.get(register, 0) if register else 0)
    write_bits(core, PC_BIT, entry)
    for address, data in (memory or {}).items():
        core[MEMORY_BASE//8+address:MEMORY_BASE//8+address+len(data)] = data
    core[MEMORY_BASE//8:MEMORY_BASE//8+len(program)] = program
    (folder / "core.bin").write_bytes(core)
    (folder / "program.bin").write_bytes(program)
    (folder / "in.bin").write_bytes(b"")
    (folder / "initial.json").write_text(json.dumps({"registers": registers, "entry": entry}, indent=2)+"\n")
    args = ["build/bin/space_image_proof", "--core", str(folder / "core.bin"),
            "--in", str(folder / "in.bin"), "--out", str(folder / "out.bin"),
            "--dump-space", str(folder / "space.bin"), "--trace", str(folder / "trace.txt"),
            "--report", str(folder / "report.txt"), "--ticks", str(100*len(expected)+100)]
    (folder / "args.json").write_text(json.dumps(args, indent=2)+"\n")
    result = subprocess.run(args, capture_output=True, timeout=20)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, (name, result.stderr)
    output = (folder / "out.bin").read_bytes()
    assert len(output) == 136*len(expected), (name, len(output), len(expected))
    actual = [read_frame(output[offset:offset+136]) for offset in range(0, len(output), 136)]
    for step, (want, got) in enumerate(zip(expected, actual)):
        assert got == want, (name, step, {i: (want[i], got[i]) for i in range(34) if want[i] != got[i]})
    (folder / "states.json").write_text(json.dumps(actual, indent=2)+"\n")
    raw = (folder / "space.bin").read_bytes()
    assert raw[MEMORY_BASE//8:MEMORY_BASE//8+65536] == expected_memory, name
    assert raw[:2272] == bytes(2272), name
    assert read_frame(raw[REG_BASE//8:REG_BASE//8+136]) == expected[-1], name
    report = dict(line.split("=", 1) for line in (folder / "report.txt").read_text().splitlines())
    assert report["stop"] == "idle", (name, report)
    # Each instruction is fetched from a runtime-computed guest address.
    observed_fetches = []
    active_layer = MANIFEST["labels"]["fetch"]
    for line in (folder / "trace.txt").read_text().splitlines():
        parts = line.split()
        if parts[0] == "copy":
            _, tick, slot, n, dst, src = parts
            if (active_layer == MANIFEST["fetch_layer_bit"] and int(n) == 32 and
                    int(dst) == 135200 and int(src) >= MEMORY_BASE):
                observed_fetches.append((int(src)-MEMORY_BASE)//8)
            if int(n) == 18176 and int(dst) == 0:
                active_layer = int(src)
    assert observed_fetches == fetches, (name, observed_fetches, fetches)
    case_count += 1
    frame_count += len(actual)
    print(f"OK RV32I {name}: {len(actual)} states, {report['ticks']} ticks, status={actual[-1][-1]}")
    return folder, actual


# First public example and the full carry chain, with explicit arithmetic expectations.
_, frames = run_case("first", [iword(rd=1, rs1=0, imm=1), iword(rd=2, rs1=0, imm=2), rword(), 0x73])
assert frames[-1][3] == 3
folder, frames = run_case("carry32", [rword(), 0x73], {1: 0xffffffff, 2: 1})
assert frames[0][3] == 0
adder = MANIFEST["gate_tables"]["adder"]
trace = (folder / "trace.txt").read_text().splitlines()
add_tick = next(int(line.split()[1])+1 for line in trace if line.startswith("copy ") and
                line.split()[3:] == ["18176", "0", str(MANIFEST["labels"]["add"])])
indices = [(int(p[5])-adder)//2 for line in trace if (p := line.split())[0] == "copy" and
           int(p[1]) == add_tick and p[3:5] == ["2", "135488"]]
assert indices == [3]+[5]*31, indices
(folder / "carry_indices.json").write_text(json.dumps(indices)+"\n")

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

# The production CLI also generates a silent image; ordinary space executes it.
silent = ROOT / "silent"
silent.mkdir(exist_ok=True)
(silent / "program.bin").write_bytes(b"\x93\x00\x10\x00\x73\x00\x00\x00")
subprocess.run([sys.executable, "modules/rv32i.py", "--program", str(silent / "program.bin"),
                "--output", str(silent / "core.bin"), "--manifest", str(silent / "manifest.json")], check=True)
result = subprocess.run(["build/bin/space", "--core", str(silent / "core.bin")],
                        input=b"", capture_output=True, check=True, timeout=5)
(silent / "out.bin").write_bytes(result.stdout)
assert result.stdout == b""
assert coverage == set("LUI AUIPC JAL JALR BEQ BNE BLT BGE BLTU BGEU LB LH LW LBU LHU SB SH SW "
                       "ADDI SLTI SLTIU XORI ORI ANDI SLLI SRLI SRAI ADD SUB SLL SLT SLTU XOR SRL SRA OR AND "
                       "FENCE ECALL EBREAK".split()), coverage
(ROOT / "coverage.json").write_text(json.dumps(sorted(coverage), indent=2)+"\n")
print(f"OK RV32I: {case_count} programs, {frame_count} independently checked states")
