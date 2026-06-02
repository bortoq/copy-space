# RV32 Guest I/O Contract (Stage-20)

Status: frozen baseline for three-binary SHA path

## Guest image load contract
- Guest binary bits are loaded by runtime ABI op `LOAD_CODE` (op=7).
- Source address is provided in `ch_a`.
- Guest destination offset (from `G_MEM_BASE`) is provided in `ch_b` (bits).
- Transfer size is provided in `ch_c` (bits).

## Execution contract
- Guest execution control is performed only by runtime ABI ops:
  - `RUN` (op=8): arm/drive bounded execution window.
  - `STEP` (op=9): bounded stepping window.
- Running before successful load is protocol error.

## Readback contract
- Guest-observable state is read only via runtime ABI:
  - `READ_REGS` (op=10): register dump view.
  - `READ_MEM` (op=11): memory window view.
- For SHA-256 canonical check, digest is read from guest memory window at offset `0` from `G_MEM_BASE` for 256 bits.

## Error contract
- `ch_err=1` on ABI operation failure.
- `ch_c` carries error code for failing operation:
  - `1` bounds,
  - `2` alignment,
  - `3` protocol.
