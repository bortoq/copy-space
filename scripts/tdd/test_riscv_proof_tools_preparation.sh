#!/bin/sh
set -eu

grep -F -q 'Prepare `rv32_space_*` proof tools for later resident execution' doc/resident_riscv_proof_tools_preparation.md
grep -F -q 'resident-ready, not resident-executing' doc/resident_riscv_proof_tools_preparation.md
grep -F -q '## 13. Prepare proof tools for resident execution' doc/roadmap.md
grep -F -q 'doc/resident_riscv_proof_tools_preparation.md' doc/project_structure.md
grep -F -q 'doc/resident_riscv_proof_tools_preparation.md' README.md

echo "OK riscv proof tools preparation"
