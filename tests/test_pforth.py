"""Run actual pForth C on copy-only RV32I; retain compressed raw copy logs."""
import gzip
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from space_trace_audit import audit_trace

ROOT = Path("tmp/space-tests/pforth")
ROOT.mkdir(parents=True, exist_ok=True)


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def build(name, core=False):
    output = ROOT / name
    command = [sys.executable, "scripts/pforth/build.py", "-o", str(output)]
    if core:
        command += ["--core"]
    result = subprocess.run(command, capture_output=True, timeout=30)
    (ROOT / (name+"-build.json")).write_text(json.dumps(command, indent=2)+"\n")
    (ROOT / (name+"-build.stderr")).write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(output.with_name(output.name+".json").read_text())
    assert manifest["pforth_dictionary"]["cell_bytes"] == 4 and manifest["io"]
    assert manifest["guest_memory_bytes"] == 524288
    return output


def run(name, image, source, expected, code=0, stream=False, input_error=False,
        output_error=False, live=False):
    folder = ROOT / name
    folder.mkdir(exist_ok=True)
    (folder / "in.fth").write_bytes(source)
    fifo = folder / "trace.fifo"
    if fifo.exists():
        fifo.unlink()
    os.mkfifo(fifo)
    # Lossless compression preserves every observer event while keeping the
    # several-gigabyte copy trace out of the workspace as an uncompressed file.
    keepalive = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    compressed = folder / "trace.txt.gz"
    compression_errors = []

    def compress():
        try:
            with fifo.open("rb", buffering=0) as incoming, gzip.open(compressed, "wb", compresslevel=1) as outgoing:
                shutil.copyfileobj(incoming, outgoing, 1024*1024)
        except Exception as error:
            compression_errors.append(error)

    compressor = threading.Thread(target=compress, daemon=True)
    compressor.start()
    command = [sys.executable, "scripts/rv32i/run.py", str(image), "--dump-space", str(folder / "space.bin"),
               "--trace", str(fifo), "--ticks", "20000000"]
    if stream:
        command += ["--stream"]
    if input_error:
        command += ["--in", str(folder)]
    if output_error:
        command += ["--out", "/dev/full"]
    (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
    started = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        if live:
            process.stdin.write(source)
            process.stdin.flush()
            process.wait(timeout=900)
            output, errors = process.stdout.read(), process.stderr.read()
        else:
            output, errors = process.communicate(source, timeout=900)
    except BaseException:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        raise
    finally:
        os.close(keepalive)
        compressor.join(timeout=30)
        fifo.unlink()
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe and not pipe.closed:
                pipe.close()
    assert not compressor.is_alive() and not compression_errors, compression_errors
    (folder / "out.bin").write_bytes(output)
    (folder / "stderr.txt").write_bytes(errors)
    raw = (folder / "space.bin").read_bytes()
    assert process.returncode == code, (name, process.returncode, errors)
    if expected is not None:
        assert output == expected, (name, output, expected)
    assert errors == b"", (name, errors)
    assert raw[:2272] == bytes(2272) and word(raw, 132128) == 10
    assert word(raw, 132160) == code
    if name == "live-language":
        binary = image.with_name(image.name+".build") / "program.bin"
        initial_program = binary.read_bytes()
        guest = raw[1048576:1048576+524288]
        for new_word in (b"SQUARE", b"SIGN-TEST", b"SUM-TEN", b"AREA"):
            assert new_word not in initial_program and new_word in guest, new_word
    copies, channels, last = audit_trace(compressed)
    assert copies > 0 and channels > 0 and last.endswith(b" idle\n"), (name, last)
    report = {"exit_code": code, "seconds": time.monotonic()-started,
              "copy_events": copies, "channel_events": channels,
              "trace_stop": last.decode().strip()}
    (folder / "result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(f"OK pForth {name}: OUT={output!r}, code={code}, {report['seconds']:.1f}s", flush=True)
    return output


stream = build("pforth.stream")
core = build("pforth.core", True)

# All user definitions, arithmetic, branches, loops and memory operations
# run in one live session. BYE must finish while stdin is still open.
source = b"""1 2 + . cr
: square dup * ; 7 square . cr
: sign-test 0< if 111 else 222 then ; -1 sign-test . 1 sign-test . cr
: sum-ten 0 10 0 do i + loop ; sum-ten . cr
: down begin dup . 1- dup 0= until drop ; 3 down cr
variable counter 123 counter ! counter @ . cr
hex FFFFFFFF 1 + . decimal cr
create area 60000 allot 42 area 59999 + c! area 59999 + c@ . cr
7 square . cr
bye
999 .
"""
expected = b"3 \n49 \n111 222 \n45 \n3 2 1 \n123 \n0 \n42 \n49 \n\n"
run("live-language", stream, source, expected, stream=True, live=True)
run("last-line", core, b"1 2 + .", b"3 ")
output = run("unknown-word", core, b"NO_SUCH_WORD\n", None, 2)
assert b"NO_SUCH_WORD" in output
run("unfinished", core, b": unfinished 1", b"pForth: unfinished definition\n", 2)
run("long-line", core, b" "*256+b"\n", b"pForth: input line too long\n", 2)
run("input-error", core, b"", b"", 1, input_error=True)
run("output-error", core, b"1 .\n", b"", 1, output_error=True)

prepared = json.loads(Path("runtime/pforth/pfdicdat.h.json").read_text())
assert hashlib.sha256(Path("runtime/pforth/pfdicdat.h").read_bytes()).hexdigest() == prepared["header_sha256"]
print(f"OK pForth: seven executions; complete raw copy logs in {ROOT}", flush=True)
