"""Exercise real make clean in an isolated repository, including source protection."""
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def write(root, name):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test data\n")
    return path


with tempfile.TemporaryDirectory(prefix="copy-space-clean-") as directory:
    base = Path(directory)
    root = base / "project"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "scripts").mkdir()
    for name in ("Makefile", ".gitignore", "scripts/clean.py"):
        shutil.copyfile(PROJECT / name, root / name)
    sources = ["src/main.c", "runtime/pforth/pfdicdat.h", "runtime/pforth/pfdicdat.h.json",
               "third_party/pforth/csrc/pf_core.c", "build/keep source.c", "fixtures/input.bin",
               "config/keep file.d"]
    for name in sources:
        write(root, name)
    subprocess.run(["git", "add", "-f", "Makefile", ".gitignore", "scripts/clean.py", *sources],
                   cwd=root, check=True)
    artifacts = ["build/bin/space", "out/result", "bak/old", "dist/package", "tmp/trace.txt.gz",
                 "tmp/rv32i-toolchain/gcc.deb", "job.in", "job.in.json", "result.out",
                 "test.stream", "test.stream.json", "test.bin", "test.bin.json", "test.core",
                 "test.core.json", "test.o", "test.a", "test.so", "test.dylib", "test.d",
                 "test.gcda", "test.gcno", "test.gcov", "test.deb", "test.log", "test.log.gz",
                 "trace.txt", "trace.txt.gz", "trace.txt.zst", "nested/trace-full.txt.zst",
                 "test.pyc", "test.pyo", "test.pyd",
                 "nested/with spaces.bin.build/disassembly.txt", "nested/__pycache__/module.pyc",
                 "nested/module.egg-info/PKG-INFO", ".pytest_cache/cache", ".mypy_cache/cache",
                 ".ruff_cache/cache", ".coverage", ".coverage.local", "htmlcov/index.html",
                 "CMakeFiles/cache", "cmake-build-debug/space", "CMakeCache.txt",
                 "cmake_install.cmake", "CTestTestfile.cmake", "compile_commands.json",
                 "install_manifest.txt", "build.ninja", ".ninja_deps", ".ninja_log",
                 ".DS_Store", "Thumbs.db"]
    for name in artifacts:
        write(root, name)
    # These ignored settings/data are not build artifacts.
    preserved = ["notes.md", "task.fth", "input.in", "data.csv", ".vscode/settings.json",
                 ".idea/project.xml", ".venv/lib/module.pyc", ".agents/AGENTS.md",
                 ".aws/config", ".codex/settings.json",
                 "tmp/rv32i-toolchain/root/usr/bin/riscv64-unknown-elf-gcc"]
    for name in preserved:
        write(root, name)
    outside = write(base, "outside/keep.bin")
    (root / "linked.build").symlink_to(outside.parent, target_is_directory=True)
    (root / "build/outside-link").symlink_to(outside.parent, target_is_directory=True)
    snapshots = {name: hashlib.sha256((root / name).read_bytes()).digest()
                 for name in sources+preserved+["Makefile", ".gitignore", "scripts/clean.py"]}
    for name in artifacts:
        result = subprocess.run(["git", "check-ignore", "--no-index", name], cwd=root,
                                capture_output=True)
        assert result.returncode == 0, ("artifact not ignored", name)
    assert subprocess.run(["git", "check-ignore", "input.in"], cwd=root,
                          capture_output=True).returncode == 1
    for attempt in range(2):
        result = subprocess.run(["make", "clean"], cwd=root, capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr
        for name in artifacts:
            assert not (root / name).exists(), (attempt, name)
        for name, digest in snapshots.items():
            assert hashlib.sha256((root / name).read_bytes()).digest() == digest, name
        assert outside.read_text() == "test data\n"
        assert not (root / "linked.build").is_symlink()
        assert not (root / "build/outside-link").is_symlink()
    assert not subprocess.check_output(["git", "diff", "--name-only"], cwd=root)
    # Failure to enumerate tracked files must leave artifacts intact.
    shutil.rmtree(root / ".git")
    marker = write(root, "result.out")
    result = subprocess.run(["make", "clean"], cwd=root, capture_output=True, timeout=10)
    assert result.returncode != 0 and marker.read_text() == "test data\n"

print("OK clean: ignored artifacts removed; tracked files, tools, settings and link targets retained")
print("OK clean: repeat invocation and missing Git metadata")
