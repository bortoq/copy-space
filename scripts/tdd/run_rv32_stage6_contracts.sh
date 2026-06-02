#!/bin/sh
set -eu

sh scripts/tdd/run_rv32_bootstrap_closure.sh
sh scripts/tdd/test_rv32_stage6_docs_sync.sh
sh scripts/tdd/test_rv32_stage6_roadmap_sync.sh

echo "OK rv32 stage6 contracts"
