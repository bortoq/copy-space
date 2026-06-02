#!/usr/bin/env python3
"""
RV32M Image Builder v1 — build, validate, and verify RV32M images.
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import time

MAGIC = b"CSRV"
VERSION = 1
HEADER_SIZE = 52


def _magic_bytes():
    return MAGIC


def build_image(payload_bytes, entry_bitaddr, processor_bits, flags=0):
    payload_bits = len(payload_bytes) * 8
    if payload_bits != processor_bits:
        raise ValueError(
            f"payload_bits ({payload_bits}) must equal processor_bits ({processor_bits}) for v1"
        )
    if payload_bits % 8 != 0:
        raise ValueError(f"payload_bits ({payload_bits}) must be byte-aligned")
    payload_sha256 = hashlib.sha256(payload_bytes).digest()
    header = struct.pack(
        '<4s H H I I I 32s',
        MAGIC, VERSION, flags, payload_bits, entry_bitaddr, processor_bits, payload_sha256,
    )
    assert len(header) == HEADER_SIZE
    return header + payload_bytes


def parse_header(data):
    if len(data) < HEADER_SIZE:
        return None
    magic, version, flags, image_bits, entry_bitaddr, processor_bits, payload_sha256 = \
        struct.unpack('<4s H H I I I 32s', data[:HEADER_SIZE])
    return {
        'magic': magic,
        'version': version,
        'flags': flags,
        'image_bits': image_bits,
        'entry_bitaddr': entry_bitaddr,
        'processor_bits': processor_bits,
        'payload_sha256': payload_sha256,
        'payload_offset': HEADER_SIZE,
        'payload_size_bytes': image_bits // 8 if image_bits % 8 == 0 else None,
    }


def validate_image(data, verbose=False):
    errors = []
    h = parse_header(data)
    if h is None:
        return ["truncated header"]

    def err(msg):
        errors.append(msg)
        if verbose:
            print(f"  FAIL: {msg}", file=sys.stderr)

    if h['magic'] != MAGIC:
        err(f"bad magic: got {h['magic']!r}, expected {MAGIC!r}")
    if h['version'] != VERSION:
        err(f"unsupported version: {h['version']}, expected {VERSION}")
    if h['image_bits'] % 8 != 0:
        err(f"image_bits not byte-aligned: {h['image_bits']}")
    if h['image_bits'] != h['processor_bits']:
        err(f"image_bits ({h['image_bits']}) != processor_bits ({h['processor_bits']})")
    max_addr = 1 << 24
    if h['entry_bitaddr'] >= max_addr:
        err(f"entry_bitaddr ({h['entry_bitaddr']}) out of range (max {max_addr})")
    expected_payload_bits = h['image_bits']
    expected_payload_bytes = expected_payload_bits // 8 if expected_payload_bits % 8 == 0 else 0
    actual_payload_bytes = len(data) - HEADER_SIZE
    if actual_payload_bytes < expected_payload_bytes:
        err(f"truncated payload: have {actual_payload_bytes} bytes, need {expected_payload_bytes}")
    if actual_payload_bytes >= expected_payload_bytes:
        payload = data[HEADER_SIZE:HEADER_SIZE + expected_payload_bytes]
        actual_sha = hashlib.sha256(payload).digest()
        if actual_sha != h['payload_sha256']:
            err(f"SHA-256 mismatch: got {actual_sha.hex()}, expected {h['payload_sha256'].hex()}")
    return errors


def image_info(data):
    h = parse_header(data)
    if h is None:
        return "invalid header"
    sha_hex = h['payload_sha256'].hex()
    return (
        f"magic:          {h['magic']!r}\n"
        f"version:        {h['version']}\n"
        f"flags:          0x{h['flags']:04x}\n"
        f"image_bits:     {h['image_bits']} ({h['image_bits']//8} bytes)\n"
        f"entry_bitaddr:  0x{h['entry_bitaddr']:06x}\n"
        f"processor_bits: {h['processor_bits']} ({h['processor_bits']//8} bytes)\n"
        f"payload_sha256: {sha_hex}\n"
        f"total_size:     {len(data)} bytes"
    )


def compute_manifest(data, toolchain="rv32m_image_builder.py", version="1"):
    """Generate a manifest dict for an RV32M image."""
    h = parse_header(data)
    if h is None:
        return None
    expected_payload_bytes = h['image_bits'] // 8
    payload = data[HEADER_SIZE:HEADER_SIZE + expected_payload_bytes]
    header_bytes = data[:HEADER_SIZE]
    full_sha = hashlib.sha256(data).hexdigest()
    return {
        "format": "rv32m_image_manifest",
        "manifest_version": "1",
        "toolchain": toolchain,
        "toolchain_version": version,
        "build_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "image": {
            "magic": h['magic'].decode('ascii'),
            "version": h['version'],
            "flags": h['flags'],
            "image_bits": h['image_bits'],
            "entry_bitaddr": h['entry_bitaddr'],
            "processor_bits": h['processor_bits'],
        },
        "digests": {
            "header_sha256": hashlib.sha256(header_bytes).hexdigest(),
            "payload_sha256": h['payload_sha256'].hex(),
            "full_sha256": full_sha,
        },
    }


def make_negative_vector(variant, entry_bitaddr=0x1000, processor_bits=4608):
    payload_bytes = b'\x00' * (processor_bits // 8)
    if variant == 'bad_magic':
        h = struct.pack('<4s H H I I I 32s', b'BAD ', VERSION, 0, processor_bits,
                        entry_bitaddr, processor_bits, hashlib.sha256(payload_bytes).digest())
        return h + payload_bytes
    elif variant == 'bad_version':
        h = struct.pack('<4s H H I I I 32s', MAGIC, 0xFF, 0, processor_bits,
                        entry_bitaddr, processor_bits, hashlib.sha256(payload_bytes).digest())
        return h + payload_bytes
    elif variant == 'bad_length':
        h = struct.pack('<4s H H I I I 32s', MAGIC, VERSION, 0, processor_bits + 8,
                        entry_bitaddr, processor_bits, hashlib.sha256(payload_bytes).digest())
        return h + payload_bytes
    elif variant == 'bad_sha':
        h = struct.pack('<4s H H I I I 32s', MAGIC, VERSION, 0, processor_bits,
                        entry_bitaddr, processor_bits, b'\x00' * 32)
        return h + payload_bytes
    else:
        raise ValueError(f"unknown variant: {variant}")


def main():
    parser = argparse.ArgumentParser(description='RV32M Image Builder v1')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_build = sub.add_parser('build', help='Build an image from raw payload')
    p_build.add_argument('--payload', required=True)
    p_build.add_argument('--output', '-o', required=True)
    p_build.add_argument('--entry', type=lambda x: int(x, 0), default=0x1000)
    p_build.add_argument('--processor-bits', type=int, default=4608)
    p_build.add_argument('--flags', type=lambda x: int(x, 0), default=0)
    p_build.add_argument('--manifest', help='Output manifest.json path (optional)')

    p_info = sub.add_parser('info', help='Show image metadata')
    p_info.add_argument('image')

    p_val = sub.add_parser('validate', help='Validate an image')
    p_val.add_argument('image')

    p_neg = sub.add_parser('negative', help='Generate a negative test vector')
    p_neg.add_argument('--variant', required=True, choices=['bad_magic', 'bad_version', 'bad_length', 'bad_sha'])
    p_neg.add_argument('--output', '-o', required=True)

    p_sha = sub.add_parser('verify-sha', help='Verify payload SHA-256 against header')
    p_sha.add_argument('image')

    p_manifest = sub.add_parser('manifest', help='Generate manifest for an image')
    p_manifest.add_argument('image')
    p_manifest.add_argument('--output', '-o', required=True)

    p_verify_readback = sub.add_parser('verify-readback', help='Verify image digest after write (readback)')
    p_verify_readback.add_argument('--original', required=True, help='Original .rv32m image')
    p_verify_readback.add_argument('--readback', required=True, help='Readback image (from space dump)')

    args = parser.parse_args()

    if args.cmd == 'build':
        with open(args.payload, 'rb') as f:
            payload = f.read()
        image = build_image(payload, args.entry, args.processor_bits, args.flags)
        with open(args.output, 'wb') as f:
            f.write(image)
        print(f"built {len(image)} bytes -> {args.output}", file=sys.stderr)
        if args.manifest:
            manifest = compute_manifest(image)
            with open(args.manifest, 'w') as f:
                json.dump(manifest, f, indent=2)
            print(f"manifest -> {args.manifest}", file=sys.stderr)

    elif args.cmd == 'info':
        with open(args.image, 'rb') as f:
            data = f.read()
        print(image_info(data))

    elif args.cmd == 'validate':
        with open(args.image, 'rb') as f:
            data = f.read()
        errors = validate_image(data, verbose=True)
        if errors:
            print(f"FAIL: {len(errors)} error(s)", file=sys.stderr)
            sys.exit(1)
        else:
            print("OK: image is valid", file=sys.stderr)

    elif args.cmd == 'negative':
        image = make_negative_vector(args.variant)
        with open(args.output, 'wb') as f:
            f.write(image)
        print(f"negative vector '{args.variant}' -> {args.output} ({len(image)} bytes)", file=sys.stderr)

    elif args.cmd == 'verify-sha':
        with open(args.image, 'rb') as f:
            data = f.read()
        h = parse_header(data)
        if h is None:
            print("FAIL: invalid header", file=sys.stderr)
            sys.exit(1)
        expected_payload_bytes = h['image_bits'] // 8
        payload = data[HEADER_SIZE:HEADER_SIZE + expected_payload_bytes]
        actual_sha = hashlib.sha256(payload).digest()
        if actual_sha == h['payload_sha256']:
            print("OK: SHA-256 matches", file=sys.stderr)
        else:
            print(f"FAIL: SHA-256 mismatch", file=sys.stderr)
            print(f"  got:      {actual_sha.hex()}", file=sys.stderr)
            print(f"  expected: {h['payload_sha256'].hex()}", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == 'manifest':
        with open(args.image, 'rb') as f:
            data = f.read()
        manifest = compute_manifest(data)
        if manifest is None:
            print("FAIL: invalid image", file=sys.stderr)
            sys.exit(1)
        with open(args.output, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f"manifest -> {args.output}", file=sys.stderr)

    elif args.cmd == 'verify-readback':
        with open(args.original, 'rb') as f:
            orig = f.read()
        with open(args.readback, 'rb') as f:
            readback = f.read()
        # Compare full digests
        orig_sha = hashlib.sha256(orig).hexdigest()
        readback_sha = hashlib.sha256(readback).hexdigest()
        if orig_sha == readback_sha:
            print("OK: readback matches original", file=sys.stderr)
        else:
            print(f"FAIL: readback digest mismatch", file=sys.stderr)
            print(f"  original: {orig_sha}", file=sys.stderr)
            print(f"  readback: {readback_sha}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
