"""Generate a program of interval copies, not a host RV32I interpreter.

No guest instruction is examined during generation. The same layers execute
any bytes placed in guest memory. All runtime decisions are LUT reads whose
addresses are patched by copies of bits in space.
"""
import argparse
import json
from dataclasses import dataclass
from pathlib import Path

SPACE_BYTES = 2097152
SLOTS, N_BITS, ADDRESS_BITS = 256, 23, 24
INSN_BITS = 71
LAYER_BITS = SLOTS * INSN_BITS
REGS = 0x20000
PC, STATUS = REGS + 1024, REGS + 1056
EXIT_CODE = STATUS + 32
FRAME_BITS = 1088
MEMORY = 0x800000
MEMORY_BYTES = 512 * 1024
ZERO = 0x10000
CODE = 0x40000
SCRATCH = 0x21000
(IR, RAW, A, RHS, B, RESULT, NEXT_PC, EA, IMM, TEMP, PAIR, CARRY,
 COND, REDUCE, ULT, SLT, EQUAL, RD_ADDRESS, JUMP, DISCARD, SHIFT0,
 SHIFT1) = (SCRATCH + 32*i for i in range(22))
IO_STATUS = SCRATCH + 22*32


@dataclass(eq=False)
class Copy:
    n: int
    dst: object
    src: object
    layer: int = 0
    slot: int = 0


@dataclass
class Field:
    instruction: Copy
    name: str
    offset: int = 0


class Image:
    def __init__(self, state_output=False, io=False, *, code_base=CODE,
                 constant_base=0x24000, table_base=0x30000, code_limit=MEMORY,
                 memory_bytes=MEMORY_BYTES):
        if state_output and io:
            raise ValueError("--io and --state-output cannot share OUT")
        self.state_output = state_output
        self.io = io
        if memory_bytes not in (65536, 131072, 262144, 524288):
            raise ValueError("guest memory must be 65536, 131072, 262144 or 524288 bytes")
        self.memory_bytes = memory_bytes
        self.memory_bits = (memory_bytes-1).bit_length()
        self.channels = {}
        self.blocks = {}
        self.current = None
        self.data = []
        self.constants = {}
        self.gates = {}
        self.constant_end = constant_base
        self.constant_limit = table_base
        self.table_end = table_base
        self.code_base = code_base
        self.code_limit = code_limit
        self.serial = 0

    def constant(self, value):
        if value not in self.constants:
            self.constants[value] = self.constant_end
            self.data.append((self.constant_end, 32, value))
            self.constant_end += 32
            if self.constant_end > self.constant_limit:
                raise ValueError("constant region exhausted")
        return self.constants[value]

    def table(self, values, stride=5):
        size = len(values) << stride
        if size & (size - 1):
            raise ValueError("table size must be a power of two")
        base = (self.table_end + size - 1) & -size
        self.table_end = base + size
        if self.table_end > self.code_base:
            raise ValueError("table region exhausted")
        for i, value in enumerate(values):
            self.data.append((base + (i << stride), 1 << stride, value))
        return base

    def start(self, name):
        if self.current is not None and self.blocks[self.current][1] is None:
            raise ValueError("previous block has no terminator")
        if name in self.blocks:
            raise ValueError("duplicate block: " + name)
        self.blocks[name] = ([], None)
        self.current = name

    def emit(self, n, dst, src):
        instruction = Copy(n, dst, src)
        self.blocks[self.current][0].append(instruction)
        return instruction

    def jump(self, label=None):
        end = Copy(LAYER_BITS, 0, label or 0)
        if label is None:
            self.emit(24, Field(end, "src"), JUMP)
        ops, old = self.blocks[self.current]
        if old is not None:
            raise ValueError("duplicate terminator")
        self.blocks[self.current] = (ops, end)

    def lookup(self, dst, base, indices, width, stride=0):
        read = Copy(width, dst, base)
        # Merge adjacent input bits; patches otherwise stay independent.
        at = 0
        while at < len(indices):
            count = 1
            while at + count < len(indices) and indices[at+count] == indices[at] + count:
                count += 1
            self.emit(count, Field(read, "src", stride + at), indices[at])
            at += count
        self.blocks[self.current][0].append(read)

    def dispatch(self, indices, mapping, default="illegal"):
        table = self.table([mapping.get(i, default) for i in range(1 << len(indices))])
        self.lookup(JUMP, table, indices, 24, 5)
        self.jump()

    def branch(self, condition, no, yes):
        table = self.table([no, yes])
        self.lookup(JUMP, table, [condition], 24, 5)
        self.jump()

    def guard(self, condition, error):
        self.serial += 1
        continuation = f"guard_{self.serial}"
        self.branch(condition, error, continuation)
        self.start(continuation)

    def gate(self, name, dst, inputs):
        if name not in self.gates:
            functions = {
                "and": lambda a, b: a & b,
                "or": lambda a, b: a | b,
                "xor": lambda a, b: a ^ b,
                "not": lambda a: a ^ 1,
                "mux": lambda a, b, select: b if select else a,
                "signed_lt": lambda sign_a, sign_b, unsigned: sign_a if sign_a != sign_b else unsigned,
            }
            fn = functions[name]
            count = len(inputs)
            self.gates[name] = self.table([
                fn(*[(i >> j) & 1 for j in range(count)]) for i in range(1 << count)
            ], 0)
        self.lookup(dst, self.gates[name], inputs, 1)

    def reduce_or(self, dst, inputs):
        self.emit(1, dst, self.constant(0))
        for bit in inputs:
            self.gate("or", dst, [dst, bit])

    def require_zero(self, inputs, error):
        self.reduce_or(REDUCE, inputs)
        self.gate("not", COND, [REDUCE])
        self.guard(COND, error)

    def validate(self, mask, expected):
        self.emit(1, COND, self.constant(1))
        for i in range(32):
            if mask & (1 << i):
                source = IR + i
                if not (expected & (1 << i)):
                    self.gate("not", REDUCE, [source])
                    source = REDUCE
                self.gate("and", COND, [COND, source])
        self.guard(COND, "illegal")

    def require_value(self, source, expected, error):
        self.emit(1, COND, self.constant(1))
        for i in range(32):
            bit = source+i
            if not ((expected >> i) & 1):
                self.gate("not", REDUCE, [bit])
                bit = REDUCE
            self.gate("and", COND, [COND, bit])
        self.guard(COND, error)

    def add(self, dst, a, b, subtract=False):
        if "adder" not in self.gates:
            # Eight entries, two bits per entry: sum followed by carry.
            self.gates["adder"] = self.table([
                ((i & 1) + ((i >> 1) & 1) + ((i >> 2) & 1)) for i in range(8)
            ], 1)
        self.emit(1, CARRY, self.constant(int(subtract)))
        for i in range(32):
            second = b + i
            if subtract:
                self.gate("not", TEMP + i, [second])
                second = TEMP + i
            self.lookup(PAIR, self.gates["adder"], [a+i, second, CARRY], 2, 1)
            self.emit(1, dst+i, PAIR)
            self.emit(1, CARRY, PAIR+1)

    def compare(self):
        self.add(EA, A, B, subtract=True)
        self.gate("not", ULT, [CARRY])
        self.gate("signed_lt", SLT, [A+31, B+31, ULT])
        self.reduce_or(REDUCE, list(range(EA, EA+32)))
        self.gate("not", EQUAL, [REDUCE])

    def immediate(self, form):
        if form == "I":
            sources = list(range(20, 32)) + [31]*20
        elif form == "S":
            sources = list(range(7, 12)) + list(range(25, 32)) + [31]*20
        elif form == "B":
            sources = [None] + list(range(8, 12)) + list(range(25, 31)) + [7] + [31]*20
        elif form == "J":
            sources = [None] + list(range(21, 31)) + [20] + list(range(12, 20)) + [31]*12
        elif form == "U":
            sources = [None]*12 + list(range(12, 32))
        else:
            raise ValueError(form)
        assert len(sources) == 32
        for i, source in enumerate(sources):
            self.emit(1, B+i, self.constant(0) if source is None else IR+source)

    def memory_address(self, instruction, field):
        # The guest region is aligned to its size; patch only its offset bits.
        self.emit(self.memory_bits, Field(instruction, field, 3), EA)

    def memory_guard(self, width, store=False):
        self.require_zero(list(range(EA+self.memory_bits, EA+32)), "store_access" if store else "load_access")
        alignment = (width // 8).bit_length() - 1
        if alignment:
            self.require_zero(list(range(EA, EA+alignment)), "store_align" if store else "load_align")

    def build(self):
        self.start("fetch")
        self.require_zero([PC, PC+1], "instruction_align")
        self.require_zero(list(range(PC+self.memory_bits, PC+32)), "instruction_access")
        fetch = Copy(32, RAW, MEMORY)
        self.fetch_instruction = fetch
        self.emit(self.memory_bits, Field(fetch, "src", 3), PC)
        self.blocks[self.current][0].append(fetch)
        for i in range(32):
            self.emit(1, IR+i, RAW + (i//8)*8 + 7-i%8)
        self.add(NEXT_PC, PC, self.constant(4))
        for dest, index in [(A, 15), (RHS, 20)]:
            read = Copy(32, dest, REGS)
            self.emit(5, Field(read, "src", 5), IR+index)
            self.blocks[self.current][0].append(read)
        self.emit(32, B, RHS)
        rd_table = self.table([DISCARD] + [REGS+32*i for i in range(1, 32)])
        self.lookup(RD_ADDRESS, rd_table, list(range(IR+7, IR+12)), 24, 5)
        self.dispatch(list(range(IR, IR+7)), {
            0x13: "immediate", 0x33: "register", 0x37: "lui", 0x17: "auipc",
            0x6f: "jal", 0x67: "jalr", 0x63: "branch", 0x03: "load",
            0x23: "store", 0x0f: "fence", 0x73: "system",
        })

        self.start("immediate")
        self.immediate("I")
        self.dispatch(list(range(IR+12, IR+15)), {
            0: "add", 1: "slli_check", 2: "slt", 3: "sltu",
            4: "xor", 5: "right_immediate", 6: "or", 7: "and",
        })
        self.start("slli_check")
        self.validate(0xfe000000, 0)
        self.jump("sll")
        self.start("right_immediate")
        self.dispatch(list(range(IR+25, IR+32)), {0: "srl", 32: "sra"})
        self.start("register")
        self.dispatch(list(range(IR+25, IR+32)), {0: "register_base", 32: "register_alt"})
        self.start("register_base")
        self.dispatch(list(range(IR+12, IR+15)), {
            0: "add", 1: "sll", 2: "slt", 3: "sltu", 4: "xor", 5: "srl", 6: "or", 7: "and",
        })
        self.start("register_alt")
        self.dispatch(list(range(IR+12, IR+15)), {0: "sub", 5: "sra"})
        for name in ["add", "sub"]:
            self.start(name)
            self.add(RESULT, A, B, subtract=name == "sub")
            self.jump("writeback")
        for name, condition in [("slt", SLT), ("sltu", ULT)]:
            self.start(name)
            self.compare()
            self.emit(32, RESULT, self.constant(0))
            self.emit(1, RESULT, condition)
            self.jump("writeback")
        for name in ["xor", "or", "and"]:
            self.start(name)
            for i in range(32):
                self.gate(name, RESULT+i, [A+i, B+i])
            self.jump("writeback")
        for name in ["sll", "srl", "sra"]:
            self.start(name)
            self.emit(32, SHIFT0, A)
            source, dest = SHIFT0, SHIFT1
            for stage in range(5):
                distance = 1 << stage
                for i in range(32):
                    shifted = i-distance if name == "sll" else i+distance
                    bit = source+shifted if 0 <= shifted < 32 else (A+31 if name == "sra" else self.constant(0))
                    self.gate("mux", dest+i, [source+i, bit, B+stage])
                source, dest = dest, source
            self.emit(32, RESULT, source)
            self.jump("writeback")

        for name in ["lui", "auipc"]:
            self.start(name)
            self.immediate("U")
            if name == "lui":
                self.emit(32, RESULT, B)
            else:
                self.add(RESULT, PC, B)
            self.jump("writeback")
        for name in ["jal", "jalr"]:
            self.start(name)
            if name == "jalr":
                self.validate(0x7000, 0)
            self.immediate("J" if name == "jal" else "I")
            self.add(EA, PC if name == "jal" else A, B)
            if name == "jalr":
                self.emit(1, EA, self.constant(0))
            self.require_zero([EA, EA+1], "instruction_align")
            self.emit(32, RESULT, NEXT_PC)
            self.emit(32, NEXT_PC, EA)
            self.jump("writeback")

        self.start("branch")
        self.compare()
        self.immediate("B")
        self.dispatch(list(range(IR+12, IR+15)), {
            0: "beq", 1: "bne", 4: "blt", 5: "bge", 6: "bltu", 7: "bgeu",
        })
        for name, condition, inverted in [("beq", EQUAL, False), ("bne", EQUAL, True),
                                         ("blt", SLT, False), ("bge", SLT, True),
                                         ("bltu", ULT, False), ("bgeu", ULT, True)]:
            self.start(name)
            self.branch(condition, "branch_taken" if inverted else "commit",
                        "commit" if inverted else "branch_taken")
        self.start("branch_taken")
        self.add(EA, PC, B)
        self.require_zero([EA, EA+1], "instruction_align")
        self.emit(32, NEXT_PC, EA)
        self.jump("commit")

        for name, form, handlers in [
            ("load", "I", {0: "lb", 1: "lh", 2: "lw", 4: "lbu", 5: "lhu"}),
            ("store", "S", {0: "sb", 1: "sh", 2: "sw"}),
        ]:
            self.start(name)
            self.immediate(form)
            self.add(EA, A, B)
            self.dispatch(list(range(IR+12, IR+15)), handlers)
        for name, width, signed in [("lb", 8, True), ("lh", 16, True), ("lw", 32, False),
                                    ("lbu", 8, False), ("lhu", 16, False)]:
            self.start(name)
            self.memory_guard(width)
            read = Copy(width, RAW, MEMORY)
            self.memory_address(read, "src")
            self.blocks[self.current][0].append(read)
            self.emit(32, RESULT, self.constant(0))
            for i in range(width):
                self.emit(1, RESULT+i, RAW + (i//8)*8 + 7-i%8)
            if signed:
                for i in range(width, 32):
                    self.emit(1, RESULT+i, RESULT+width-1)
            self.jump("writeback")
        for name, width in [("sb", 8), ("sh", 16), ("sw", 32)]:
            self.start(name)
            self.memory_guard(width, store=True)
            for i in range(width):
                self.emit(1, RAW + (i//8)*8 + 7-i%8, RHS+i)
            write = Copy(width, MEMORY, RAW)
            self.memory_address(write, "dst")
            self.blocks[self.current][0].append(write)
            self.jump("commit")

        self.start("fence")
        self.validate(0x7000, 0)
        self.jump("commit")
        self.start("system")
        self.validate(0xffefffff, 0x73)
        self.branch(IR+20, "io_dispatch" if self.io else "ecall", "ebreak")
        self.start("writeback")
        write = Copy(32, 0, RESULT)
        self.emit(24, Field(write, "dst"), RD_ADDRESS)
        self.blocks[self.current][0].append(write)
        self.jump("commit")
        self.start("commit")
        self.emit(32, PC, NEXT_PC)
        self.jump("checkpoint")
        self.start("checkpoint")
        self.jump("fetch")
        for code, name in enumerate(["ecall", "ebreak", "illegal", "instruction_access",
                                     "instruction_align", "load_access", "load_align",
                                     "store_access", "store_align"], 1):
            self.start(name)
            self.emit(32, STATUS, self.constant(code))
            self.jump("halt")
        self.start("halt")
        # No link: this copy clears all PROCESSOR slots after the final OUT.
        self.blocks[self.current] = ([], Copy(LAYER_BITS, 0, ZERO))
        if self.io:
            self.build_io()
        return self

    def build_io(self):
        a0, a1, a2, a7 = (REGS+32*i for i in (10, 11, 12, 17))
        self.start("io_dispatch")
        self.require_zero(list(range(a7+7, a7+32)), "io_enosys")
        self.dispatch(list(range(a7, a7+7)), {63: "io_read", 64: "io_write", 93: "io_exit"},
                      default="io_enosys")
        for name, descriptor, slot in [("read", 0, 1), ("write", 1, 2)]:
            self.start("io_"+name)
            self.require_value(a0, descriptor, "io_ebadf")
            self.reduce_or(COND, list(range(a2, a2+32)))
            self.branch(COND, "io_zero", "io_"+name+"_range")
            self.start("io_"+name+"_range")
            self.require_zero(list(range(a1+self.memory_bits, a1+32)), "io_efault")
            self.add(EA, a1, a2)
            self.gate("not", COND, [CARRY])
            self.guard(COND, "io_efault")
            self.add(IMM, EA, self.constant(self.memory_bytes+1), subtract=True)
            self.gate("not", COND, [CARRY])
            self.guard(COND, "io_efault")
            channel = Copy(0, MEMORY, 0)
            # Prepare the future channel layer; the next tick services it once.
            self.emit(self.memory_bits+1, Field(channel, "n", 3), a2)
            self.emit(self.memory_bits, Field(channel, "dst", 3), a1)
            transfer = "io_"+name+"_transfer"
            self.jump(transfer)
            self.start(transfer)
            self.channels[transfer] = (slot, channel)
            self.emit(24, IO_STATUS, Field(channel, "src"))
            self.emit(32, RESULT, self.constant(0))
            # Packed status = bytes_copied << 4 | error. No byte conversion.
            self.emit(self.memory_bits+1, RESULT, IO_STATUS+4)
            self.reduce_or(REDUCE, list(range(RESULT, RESULT+self.memory_bits+1)))
            self.gate("not", COND, [REDUCE])
            self.gate("and", COND, [COND, IO_STATUS])
            self.branch(COND, "io_return", "io_eio")
        self.start("io_zero")
        self.emit(32, RESULT, self.constant(0))
        self.jump("io_return")
        for name, value in [("enosys", -38), ("ebadf", -9), ("efault", -14), ("eio", -5)]:
            self.start("io_"+name)
            self.emit(32, RESULT, self.constant(value & 0xffffffff))
            self.jump("io_return")
        self.start("io_return")
        self.emit(32, a0, RESULT)
        self.jump("commit")
        self.start("io_exit")
        self.emit(32, EXIT_CODE, a0)
        self.emit(32, STATUS, self.constant(10))
        self.jump("halt")

    def encode(self, program=b"", entry=0, registers=None, *, initial_label="fetch",
               image_bytes=None):
        if len(program) > self.memory_bytes:
            raise ValueError("program exceeds guest memory")
        if not 0 <= entry < (1 << 32):
            raise ValueError("entry must be a 32-bit address")
        if registers is None:
            registers = {2: self.memory_bytes-16}
        if any(not 0 <= i < 32 or not 0 <= value < (1 << 32) for i, value in registers.items()):
            raise ValueError("invalid initial register")
        labels, layers = {}, []
        end = self.code_base
        for name, (ops, terminator) in self.blocks.items():
            labels[name] = end
            chunks = [ops[i:i+252] for i in range(0, len(ops), 252)] or [[]]
            for j, chunk in enumerate(chunks):
                link = terminator if j == len(chunks)-1 else Copy(LAYER_BITS, 0, end+LAYER_BITS)
                for slot, op in enumerate(chunk, 3):
                    op.layer, op.slot = end, slot
                link.layer, link.slot = end, 255
                if j == 0 and name in self.channels:
                    slot, channel = self.channels[name]
                    channel.layer, channel.slot = end, slot
                layers.append((end, name if j == 0 else name+f"/{j}", chunk, link))
                end += LAYER_BITS
        if end > self.code_limit:
            raise ValueError("copy layers overlap guest memory")
        image = bytearray(image_bytes if image_bytes is not None else MEMORY//8+self.memory_bytes)

        def bits(address, width, value):
            if isinstance(value, str):
                value = labels[value]
            if not 0 <= value < (1 << width):
                raise ValueError(f"field overflow: {value}, {width}")
            for i in range(width):
                mask = 1 << (7-(address+i) % 8)
                byte = (address+i) // 8
                if (value >> i) & 1:
                    image[byte] |= mask
                else:
                    image[byte] &= ~mask

        def resolve(value, context):
            if isinstance(value, Field):
                target = value.instruction
                base = 0 if target.layer == context.layer else target.layer
                offset = {"n": 0, "dst": N_BITS, "src": N_BITS+ADDRESS_BITS}[value.name]
                return base + target.slot*INSN_BITS + offset + value.offset
            return labels[value] if isinstance(value, str) else value

        for address, width, value in self.data:
            bits(address, width, value)
        for address, name, ops, link in layers:
            if name in ("checkpoint", "halt") and self.state_output:
                bits(address+2*INSN_BITS, N_BITS, FRAME_BITS)
                bits(address+2*INSN_BITS+N_BITS, ADDRESS_BITS, REGS)
            channels = [self.channels[name][1]] if name in self.channels else []
            for instruction in ops + [link] + channels:
                at = address + instruction.slot*INSN_BITS
                for width, value in [(N_BITS, instruction.n), (ADDRESS_BITS, instruction.dst),
                                     (ADDRESS_BITS, instruction.src)]:
                    bits(at, width, resolve(value, instruction))
                    at += width
        for i, value in registers.items():
            if i:
                bits(REGS+i*32, 32, value)
        bits(PC, 32, entry)
        image[MEMORY//8:MEMORY//8+len(program)] = program
        first = labels[initial_label] // 8
        image[:LAYER_BITS//8] = image[first:first+LAYER_BITS//8]
        manifest = {
            "space_bytes": SPACE_BYTES, "processor_n": SLOTS, "layer_bits": LAYER_BITS,
            "registers_bit": REGS, "pc_bit": PC, "status_bit": STATUS,
            "io": self.io, "exit_code_bit": EXIT_CODE,
            "guest_memory_bit": MEMORY, "guest_memory_bytes": self.memory_bytes,
            "initial_stack": registers.get(2, 0),
            "state_output": self.state_output, "frame_bits": FRAME_BITS,
            "layer_count": len(layers), "code_end_bit": end, "entry": entry,
            "gate_tables": self.gates,
            "fetch_layer_bit": self.fetch_instruction.layer if hasattr(self, "fetch_instruction") else None,
            "labels": labels, "layers": {name: address for address, name, _, _ in layers},
        }
        return bytes(image), manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", type=Path, required=True, help="raw little-endian RV32I binary")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--entry", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--stack", type=lambda value: int(value, 0))
    parser.add_argument("--memory-bytes", type=lambda value: int(value, 0), default=MEMORY_BYTES)
    parser.add_argument("--state-output", action="store_true")
    parser.add_argument("--io", action="store_true", help="enable read/write/exit ECALL profile")
    args = parser.parse_args()
    try:
        image, manifest = Image(args.state_output, args.io, memory_bytes=args.memory_bytes).build().encode(
            args.program.read_bytes(), args.entry,
            None if args.stack is None else {2: args.stack})
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.output.write_bytes(image)
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest, indent=2)+"\n")


if __name__ == "__main__":
    main()
