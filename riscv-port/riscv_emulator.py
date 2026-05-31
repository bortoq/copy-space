"""
RISC-V RV32I Emulator for Copy-Space port (stage 1 complete)
Supports most of RV32I base integer instruction set.
"""

class RISCVEmulator:
    def __init__(self, mem_size=1024*1024):
        self.regs = [0] * 32
        self.memory = bytearray(mem_size)
        self.pc = 0

    def fetch(self):
        instr = int.from_bytes(self.memory[self.pc:self.pc+4], 'little')
        self.pc += 4
        return instr

    @staticmethod
    def _u32(x):
        return x & 0xFFFFFFFF

    @staticmethod
    def _s32(x):
        x &= 0xFFFFFFFF
        return x if x < 0x80000000 else x - 0x100000000

    @staticmethod
    def _sign_extend(x, bits):
        m = 1 << (bits - 1)
        return (x & (m - 1)) - (x & m)

    def execute(self, instr):
        opcode = instr & 0x7f
        rd  = (instr >> 7) & 0x1f
        rs1 = (instr >> 15) & 0x1f
        rs2 = (instr >> 20) & 0x1f

        if opcode == 0x13:  # OP-IMM
            funct3 = (instr >> 12) & 0x7
            imm = self._sign_extend((instr >> 20) & 0xFFF, 12)
            if funct3 == 0:   self.regs[rd] = self._u32(self.regs[rs1] + imm)  # addi
            elif funct3 == 1: self.regs[rd] = self._u32((self.regs[rs1] & 0xFFFFFFFF) << (rs2 & 0x1F))  # slli
            elif funct3 == 2: self.regs[rd] = 1 if self._s32(self.regs[rs1]) < imm else 0  # slti
            elif funct3 == 3: self.regs[rd] = 1 if (self.regs[rs1] & 0xFFFFFFFF) < (imm & 0xFFFFFFFF) else 0  # sltiu
            elif funct3 == 4: self.regs[rd] = self._u32(self.regs[rs1] ^ imm)  # xori
            elif funct3 == 5:
                shamt = (instr >> 20) & 0x1F
                funct7 = (instr >> 25) & 0x7F
                if funct7 == 0x00:  # srli
                    self.regs[rd] = (self.regs[rs1] & 0xFFFFFFFF) >> shamt
                elif funct7 == 0x20:  # srai
                    self.regs[rd] = self._u32(self._s32(self.regs[rs1]) >> shamt)
            elif funct3 == 6: self.regs[rd] = self._u32(self.regs[rs1] | imm)  # ori
            elif funct3 == 7: self.regs[rd] = self._u32(self.regs[rs1] & imm)  # andi

        elif opcode == 0x33:  # OP
            funct3 = (instr >> 12) & 0x7
            funct7 = (instr >> 25) & 0x7f
            if funct3 == 0 and funct7 == 0:   self.regs[rd] = self._u32(self.regs[rs1] + self.regs[rs2])  # add
            elif funct3 == 0 and funct7 == 0x20: self.regs[rd] = self._u32(self.regs[rs1] - self.regs[rs2])  # sub
            elif funct3 == 1: self.regs[rd] = self._u32((self.regs[rs1] & 0xFFFFFFFF) << (self.regs[rs2] & 0x1f))  # sll
            elif funct3 == 2: self.regs[rd] = 1 if self._s32(self.regs[rs1]) < self._s32(self.regs[rs2]) else 0  # slt
            elif funct3 == 3: self.regs[rd] = 1 if (self.regs[rs1]&0xffffffff) < (self.regs[rs2]&0xffffffff) else 0
            elif funct3 == 4: self.regs[rd] = self._u32(self.regs[rs1] ^ self.regs[rs2])
            elif funct3 == 5 and funct7 == 0: self.regs[rd] = self.regs[rs1] >> (self.regs[rs2] & 0x1f)  # srl
            elif funct3 == 5 and funct7 == 0x20: self.regs[rd] = self._u32(self._s32(self.regs[rs1]) >> (self.regs[rs2] & 0x1f))  # sra
            elif funct3 == 6: self.regs[rd] = self._u32(self.regs[rs1] | self.regs[rs2])
            elif funct3 == 7: self.regs[rd] = self._u32(self.regs[rs1] & self.regs[rs2])

        elif opcode == 0x03:  # LOAD
            funct3 = (instr >> 12) & 0x7
            imm = self._sign_extend((instr >> 20) & 0xFFF, 12)
            addr = (self.regs[rs1] + imm) & 0xFFFFFFFF
            if funct3 == 0:   # lb
                b = self.memory[addr] if addr < len(self.memory) else 0
                self.regs[rd] = self._u32(self._sign_extend(b, 8))
            elif funct3 == 1: # lh
                if addr + 1 < len(self.memory):
                    v = int.from_bytes(self.memory[addr:addr+2], 'little')
                else:
                    v = 0
                self.regs[rd] = self._u32(self._sign_extend(v, 16))
            elif funct3 == 2: # lw
                if addr + 3 < len(self.memory):
                    self.regs[rd] = int.from_bytes(self.memory[addr:addr+4], 'little')
                else:
                    self.regs[rd] = 0
            elif funct3 == 4: # lbu
                self.regs[rd] = self.memory[addr] if addr < len(self.memory) else 0
            elif funct3 == 5: # lhu
                if addr + 1 < len(self.memory):
                    self.regs[rd] = int.from_bytes(self.memory[addr:addr+2], 'little')
                else:
                    self.regs[rd] = 0

        elif opcode == 0x23:  # STORE
            funct3 = (instr >> 12) & 0x7
            imm = ((instr >> 25) << 5) | ((instr >> 7) & 0x1f)
            imm = self._sign_extend(imm, 12)
            addr = (self.regs[rs1] + imm) & 0xFFFFFFFF
            if funct3 == 0 and addr < len(self.memory):  # sb
                self.memory[addr] = self.regs[rs2] & 0xFF
            elif funct3 == 1 and addr + 1 < len(self.memory):  # sh
                self.memory[addr:addr+2] = (self.regs[rs2] & 0xFFFF).to_bytes(2, 'little')
            elif funct3 == 2 and addr + 3 < len(self.memory):  # sw
                self.memory[addr:addr+4] = self._u32(self.regs[rs2]).to_bytes(4, 'little')

        elif opcode == 0x63:  # BRANCH
            funct3 = (instr >> 12) & 0x7
            imm = (((instr >> 31) << 12) | (((instr >> 25) & 0x3f) << 5) |
                   (((instr >> 8) & 0xf) << 1) | (((instr >> 7) & 0x1) << 11))
            imm = self._sign_extend(imm, 13)
            take = False
            if funct3 == 0: take = self.regs[rs1] == self.regs[rs2]   # beq
            elif funct3 == 1: take = self.regs[rs1] != self.regs[rs2] # bne
            elif funct3 == 4: take = self._s32(self.regs[rs1]) < self._s32(self.regs[rs2])   # blt
            elif funct3 == 5: take = self._s32(self.regs[rs1]) >= self._s32(self.regs[rs2])  # bge
            elif funct3 == 6: take = (self.regs[rs1] & 0xFFFFFFFF) < (self.regs[rs2] & 0xFFFFFFFF)   # bltu
            elif funct3 == 7: take = (self.regs[rs1] & 0xFFFFFFFF) >= (self.regs[rs2] & 0xFFFFFFFF)  # bgeu
            if take:
                self.pc += imm - 4

        elif opcode == 0x37:  # LUI
            self.regs[rd] = instr & 0xFFFFF000

        elif opcode == 0x17:  # AUIPC
            self.regs[rd] = self._u32((self.pc - 4) + (instr & 0xFFFFF000))

        elif opcode == 0x6F:  # JAL
            imm = (((instr >> 31) << 20) |
                   (((instr >> 12) & 0xFF) << 12) |
                   (((instr >> 20) & 0x1) << 11) |
                   (((instr >> 21) & 0x3FF) << 1))
            imm = self._sign_extend(imm, 21)
            self.regs[rd] = self.pc
            self.pc = self._u32((self.pc - 4) + imm)

        elif opcode == 0x67:  # JALR
            imm = self._sign_extend((instr >> 20) & 0xFFF, 12)
            t = self.pc
            self.pc = ((self.regs[rs1] + imm) & 0xFFFFFFFE) & 0xFFFFFFFF
            self.regs[rd] = t

        self.regs[0] = 0  # x0 always zero

    def run(self, cycles=1000):
        for _ in range(cycles):
            if self.pc >= len(self.memory) - 4:
                break
            instr = self.fetch()
            self.execute(instr)

    def load_program(self, program_bytes, base=0):
        self.memory[base:base+len(program_bytes)] = program_bytes
        self.pc = base


# Demo
if __name__ == "__main__":
    emu = RISCVEmulator()
    # addi x1, x0, 42; add x2, x1, x1; sw x2, 0(x0)
    code = bytes([
        0x93, 0x00, 0xa0, 0x02,   # addi x1, x0, 42
        0x33, 0x01, 0x10, 0x00,   # add  x2, x1, x1
        0x23, 0x20, 0x20, 0x00    # sw   x2, 0(x0)
    ])
    emu.load_program(code)
    emu.run(3)
    print("x1 =", emu.regs[1])
    print("x2 =", emu.regs[2])
    print("mem[0:4] =", list(emu.memory[0:4]))
