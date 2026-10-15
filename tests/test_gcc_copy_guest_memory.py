"""Run the memory-aware C linker in Space; compiler output is an explicit input."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/rv32i'))
from build import build
from space_segments import execute_segments


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def direct(image, folder, expected, memory_bytes):
    folder.mkdir()
    (folder/'image.bin').write_bytes(image)
    command = [str(ROOT/'build/bin/space'), '--ticks', '100000', '--core',
        str(folder/'image.bin'), '--trace', str(folder/'trace.txt'),
        '--dump-space', str(folder/'space.bin')]
    (folder/'command.json').write_text(json.dumps(command)+'\n')
    result = subprocess.run(command, capture_output=True, check=True, timeout=120)
    (folder/'out.bin').write_bytes(result.stdout)
    assert not result.stderr and result.stdout == (b'' if expected is None else struct.pack('<I', expected))
    raw = (folder/'space.bin').read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
    if expected is not None:
        assert word(32768) == word(32800) == memory_bytes
    assert (folder/'trace.txt').read_bytes().endswith(b' idle\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--assembly', type=Path)
    parser.add_argument('--expected-result', type=lambda value: int(value, 0), default=7)
    parser.add_argument('--expect-trap', action='store_true', help='expect idle termination without OUT')
    parser.add_argument('--memory-bytes', type=int, default=65536)
    parser.add_argument('--compiler')
    parser.add_argument('--newlib', type=Path)
    parser.add_argument('--emulator', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--segment-ticks', type=int, default=1000000)
    parser.add_argument('--timeout', type=float, default=1800)
    args = parser.parse_args()
    if args.expect_trap:
        args.expected_result = None
    if args.segment_ticks < 1:
        parser.error('--segment-ticks must be positive')
    root = args.artifacts.resolve()
    if not args.resume:
        if not args.assembly or not args.newlib:
            parser.error('initial execution requires --assembly and --newlib')
        root.mkdir(parents=True, exist_ok=False)
        names = ['tests/fixtures/gcc/copy_link.c'] + ['runtime/gcc/'+name for name in
            ('copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]
        for name in names:
            dest = root/'sources'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, dest)
        hashes = {name: digest(root/'sources'/name) for name in names}
        sources = [root/'sources'/name for name in names if name.endswith('.c')]
        flags = ['-DCS_COPY_PROGRAM', '-DCS_COPY_MEMORY_BYTES='+str(args.memory_bytes),
            '-DCS_COPY_RESULT_ADDRESS_BITS=24', '-I'+str(root/'sources/runtime/gcc')]
        command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror'] + flags + [str(p) for p in sources] + ['-o', str(root/'native')]
        (root/'native-command.json').write_text(json.dumps(command)+'\n')
        subprocess.run(command, capture_output=True, check=True)
        assembly = args.assembly.read_bytes()
        (root/'input.s').write_bytes(assembly)
        native = subprocess.run([str(root/'native')], input=assembly, capture_output=True, check=True)
        assert not native.stderr and len(native.stdout) == 262144
        (root/'expected.bin').write_bytes(native.stdout)
        direct(native.stdout, root/'native-result', args.expected_result, args.memory_bytes)
        prefix = args.newlib.resolve()/'riscv64-unknown-elf'
        build(sources, root/'linker.stream', compiler=args.compiler, stream=True,
            optimization='-O2', memory_bytes=1048576, space_bytes=67108864,
            extra_cflags=flags+['-DCS_RUNTIME_EXTERNAL_MEMORY', '-isystem', str(prefix/'include'),
                '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections'],
            extra_libraries=['-Wl,--start-group', str(prefix/'lib/libc.a'), '-lgcc', '-Wl,--end-group'])
        (root/'in.bin').write_bytes((root/'linker.stream').read_bytes()+assembly)
        emulator = args.emulator.resolve() if args.emulator else ROOT/'build/bin/space-64m'
        shutil.copyfile(emulator, root/'emulator')
        (root/'emulator').chmod(0o755)
        evidence = {'scope': 'C linker in Space with explicit data/stack memory; compiler execution is not covered',
            'pending': True, 'source_sha256': hashes, 'memory_bytes': args.memory_bytes,
            'expected_result': args.expected_result, 'segment_ticks': args.segment_ticks,
            'input_sha256': digest(root/'in.bin'), 'assembly_sha256': digest(root/'input.s'),
            'expected_image_sha256': digest(root/'expected.bin'), 'emulator_sha256': digest(root/'emulator')}
        (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    else:
        if args.assembly or args.emulator:
            parser.error('resume uses frozen assembly and emulator')
        evidence = json.loads((root/'evidence.json').read_text())
        assert evidence['pending'], 'execution already completed'
    for name, expected in evidence['source_sha256'].items():
        assert digest(root/'sources'/name) == expected, 'changed frozen source'
    for name, key in [('in.bin', 'input_sha256'), ('input.s', 'assembly_sha256'),
                      ('expected.bin', 'expected_image_sha256'), ('emulator', 'emulator_sha256')]:
        assert digest(root/name) == evidence[key], 'changed '+name
    assert (root/'in.bin').read_bytes() == (root/'linker.stream').read_bytes()+(root/'input.s').read_bytes(), 'changed stream/input pairing'
    manifest = json.loads((root/'linker.stream.json').read_text())
    execution = execute_segments(root/'emulator', root/'space', root/'in.bin',
        space_bytes=manifest['space_bytes'], layer_bytes=manifest['layer_bits']//8,
        ticks=evidence['segment_ticks'], timeout=args.timeout, compression='zstd',
        channels_only=True, resume=args.resume)
    output = (root/'space/program.in').read_bytes()
    assert output == (root/'expected.bin').read_bytes()
    raw = (root/'space/space.bin').read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
    assert word(132128) == 10 and word(132160) == 0
    direct(output, root/'guest-result', evidence['expected_result'], evidence['memory_bytes'])
    evidence.update({'pending': False, 'guest_exit': 0, 'guest_execution': execution,
        'guest_direct_result': evidence['expected_result']})
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK guest linker memory:', evidence['memory_bytes'], 'bytes;', execution['copy_events'],
        'copies; direct result', evidence['expected_result'], flush=True)


if __name__ == '__main__':
    main()
