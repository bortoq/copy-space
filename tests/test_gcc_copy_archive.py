"""Exercise demand-driven copy assembly archives through the GCC guest adapter.

The fixture uses mock cc1; compilation of C is covered separately.
"""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

from test_gcc_copy_output import job, decode, direct
from test_gcc_copy_object_output import ROOT
import sys
sys.path.insert(0, str(ROOT/'scripts/rv32i'))
from build import build
from space_segments import execute_segments


def archive(members):
    result = b'!<arch>\n'
    for name, data in members:
        name = name.encode() if isinstance(name, str) else name
        assert len(name) <= 16
        result += (name.ljust(16)+b'0'.ljust(12)+b'0'.ljust(6)+b'0'.ljust(6)+
                   b'100644'.ljust(8)+str(len(data)).encode().ljust(10)+b'`\n'+data)
        if len(data) & 1:
            result += b'\n'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--guest', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--compiler')
    parser.add_argument('--newlib', type=Path)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    if args.resume:
        assert args.guest, '--resume requires --guest'
        evidence = json.loads((root/'evidence.json').read_text())
        assert evidence['guest_pending']
        for name, expected in evidence['sources_sha256'].items():
            assert hashlib.sha256((root/'sources'/name).read_bytes()).hexdigest() == expected
    else:
        root.mkdir(parents=True, exist_ok=False)
        names = ['tests/fixtures/gcc/copy_output.c']+['runtime/gcc/'+n for n in
                 ('main.c', 'job.c', 'job.h', 'files.c', 'files.h', 'response.c', 'response.h',
                  'copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h', 'syscalls.c', 'start.S', 'link.ld')]
        names += ['runtime/copy_c/input_files.h', 'runtime/rv32i/copy_space.h', 'runtime/rv32i/runtime.c']
        for name in names:
            dest = root/'sources'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, dest)
        shutil.copyfile(__file__, root/'run.py')
        sources = [root/'sources'/n for n in names if n.endswith('.c') and not n.endswith(('syscalls.c', 'runtime.c'))]
        flags = ['-DCS_GCC_FRAMED_OUTPUT', '-DCS_GCC_COPY_OUTPUT', '-Wl,--wrap=main',
                 '-I'+str(root/'sources/runtime/gcc'), '-I'+str(root/'sources/runtime/rv32i')]
        for executable in ('native', 'sanitized', 'native-wide', 'sanitized-wide'):
            command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror']+flags
            if executable.startswith('sanitized'):
                command += ['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
            if executable.endswith('-wide'):
                command += ['-DCS_GCC_COPY_PROGRAM_BYTES=2097152', '-DCS_COPY_LABEL_CAPACITY=512',
                            '-DCS_COPY_JUMP_CAPACITY=1024', '-DCS_COPY_CALL_CAPACITY=128']
            command += list(map(str, sources))+['-o', str(root/executable)]
            (root/(executable+'-command.json')).write_text(json.dumps(command)+'\n')
            subprocess.run(command, check=True, capture_output=True)
        options = ['--space-program=result.s', '--space-entry=value', '--space-arg=3', '--space-arg=4']
        caller = b'.global value; value: copy.jsra helper; copy.ret\n'
        add = b'.global value; value: copy.add $r0,$r1; copy.ret\n'
        helper = b'.global helper; helper: copy.inc $r0,2; copy.ret\n'
        dependency = b'.global helper; helper: copy.jsra base; copy.inc $r0,2; copy.ret\n'
        base = b'.global base; base: copy.add $r0,$r1; copy.ret\n'
        unused = b'.global unused; unused: copy.unsupported $r0; copy.jsra absent; copy.ret\n'
        weak_caller = b'.weak helper; .global value; value: copy.ldi.l $r0,helper; copy.ret\n'
        cases = [
            ('empty', add, [], [], 7),
            ('extract', caller, [('helper.s/', helper)], [helper], 5),
            ('unused', caller, [('unused.s/', unused), ('helper.s/', helper)], [helper], 5),
            ('transitive', caller, [('base.s/', base), ('helper.s/', dependency)], [dependency, base], 9),
            ('forward', caller, [('helper.s/', dependency), ('base.s/', base)], [dependency, base], 9),
            ('first-definition', caller, [('first.s/', helper), ('second.s/', helper.replace(b',2', b',8'))], [helper], 5),
            ('provided', caller+helper, [('bad.s/', helper.replace(b',2', b',8'))], [], 5),
            ('private', caller+b'helper: copy.inc $r0,1; copy.ret\n', [('helper.s/', helper)], [], 4),
            ('weak-import', weak_caller, [('helper.s/', helper)], [], 0),
            ('weak-definition', caller+b'.weak helper; helper: copy.inc $r0,1; copy.ret\n', [('helper.s/', helper)], [], 4),
            ('weak-export', caller, [('weak.s/', b'.weak helper; helper: copy.inc $r0,2; copy.ret\n')],
             [b'.weak helper; helper: copy.inc $r0,2; copy.ret\n'], 5),
            ('common-supplied', b'.comm shared,4,4; .global value; value: copy.lda.l $r0,shared; copy.ret\n',
             [('shared.s/', b'.global shared; .data; shared: .long 17\n')], [], 0),
            ('common-extracted', b'.global value; value: copy.lda.l $r0,shared; copy.ret\n',
             [('shared.s/', b'.comm shared,4,4\n')], [b'.comm shared,4,4\n'], 0),
            ('entry', b'', [('entry.s/', add)], [add], 7),
            ('metadata', caller, [('/', b'\0index'), ('//', b'long-filename.s/\n'), ('/0', helper)], [helper], 5),
            ('sym64', caller, [('/SYM64/', b'\0index'), ('x/', helper)], [helper], 5),
            ('bsd', caller, [('#1/20', b'long-helper-name.s\0\0'+helper)], [helper], 5),
            ('bsd-index', caller, [('#1/12', b'__.SYMDEF\0\0\0'+b'\0index'), ('x/', helper)], [helper], 5),
            ('empty-member', caller, [('empty.s/', b''), ('helper.s/', helper)], [helper], 5),
            ('maximum-members', caller, [(f'u{i}/', b'') for i in range(255)]+[('helper.s/', helper)], [helper], 5),
            ('cycle', caller, [('base.s/', b'.global base; base: copy.ret\n.data; .long helper\n'),
                               ('helper.s/', dependency)],
             [dependency, b'.global base; base: copy.ret\n.data; .long helper\n'], 5),
            ('data-reference', b'.global value; value: copy.lda.l $r2,ptr; copy.ld.l $r0,0($r2); copy.ret\n.data; ptr: .long shared\n',
             [('shared.s/', b'.data; .global shared; shared: .long 17\n')],
             [b'.data; .global shared; shared: .long 17\n'], 17),
            ('difference-reference', b'.global value; value: copy.lda.l $r0,delta; copy.ret\n'
             b'.data; delta: .long high-(low)\n',
             [('low.s/', b'.data; .global low; low: .byte 1; .space 8\n'),
              ('high.s/', b'.data; .global high; high: .long 0\n')],
             [b'.data; .global low; low: .byte 1; .space 8\n',
              b'.data; .global high; high: .long 0\n'], 9),
        ]
        chain = [(f'f{i}.s/', (f'.global f{i}; f{i}: copy.jsra f{i+1}; copy.inc $r0,1; copy.ret\n'
                               if i<6 else '.global f6; f6: copy.inc $r0,1; copy.ret\n').encode()) for i in range(7)]
        cases.append(('maximum-selected', b'.global value; value: copy.jsra f0; copy.ret\n',
                      chain[::-1], [unit for _, unit in chain], 10))
        alias_unit = b'.global helper; .set helper,private; private: copy.inc $r0,2; copy.ret\n'
        cases.append(('alias', caller, [('alias.s/', alias_unit)], [alias_unit], 5))
        for total in (12, 16, 64):
            units = []
            for i in range(total-1):
                body = (f'.global f{i}; f{i}: copy.jsra f{i+1}; copy.inc $r0,1; copy.ret\n' if i<total-2 else
                        f'.global f{i}; f{i}: copy.jmpa 1f; 1: copy.jmpa private; private: copy.inc $r0,1; copy.ret\n')
                units.append((f'f{i}.s/', body.encode()))
            cases.append((f'late-locals-{total}', b'.global value; value: copy.jsra f0; copy.ret\n',
                          units, [unit for _, unit in units], total+2))
        results = []
        for name, assembly, members, extracted, expected in cases:
            folder = root/name
            folder.mkdir()
            library = archive(members)
            incoming = job(assembly, options+['--space-library=lib/libgcc.a'], [('lib/libgcc.a', library)])
            (folder/'job.bin').write_bytes(incoming)
            wide = name in ('late-locals-16', 'late-locals-64')
            result = subprocess.run([str(root/('native-wide' if wide else 'native'))], input=incoming, capture_output=True, check=True)
            assert not result.stderr
            code, stdout, stderr, image = decode(result.stdout)
            assert not code and not stdout and not stderr and len(image) == (2097152 if wide else 262144)
            if len(extracted) <= 7:
                explicit_options = options+[f'--space-object=unit{i}.s' for i in range(len(extracted))]
                explicit = subprocess.run([str(root/'native')], input=job(assembly, explicit_options,
                    [(f'unit{i}.s', unit) for i, unit in enumerate(extracted)]), capture_output=True, check=True)
                assert explicit.stdout == result.stdout, name
            sanitized = subprocess.run([str(root/('sanitized-wide' if wide else 'sanitized'))], input=incoming, capture_output=True,
                env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
            assert sanitized.returncode == 0 and not sanitized.stderr and sanitized.stdout == result.stdout, sanitized.stderr
            (folder/'response.bin').write_bytes(result.stdout)
            direct(image, folder/'direct', expected)
            assert (folder/'direct/trace.txt').read_bytes().endswith(b' idle\n')
            results.append({'name': name, 'result': expected, 'sha256': hashlib.sha256(image).hexdigest()})
        # References introduced by an explicit additional object also extract members.
        folder = root/'mixed-inputs'
        folder.mkdir()
        unit = b'.global imported; imported: copy.jsra helper; copy.inc $r0,1; copy.ret\n'
        assembly = b'.global value; value: copy.jsra imported; copy.ret\n'
        incoming = job(assembly, options+['--space-object=unit.s', '--space-library=lib.a'],
                       [('unit.s', unit), ('lib.a', archive([('helper.s/', helper)]))])
        (folder/'job.bin').write_bytes(incoming)
        result = subprocess.run([str(root/'native')], input=incoming, capture_output=True, check=True)
        explicit = subprocess.run([str(root/'native')], input=job(assembly,
            options+['--space-object=unit.s', '--space-object=helper.s'], [('unit.s', unit), ('helper.s', helper)]),
            capture_output=True, check=True)
        assert not result.stderr and result.stdout == explicit.stdout
        sanitized = subprocess.run([str(root/'sanitized')], input=incoming, capture_output=True,
            env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
        assert sanitized.returncode == 0 and not sanitized.stderr and sanitized.stdout == result.stdout
        (folder/'response.bin').write_bytes(result.stdout)
        direct(decode(result.stdout)[3], folder/'direct', 6)
        results.append({'name': 'mixed-inputs', 'result': 6,
                        'sha256': hashlib.sha256(decode(result.stdout)[3]).hexdigest()})
        valid = archive([('x/', helper)])
        invalid = [b'', b'!<thin>\n', b'!<arch>\nx', valid[:-1], valid[:66]+b'xx'+valid[68:],
                   valid[:56]+b'9999999999'+valid[66:], valid[:56]+b'-1        '+valid[66:],
                   valid[:56]+b'1x        '+valid[66:], archive([('x/', b'\0')]),
                   archive([('#1/99', b'short')]), archive([('x/', b'.weakref alias,other\n')]),
                   archive([(f'u{i}/', b'') for i in range(257)]),
                   archive([('x/', b'.global helper; helper: copy.jsra absent; copy.ret\n')]),
                   archive([('x/', helper+b'.global value; value: copy.ret\n')])]
        # A selected dependency chain beyond the sixty-four-unit limit must fail before linking.
        chain = [(f'u{i}/', (f'.global f{i}; f{i}: copy.jsra f{i+1}; copy.ret\n' if i<63 else
                             '.global f63; f63: copy.ret\n').encode()) for i in range(64)]
        invalid.append(archive(chain))
        for i, library in enumerate(invalid):
            assembly = b'.global value; value: copy.jsra f0; copy.ret\n' if i == len(invalid)-1 else caller
            incoming = job(assembly, options+['--space-library=lib.a'], [('lib.a', library)])
            (root/f'invalid-{i}.job').write_bytes(incoming)
            for executable in ('native', 'sanitized'):
                failed = subprocess.run([str(root/executable)], input=incoming, capture_output=True,
                    env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
                code, stdout, stderr, image = decode(failed.stdout)
                assert failed.returncode == code == 126 and not stdout and stderr and not image and not failed.stderr, (i, failed)
        for private in (options+['--space-library='], options+['--space-library=x', '--space-library=y'],
                        ['--space-copy=result.s', '--space-library=x']):
            failed = subprocess.run([str(root/'native')], input=job(caller, private), capture_output=True)
            assert failed.returncode == 125 and not failed.stdout
        missing = subprocess.run([str(root/'native')], input=job(caller, options+['--space-library=absent']), capture_output=True)
        assert decode(missing.stdout)[:1] == (126,) and b'missing copy library' in decode(missing.stdout)[2]
        # Exercise every allocator failure in the C API without filesystem allocations.
        allocation_checks = root/'allocation_checks.c'
        allocation_checks.write_text('''#include <stdlib.h>
    static unsigned active, calls;
    extern void *__real_malloc(size_t);
    extern void __real_free(void *);
    void *__wrap_malloc(size_t size) {
        const char *fail=getenv("CS_COPY_TEST_ALLOC_FAIL");
        ++calls; if(fail && (unsigned)atoi(fail)==calls) return NULL;
        void *p=__real_malloc(size); if(p) ++active; return p;
    }
    void __wrap_free(void *p) {
        if(p) { if(!active) abort(); --active; } __real_free(p);
    }
    __attribute__((destructor)) static void check(void) { if(active) abort(); }
    ''')
        fixture = root/'sources/tests/fixtures/gcc/copy_link.c'
        shutil.copyfile(ROOT/'tests/fixtures/gcc/copy_link.c', fixture)
        command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-g', '-fsanitize=address,undefined',
            '-fno-omit-frame-pointer', '-fno-pie', '-no-pie', '-DCS_COPY_PROGRAM', '-DCS_COPY_ARCHIVE', '-fno-builtin-malloc',
            '-Wl,--wrap=malloc', '-Wl,--wrap=free', '-I'+str(root/'sources/runtime/gcc'), str(allocation_checks),
            str(fixture), str(root/'sources/runtime/gcc/copy_link.c'), str(root/'sources/runtime/gcc/copy_emit.c'),
            '-o', str(root/'allocation-test')]
        (root/'allocation-command.json').write_text(json.dumps(command)+'\n')
        subprocess.run(command, capture_output=True, check=True)
        packet = struct.pack('<I', len(caller))+caller+archive([('helper.s/', helper)])
        for fail in range(7):
            env = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=1'}
            if fail:
                env['CS_COPY_TEST_ALLOC_FAIL'] = str(fail)
            checked = subprocess.run([str(root/'allocation-test')], input=packet, capture_output=True, env=env)
            (root/f'allocation-{fail}.stderr').write_bytes(checked.stderr)
            if fail:
                assert checked.returncode == 2 and not checked.stdout and b'out of memory' in checked.stderr, (fail, checked)
            else:
                assert checked.returncode == 0 and not checked.stderr
                assert checked.stdout == decode((root/'extract/response.bin').read_bytes())[3]
        names.append('tests/fixtures/gcc/copy_link.c')
        evidence = {'scope': __doc__, 'sources_sha256': {n: hashlib.sha256((root/'sources'/n).read_bytes()).hexdigest() for n in names},
                    'direct_cases': results, 'rejected_archives': len(invalid), 'rejected_options': 3, 'missing_library': True, 'allocation_failures_checked': 6}
        (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if args.guest:
        if args.resume:
            manifest = json.loads((root/'program.stream.json').read_text())
        else:
            assert args.newlib
            prefix = args.newlib.resolve()/'riscv64-unknown-elf'
            manifest = build(sources+[root/'sources/runtime/gcc/syscalls.c'], root/'program.stream',
                compiler=args.compiler, stream=True, memory_bytes=4194304, space_bytes=67108864,
                extra_cflags=flags+['-DCS_RUNTIME_EXTERNAL_MEMORY', '-DCS_GCC_MEMORY_BYTES=4194304',
                    '-DCS_GCC_HEAP_BYTES=2097152', '-isystem', str(prefix/'include'),
                    '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections'],
                extra_libraries=['-Wl,--start-group', str(prefix/'lib/libc.a'), '-lgcc', '-Wl,--end-group'],
                startup=root/'sources/runtime/gcc/start.S', linker_script=root/'sources/runtime/gcc/link.ld')
            (root/'in.bin').write_bytes((root/'program.stream').read_bytes()+(root/'transitive/job.bin').read_bytes())
            shutil.copyfile(ROOT/'build/bin/space-64m', root/'emulator')
            (root/'emulator').chmod(0o755)
            evidence.update(guest_pending=True, input_sha256=hashlib.sha256((root/'in.bin').read_bytes()).hexdigest(),
                            emulator_sha256=hashlib.sha256((root/'emulator').read_bytes()).hexdigest())
            (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
        assert hashlib.sha256((root/'in.bin').read_bytes()).hexdigest() == evidence['input_sha256']
        assert hashlib.sha256((root/'emulator').read_bytes()).hexdigest() == evidence['emulator_sha256']
        execution = execute_segments(root/'emulator', root/'space', root/'in.bin',
            space_bytes=manifest['space_bytes'], layer_bytes=manifest['layer_bits']//8,
            ticks=1000000, timeout=1800, channels_only=True, resume=args.resume)
        packet = (root/'space/program.in').read_bytes()
        assert packet == (root/'transitive/response.bin').read_bytes()
        raw = (root/'space/space.bin').read_bytes()
        def word(at): return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))
        assert (word(132128), word(132160)) == (10, 0)
        direct(decode(packet)[3], root/'guest-direct', 9)
        evidence.update(guest_pending=False, guest_exit=0, guest_result=9, guest_execution=execution,
                        snapshot_sha256=hashlib.sha256(raw).hexdigest())
        (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(f"OK copy archives: {len(evidence['direct_cases'])} direct cases, {evidence['rejected_archives']} rejected archives, ASan/UBSan; mock cc1")


if __name__ == '__main__':
    main()
