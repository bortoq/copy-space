#!/usr/bin/env sh
set -eu

python3 scripts/riscv/run_external_rv32i_corpus.py --manifest third_party/riscv-external/manifest_rv32i.json --outdir tmp/rv32i_external
