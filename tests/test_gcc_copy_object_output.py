"""Check uploaded copy objects through the guest GCC adapter (mock cc1)."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/rv32i'))
from build import build
from space_segments import execute_segments
from test_gcc_copy_output import job, decode, direct


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--guest', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--compiler')
    parser.add_argument('--newlib', type=Path)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    options = ['--space-program=result.s', '--space-entry=value', '--space-arg=3', '--space-arg=4']
    if not args.resume:
        root.mkdir(parents=True, exist_ok=False)
        names = ['tests/fixtures/gcc/copy_output.c']+['runtime/gcc/'+name for name in
            ('main.c', 'job.c', 'job.h', 'files.c', 'files.h', 'response.c', 'response.h',
             'copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h', 'syscalls.c', 'start.S', 'link.ld')]
        names += ['runtime/copy_c/input_files.h', 'runtime/rv32i/copy_space.h', 'runtime/rv32i/runtime.c']
        for name in names:
            dest = root/'sources'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, dest)
        shutil.copyfile(__file__, root/'run.py')
        sources = [root/'sources'/name for name in names if name.endswith('.c') and
                   not name.endswith(('syscalls.c', 'runtime.c'))]
        flags = ['-DCS_GCC_FRAMED_OUTPUT', '-DCS_GCC_COPY_OUTPUT', '-Wl,--wrap=main',
                 '-I'+str(root/'sources/runtime/gcc'), '-I'+str(root/'sources/runtime/rv32i')]

        def prepare(name, sanitize=False):
            command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror']+flags
            if sanitize:
                command += ['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
            command += list(map(str, sources))+['-o', str(root/name)]
            (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
            subprocess.run(command, capture_output=True, check=True)

        prepare('native')
        prepare('sanitized', True)
        root_unit = (b'.data; counter: .long 5; .text; .global value; value: '
            b'copy.jsra helper; copy.jsra external; copy.lda.l $r1,counter; copy.add $r0,$r1; copy.ret; '
            b'helper: copy.inc $r0,1; copy.ret\n')
        library_unit = (b'.data; counter: .long 9; .text; .global external; external: '
            b'copy.jsra helper; copy.lda.l $r1,counter; copy.add $r0,$r1; '
            b'copy.lda.l $r1,shared; copy.add $r0,$r1; copy.ret; helper: copy.inc $r0,2; copy.ret\n')
        shared_unit = b'.data; .global shared; shared: .long 7\n'
        add = b'.global value; value: copy.add $r0,$r1; copy.ret\n'
        helper = b'.global helper; helper: copy.add $r0,$r1; copy.ret\n'
        cases = [
            ('single', add, [], [], 7),
            ('call', b'.global value; value: copy.jsra helper; copy.ret\n',
             [('lib/helper.s', helper)], ['--space-object=./lib/../lib/helper.s'], 7),
            ('scoped-data', root_unit, [('lib/code.s', library_unit), ('data.s', shared_unit)],
             ['--space-object=lib/code.s', '--space-object=data.s'], 27),
            ('empty-main', b'', [('entry.s', add)], ['--space-object=entry.s'], 7),
            ('empty-object', add, [('empty.s', b'')], ['--space-object=empty.s'], 7),
            ('weak', b'.global value; value: copy.jsra helper; copy.ret\n',
             [('weak.s', b'.weak helper; helper: copy.inc $r0,10; copy.ret\n'),
              ('strong.s', b'.global helper; helper: copy.inc $r0,100; copy.ret\n')],
             ['--space-object=weak.s', '--space-object=strong.s'], 103),
            ('numeric', b'.global value; value: copy.jmpa 1f; 1: copy.jsra helper; copy.ret\n',
             [('helper.s', b'.global helper; helper: copy.jmpa 1f; 1: copy.add $r0,$r1; copy.ret\n')],
             ['--space-object=helper.s'], 7),
            ('maximum', b'.global value; value: '+b''.join(
                f'copy.jsra helper{i}; '.encode() for i in range(7))+b'copy.ret\n',
             [(f'helper{i}.s', f'.global helper{i}; helper{i}: copy.inc $r0,1; copy.ret\n'.encode()) for i in range(7)],
             [f'--space-object=helper{i}.s' for i in range(7)], 10)]
        results = []
        for name, assembly, files, extra, expected in cases:
            folder = root/name
            folder.mkdir()
            incoming = job(assembly, options+extra, files)
            (folder/'job.bin').write_bytes(incoming)
            result = subprocess.run([str(root/'native')], input=incoming, capture_output=True, check=True)
            (folder/'response.bin').write_bytes(result.stdout)
            assert not result.stderr
            code, stdout, stderr, image = decode(result.stdout)
            assert code == 0 and not stdout and not stderr and len(image) == 262144
            checked = subprocess.run([str(root/'sanitized')], input=incoming, capture_output=True,
                                    env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}, timeout=60)
            assert checked.returncode == 0 and not checked.stderr and checked.stdout == result.stdout
            direct(image, folder/'direct', expected)
            assert (folder/'direct/trace.txt').read_bytes().endswith(b' idle\n')
            results.append({'name': name, 'result': expected, 'image_sha256': hashlib.sha256(image).hexdigest()})
        invalid = [
            ('missing', add, [], ['--space-object=missing.s']),
            ('directory', add, [('lib/x.s', helper)], ['--space-object=lib']),
            ('nul', add, [('bad.s', b'\0')], ['--space-object=bad.s']),
            ('duplicate', add, [('duplicate.s', add)], ['--space-object=duplicate.s']),
            ('undefined', b'.global value; value: copy.jsra helper; copy.ret\n',
             [('helper.s', b'.global helper; helper: copy.jsra absent; copy.ret\n')], ['--space-object=helper.s']),
            ('same-file', add, [], ['--space-object=result.s'])]
        for name, assembly, files, extra in invalid:
            incoming = job(assembly, options+extra, files)
            (root/('invalid-'+name+'.bin')).write_bytes(incoming)
            for executable in ('native', 'sanitized'):
                failed = subprocess.run([str(root/executable)], input=incoming, capture_output=True,
                    env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
                code, stdout, stderr, image = decode(failed.stdout)
                assert failed.returncode == code == 126 and not stdout and stderr and not image
                assert not failed.stderr
                (root/('invalid-'+name+'-'+executable+'.response')).write_bytes(failed.stdout)
        for extra in (['--space-object='], ['--space-object=x.s']*8):
            failed = subprocess.run([str(root/'native')], input=job(add, options+extra), capture_output=True)
            assert failed.returncode == 125 and not failed.stdout
        failed = subprocess.run([str(root/'native')], input=job(add,
            ['--space-copy=result.s', '--space-object=x.s']), capture_output=True)
        assert failed.returncode == 125 and not failed.stdout
        evidence = {'scope': __doc__, 'source_sha256': {name: digest(root/'sources'/name) for name in names},
            'direct_cases': results, 'rejected_links': len(invalid), 'rejected_options': 3, 'pending': args.guest}
        (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
        if not args.guest:
            print('OK object adapter: eight direct cases, nine rejections and ASan/UBSan; mock cc1')
            return
        if not args.newlib:
            parser.error('--guest requires --newlib')
        prefix = args.newlib.resolve()/'riscv64-unknown-elf'
        manifest = build(sources+[root/'sources/runtime/gcc/syscalls.c'], root/'program.stream',
            compiler=args.compiler, stream=True, memory_bytes=4194304, space_bytes=67108864,
            extra_cflags=flags+['-DCS_RUNTIME_EXTERNAL_MEMORY', '-DCS_GCC_MEMORY_BYTES=4194304',
                '-DCS_GCC_HEAP_BYTES=2097152', '-isystem', str(prefix/'include'),
                '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections'],
            extra_libraries=['-Wl,--start-group', str(prefix/'lib/libc.a'), '-lgcc', '-Wl,--end-group'],
            startup=root/'sources/runtime/gcc/start.S', linker_script=root/'sources/runtime/gcc/link.ld')
        (root/'in.bin').write_bytes((root/'program.stream').read_bytes()+(root/'scoped-data/job.bin').read_bytes())
        shutil.copyfile(ROOT/'build/bin/space-64m', root/'emulator')
        (root/'emulator').chmod(0o755)
        evidence.update(input_sha256=digest(root/'in.bin'), emulator_sha256=digest(root/'emulator'))
        (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    else:
        evidence = json.loads((root/'evidence.json').read_text())
        assert evidence['pending']
        for name, expected in evidence['source_sha256'].items():
            assert digest(root/'sources'/name) == expected
        assert digest(root/'in.bin') == evidence['input_sha256']
        assert digest(root/'emulator') == evidence['emulator_sha256']
        manifest = json.loads((root/'program.stream.json').read_text())
    execution = execute_segments(root/'emulator', root/'space', root/'in.bin',
        space_bytes=manifest['space_bytes'], layer_bytes=manifest['layer_bits']//8,
        ticks=1000000, timeout=1800, channels_only=True, resume=args.resume)
    packet = (root/'space/program.in').read_bytes()
    assert packet == (root/'scoped-data/response.bin').read_bytes()
    raw = (root/'space/space.bin').read_bytes()
    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
    assert word(132128) == 10 and word(132160) == 0
    direct(decode(packet)[3], root/'guest-direct', 27)
    evidence.update(pending=False, guest_exit=0, guest_direct_result=27, guest_execution=execution)
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK object adapter inside Space: three input units, direct result 27; mock cc1')


if __name__ == '__main__':
    main()
