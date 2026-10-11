"""Build distinct configurations; independently decode initial core."""
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

root = Path("tmp/space-tests/configuration")
root.mkdir(parents=True, exist_ok=True)
compiler = shlex.split(os.environ.get("CC", "cc"))
for space_bytes, processor_n in ((2097152, 512), (65536, 32), (65536, 4), (67108864, 256)):
    folder = root / f"{space_bytes}-{processor_n}"
    folder.mkdir(exist_ok=True)
    address = (space_bytes*8-1).bit_length()
    widths = (address-1, address, address)
    instruction = sum(widths)
    processor_bits = instruction*processor_n
    buffer_start = (processor_bits+7)//8*8
    layer_bits = 4*instruction
    input_bits = ((layer_bits+7)//8+1)*8
    status_bits = (2*input_bits+1).bit_length()
    shift = (layer_bits-1).bit_length()
    stride = 1 << shift
    table_bits = 1 << (status_bits+shift)
    restart = buffer_start+stride
    table_start = (restart+layer_bits+table_bits-1)//table_bits*table_bits
    compile_args = compiler + ["-O2", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Isrc",
                               f"-DVM_SPACE_BYTES={space_bytes}", f"-DPROCESSOR_N={processor_n}"]
    with tempfile.TemporaryDirectory(prefix="space-configuration-") as directory:
        proof, assembler = Path(directory)/"proof", Path(directory)/"assembler"
        commands = [compile_args + ["tests/space_image_proof.c", "src/core.c", "src/space_run.c",
                                    "src/space_trace.c", "src/space.c", "src/bitcopy.c", "-o", str(proof)],
                    compile_args + ["src/assembler.c", "src/bitcopy.c", "-o", str(assembler)]]
        (folder / "build.json").write_text(json.dumps(commands, indent=2) + "\n")
        for command in commands:
            subprocess.run(command, check=True)
        assembly = f"0 0 0\n0 0 0\n0 0 0\nCORE_LAYER_BITS PROCESSOR_START {space_bytes*8-processor_bits-8}\n"
        data = subprocess.run([str(assembler)], input=assembly.encode(), capture_output=True, check=True).stdout + b"\0"
        assert len(data)*8 == input_bits
        (folder / "input.copy").write_text(assembly)
        (folder / "in.bin").write_bytes(data)
        for ticks, stop, completed in ((0, "limit", 0), (10, "idle", 3)):
            report = folder / f"report-{ticks}.txt"
            dump = folder / f"space-{ticks}.bin"
            args = [str(proof), "--in", str(folder / "in.bin"), "--ticks", str(ticks),
                    "--dump-space", str(dump), "--report", str(report),
                    "--trace", str(folder / f"trace-{ticks}.txt")]
            (folder / f"args-{ticks}.json").write_text(json.dumps(args, indent=2) + "\n")
            subprocess.run(args, check=True, timeout=5)
            metadata = dict(line.split("=",1) for line in report.read_text().splitlines())
            assert metadata["stop"] == stop and int(metadata["ticks"]) == completed, metadata
            raw = dump.read_bytes()
            assert len(raw) == space_bytes
            if ticks == 0:
                rows = []
                for slot in range(4):
                    start, values = slot*instruction, []
                    for width in widths:
                        values.append(sum(((raw[(start+i)//8] >> (7-(start+i)%8)) & 1) << i
                                          for i in range(width)))
                        start += width
                    rows.append(values)
                assert rows == [[status_bits,3*instruction+widths[0]+address+shift,
                                 instruction+widths[0]+address],
                                [input_bits,buffer_start,0], [0,0,0],
                                [layer_bits,0,table_start]], rows
            else:
                assert raw[buffer_start//8:buffer_start//8+len(data)] == data
                assert raw[:(processor_bits+7)//8] == bytes((processor_bits+7)//8)
    print(f"OK configuration: space_bytes={space_bytes} PROCESSOR_N={processor_n} buffer={buffer_start}")
