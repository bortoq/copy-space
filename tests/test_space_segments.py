"""Compare resumed execution, file cursors and output with one continuous run."""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "modules")
from rv32i import Image
from rv32i_stream import encode_stream
from space_segments import execute_segments

root = Path("tmp/space-tests/space-segments") / str(time.time_ns())
root.mkdir(parents=True, exist_ok=True)
program = b"".join(word.to_bytes(4, "little") for word in (
    0x73, 0x00100513, 0x04000893, 0x73, 0x00000513, 0x03f00893, 0x73,
    0x00100513, 0x04000893, 0x73, 0x00000513, 0x05d00893, 0x73))
image, manifest = Image(io=True, memory_bytes=65536).build().encode(
    program, registers={10: 0, 11: 4096, 12: 8, 17: 63})
core = root / "initial.core"
core.write_bytes(image)
packet, manifest = encode_stream(image, manifest, program)
data = b"ABCDEFGHIJKLMNOPunused input!"

for name, prefix, initial, ticks in (("runtime", b"", core, 10), ("loading", packet, None, 500)):
    folder = root / name
    folder.mkdir(exist_ok=True)
    incoming = folder / "in.bin"
    incoming.write_bytes(prefix+data)
    command = ["build/bin/space", "--trace", str(folder / "continuous-trace.txt"),
               "--dump-space", str(folder / "continuous-space.bin")]
    if initial is not None:
        command += ["--core", str(initial)]
    (folder / "continuous-args.json").write_text(json.dumps(command, indent=2)+"\n")
    result = subprocess.run(command, input=prefix+data, capture_output=True, timeout=10)
    assert result.returncode == 0 and not result.stderr and result.stdout == b"ABCDEFGHIJKLMNOP"
    (folder / "continuous.out").write_bytes(result.stdout)
    try:
        execute_segments("build/bin/space", folder / "resumed", incoming,
                         space_bytes=2097152, layer_bytes=2272, ticks=ticks,
                         timeout=10, compression="gzip", initial_core=initial, max_parts=1)
    except AssertionError as error:
        assert str(error) == "space exceeded the segment limit", error
    else:
        raise AssertionError("first segment unexpectedly completed")
    original = (folder / "resumed/part-0000/trace.txt.gz").read_bytes()
    if name == "runtime":
        def rejected(message):
            try:
                execute_segments("build/bin/space", folder / "resumed", incoming,
                                 space_bytes=2097152, layer_bytes=2272, ticks=ticks,
                                 timeout=10, compression="gzip", initial_core=initial, resume=True)
            except AssertionError as error:
                assert str(error) == message, error
            else:
                raise AssertionError("corrupt resume accepted")

        incoming.write_bytes(prefix+data+b"changed")
        rejected("changed execution input/configuration")
        incoming.write_bytes(prefix+data)
        checkpoint = folder / "resumed/part-0000/space.bin"
        snapshot = checkpoint.read_bytes()
        checkpoint.write_bytes(bytes([snapshot[0]^1])+snapshot[1:])
        rejected("changed checkpoint")
        checkpoint.write_bytes(snapshot)
        output = folder / "resumed/program.in"
        saved = output.read_bytes()
        output.write_bytes(saved+b"changed")
        rejected("changed output length")
        output.write_bytes(saved)
    interrupted = folder / "resumed/part-0001"
    interrupted.mkdir()
    (interrupted / "partial.trace").write_bytes(b"interrupted attempt")
    evidence = execute_segments("build/bin/space", folder / "resumed", incoming,
                                space_bytes=2097152, layer_bytes=2272, ticks=ticks,
                                timeout=10, compression="gzip", initial_core=initial, resume=True)
    assert (folder / "resumed/part-0001.interrupted-0/partial.trace").read_bytes() == b"interrupted attempt"
    assert (folder / "resumed/part-0000/trace.txt.gz").read_bytes() == original
    assert (folder / "resumed/program.in").read_bytes() == result.stdout
    assert (folder / "resumed/space.bin").read_bytes() == (folder / "continuous-space.bin").read_bytes()
    parts = json.loads((folder / "resumed/segments.json").read_text())
    assert len(parts) > 1 and parts[-1]["input_after"] == len(prefix)+16
    if name == "runtime":
        assert sum(part["output_after"] > part["output_before"] for part in parts) == 2
    (folder / "evidence.json").write_text(json.dumps(evidence, indent=2)+"\n")
    print("OK resumed "+name+": exact final memory/OUT, logical IN cursor, full traces")
