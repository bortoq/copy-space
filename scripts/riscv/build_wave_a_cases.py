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
        i_type(128, 0, 0, 8),         # x8=128 (jump beyond program to stop)
        i_type(0, 8, 0, 9, 0x67),     # jalr x9,0(x8)
    ]),
    # Non-trivial compute demo for MVP: sum 1..10 -> store 55 at mem[0]
    "wave_mvp_compute.bin": le([
        i_type(1, 0, 0, 1),           # x1=1 (i)
        i_type(11, 0, 0, 2),          # x2=11 (limit exclusive)
        i_type(0, 0, 0, 3),           # x3=0 (sum)
        r_type(0x00, 1, 3, 0, 3),     # loop: add x3,x3,x1
        i_type(1, 1, 0, 1),           # addi x1,x1,1
        b_type(-8, 2, 1, 4),          # blt x1,x2,loop
        s_type(0, 3, 0, 2),           # sw x3,0(x0)
    ]),
    # Edge semantics: sign-extended loads + unsigned compare branch.
    "wave_edge_sign_branch.bin": le([
        i_type(-1, 0, 0, 1),          # x1=-1
        s_type(0, 1, 0, 0),           # sb x1,0(x0) -> 0xFF
        i_type(0, 0, 0, 2, 0x03),     # lb x2,0(x0)  -> 0xFFFFFFFF
        i_type(0, 0, 4, 3, 0x03),     # lbu x3,0(x0) -> 0x000000FF
        b_type(8, 3, 2, 6),           # bltu x2,x3 (not taken)
        i_type(7, 0, 0, 4),           # x4=7 (must execute)
    ]),
    "wave_branch_bge.bin": le([
        i_type(5, 0, 0, 1),           # x1=5
        i_type(5, 0, 0, 2),           # x2=5
        b_type(8, 2, 1, 5),           # bge taken
        i_type(99, 0, 0, 3),          # skipped
        i_type(1, 0, 0, 3),           # x3=1
    ]),
    "wave_branch_bgeu.bin": le([
        i_type(-1, 0, 0, 1),          # x1=0xFFFFFFFF
        i_type(1, 0, 0, 2),           # x2=1
        b_type(8, 2, 1, 7),           # bgeu taken
        i_type(88, 0, 0, 3),          # skipped
        i_type(2, 0, 0, 3),           # x3=2
    ]),
    "wave_jump_jal_link.bin": le([
        j_type(8, 5),                 # jal x5, +8
        i_type(77, 0, 0, 1),          # skipped
        i_type(3, 0, 0, 1),           # x1=3
    ]),
    "wave_mem_signed_half.bin": le([
        i_type(-2, 0, 0, 1),          # x1=0xFFFFFFFE
        s_type(0, 1, 0, 1),           # sh x1,0(x0)
        i_type(0, 0, 1, 2, 0x03),     # lh x2,0(x0) -> 0xFFFFFFFE
        i_type(0, 0, 5, 3, 0x03),     # lhu x3,0(x0) -> 0x0000FFFE
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
