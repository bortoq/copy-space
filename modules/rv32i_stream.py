"""Generate checked IN installation records and a copy-only RV32I loader."""
import argparse
import json
import struct
from pathlib import Path

from rv32i import (Image, Copy, Field, N_BITS, ADDRESS_BITS, INSN_BITS,
                   LAYER_BITS, SPACE_BYTES, REGS, PC, STATUS, MEMORY, MEMORY_BYTES,
                   ZERO, IO_STATUS, COND, CARRY, EA, IMM)

CORE_BUFFER = LAYER_BITS
CORE_RESTART = CORE_BUFFER + 512
CONSTANT_BASE, TABLE_BASE, LOADER_CODE = 0xC00000, 0xC40000, 0xC80000
HEADER = 0xF00000
LENGTH, ENTRY = HEADER+128, HEADER+160
NOP = (0, 0, 0)


def record(rows):
    raw = bytearray(37)
    at = 0
    for row in rows:
        for value, width in zip(row, (N_BITS, ADDRESS_BITS, ADDRESS_BITS)):
            if not 0 <= value < 1 << width:
                raise ValueError("installation field overflow")
            for bit in range(width):
                raw[at//8] |= ((value >> bit) & 1) << (7-at%8)
                at += 1
    return bytes(raw)


class Loader(Image):
    def __init__(self, cpu_bytes, first_cpu_layer, memory_bytes):
        super().__init__(code_base=LOADER_CODE, constant_base=CONSTANT_BASE,
                         table_base=TABLE_BASE, code_limit=HEADER, memory_bytes=memory_bytes)
        self.start("handoff")
        self.jump("cpu")
        self.start("cpu")
        self.read("cpu", cpu_bytes*8, REGS)
        self.jump("header")
        self.start("header")
        self.read("header", 96, HEADER)
        # External bytes have normal little-endian integer representation.
        for dst, byte in [(IMM, 0), (LENGTH, 4), (ENTRY, 8)]:
            for i in range(32):
                self.emit(1, dst+i, HEADER+8*byte+(i//8)*8+7-i%8)
        self.require_value(IMM, int.from_bytes(b"RVS1", "little"), "load_error")
        self.require_zero(list(range(LENGTH+self.memory_bits+1, LENGTH+32)), "load_error")
        self.add(EA, LENGTH, self.constant(self.memory_bytes+1), subtract=True)
        self.gate("not", COND, [CARRY])
        self.guard(COND, "load_error")
        self.add(EA, LENGTH, self.constant(4), subtract=True)
        self.guard(CARRY, "load_error")
        self.require_zero([ENTRY, ENTRY+1], "load_error")
        self.add(EA, ENTRY, self.constant(4))
        self.gate("not", COND, [CARRY])
        self.guard(COND, "load_error")
        self.add(IMM, LENGTH, EA, subtract=True)
        self.guard(CARRY, "load_error")
        self.emit(32, PC, ENTRY)
        guest = Copy(0, MEMORY, 0)
        self.emit(self.memory_bits+1, Field(guest, "n", 3), LENGTH)
        self.jump("program")
        self.start("program")
        self.channels["program"] = (1, guest)
        self.emit(32, IO_STATUS, self.constant(0))
        self.emit(24, IO_STATUS, Field(guest, "src"))
        # Expected status is byte count << 4; include the error bit.
        self.emit(32, IMM, self.constant(0))
        self.emit(self.memory_bits+1, IMM+4, LENGTH)
        for i in range(24):
            self.gate("xor", EA+i, [IO_STATUS+i, IMM+i])
        self.require_zero(list(range(EA, EA+24)), "load_error")
        self.blocks[self.current] = (self.blocks[self.current][0],
                                    Copy(LAYER_BITS, 0, first_cpu_layer))
        self.start("load_error")
        self.emit(32, STATUS, self.constant(11))
        self.jump("halt")
        self.start("halt")
        self.blocks[self.current] = ([], Copy(LAYER_BITS, 0, ZERO))

    def read(self, name, bits, destination):
        channel = Copy(bits, destination, 0)
        self.channels[name] = (1, channel)
        self.emit(32, IO_STATUS, self.constant(0))
        self.emit(24, IO_STATUS, Field(channel, "src"))
        self.require_value(IO_STATUS, bits*2, "load_error")


def encode_stream(cpu_image, cpu_manifest, program):
    if cpu_manifest["space_bytes"] != SPACE_BYTES or cpu_manifest["processor_n"] != 256:
        raise ValueError("stream format requires the default space configuration")
    entry = cpu_manifest["entry"]
    memory_bytes = cpu_manifest["guest_memory_bytes"]
    if not 4 <= len(program) <= memory_bytes or entry % 4 or entry+4 > len(program):
        raise ValueError("program length/entry is outside the stream contract")
    cpu_end = cpu_manifest["code_end_bit"]//8
    cpu = cpu_image[REGS//8:cpu_end]
    loader, layout = Loader(len(cpu), cpu_manifest["labels"]["fetch"], memory_bytes).encode(
        registers={}, initial_label="handoff", image_bytes=SPACE_BYTES)
    installation = bytearray()
    # Only nonzero chunks need installation into initially zero memory.
    end = layout["code_end_bit"]//8
    installed = 0
    for start in range(CONSTANT_BASE//8, end, 6):
        chunk = loader[start:min(start+6, end)].ljust(6, b"\0")
        if not any(chunk):
            continue
        value = sum(((chunk[i//8] >> (7-i%8)) & 1) << i for i in range(48))
        installation += record([(48, start*8, CORE_BUFFER+INSN_BITS+N_BITS),
                                (0, value & 0xffffff, value >> 24), NOP,
                                (284, 0, CORE_RESTART)])
        installed += 1
    installation += record([NOP, NOP, NOP,
                            (LAYER_BITS, 0, layout["labels"]["handoff"])])
    header = b"RVS1" + struct.pack("<II", len(program), entry)
    packet = bytes(installation) + cpu + header + program
    manifest = dict(cpu_manifest)
    manifest.update({
        "stream": True, "installation_bytes": len(installation),
        "installation_records": installed+1, "loader_layer_count": layout["layer_count"],
        "loader_code_end_bit": layout["code_end_bit"], "loader_labels": layout["labels"],
        "loader_nonzero_chunk_bytes": installed*6,
        "cpu_payload_bytes": len(cpu), "header_offset": len(installation)+len(cpu),
        "program_bytes": len(program), "stream_bytes": len(packet),
    })
    return packet, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--entry", type=lambda s: int(s, 0), default=0)
    parser.add_argument("--stack", type=lambda s: int(s, 0))
    parser.add_argument("--memory-bytes", type=lambda s: int(s, 0), default=MEMORY_BYTES)
    parser.add_argument("--io", action="store_true")
    args = parser.parse_args()
    try:
        program = args.program.read_bytes()
        cpu, manifest = Image(io=args.io, memory_bytes=args.memory_bytes).build().encode(
            program, args.entry, None if args.stack is None else {2: args.stack})
        packet, manifest = encode_stream(cpu, manifest, program)
        args.output.write_bytes(packet)
        if args.manifest:
            args.manifest.write_text(json.dumps(manifest, indent=2)+"\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
