"""Independent, byte-addressed test oracle. Never linked to the space runner."""
MASK = 0xffffffff


def signed(value, width=32):
    return (value & ((1 << (width-1))-1)) - (value & (1 << (width-1)))


class Fault(Exception):
    def __init__(self, status):
        self.status = status


def execute(program, registers=None, entry=0, initial_memory=None, max_steps=2000, coverage=None, io=None,
            memory_bytes=65536, memory_bit=8388608):
    memory = bytearray(memory_bytes)
    if initial_memory:
        for address, data in initial_memory.items():
            memory[address:address+len(data)] = data
    memory[:len(program)] = program
    regs = [0]*32
    for register, value in (registers if registers is not None else {2: memory_bytes-16}).items():
        if register:
            regs[register] = value & MASK
    pc, frames, fetches = entry, [], []
    input_position = 0
    if io is not None:
        io["output"], io["calls"], io["channels"] = b"", [], []

    def check_address(address, width, store=False):
        if not 0 <= address < memory_bytes:
            raise Fault(8 if store else 6)
        if address % width:
            raise Fault(9 if store else 7)
        if address+width > memory_bytes:
            raise Fault(8 if store else 6)

    for _ in range(max_steps):
        status = 0
        name = None
        try:
            if pc % 4:
                raise Fault(5)
            if not 0 <= pc <= memory_bytes-4:
                raise Fault(4)
            fetches.append(pc)
            word = int.from_bytes(memory[pc:pc+4], "little")
            op, rd, f3 = word & 127, (word >> 7) & 31, (word >> 12) & 7
            rs1, rs2, f7 = (word >> 15) & 31, (word >> 20) & 31, word >> 25
            a, b = regs[rs1], regs[rs2]
            imm = signed(word >> 20, 12)
            next_pc, result = (pc+4) & MASK, None
            if op in (0x13, 0x33):
                immediate = op == 0x13
                rhs = imm & MASK if immediate else b
                shift = rhs & 31
                if f3 == 0:
                    if immediate or f7 == 0:
                        result = a + rhs
                    elif f7 == 32:
                        result = a - rhs
                    else:
                        raise Fault(3)
                elif f3 == 1:
                    if f7 != 0:
                        raise Fault(3)
                    result = a << shift
                elif f3 == 5:
                    if f7 == 0:
                        result = a >> shift
                    elif f7 == 32:
                        result = signed(a) >> shift
                    else:
                        raise Fault(3)
                else:
                    if not immediate and f7 != 0:
                        raise Fault(3)
                    if f3 == 2:
                        result = int(signed(a) < signed(rhs))
                    elif f3 == 3:
                        result = int(a < rhs)
                    elif f3 == 4:
                        result = a ^ rhs
                    elif f3 == 6:
                        result = a | rhs
                    elif f3 == 7:
                        result = a & rhs
                    else:
                        raise Fault(3)
                name = ["ADD", "SLL", "SLT", "SLTU", "XOR", "SRL", "OR", "AND"][f3]
                if f3 == 0 and not immediate and f7 == 32:
                    name = "SUB"
                if f3 == 5 and f7 == 32:
                    name = "SRA"
                if immediate:
                    name = "SLTIU" if name == "SLTU" else name+"I"
            elif op in (0x37, 0x17):
                name = "LUI" if op == 0x37 else "AUIPC"
                result = (word & 0xfffff000) + (pc if op == 0x17 else 0)
            elif op in (0x6f, 0x67):
                name = "JAL" if op == 0x6f else "JALR"
                if op == 0x6f:
                    offset = (((word >> 31) & 1) << 20) | (((word >> 12) & 255) << 12)
                    offset |= (((word >> 20) & 1) << 11) | (((word >> 21) & 1023) << 1)
                    target = (pc + signed(offset, 21)) & MASK
                else:
                    if f3 != 0:
                        raise Fault(3)
                    target = ((a + imm) & MASK) & ~1
                if target % 4:
                    raise Fault(5)
                result, next_pc = next_pc, target
            elif op == 0x63:
                conditions = {0: a == b, 1: a != b, 4: signed(a) < signed(b),
                              5: signed(a) >= signed(b), 6: a < b, 7: a >= b}
                if f3 not in conditions:
                    raise Fault(3)
                name = {0: "BEQ", 1: "BNE", 4: "BLT", 5: "BGE", 6: "BLTU", 7: "BGEU"}[f3]
                if conditions[f3]:
                    offset = (((word >> 31) & 1) << 12) | (((word >> 7) & 1) << 11)
                    offset |= (((word >> 25) & 63) << 5) | (((word >> 8) & 15) << 1)
                    next_pc = (pc + signed(offset, 13)) & MASK
                    if next_pc % 4:
                        raise Fault(5)
            elif op == 0x03:
                if f3 not in (0, 1, 2, 4, 5):
                    raise Fault(3)
                name = {0: "LB", 1: "LH", 2: "LW", 4: "LBU", 5: "LHU"}[f3]
                width = {0: 1, 1: 2, 2: 4, 4: 1, 5: 2}[f3]
                address = (a + imm) & MASK
                check_address(address, width)
                result = int.from_bytes(memory[address:address+width], "little")
                if f3 in (0, 1):
                    result = signed(result, width*8)
            elif op == 0x23:
                if f3 not in (0, 1, 2):
                    raise Fault(3)
                name = ["SB", "SH", "SW"][f3]
                width = 1 << f3
                offset = ((word >> 25) << 5) | ((word >> 7) & 31)
                address = (a + signed(offset, 12)) & MASK
                check_address(address, width, True)
                memory[address:address+width] = (b & ((1 << (width*8))-1)).to_bytes(width, "little")
            elif op == 0x0f:
                if f3 != 0:
                    raise Fault(3)
                name = "FENCE"
            elif op == 0x73:
                if word == 0x73:
                    name = "ECALL"
                    if io is None:
                        raise Fault(1)
                    operation, descriptor, pointer, count = regs[17], regs[10], regs[11], regs[12]
                    if operation == 93:
                        io["exit_code"] = descriptor
                        raise Fault(10)
                    if operation not in (63, 64):
                        returned = -38
                    elif descriptor != (0 if operation == 63 else 1):
                        returned = -9
                    elif count == 0:
                        returned = 0
                    elif pointer >= memory_bytes or pointer+count > memory_bytes:
                        returned = -14
                    else:
                        error = io.get("read_error" if operation == 63 else "write_error", False)
                        if error:
                            copied, returned = 0, -5
                        elif operation == 63:
                            data = io.get("input", b"")[input_position:input_position+count]
                            copied = returned = len(data)
                            memory[pointer:pointer+copied] = data
                            input_position += copied
                        else:
                            copied = returned = count
                            io["output"] += memory[pointer:pointer+count]
                        io["channels"].append([1 if operation == 63 else 2, count*8,
                                               memory_bit+pointer*8, copied*8, int(error)])
                    io["calls"].append([operation, descriptor, pointer, count, returned])
                    regs[10] = returned & MASK
                elif word == 0x100073:
                    name = "EBREAK"
                    raise Fault(2)
                else:
                    raise Fault(3)
            else:
                raise Fault(3)
            if result is not None and rd:
                regs[rd] = result & MASK
            pc = next_pc
        except Fault as error:
            status = error.status
        if coverage is not None and name is not None and status != 3:
            coverage.add(name)
        frames.append(regs[:] + [pc, status])
        if status:
            return frames, bytes(memory), fetches
    raise AssertionError("reference program did not terminate")
