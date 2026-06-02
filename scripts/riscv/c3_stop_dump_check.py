#!/usr/bin/env python3
import argparse
from pathlib import Path


def u32be(b):
    return int.from_bytes(b, 'big')


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate C3 stop-dump ABI block')
    ap.add_argument('--bin', required=True)
    ap.add_argument('--allowed-reasons', default='1,2,3,4,5')
    ap.add_argument('--expect-reason', type=int)
    args = ap.parse_args()

    p = Path(args.bin)
    data = p.read_bytes()
    if len(data) < 20:
        raise SystemExit(f'FAIL: stop dump too short: {len(data)} < 20')

    reason = data[0]
    guest_pc = u32be(data[1:5])
    instr = u32be(data[5:9])
    fault_addr = u32be(data[9:13])
    steps = u32be(data[13:17])
    reserved = data[17:20]

    allowed = {int(x) for x in args.allowed_reasons.split(',') if x}
    if reason not in allowed:
        raise SystemExit(f'FAIL: invalid reason={reason}; allowed={sorted(allowed)}')
    if args.expect_reason is not None and reason != args.expect_reason:
        raise SystemExit(f'FAIL: reason mismatch got={reason} exp={args.expect_reason}')
    if reserved != b'\x00\x00\x00':
        raise SystemExit(f'FAIL: reserved bytes must be zero, got={reserved.hex()}')
    if guest_pc % 4 != 0:
        raise SystemExit(f'FAIL: guest_pc must be 4-byte aligned, got={guest_pc}')

    # Minimal path-specific sanity checks.
    if reason == 4 and fault_addr == 0:
        raise SystemExit('FAIL: memory fault requires non-zero fault_addr')
    if reason in (1, 2, 3) and steps == 0:
        raise SystemExit(f'FAIL: reason={reason} expects steps>0')

    print(f'OK c3_stop_dump_check reason={reason} pc={guest_pc} instr=0x{instr:08x} fault=0x{fault_addr:08x} steps={steps}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
