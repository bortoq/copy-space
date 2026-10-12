"""Generate checked IN installation records and a copy-only RV32I loader."""
import argparse
import json
import struct
from pathlib import Path

from rv32i import (Image, Copy, Field, Layout, N_BITS, ADDRESS_BITS, INSN_BITS,
                   LAYER_BITS, SPACE_BYTES, REGS, PC, STATUS, MEMORY, MEMORY_BYTES,
                   ZERO, IO_STATUS, COND, CARRY, EA, IMM, REPORT_DETAIL)

CORE_BUFFER = LAYER_BITS
CORE_RESTART = CORE_BUFFER + 512
CONSTANT_BASE, TABLE_BASE, LOADER_CODE = 0xC00000, 0xC40000, 0xC80000
HEADER = 0xF00000
LENGTH, ENTRY = HEADER+128, HEADER+160
NOP = (0, 0, 0)


def record(rows, layout=Layout()):
    if len(rows) != 4:
        raise ValueError("installation requires four rows")
    raw = bytearray(layout.core_record_bytes)
    at = 0
    for row in rows:
        if len(row) != 3:
            raise ValueError("installation row requires three fields")
        for value, width in zip(row, (layout.n_bits, layout.address_bits, layout.address_bits)):
            if not 0 <= value < 1 << width:
                raise ValueError("installation field overflow")
            for bit in range(width):
                raw[at//8] |= ((value >> bit) & 1) << (7-at%8)
                at += 1
    return bytes(raw)


class Loader(Image):
    def __init__(self, cpu_bytes, first_cpu_layer, memory_bytes, report_status=False,
                 layout=Layout()):
        constant_base = layout.space_bytes*6
        header = layout.space_bytes*15//2
        length, entry = header+128, header+160
        super().__init__(code_base=constant_base+0x80000, constant_base=constant_base,
                         table_base=constant_base+0x40000, code_limit=header,
                         memory_bytes=memory_bytes, report_status=report_status, layout=layout)
        self.start("handoff")
        self.jump("cpu")
        self.start("cpu")
        self.read("cpu", cpu_bytes*8, REGS)
        self.jump("header")
        self.start("header")
        self.read("header", 96, header)
        # External bytes have normal little-endian integer representation.
        for dst, byte in [(IMM, 0), (length, 4), (entry, 8)]:
            for i in range(32):
                self.emit(1, dst+i, header+8*byte+(i//8)*8+7-i%8)
        self.require_value(IMM, int.from_bytes(b"RVS1", "little"), "load_error")
        self.require_zero(list(range(length+self.memory_bits+1, length+32)), "load_error")
        self.add(EA, length, self.constant(self.memory_bytes+1), subtract=True)
        self.gate("not", COND, [CARRY])
        self.guard(COND, "load_error")
        self.add(EA, length, self.constant(4), subtract=True)
        self.guard(CARRY, "load_error")
        self.require_zero([entry, entry+1], "load_error")
        self.add(EA, entry, self.constant(4))
        self.gate("not", COND, [CARRY])
        self.guard(COND, "load_error")
        self.add(IMM, length, EA, subtract=True)
        self.guard(CARRY, "load_error")
        self.emit(32, PC, entry)
        guest = Copy(0, layout.memory_bit, 0)
        self.emit(self.memory_bits+1, Field(guest, "n", 3), length)
        self.jump("program")
        self.start("program")
        self.channels["program"] = (1, guest)
        self.emit(32, IO_STATUS, self.constant(0))
        self.emit(layout.address_bits, IO_STATUS, Field(guest, "src"))
        # Expected status is byte count << 4; include the error bit.
        self.emit(32, IMM, self.constant(0))
        self.emit(self.memory_bits+1, IMM+4, length)
        for i in range(layout.address_bits):
            self.gate("xor", EA+i, [IO_STATUS+i, IMM+i])
        self.require_zero(list(range(EA, EA+layout.address_bits)), "load_error")
        self.blocks[self.current] = (self.blocks[self.current][0],
                                    Copy(layout.layer_bits, 0, first_cpu_layer))
        self.start("load_error")
        self.emit(32, STATUS, self.constant(11))
        if report_status:
            self.emit(32, REPORT_DETAIL, self.constant(0))
        self.jump("report_prepare" if report_status else "halt")
        self.start("halt")
        self.blocks[self.current] = ([], Copy(layout.layer_bits, 0, ZERO))
        if report_status:
            self.build_report("L")

    def read(self, name, bits, destination):
        channel = Copy(bits, destination, 0)
        self.channels[name] = (1, channel)
        self.emit(32, IO_STATUS, self.constant(0))
        self.emit(self.layout.address_bits, IO_STATUS, Field(channel, "src"))
        self.require_value(IO_STATUS, bits*2, "load_error")


def encode_stream(cpu_image, cpu_manifest, program):
    placement = Layout(cpu_manifest["space_bytes"])
    if (cpu_manifest["processor_n"] != 256
            or cpu_manifest["layer_bits"] != placement.layer_bits
            or cpu_manifest["guest_memory_bit"] != placement.memory_bit
            or any(cpu_manifest.get(key, value) != value for key, value in (
                ("n_bits", placement.n_bits), ("address_bits", placement.address_bits),
                ("instruction_bits", placement.instruction_bits)))):
        raise ValueError("stream layout does not match CPU manifest")
    entry = cpu_manifest["entry"]
    memory_bytes = cpu_manifest["guest_memory_bytes"]
    if not 4 <= len(program) <= memory_bytes or entry % 4 or entry+4 > len(program):
        raise ValueError("program length/entry is outside the stream contract")
    cpu_end = cpu_manifest["code_end_bit"]//8
    if not REGS//8 < cpu_end <= min(len(cpu_image), placement.memory_bit//8):
        raise ValueError("CPU payload is outside its code region")
    cpu = cpu_image[REGS//8:cpu_end]
    loader, layout = Loader(len(cpu), cpu_manifest["labels"]["fetch"], memory_bytes,
                            cpu_manifest.get("report_status", False), placement).encode(
        registers={}, initial_label="handoff", image_bytes=placement.space_bytes)
    installation = bytearray()
    # Only nonzero chunks need installation into initially zero memory.
    end = layout["code_end_bit"]//8
    installed = 0
    chunk_bytes = placement.literal_bytes
    for start in range(placement.space_bytes*6//8, end, chunk_bytes):
        chunk = loader[start:min(start+chunk_bytes, end)].ljust(chunk_bytes, b"\0")
        if not any(chunk):
            continue
        value = sum(((chunk[i//8] >> (7-i%8)) & 1) << i for i in range(chunk_bytes*8))
        installation += record([
            (chunk_bytes*8, start*8, placement.core_buffer+placement.instruction_bits+placement.n_bits),
            (0, value & ((1 << placement.address_bits)-1), value >> placement.address_bits), NOP,
            (4*placement.instruction_bits, 0, placement.core_restart)], placement)
        installed += 1
    installation += record([NOP, NOP, NOP,
                            (placement.layer_bits, 0, layout["labels"]["handoff"])], placement)
    header = b"RVS1" + struct.pack("<II", len(program), entry)
    packet = bytes(installation) + cpu + header + program
    manifest = dict(cpu_manifest)
    manifest.update({
        "stream": True, "installation_bytes": len(installation),
        "installation_records": installed+1, "loader_layer_count": layout["layer_count"],
        "loader_code_end_bit": layout["code_end_bit"], "loader_labels": layout["labels"],
        "loader_nonzero_chunk_bytes": installed*chunk_bytes,
        "installation_record_bytes": placement.core_record_bytes,
        "installation_literal_bytes": chunk_bytes,
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
    parser.add_argument("--space-bytes", type=lambda s: int(s, 0), default=SPACE_BYTES)
    parser.add_argument("--io", action="store_true")
    parser.add_argument("--report-status", action="store_true")
    args = parser.parse_args()
    try:
        program = args.program.read_bytes()
        cpu, manifest = Image(io=args.io, memory_bytes=args.memory_bytes,
                              report_status=args.report_status,
                              layout=Layout(args.space_bytes)).build().encode(
            program, args.entry, None if args.stack is None else {2: args.stack})
        packet, manifest = encode_stream(cpu, manifest, program)
        args.output.write_bytes(packet)
        if args.manifest:
            args.manifest.write_text(json.dumps(manifest, indent=2)+"\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
