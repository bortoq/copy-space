"""Remove known build artifacts while preserving tracked files and installed tools."""
import fnmatch
import shutil
import subprocess
from pathlib import Path

DIRECTORIES = ("build", "tmp", "out", "bak", "dist", "*.build", "cmake-build-*",
               "CMakeFiles", "__pycache__", "*.egg-info", ".pytest_cache",
               ".mypy_cache", ".ruff_cache", "htmlcov")
FILES = ("*.o", "*.a", "*.so", "*.dylib", "*.bin", "*.elf", "*.core", "*.stream",
         "*.d", "*.gcda", "*.gcno", "*.gcov", "*.bin.json", "*.core.json",
         "*.stream.json", "*.deb", "*.log", "*.log.gz", "*.out", "*.meta",
         "trace*.txt", "trace*.txt.gz", "trace*.txt.zst", "*.pyc", "*.pyo", "*.pyd", ".coverage",
         ".coverage.*", "CMakeCache.txt", "cmake_install.cmake", "CTestTestfile.cmake",
         "compile_commands.json", "install_manifest.txt", "build.ninja",
         ".ninja_deps", ".ninja_log", ".DS_Store", "Thumbs.db")
KEEP = (".git", ".agents", ".aws", ".codex", ".idea", ".vscode", ".venv",
        "tmp/rv32i-toolchain/root")
ROOT_FILES = ("job.in", "job.in.json")


def clean(root):
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True)
    if result.returncode:
        raise RuntimeError("cannot list tracked files; cleanup cancelled")
    tracked = {name.decode(errors="surrogateescape") for name in result.stdout.split(b"\0") if name}
    protected_parents = set()
    for name in tracked | set(KEEP):
        protected_parents.update(parent.as_posix() for parent in Path(name).parents)
    removed = 0

    def walk(folder, temporary=False):
        nonlocal removed
        for path in sorted(folder.iterdir()):
            relative = path.relative_to(root).as_posix()
            if relative in tracked or any(relative == keep or relative.startswith(keep+"/") for keep in KEEP):
                continue
            directory = path.is_dir() and not path.is_symlink()
            patterns = DIRECTORIES if directory or path.is_symlink() else FILES
            artifact = (temporary or any(fnmatch.fnmatchcase(path.name, pattern) for pattern in patterns)
                        or relative in ROOT_FILES)
            if path.is_symlink():
                artifact = artifact or any(fnmatch.fnmatchcase(path.name, pattern) for pattern in FILES)
            if directory:
                if artifact and relative not in protected_parents:
                    shutil.rmtree(path)
                    removed += 1
                else:
                    walk(path, artifact)
                    if artifact and not any(path.iterdir()):
                        path.rmdir()
                        removed += 1
            elif artifact:
                path.unlink()
                removed += 1

    walk(root)
    return removed


if __name__ == "__main__":
    try:
        print(f"Removed {clean(Path.cwd())} artifact files/directories")
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error))
