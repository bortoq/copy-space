#!/bin/sh
set -eu

build/bin/test_bitcopy
build/bin/test_space_runtime
python3 tests/test_space_trace_audit.py
python3 tests/test_space_segments.py
python3 tests/test_assembler.py
python3 tests/test_space.py
python3 tests/test_configuration.py
sh scripts/tdd/test_first_layer_load.sh
sh scripts/tdd/test_add8_lut_sum.sh
python3 tests/test_rv32i.py
python3 tests/test_rv32i_io.py
python3 tests/test_rv32i_memory.py
python3 tests/test_rv32i_layout.py
