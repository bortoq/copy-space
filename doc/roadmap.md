# Copy-Space Roadmap

Audit baseline: 2026-06-02.
Rule: only artifact-backed, code-backed, or directly executed project state is recorded here.

## 1. Verified Foundation

1.1. ✅ Bit-addressable VM substrate exists in active code.
1.1.1. ✅ Core VM runtime is implemented in `src/vm/space.c`.
1.1.2. ✅ VM public interface exists in `src/vm/space.h`.
1.1.3. ✅ Native VM runner/toolchain is part of the active tree (`vmrun`, `mkimage_std7_fixed`, `forth0c`, `vmprep_forth0`).

1.2. ✅ Image-generation path exists.
1.2.1. ✅ Space image layout/build path exists under `src/mkimage/std7_fixed/`.
1.2.2. ✅ Generated artifact/address tables exist and are wired into the image build.
1.2.3. ✅ RV32M image tooling exists in `scripts/riscv/rv32m_image_builder.py` and `src/tools/rv32m_loader_tool.c`.

1.3. ✅ MMIO/channel/watchdog foundations exist.
1.3.1. ✅ Loader MMIO path exists in `src/vm/space.c`.
1.3.2. ✅ Channel ABI entrypoint exists in `service_channel()` in `src/vm/space.c`.
1.3.3. ✅ Watchdog/bounded-run controls exist in the same runtime.

## 2. Verified In-Space RISC-V Progress

2.1. ✅ Minimal runtime ABI is implemented inside the VM.
2.1.1. ✅ Implemented channel ops include `STATUS`, `LOAD_CODE`, `RUN`, `STEP`, `READ_REGS`, `READ_MEM`, `WRITE_MEM`.
2.1.2. ✅ These ops are exercised by active C-level harnesses in `scripts/tdd/test_rv32_runtime_abi_ops.sh` and `scripts/tdd/test_rv32_guest_run_contract.sh`.

2.2. ✅ Guest architectural state layout exists.
2.2.1. ✅ `G_PC` exists at `0x001000`.
2.2.2. ✅ `G_REG_BASE` exists at `0x001200`.
2.2.3. ✅ `G_MEM_BASE` exists at `0x002000`.

2.3. ✅ Real in-space guest stepping exists, but only for a narrow subset.
2.3.1. ✅ Implemented guest instructions in active runtime: `ADDI`.
2.3.2. ✅ Implemented guest instructions in active runtime: `LW`, `SW`.
2.3.3. ✅ Implemented guest instructions in active runtime: `BEQ`, `BNE`, `JAL`.
2.3.4. ✅ Unsupported instructions currently stop deterministically instead of executing.

2.4. ✅ Development assets around RISC-V are present and usable.
2.4.1. ✅ Loader/image/channel docs exist under `doc/rv32*` and `doc/rv32m*`.
2.4.2. ✅ Directed shell/C harnesses exist under `scripts/tdd/`.
2.4.3. ✅ Host-side corpus and helper scripts remain available as development aids.

## 3. Verified C3/Forth0 Progress

3.1. ✅ `C3_RUN` exists as an image-generation artifact.
3.1.1. ✅ Generator exists in `scripts/riscv/gen_c3_run.py`.
3.1.2. ✅ Generated word exists in `src/mkimage/std7_fixed/words_c3_run.c`.
3.1.3. ✅ Symbol/address wiring exists in `src/mkimage/std7_fixed/legacy.c`, `words.h`, `syms.c`, `artifacts.c`.

3.2. ✅ Some C3 microcode building blocks exist.
3.2.1. ✅ `ADD32` artifact exists.
3.2.2. ✅ C3 state layout/docs exist.
3.2.3. ✅ Multiple C3-oriented tests and trace helpers exist as development material.

3.3. ❌ Forth0 is not ported into Copy-Space as an autonomous in-space system.
3.3.1. ❌ Active `forth0` workflow still depends on host-side compilation/prep scripts.
3.3.2. ❌ `scripts/forth0/run_f0.sh` still orchestrates the path from the host.

3.4. ❌ C3 execution is not proven as the real RISC-V closure path.
3.4.1. ❌ `C3_RUN` is only partially verified.
3.4.2. ❌ Current proof level is limited to a narrow `ADDI`-class path.
3.4.3. ❌ Existing C3 trace/e2e gates are not acceptable as proof of in-space execution.

## 4. Verified Reality Gaps

4.1. ❌ There is no accepted raw PC/decoder trace proving in-space RISC-V execution.
4.1.1. ❌ This blocks strong claims about true guest execution closure.
4.1.2. ❌ This also blocks strong claims about C3-based execution proof.

4.2. ❌ The active in-space RISC-V executor is far below full RV32I.
4.2.1. ❌ Missing major RV32I arithmetic/logical families.
4.2.2. ❌ Missing major control-flow families (`JALR`, signed/unsigned branch matrix beyond `BEQ/BNE`).
4.2.3. ❌ Missing byte/halfword memory ops and exact fault semantics.

4.3. ❌ RV32M is not proven in the active in-space executor.
4.3.1. ❌ Multiplication/division/reminder families are not implemented in the runtime executor in `src/vm/space.c`.
4.3.2. ❌ Existing RV32M closure claims rely on surrounding harnesses, not on the verified narrow executor.

4.4. ❌ SHA/FreeRTOS milestones are not proven as real computational closure.
4.4.1. ❌ Current SHA three-binary gate reads a prearranged payload shape rather than proving SHA computation by the in-space executor.
4.4.2. ❌ Current FreeRTOS interactive gate proves a small guest loop/harness shape, not a trustworthy production-grade FreeRTOS port.

4.5. ❌ The release/gate layer contains false-positive risk.
4.5.1. ❌ Some gates are infrastructure smoke tests rather than semantic execution proofs.
4.5.2. ❌ Some gates rely on synthetic traces, scaffolded `TESTG`, or indirect invariants.

## 5. Active Development Roadmap

5.1. ❌ Finish a trustworthy in-space RV32I baseline in the runtime executor.
5.1.1. ❌ Add the remaining arithmetic/logical instructions required for a coherent RV32I core.
5.1.2. ❌ Add the remaining control-flow instructions and exact PC progression rules.
5.1.3. ❌ Add byte/halfword memory ops and exact alignment/bounds behavior.

5.2. ❌ Add proof-grade execution observability.
5.2.1. ❌ Emit raw PC/instruction/stop logs from the active in-space executor.
5.2.2. ❌ Make these logs the truth source for semantic validation.
5.2.3. ❌ Rebuild trace diff gates on top of real runtime traces only.

5.3. ❌ Replace false-positive tests with executable semantic proofs.
5.3.1. ❌ Retire scaffold-only C3 e2e/trace gates from active closure claims.
5.3.2. ❌ Rewrite SHA acceptance so the digest is produced by guest execution, not preloaded data.
5.3.3. ❌ Rewrite FreeRTOS acceptance so it proves a real scheduler/task/runtime path.

5.4. ❌ Reach a clean stage where RISC-V, not Forth0, is the primary closure path.
5.4.1. ❌ Keep `C3_RUN` as a research/development branch until it has proof-grade traces.
5.4.2. ❌ Drive project closure through the simpler active path: `LOAD_CODE -> RUN/STEP -> READ_*`.

5.5. ❌ Only after 5.1-5.4, decide whether RV32M belongs in the active path.
5.5.1. ❌ If needed, extend the runtime executor to full required RV32M semantics.
5.5.2. ❌ Otherwise, freeze unsupported instructions explicitly and narrow the project contract.
