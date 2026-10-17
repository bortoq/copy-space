"""Bulk-synchronous RV32I generator (roadmap 8.10, variant A).

Same universal interpreter as rv32i.py (no guest instruction is examined),
but the emitted copy schedule is rewritten for the bulk-synchronous tick:
all instructions of a tick are fetched at the start, all copies commit
together, a field patched in a tick is visible only from the next tick.

The generator therefore splits every block into layers ("ticks"):

* a node (a copy) is placed at a dependency level: a read of a position
  written by another node follows it; a field patch follows its index bits;
* a patched instruction executes at least two layers after its patch, so
  the patch writes the target's home before the link of the previous layer
  reads that home (rule P1: patch at L writes H_M, the link at M-1 reads
  H_M, so M >= L+2);
* within a layer all writes are pairwise disjoint (read-after-write and
  write-after-write order are both preserved);
* the block terminator is the link of its last layer.

Arithmetic and reductions are rewritten to logarithmic depth: a
Kogge-Stone prefix adder and binary reduction trees, so a layer holds
many independent gate reads.
"""
import argparse
import json
from pathlib import Path

from rv32i import (Image, Copy, Field, Layout, SLOTS, SPACE_BYTES,
                   MEMORY_BYTES, REGS, PC, STATUS, EXIT_CODE, FRAME_BITS,
                   SCRATCH, TEMP, COND, REDUCE, IR, A, B, RHS, RESULT,
                   NEXT_PC, EA, IMM, JUMP, RD_ADDRESS, CARRY)

# scratch for the log-depth primitives, above the named rv32i scratch and
# below the constant region (SCRATCH .. SCRATCH+12288 bits)
PB_G0 = SCRATCH + 64*32
PB_P0 = SCRATCH + 65*32
PB_AG = SCRATCH + 66*32
PB_AP = SCRATCH + 67*32
PB_BG = SCRATCH + 68*32
PB_BP = SCRATCH + 69*32
PB_T = SCRATCH + 70*32
PB_CIN = SCRATCH + 71*32
TREE = SCRATCH + 72*32
VAL = SCRATCH + 80*32
# io adapter scratch: the SYS answer record and the status byte
IO_RSP = SCRATCH + 96*32
IO_ST = SCRATCH + 100*32


class BulkImage(Image):
    """Image that emits a bulk-synchronous (new emulator) schedule."""

    # ------------------------------------------------------------------
    # log-depth primitives
    # ------------------------------------------------------------------
    def add(self, dst, a, b, subtract=False):
        """Kogge-Stone prefix adder: dst[0..31] = a +/- b, CARRY = carry out."""
        for i in range(32):
            x = b + i
            if subtract:
                self.gate("not", TEMP + i, [b + i])
                x = TEMP + i
            self.gate("and", PB_G0 + i, [a + i, x])
            self.gate("xor", PB_P0 + i, [a + i, x])
        source_g, source_p = PB_G0, PB_P0
        buffers = [(PB_AG, PB_AP), (PB_BG, PB_BP)]
        selected = 0
        for shift in (1, 2, 4, 8, 16):
            dest_g, dest_p = buffers[selected]
            for i in range(32):
                if i < shift:
                    self.emit(1, dest_g + i, source_g + i)
                    self.emit(1, dest_p + i, source_p + i)
                else:
                    self.gate("and", PB_T + i, [source_p + i, source_g + i - shift])
                    self.gate("or", dest_g + i, [source_g + i, PB_T + i])
                    self.gate("and", dest_p + i, [source_p + i, source_p + i - shift])
            source_g, source_p = dest_g, dest_p
            selected ^= 1
        zero = self.constant(0)
        for i in range(32):
            if i == 0:
                carry = self.constant(1) if subtract else zero
                self.gate("xor", dst + 0, [PB_P0 + 0, carry])
            elif subtract:
                self.gate("or", PB_CIN + i, [source_g + i - 1, source_p + i - 1])
                self.gate("xor", dst + i, [PB_P0 + i, PB_CIN + i])
            else:
                self.gate("xor", dst + i, [PB_P0 + i, source_g + i - 1])
        if subtract:
            self.gate("or", CARRY, [source_g + 31, source_p + 31])
        else:
            self.emit(1, CARRY, source_g + 31)

    def _tree(self, name, dst, inputs):
        current = list(inputs)
        if not current:
            self.emit(1, dst, self.constant(0))
            return
        level = 0
        while len(current) > 1:
            following = []
            for j in range(0, len(current) - 1, 2):
                node = TREE + level * 32 + j // 2
                self.gate(name, node, [current[j], current[j + 1]])
                following.append(node)
            if len(current) % 2:
                following.append(current[-1])
            current = following
            level += 1
        if current[0] != dst:
            self.emit(1, dst, current[0])

    def reduce_or(self, dst, inputs):
        self._tree("or", dst, inputs)

    def _check(self, bits, error):
        self._tree("and", COND, bits)
        self.guard(COND, error)

    def validate(self, mask, expected):
        bits = []
        for i in range(32):
            if mask & (1 << i):
                source = IR + i
                if not (expected & (1 << i)):
                    self.gate("not", VAL + i, [source])
                    source = VAL + i
                bits.append(source)
        self._check(bits, "illegal")

    def require_value(self, source, expected, error):
        bits = []
        for i in range(32):
            bit = source + i
            if not ((expected >> i) & 1):
                self.gate("not", VAL + i, [bit])
                bit = VAL + i
            bits.append(bit)
        self._check(bits, error)

    # ------------------------------------------------------------------
    # scheduling
    # ------------------------------------------------------------------
    @staticmethod
    def _span(value, n):
        if isinstance(value, int):
            return range(value, value + n)
        return ()

    def _level(self, ops, term):
        """Assign _level to every node; return the terminator layer index."""
        avail_read, avail_write, levels, patch = {}, {}, {}, {}
        for node in ops:
            level = 0
            for position in self._span(node.src, node.n):
                level = max(level, avail_read.get(position, 0))
            level += 1
            if isinstance(node.dst, int):
                for position in self._span(node.dst, node.n):
                    level = max(level, avail_write.get(position, 0) + 1)
            if id(node) in patch:
                level = max(level, patch[id(node)] + 2)
            levels[id(node)] = level
            if isinstance(node.dst, int):
                for position in self._span(node.dst, node.n):
                    avail_read[position] = level
                    avail_write[position] = level
            if isinstance(node.dst, Field):
                target = id(node.dst.instruction)
                patch[target] = max(patch.get(target, 0), level)
        top = max(levels.values()) if levels else 0
        last = top + 1 if term is not None else top
        if term is not None and id(term) in patch:
            last = max(last, patch[id(term)] + 2)
        for node in ops:
            node._level = levels[id(node)]
        if term is not None:
            term._level = last
        return last

    def _resolve_field(self, value, context):
        if isinstance(value, Field):
            target = value.instruction
            offset = {"n": 0, "dst": self.layout.n_bits,
                      "src": self.layout.n_bits + self.layout.address_bits}[value.name]
            return target.home + target.slot * self.layout.instruction_bits + offset + value.offset
        return value

    # ------------------------------------------------------------------
    # io adapter (roadmap 8.1): old IN/OUT through the new data channels
    # ------------------------------------------------------------------
    @property
    def sys_nbits(self):
        """The emulator is launched with -s space_bytes*8-4, so its address
        width is bit_length(space_bytes*8-4) = the generator address_bits and
        the SYS/devices positions fit below 2**address_bits."""
        return self.layout.space_bytes*8 - 4

    @staticmethod
    def _offsets(widths):
        off, at = [], 0
        for width in widths:
            off.append(at)
            at += width
        return off

    @staticmethod
    def _record(widths, values):
        """Pack record fields low bit first into bytes the `literal` reads."""
        total, at, value = sum(widths), 0, 0
        for width, field in zip(widths, values):
            value |= (field & ((1 << width) - 1)) << at
            at += width
        raw = bytearray((total + 7)//8)
        for i in range(total):
            if (value >> i) & 1:
                raw[i//8] |= 1 << (7 - i % 8)
        return bytes(raw)

    def build_io(self):
        address_bits, n_bits = self.layout.address_bits, self.layout.n_bits
        sys_nbits = self.sys_nbits
        # SYS record fields (proto.def): req op/chan/flags/arg/off,
        # rsp op/status/flags/size/moved/eof; SYS controls any channel.
        req_w = [8, address_bits, 16, 32, 64]
        rsp_w = [8, 8, 16, 64, n_bits, 1]
        req_bits, rsp_bits = sum(req_w), sum(rsp_w)
        rsp_off = self._offsets(rsp_w)          # [op, status, flags, size, moved, eof]
        a0, a1, a2, a7 = (REGS + 32*i for i in (10, 11, 12, 17))

        for name, descriptor, device, reading in [
                ("read", 0, sys_nbits + 1, True), ("write", 1, sys_nbits + 2, False)]:
            self.start("io_" + name)
            self.require_value(a0, descriptor, "io_ebadf")
            self.reduce_or(COND, list(range(a2, a2 + 32)))
            self.branch(COND, "io_zero", "io_" + name + "_range")
            self.start("io_" + name + "_range")
            self.require_zero(list(range(a1 + self.memory_bits, a1 + 32)), "io_efault")
            self.add(EA, a1, a2)
            self.gate("not", COND, [CARRY])
            self.guard(COND, "io_efault")
            self.add(IMM, EA, self.constant(self.memory_bytes + 1), subtract=True)
            self.gate("not", COND, [CARRY])
            self.guard(COND, "io_efault")
            # prepare a data copy; it is placed in its own block so the host
            # services it in its own tick, after the field patches commit
            if reading:
                channel, field = Copy(0, self.layout.memory_bit, device), "dst"
            else:
                channel, field = Copy(0, device, self.layout.memory_bit), "src"
            self.emit(self.memory_bits + 1, Field(channel, "n", 3), a2)
            self.emit(self.memory_bits, Field(channel, field, 3), a1)
            self.jump("io_" + name + "_transfer")
            self.start("io_" + name + "_transfer")
            self.blocks[self.current][0].append(channel)
            self.jump("io_" + name + "_status")
            # a later block asks SYS to fstat the channel and reads the answer
            self.start("io_" + name + "_status")
            self.blocks[self.current][0].append(Copy(
                req_bits, sys_nbits,
                self.literal(self._record(req_w, [3, device, 0, 0, 0]))))
            self.blocks[self.current][0].append(Copy(rsp_bits, IO_RSP, sys_nbits))
            self.emit(8, IO_ST, IO_RSP + rsp_off[1])
            self.reduce_or(REDUCE, list(range(IO_ST, IO_ST + 8)))
            self.gate("not", COND, [REDUCE])            # status == 0
            if reading:
                self.emit(32, RESULT, self.constant(0))
                self.emit(n_bits, RESULT, IO_RSP + rsp_off[4])
            else:
                self.emit(32, RESULT, a2)
            self.branch(COND, "io_eio", "io_return")

        a0, a1, a2, a7 = (REGS + 32*i for i in (10, 11, 12, 17))
        self.start("io_dispatch")
        self.require_zero(list(range(a7 + 7, a7 + 32)), "io_enosys")
        self.dispatch(list(range(a7, a7 + 7)),
                      {63: "io_read", 64: "io_write", 93: "io_exit"}, default="io_enosys")
        self.start("io_zero")
        self.emit(32, RESULT, self.constant(0))
        self.jump("io_return")
        for name, value in [("enosys", -38), ("ebadf", -9), ("efault", -14), ("eio", -5)]:
            self.start("io_" + name)
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
        if self.state_output or self.report_status:
            raise NotImplementedError("the bulk generator supports the base and io profiles")
        if len(program) > self.memory_bytes:
            raise ValueError("program exceeds guest memory")
        if not 0 <= entry < (1 << 32):
            raise ValueError("entry must be a 32-bit address")
        if registers is None:
            registers = {2: self.memory_bytes-16}
        if any(not 0 <= i < 32 or not 0 <= value < (1 << 32) for i, value in registers.items()):
            raise ValueError("invalid initial register")

        instruction_bits = self.layout.instruction_bits
        layer_bits = self.layout.layer_bits
        link_slot = SLOTS - 1
        labels, scheduled = {}, []
        end, tick = self.code_base, 0
        for name, (ops, term) in self.blocks.items():
            if term is None:
                raise ValueError("block without terminator: " + name)
            last = self._level(ops, term)
            labels[name] = end
            scheduled.append((name, end, ops, term, last))
            for node in ops:
                node._abs = tick + node._level
            term._abs = tick + last
            tick += last
            end += last * layer_bits
        if end > self.code_limit:
            raise ValueError("copy layers overlap guest memory")

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

        def resolve(value):
            value = self._resolve_field(value, None)
            return labels[value] if isinstance(value, str) else value

        def place(node, home):
            node.home = home
            at = node.home + node.slot * instruction_bits
            for width, value in [(self.layout.n_bits, node.n),
                                 (self.layout.address_bits, resolve(node.dst)),
                                 (self.layout.address_bits, resolve(node.src))]:
                bits(at, width, value)
                at += width

        # first assign every home and slot (labels and homes are needed
        # by resolve for field patches that point at later layers)
        layout = []
        for name, base, ops, term, last in scheduled:
            by_level = {}
            for node in ops:
                by_level.setdefault(node._level, []).append(node)
            for level, group in by_level.items():
                if len(group) > link_slot:
                    raise ValueError(
                        f"level {level} of {name} has {len(group)} nodes > {link_slot}")
            for level in range(1, last + 1):
                home = base + (level-1) * layer_bits
                for slot, node in enumerate(by_level.get(level, ())):
                    node.home, node.slot = home, slot
            term.home, term.slot = base + (last-1) * layer_bits, link_slot
            layout.append((base, by_level, term, last))

        # invariants of the bulk schedule: within one tick all copies are
        # pairwise disjoint (P2), no copy touches the processor region, and
        # a patched instruction runs at least two layers after its patch (P1).
        # An instruction whose "dst" field is patched has a data-dependent
        # destination (the writeback write goes to REGS or DISCARD); it is
        # skipped here, the generator guarantees the destination is outside
        # the processor region.
        dynamic = set()
        for base, by_level, term, last in layout:
            for group in by_level.values():
                for node in group:
                    if isinstance(node.dst, Field) and node.dst.name == "dst":
                        dynamic.add(id(node.dst.instruction))
        for base, by_level, term, last in layout:
            for level, group in by_level.items():
                ranges = sorted((node.dst, node.dst + node.n)
                                for node in group
                                if isinstance(node.dst, int) and id(node) not in dynamic)
                for (a0, a1), (b0, _) in zip(ranges, ranges[1:]):
                    if b0 < a1:
                        raise ValueError("overlapping copies in one tick")
                for node in group:
                    if id(node) in dynamic:
                        continue
                    if isinstance(node.dst, int) and node.dst < layer_bits:
                        raise ValueError("a copy writes the processor region")
                    if (isinstance(node.dst, Field)
                            and node.dst.instruction._abs - node._abs < 2):
                        raise ValueError("a patch is closer than two layers to its instruction")

        image = bytearray(image_bytes if image_bytes is not None else
                          self.layout.memory_bit//8 + self.memory_bytes)
        for address, width, value in self.data:
            bits(address, width, value)
        for base, by_level, term, last in layout:
            for level in range(1, last + 1):
                home = base + (level-1) * layer_bits
                for node in by_level.get(level, ()):
                    place(node, home)
                if level == last:
                    place(term, home)
                else:
                    link = Copy(layer_bits, 0, base + level * layer_bits)
                    link.slot = link_slot
                    place(link, home)
        for i, value in registers.items():
            if i:
                bits(REGS+i*32, 32, value)
        bits(PC, 32, entry)
        image[self.layout.memory_bit//8:self.layout.memory_bit//8+len(program)] = program
        first = labels[initial_label] // 8
        image[:layer_bits//8] = image[first:first+layer_bits//8]
        manifest = {
            "space_bytes": self.layout.space_bytes, "processor_n": SLOTS,
            "n_bits": self.layout.n_bits, "address_bits": self.layout.address_bits,
            "instruction_bits": instruction_bits, "layer_bits": layer_bits,
            "code_base": self.code_base, "code_end_bit": end,
            "registers_bit": REGS, "pc_bit": PC, "status_bit": STATUS,
            "guest_memory_bit": self.layout.memory_bit, "guest_memory_bytes": self.memory_bytes,
            "initial_stack": registers.get(2, 0), "entry": entry,
            "layer_count": sum(last for _, _, _, _, last in scheduled),
            "labels": labels,
        }
        return bytes(image), manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--entry", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--stack", type=lambda value: int(value, 0))
    parser.add_argument("--memory-bytes", type=lambda value: int(value, 0), default=MEMORY_BYTES)
    parser.add_argument("--space-bytes", type=lambda value: int(value, 0), default=SPACE_BYTES)
    args = parser.parse_args()
    try:
        image, manifest = BulkImage(memory_bytes=args.memory_bytes,
                                    layout=Layout(args.space_bytes)).build().encode(
            args.program.read_bytes(), args.entry,
            None if args.stack is None else {2: args.stack})
    except (OSError, ValueError, NotImplementedError) as error:
        parser.error(str(error))
    args.output.write_bytes(image)
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest, indent=2)+"\n")


if __name__ == "__main__":
    main()
