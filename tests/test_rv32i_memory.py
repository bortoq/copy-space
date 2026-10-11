"""Independent large-memory RV32I checks, including IN loading and compiled C."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "modules")
from rv32i import Image, MEMORY, REGS, PC, STATUS
from rv32i_stream import encode_stream
from rv32i_reference import execute

ROOT = Path("tmp/space-tests/rv32i-memory")
ROOT.mkdir(parents=True, exist_ok=True)
cases = 0


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def run(name, program, size=524288, registers=None, entry=0, memory=None, io=None, stream=False):
    global cases
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    expected, expected_memory, _ = execute(program, registers, entry, memory,
                                           io=io, memory_bytes=size)
    image, manifest = Image(io=io is not None, memory_bytes=size).build().encode(
        program, entry, registers)
    for address, content in (memory or {}).items():
        assert not stream
        image = bytearray(image)
        image[MEMORY//8+address:MEMORY//8+address+len(content)] = content
        image = bytes(image)
    if stream:
        image, manifest = encode_stream(image, manifest, program)
    (folder / "image.bin").write_bytes(image)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    data = (b"" if not stream else image)+(io.get("input", b"") if io is not None else b"")
    (folder / "in.bin").write_bytes(data)
    command = ["build/bin/space_image_proof", "--in", str(folder / "in.bin"),
               "--out", str(folder / "out.bin"), "--dump-space", str(folder / "space.bin"),
               "--trace", str(folder / "trace.txt"), "--report", str(folder / "report.txt"), "--unlimited"]
    if not stream:
        command += ["--core", str(folder / "image.bin")]
    (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
    result = subprocess.run(command, capture_output=True, timeout=20)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0, (name, result.stderr)
    raw = (folder / "space.bin").read_bytes()
    assert raw[:2272] == bytes(2272), name
    assert [word(raw, REGS+32*i) for i in range(34)] == expected[-1], name
    assert raw[MEMORY//8:MEMORY//8+size] == expected_memory, name
    trace = (folder / "trace.txt").read_text()
    assert trace.endswith(" idle\n"), name
    if io is not None:
        assert (folder / "out.bin").read_bytes() == io["output"], name
        actual = [[int(v) for v in line.split()[2:]] for line in trace.splitlines()
                  if line.startswith("channel ")]
        if stream:
            actual = actual[-len(io["channels"]):] if io["channels"] else []
        assert actual == io["channels"], (name, actual, io["channels"])
    cases += 1
    print(f"OK guest memory {name}: size={size}, status={expected[-1][-1]}")
    return raw


def words(*values):
    return b"".join(value.to_bytes(4, "little") for value in values)


def machine_tests():
    # SW x2,0(x1); LW x3,0(x1); EBREAK.
    program = words(0x0020a023, 0x0000a183, 0x00100073)
    for size in (65536, 131072, 262144, 524288):
        for address in (size//2, size-4):
            raw = run(f"word-{size}-{address}", program, size,
                      {1: address, 2: 0x89abcdef})
            assert word(raw, REGS+96) == 0x89abcdef
        run(f"store-outside-{size}", program, size, {1: size, 2: 7})
        run(f"load-outside-{size}", words(0x0000a183), size, {1: size})
        run(f"fetch-outside-{size}", words(0x00100073), size, entry=size)
    for address in (65536, 131072, 262144):
        run(f"distinct-high-{address}", words(0x0000a183, 0x00100073),
            registers={1: address}, memory={address: b"\x78\x56\x34\x12"})
    run("load-negative", words(0x0000a183), registers={1: 0xfffffffc})
    # SB/LBU on the last byte and misaligned LW at the same address.
    run("last-byte", words(0x00208023, 0x0000c183, 0x00100073),
        registers={1: 524287, 2: 0xab})
    run("last-word-align", words(0x0000a183), registers={1: 524287})

    # Entire payload arrives through IN; execute at the highest valid address.
    program = bytes(524284)+words(0x00100073)
    raw = run("stream-512k", program, entry=524284, stream=True)
    assert word(raw, PC) == 524284

    # READ; a0=1; a7=64; WRITE; a7=93; EXIT.
    io_program = words(0x73, 0x00100513, 0x04000893, 0x73, 0x05d00893, 0x73)
    for address, count in [(65536, 8), (262144, 8), (524287, 1), (524287, 2),
                           (524288, 1), (0xfffffffc, 8), (0, 524289), (1, 0xffffffff)]:
        run(f"io-{address}-{count}", io_program,
            registers={10: 0, 11: address, 12: count, 17: 63},
            io={"input": b"ABCDEFGH"})
    # A full-sized input operation overwrites code with identical instructions.
    entire = io_program+bytes(524288-len(io_program))
    raw = run("io-full-512k", io_program,
              registers={10: 0, 11: 0, 12: 524288, 17: 63}, io={"input": entire})
    assert word(raw, REGS+10*32) == 524288

    # Rejection happens during generation, not after an overflowing write.
    for invalid in (0, 65535, 131073, 1048576):
        try:
            Image(memory_bytes=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(invalid)
    try:
        Image().build().encode(bytes(524289))
    except ValueError:
        pass
    else:
        raise AssertionError("oversized program accepted")


def c_tests():
    global cases
    source = Path("tests/fixtures/rv32i/large_memory.c")
    for optimization in ("O0", "O2"):
        for stream in (False, True):
            folder = ROOT / f"c-{optimization}-{'stream' if stream else 'core'}"
            folder.mkdir(exist_ok=True)
            image = folder / "image.bin"
            build = [sys.executable, "scripts/rv32i/build.py", str(source), "-o", str(image),
                     "--optimization", optimization]
            if stream:
                build += ["--stream"]
            (folder / "build.json").write_text(json.dumps(build, indent=2)+"\n")
            result = subprocess.run(build, capture_output=True, timeout=20)
            (folder / "build.stderr").write_bytes(result.stderr)
            assert result.returncode == 0, result.stderr
            manifest = json.loads(image.with_name(image.name+".json").read_text())
            assert manifest["guest_memory_bytes"] == 524288
            assert manifest["initial_stack"] == 524272
            assert len((folder / "image.bin.build/program.bin").read_bytes()) > 65536
            command = [sys.executable, "scripts/rv32i/run.py", str(image),
                       "--dump-space", str(folder / "space.bin"), "--trace", str(folder / "trace.txt")]
            if stream:
                command += ["--stream"]
            (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
            (folder / "in.bin").write_bytes(b"D")
            result = subprocess.run(command, input=b"D", capture_output=True, timeout=20)
            (folder / "out.bin").write_bytes(result.stdout)
            (folder / "stderr.txt").write_bytes(result.stderr)
            assert result.returncode == 0 and result.stdout == b"XABCDE", result.stderr
            raw = (folder / "space.bin").read_bytes()
            assert word(raw, STATUS) == 10 and raw[:2272] == bytes(2272)
            assert 400000 < word(raw, REGS+64) < 524288
            trace = (folder / "trace.txt").read_text()
            assert trace.endswith(" idle\n")
            assert any(line.startswith("channel ") and int(line.split()[4]) > MEMORY+400000*8
                       for line in trace.splitlines())
            cases += 1
            print(f"OK C large memory {optimization} stream={stream}: OUT={result.stdout!r}")
    # Selected memory size also constrains the C linker and stack.
    result = subprocess.run([sys.executable, "scripts/rv32i/build.py", str(source),
                             "--memory-bytes", "65536", "-o", str(ROOT / "too-small.bin")],
                            capture_output=True, timeout=20)
    (ROOT / "too-small.stderr").write_bytes(result.stderr)
    assert result.returncode != 0 and b"program leaves less than 1024 bytes" in result.stderr


if "--c" in sys.argv:
    c_tests()
else:
    machine_tests()
print(f"OK expanded guest memory: {cases} executions; evidence in {ROOT}")
