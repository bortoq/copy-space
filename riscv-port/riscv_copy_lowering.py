"""
RISC-V → Copy-Space lowering
Each RISC-V instruction is decomposed into primitive copy operations.
This is the foundation for running RISC-V natively in Copy-Space.
"""

def lower_addi(rd, rs1, imm):
    """addi rd, rs1, imm → sequence of copy operations"""
    ops = []
    # 1. Copy register rs1 to temporary A
    ops.append(("copybits", f"reg{rs1}", "ALU_A", 32))
    # 2. Copy immediate to ALU_B
    ops.append(("copybits", f"imm_{imm}", "ALU_B", 32))
    # 3. (In real system: addition happens via carry propagation copies)
    # 4. Copy result to destination register
    ops.append(("copybits", "ALU_result", f"reg{rd}", 32))
    return ops

def lower_add(rd, rs1, rs2):
    """add rd, rs1, rs2 → copy sequence"""
    return [
        ("copybits", f"reg{rs1}", "ALU_A", 32),
        ("copybits", f"reg{rs2}", "ALU_B", 32),
        ("copybits", "ALU_result", f"reg{rd}", 32),
    ]

# Example
print("addi x1, x0, 42 lowered to:")
for op in lower_addi(1, 0, 42):
    print("  ", op)

print("\nadd x3, x1, x2 lowered to:")
for op in lower_add(3, 1, 2):
    print("  ", op)