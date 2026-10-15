"""Execute real GCC output beyond the old symbol and relocation limits."""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--diagnostics', type=Path, required=True,
                        help='globals/ and pointers/ with main.c, result.s and framed out.bin')
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    paths = ['tests/fixtures/gcc/copy_link.c'] + ['runtime/gcc/'+name for name in
             ('copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]
    hashes = {}
    for name in paths:
        dest = root/'sources'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dest)
        hashes[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    sources = [str(root/'sources'/name) for name in paths if name.endswith('.c')]
    limits = {'LABEL': 256, 'JUMP': 1024, 'CALL': 64, 'SYMBOL': 80, 'RELOCATION': 80}

    def build(name, overrides=None, sanitize=False):
        capacities = {**limits, **(overrides or {})}
        command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-DCS_COPY_PROGRAM',
                   '-DCS_COPY_RESULT_ADDRESS_BITS=31', '-DCS_COPY_IMAGE_BYTES=8388608',
                   '-DCS_COPY_MEMORY_BYTES=65536', '-DCS_COPY_ASSEMBLY_BYTES=65536',
                   '-I'+str(root/'sources/runtime/gcc')]
        if sanitize:
            command += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-fno-pie', '-no-pie']
        command += ['-DCS_COPY_'+key+'_CAPACITY='+str(value) for key, value in capacities.items()]
        command += sources + ['-o', str(root/name)]
        (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
        subprocess.run(command, check=True, capture_output=True)
        return root/name

    native = build('native')
    sanitizer = build('sanitized', sanitize=True)
    evidence = []
    for name, key, old in [('globals', 'SYMBOL', 12), ('pointers', 'RELOCATION', 64)]:
        folder = root/name
        shutil.copytree(args.diagnostics/name, folder/'compiler-diagnostic')
        assembly = (folder/'compiler-diagnostic/result.s').read_bytes()
        framed = (folder/'compiler-diagnostic/out.bin').read_bytes()
        assert framed[:8] == b'GCCOUT1\0'
        assert struct.unpack_from('<IIII', framed, 8) == (0, 0, 0, len(assembly))
        assert framed[24:] == assembly
        for capacity in (old, 79):
            rejected = build(name+'-limit-'+str(capacity), {key: capacity})
            run = subprocess.run([str(rejected)], input=assembly, capture_output=True)
            assert run.returncode == 2 and not run.stdout
            (folder/('rejected-'+str(capacity)+'.json')).write_text(json.dumps({
                'capacity': capacity, 'exit': run.returncode, 'output_bytes': len(run.stdout)})+'\n')
        run = subprocess.run([str(native)], input=assembly, capture_output=True, check=True)
        assert not run.stderr and len(run.stdout) == 8388608
        image = run.stdout
        (folder/'image.bin').write_bytes(image)
        checked = subprocess.run([str(sanitizer)], input=assembly, capture_output=True,
                                 env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}, timeout=60)
        assert checked.returncode == 0 and not checked.stderr and checked.stdout == image
        command = [str(ROOT/'build/bin/space-256m'), '--ticks', '100000',
                   '--core', str(folder/'image.bin'), '--trace', str(folder/'trace.txt')]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        run = subprocess.run(command, capture_output=True, check=True, timeout=120)
        (folder/'out.bin').write_bytes(run.stdout)
        assert not run.stderr and run.stdout == struct.pack('<I', 3240), (name, run.stdout)
        with (folder/'trace.txt').open('rb') as trace:
            trace.seek(max(0, (folder/'trace.txt').stat().st_size-80))
            assert trace.read().endswith(b' idle\n')
        evidence.append({'case': name, 'result': 3240, 'exact_capacity': 80,
                         'assembly_sha256': hashlib.sha256(assembly).hexdigest(),
                         'image_sha256': hashlib.sha256(image).hexdigest()})
    (root/'evidence.json').write_text(json.dumps({'source_sha256': hashes, 'cases': evidence,
        'sanitizer': 'ASan/UBSan, leak detector disabled under ptrace',
        'scope': 'QEMU compiler diagnostic and native linker; direct copies execute in Space. '
                 'Not GCC execution in Space.'}, indent=2)+'\n')
    print('OK symbols and relocations: two direct results 3240, exact limits and ASan/UBSan')


if __name__ == '__main__':
    main()
