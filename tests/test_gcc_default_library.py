"""Check automatic target runtime and grouped custom archives (mock cc1)."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from test_gcc_copy_archive import archive
from test_gcc_copy_output import decode, direct
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from package_target_library import embedded_assembly
from job_format import pack_job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    names = ['tests/fixtures/gcc/copy_output.c']+['runtime/gcc/'+n for n in
        ('main.c', 'job.c', 'job.h', 'files.c', 'files.h', 'response.c', 'response.h',
         'copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]+[
         'runtime/rv32i/copy_space.h', 'runtime/copy_c/input_files.h']
    for name in names:
        dest = root/'sources'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dest)
    helper = b'.global helper; helper: copy.inc $r0,2; copy.ret\n'
    base = b'.global base; base: copy.add $r0,$r1; copy.ret\n'
    builtin = b'.global builtin; builtin: copy.jsra external; copy.inc $r0,2; copy.ret\n'
    library = archive([('helper.s/', helper), ('base.s/', base), ('builtin.s/', builtin)])
    (root/'embedded.a').write_bytes(library)
    (root/'embedded.S').write_bytes(embedded_assembly('embedded.a', len(library)))
    sources = [str(root/'sources'/n) for n in names if n.endswith('.c')]
    flags = ['-DCS_GCC_FRAMED_OUTPUT', '-DCS_GCC_COPY_OUTPUT', '-Wl,--wrap=main',
             '-I'+str(root/'sources/runtime/gcc'), '-I'+str(root/'sources/runtime/rv32i')]
    for name in ('bare', 'native', 'sanitized'):
        command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror']+flags+sources
        if name != 'bare':
            command.append(str(root/'embedded.S'))
        if name == 'sanitized':
            command += ['-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
        command += ['-o', str(root/name)]
        (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
        subprocess.run(command, cwd=root, capture_output=True, check=True)
    options = ['--space-program=result.s', '--space-entry=value', '--space-arg=3', '--space-arg=4']
    call = b'.global value; value: copy.jsra helper; copy.ret\n'
    add = b'.global value; value: copy.add $r0,$r1; copy.ret\n'
    override = b'.global helper; helper: copy.inc $r0,100; copy.ret\n'
    explicit = ['--space-library=user.a']
    cases = [
        ('default', call, [], {}, 5),
        ('unused', add, [], {}, 7),
        ('weak', b'.weak helper; .global value; value: copy.ldi.l $r0,helper; copy.ret\n', [], {}, 0),
        ('override', call, explicit, {'user.a': archive([('helper.s/', override)])}, 103),
        ('forward', call, explicit, {'user.a': archive([('helper.s/', b'.global helper; helper: copy.jsra base; copy.inc $r0,2; copy.ret\n')])}, 9),
        ('backward', b'.global value; value: copy.jsra builtin; copy.ret\n', explicit,
         {'user.a': archive([('external.s/', b'.global external; external: copy.inc $r0,4; copy.ret\n')])}, 9),
        ('disabled-unused', add, ['--space-no-libgcc'], {}, 7),
        ('disabled-explicit', call, explicit+['--space-no-libgcc'], {'user.a': archive([('helper.s/', override)])}, 103),
        ('combined-limit', add, explicit, {'user.a': archive([(f'u{i}/', b'') for i in range(253)])}, 7),
    ]
    results = []
    for name, assembly, extra, files, expected in cases:
        folder = root/name
        folder.mkdir()
        incoming = pack_job(['cc1']+options+extra+['-S', 'in.s'], {'in.s': assembly, **files})
        (folder/'job.bin').write_bytes(incoming)
        response = None
        for executable in ('native', 'sanitized'):
            checked = subprocess.run([str(root/executable)], input=incoming, capture_output=True,
                env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}, check=True)
            assert not checked.stderr
            if response is None:
                response = checked.stdout
            assert response == checked.stdout
        status, stdout, stderr, image = decode(response)
        assert status == 0 and not stdout and not stderr and len(image) == 262144
        (folder/'response.bin').write_bytes(response)
        direct(image, folder/'direct', expected)
        if name in ('unused', 'disabled-unused', 'disabled-explicit'):
            bare = subprocess.run([str(root/'bare')], input=incoming, capture_output=True, check=True)
            assert bare.stdout == response
        results.append({'name': name, 'result': expected, 'image_sha256': hashlib.sha256(image).hexdigest()})
    failed_cases = [
        ('disabled-required', ['--space-no-libgcc'], {}),
        ('missing-explicit', explicit, {}),
        ('bad-explicit', explicit, {'user.a': b'bad'}),
        ('combined-overflow', explicit, {'user.a': archive([(f'u{i}/', b'') for i in range(254)])}),
    ]
    for name, extra, files in failed_cases:
        incoming = pack_job(['cc1']+options+extra+['-S', 'in.s'], {'in.s': call, **files})
        for executable in ('native', 'sanitized'):
            checked = subprocess.run([str(root/executable)], input=incoming, capture_output=True,
                env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
            code, stdout, stderr, image = decode(checked.stdout)
            assert checked.returncode == code == 126 and not stdout and stderr and not image and not checked.stderr
            (root/(name+'-'+executable+'.response')).write_bytes(checked.stdout)
    for opts in (options+['--space-no-libgcc']*2, ['--space-copy=result.s', '--space-no-libgcc']):
        checked = subprocess.run([str(root/'native')], input=pack_job(['cc1']+opts+['-S', 'in.s'], {'in.s': add}), capture_output=True)
        assert checked.returncode == 125 and not checked.stdout
    leaf = ['cc1', '--space-copy=result.s', '--space-entry=value', '--space-arg=3', '--space-arg=4', '-S', 'in.s']
    incoming = pack_job(leaf, {'in.s': b'value: copy.add $r0,$r1; copy.ret\n'})
    response = subprocess.run([str(root/'native')], input=incoming, capture_output=True, check=True)
    bare = subprocess.run([str(root/'bare')], input=incoming, capture_output=True, check=True)
    assert response.stdout == bare.stdout and len(decode(response.stdout)[3]) == 65536
    direct(decode(response.stdout)[3], root/'leaf', 7)
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'direct_cases': results,
        'rejected_links': len(failed_cases), 'rejected_flags': 2, 'leaf_unchanged': True,
        'sources_sha256': {n: hashlib.sha256((root/'sources'/n).read_bytes()).hexdigest() for n in names},
        'embedded_archive_sha256': hashlib.sha256(library).hexdigest()}, indent=2)+'\n')
    print('OK default library: nine direct programs, leaf compatibility, six rejections, ASan/UBSan')


if __name__ == '__main__':
    main()
