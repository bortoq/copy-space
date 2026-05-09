#!/bin/sh
set -eu

PY="${PYTHON:-python3}"

# Ensure the ABI artifacts doc covers exactly ART[0..ART_COUNT-1].
"$PY" scripts/check_art_doc_sync.py --doc doc/abi_artifacts.md
