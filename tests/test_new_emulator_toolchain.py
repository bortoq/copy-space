"""New-emulator (bulk) toolchain smoke tests (roadmap 8.10).

Builds a real C program and the pForth guest with the bulk generator
(--new-emulator) and runs them on the new emulator (space-dev) via --core,
the same end-to-end path scripts/rv32i, scripts/pforth and scripts/copy_c use
once they are switched to the new emulator.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMULATOR = os.environ.get("SPACE_EMULATOR", "/home/user/work/positional addressing/space-dev")
SPACE_BYTES = 8*1024*1024
OUT = Path("tmp/new-emulator")
OUT.mkdir(parents=True, exist_ok=True)

if not Path(EMULATOR).is_file():
    print(f"SKIP: new emulator not found at {EMULATOR}")
    sys.exit(0)


def run(argv, stdin=b"", timeout=120):
    return subprocess.run(argv, input=stdin, capture_output=True, timeout=timeout)


def run_core(image, stdin, dump, timeout=120):
    argv = [sys.executable, "scripts/rv32i/run.py", str(image), "--new-emulator",
            "--space-bytes", str(SPACE_BYTES), "--space", EMULATOR, "--dump-space", str(dump)]
    return run(argv, stdin, timeout)


# --- rv32i C program: read two numbers, write their sum -------------------
image = OUT / "sum.bin"
result = run([sys.executable, "scripts/rv32i/build.py", "--new-emulator",
              "examples/rv32i/sum.c", "-o", str(image), "--space-bytes", str(SPACE_BYTES)],
             timeout=300)
assert result.returncode == 0, result.stderr.decode()
result = run_core(image, b"2 40", OUT / "sum.space", timeout=120)
assert result.returncode == 0, result.stderr.decode()
assert result.stdout == b"42\n", result.stdout
print("OK new-emulator rv32i sum.c -> b'42\\n', exit 0")

# --- pForth guest: a colon definition and a print -------------------------
image = OUT / "pforth.bin"
result = run([sys.executable, "scripts/pforth/build.py", "--new-emulator", "-o", str(image)],
             timeout=600)
assert result.returncode == 0, result.stderr.decode()
result = run_core(image, b": square dup * ; 7 square . cr\n", OUT / "pforth.space", timeout=600)
assert result.returncode == 0, result.stderr.decode()
assert result.stdout.startswith(b"49"), result.stdout
print("OK new-emulator pforth ': square dup * ; 7 square . cr' -> b'49 ...'")
