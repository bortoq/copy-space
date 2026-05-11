# Cross-platform build and run (native tools + Python CLI)

_file: doc/cross_platform.md_

Goal: run Copy-Space core workflows on Linux, macOS, and Windows without requiring /bin/sh for user-facing commands.

What is cross-platform today:
- Python CLI entrypoints (copyspace-validate, copyspace-solve, copyspace-pilot)
- Native tools build via CMake (vmrun, mkimage_std7_fixed, forth0c, vmprep_forth0, mkbench_bulkcopy)
- Prebuilt native tool packages are produced by the Release native tools workflow

What is not fully cross-platform yet:
- Some bench and dev helper scripts live under scripts/ and assume a POSIX shell environment.
  On Windows, use WSL or Git Bash for those scripts, or use CI artifacts / Pages bench history.

------------------------------------------------------------

## Requirements

- Python 3.9+
- CMake 3.16+
- A C compiler
  - Linux: gcc or clang
  - macOS: Xcode Command Line Tools (clang)
  - Windows: Visual Studio Build Tools (MSVC) or clang-cl

------------------------------------------------------------

## Option A: use prebuilt native tool packages (recommended for minimal friction)

1) Download the native tools archive for your platform from GitHub Releases:
   - linux: copyspace-native-tools-linux.tar.gz
   - macos: copyspace-native-tools-macos.tar.gz
   - windows: copyspace-native-tools-windows.zip

2) Extract it and put the binaries on PATH, or place them under build/bin inside your repo checkout.

3) Verify that the tools are available:
   - vmrun
   - mkimage_std7_fixed
   - forth0c
   - vmprep_forth0

------------------------------------------------------------

## Option B: build native tools from source via CMake

From the repo root:

1) Configure:

    cmake -S . -B build/cmake

2) Build:

    cmake --build build/cmake --config Release

3) Produced binaries are placed into build/bin.

------------------------------------------------------------

## Install Python CLI (entrypoints)

From the repo root:

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .

Verify:

    copyspace-validate --help
    copyspace-solve --help
    copyspace-pilot --help

------------------------------------------------------------

## Core scheduler workflow (portable)

One-command pilot (CSV to schedules and reports):

    copyspace-pilot --csv examples/demands.csv --bw 256 --outdir tmp/pilot

Validate-only:

    copyspace-validate instance.json schedule.json --report report.json --quiet

------------------------------------------------------------

## Bench results history

- Per-run artifacts are attached to CI runs (Artifacts section in GitHub Actions).
- Rolling history is published on GitHub Pages:
  https://bortoq.github.io/copy-space/
