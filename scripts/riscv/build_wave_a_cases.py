#!/usr/bin/env python3
"""Build tiny raw RV32I binaries for staged RV32I MVP checks (Waves A-E)."""

from pathlib import Path


def r_type(f7, rs2, rs1, f3, rd, opc=0x33):
    return ((f7 & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 0x7) << 12) | ((rd & 0x1F) << 7) | (opc & 0x7F)


def i_type(imm, rs1, f3, rd, opc=0x13):
    imm &= 0xFFF
    return (imm << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 0x7) << 12) | ((rd & 0x1F) << 7) | (opc & 0x7F)


def s_type(imm, rs2, rs1, f3, opc=0x23):
    imm &= 0xFFF
    return (((imm >> 5) & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 0x7) << 12) | ((imm & 0x1F) << 7) | (opc & 0x7F)


def b_type(imm, rs2, rs1, f3, opc=0x63):
    # imm is signed byte offset, must be multiple of 2
    imm &= 0x1FFF
    b12 = (imm >> 12) & 1
    b10_5 = (imm >> 5) & 0x3F
    b4_1 = (imm >> 1) & 0xF
    b11 = (imm >> 11) & 1
    return (b12 << 31) | (b10_5 << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 0x7) << 12) | (b4_1 << 8) | (b11 << 7) | (opc & 0x7F)


def u_type(imm, rd, opc):
    return (imm & 0xFFFFF000) | ((rd & 0x1F) << 7) | (opc & 0x7F)


def j_type(imm, rd, opc=0x6F):
    imm &= 0x1FFFFF
    b20 = (imm >> 20) & 1
    b10_1 = (imm >> 1) & 0x3FF
    b11 = (imm >> 11) & 1
    b19_12 = (imm >> 12) & 0xFF
    return (b20 << 31) | (b10_1 << 21) | (b11 << 20) | (b19_12 << 12) | ((rd & 0x1F) << 7) | (opc & 0x7F)


def le(words):
    out = bytearray()
    for w in words:
        out += int(w & 0xFFFFFFFF).to_bytes(4, "little")
    return bytes(out)


CASES = {
    # Wave A
    "wave_a_demo.bin": le([
        i_type(42, 0, 0, 1),
        r_type(0x00, 1, 1, 0, 2),
        s_type(0, 2, 0, 2),
    ]),
    "wave_a_lui_logic.bin": le([
        u_type(0x12345000, 3, 0x37),  # lui
        i_type(0x678, 3, 6, 3),       # ori
        i_type(0x0FF, 3, 7, 4),       # andi
    ]),
    "wave_a_alu_mix.bin": le([
        i_type(9, 0, 0, 5),
        i_type(4, 0, 0, 6),
        r_type(0x20, 6, 5, 0, 7),     # sub
        r_type(0x00, 5, 7, 4, 8),     # xor
        r_type(0x00, 6, 8, 6, 9),     # or
        r_type(0x00, 5, 9, 7, 10),    # and
    ]),
    # Wave B
    "wave_b_shift_cmp.bin": le([
        i_type(1, 0, 0, 1),
        i_type(3, 0, 0, 2),
        r_type(0x00, 2, 1, 1, 3),     # sll
        r_type(0x00, 2, 3, 5, 4),     # srl
        r_type(0x20, 2, 3, 5, 5),     # sra
        r_type(0x00, 2, 1, 2, 6),     # slt
        r_type(0x00, 1, 2, 3, 7),     # sltu
        i_type(2, 1, 2, 8),           # slti
        i_type(2, 1, 3, 9),           # sltiu
    ]),
    # Wave C/E
    "wave_c_e_mem.bin": le([
        i_type(0x34, 0, 0, 1),        # x1=0x34
        i_type(0x12, 0, 0, 2),        # x2=0x12
        s_type(0, 1, 0, 0),           # sb x1,0(x0)
        s_type(2, 2, 0, 1),           # sh x2,2(x0)
        i_type(0, 0, 0, 10, 0x03),    # lb x10,0(x0)
        i_type(0, 0, 4, 11, 0x03),    # lbu x11,0(x0)
        i_type(2, 0, 1, 12, 0x03),    # lh x12,2(x0)
        i_type(2, 0, 5, 13, 0x03),    # lhu x13,2(x0)
        s_type(8, 13, 0, 2),          # sw x13,8(x0)
        i_type(8, 0, 2, 14, 0x03),    # lw x14,8(x0)
    ]),
    # Wave D
    "wave_d_branch_jump.bin": le([
        i_type(1, 0, 0, 1),           # x1=1
        i_type(2, 0, 0, 2),           # x2=2
        b_type(8, 2, 1, 0),           # beq not taken
        b_type(8, 2, 1, 1),           # bne taken (skip next)
        i_type(99, 0, 0, 3),          # skipped
        b_type(8, 1, 2, 4),           # blt taken
        i_type(77, 0, 0, 4),          # skipped
        u_type(0x1000, 5, 0x17),      # auipc
        j_type(8, 6),                 # jal (skip next)
        i_type(55, 0, 0, 7),          # skipped
        i_type(40, 0, 0, 8),          # x8=40
        i_type(0, 8, 0, 9, 0x67),     # jalr x9,0(x8)
    ]),
}


def main():
    out = Path("scripts/riscv/cases")
    out.mkdir(parents=True, exist_ok=True)
    for name, blob in CASES.items():
        (out / name).write_bytes(blob)
        print(f"wrote {out/name} ({len(blob)} bytes)")


if __name__ == "__main__":
    main()
