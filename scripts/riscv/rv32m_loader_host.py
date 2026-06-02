#!/usr/bin/env python3
"""
RV32M Host-side Loader CLI v1 — load an RV32M image into a space image and run it.

Usage:
  python3 rv32m_loader_host.py load --image test.rv32m --space base.bin --output loaded.bin
  python3 rv32m_loader_host.py run  --image test.rv32m --space base.bin [--life N]
"""

import argparse
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

from rv32m_image_builder import (
    HEADER_SIZE, MAGIC, VERSION, build_image, parse_header, validate_image
)


def load_image_into_space(image_path, space_path, output_path, entry_offset=0):
    """
    Load an RV32M image into a space image.
    
    1. Validates the .rv32m image
    2. Extracts payload (processor layer)
    3. Writes payload into space at addr = entry_offset (must point to processor area)
    4. Updates boot loader
    
    For v1: payload == processor_layer, written at processor_start (bitaddr 0).
    """
    # Read and validate the image
    with open(image_path, 'rb') as f:
        img_data = f.read()
    
    errors = validate_image(img_data)
    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        return False
    
    h = parse_header(img_data)
    payload_bytes = h['image_bits'] // 8
    payload = img_data[HEADER_SIZE:HEADER_SIZE + payload_bytes]
    entry_bitaddr = h['entry_bitaddr'] + entry_offset
    
    # Read space image
    with open(space_path, 'rb') as f:
        space = bytearray(f.read())
    
    space_bytes = len(space)
    space_bits = space_bytes * 8
    
    # Check sizes
    if payload_bytes * 8 > space_bits:
        print(f"ERROR: payload ({payload_bytes} bytes) exceeds space ({space_bytes} bytes)", file=sys.stderr)
        return False
    
    # Compute VM parameters the same way space.c does
    import math
    raw = math.ceil(math.log2(space_bits))
    addr_bits = (raw + 7) & ~7
    if addr_bits < 8: addr_bits = 8
    n_bits = addr_bits
    instr_bits = 3 * addr_bits
    
    # Default processor_n = 64
    processor_n = 64
    processor_bits = processor_n * instr_bits
    
    # Check that payload size matches processor_bits
    if payload_bytes * 8 != processor_bits:
        print(f"ERROR: payload bits ({payload_bytes*8}) != processor_bits ({processor_bits})", file=sys.stderr)
        return False
    
    # Write payload into space at processor_start (bit 0)
    payload_bit_offset = 0  # processor_start is always 0
    payload_byte_start = payload_bit_offset // 8
    
    if payload_byte_start + payload_bytes > space_bytes:
        print(f"ERROR: payload doesn't fit in space", file=sys.stderr)
        return False
    
    # Copy payload bytes into space
    space[payload_byte_start:payload_byte_start + payload_bytes] = payload
    
    # The payload contains the processor layer (copy instructions).
    # For the boot loader to work, we need to set entry_bitaddr in the
    # processor as the next layer pointer.
    # 
    # Method: use the last instruction slot to load the next layer.
    # For a direct-load, we write a simple boot at the last slot:
    #   slot N-1: copy PROCESSOR_BITS, dst=0, src=0 (self-loop)
    # and set entry_bitaddr to where execution should start.
    #
    # Since the payload IS the processor layer already at the processor area,
    # all slots are already filled. No boot loader needed for direct load.
    
    # Write the output
    with open(output_path, 'wb') as f:
        f.write(space)
    
    print(f"Loaded {payload_bytes} bytes payload (entry=0x{entry_bitaddr:06x}) -> {output_path}", file=sys.stderr)
    return True


def run_loaded_space(space_path, life=1000000, stdin_data=b''):
    """
    Run a loaded space image using build/bin/vmrun.
    """
    vmrun = 'build/bin/vmrun'
    if not os.path.exists(vmrun):
        print(f"ERROR: {vmrun} not found (run 'make bins' first)", file=sys.stderr)
        return False
    
    cmd = [vmrun, '--image', space_path, '--life', str(life)]
    
    proc = subprocess.run(cmd, input=stdin_data, capture_output=True)
    
    stderr_text = proc.stderr.decode('utf-8', errors='replace')
    print(stderr_text, file=sys.stderr, end='')
    print(proc.stdout.decode('utf-8', errors='replace'), end='')
    
    return proc.returncode


def main():
    parser = argparse.ArgumentParser(description='RV32M Host-side Loader v1')
    sub = parser.add_subparsers(dest='cmd', required=True)
    
    # load
    p_load = sub.add_parser('load', help='Load RV32M image into space image')
    p_load.add_argument('--image', required=True, help='.rv32m image to load')
    p_load.add_argument('--space', required=True, help='Base space image (.bin)')
    p_load.add_argument('--output', '-o', required=True, help='Output space image')
    p_load.add_argument('--entry-offset', type=lambda x: int(x, 0), default=0,
                        help='Entry offset (for chaining)')
    
    # run
    p_run = sub.add_parser('run', help='Load and run an RV32M image')
    p_run.add_argument('--image', required=True, help='.rv32m image to load')
    p_run.add_argument('--space', required=True, help='Base space image (.bin)')
    p_run.add_argument('--life', type=int, default=1000000, help='Max VM ticks')
    p_run.add_argument('--keep', action='store_true', help='Keep temp files')
    
    args = parser.parse_args()
    
    if args.cmd == 'load':
        success = load_image_into_space(args.image, args.space, args.output, args.entry_offset)
        sys.exit(0 if success else 1)
    
    elif args.cmd == 'run':
        tmpdir = tempfile.mkdtemp(prefix='rv32m_run_')
        loaded = os.path.join(tmpdir, 'loaded.bin')
        success = load_image_into_space(args.image, args.space, loaded)
        if not success:
            if not args.keep:
                import shutil
                shutil.rmtree(tmpdir)
            sys.exit(1)
        
        rc = run_loaded_space(loaded, args.life)
        
        if args.keep:
            print(f"Temp files in: {tmpdir}", file=sys.stderr)
        else:
            import shutil
            shutil.rmtree(tmpdir)
        
        sys.exit(rc)


if __name__ == '__main__':
    main()
