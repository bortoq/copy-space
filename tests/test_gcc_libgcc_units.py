"""Compile original pinned libgcc C/headers with actual copyspace GCC in QEMU.

Host preprocessing only selects input files. GCCJOB1 carries their original
bytes; this diagnostic is not evidence of GCC execution inside Space.
"""
import argparse
import hashlib
import json
import os
import random
import struct
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from test_gcc_linux_units import pack
from test_gcc_copy_output import decode
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from fetch import VERSION, NAME, SHA512


def digest(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--cc1-work', type=Path, required=True)
    parser.add_argument('--target-source', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--unit', action='append', choices=['muldi3', 'udivdi3', 'divdi3', 'umoddi3', 'moddi3',
        'ashldi3', 'lshrdi3', 'ashrdi3', 'cmpdi2', 'ucmpdi2', 'clzsi2', 'clzdi2', 'ctzsi2', 'ctzdi2', 'negdi2', 'clz',
        'ffssi2', 'ffsdi2', 'popcountsi2', 'popcountdi2', 'paritysi2', 'paritydi2', 'bswapsi2', 'bswapdi2',
        'divmoddi4', 'udivmoddi4', 'clrsbsi2', 'clrsbdi2', 'sfsingle', 'dfdouble',
        'addsub_sf', 'mul_sf', 'div_sf', 'eq_sf', 'fpcmp_parts_sf', 'pack_sf', 'unpack_sf',
        'thenan_sf', 'make_sf', 'negate_sf', 'sf_to_si', 'si_to_sf',
        'compare_sf', 'ne_sf', 'gt_sf', 'ge_sf', 'lt_sf', 'le_sf', 'unord_sf', 'usi_to_sf',
        'addsub_df', 'mul_df', 'div_df', 'eq_df', 'fpcmp_parts_df', 'pack_df', 'unpack_df',
        'thenan_df', 'make_df', 'negate_df', 'df_to_si', 'si_to_df', 'sf_to_df', 'df_to_sf',
        'compare_df', 'ne_df', 'gt_df', 'ge_df', 'lt_df', 'le_df', 'unord_df', 'usi_to_df',
        'fixunssfsi', 'fixunsdfsi', 'fixsfdi', 'fixdfdi', 'floatdisf', 'floatdidf', 'floatundisf', 'floatundidf',
        'fixunssfdi', 'fixunsdfdi', 'mulsc3', 'muldc3', 'divsc3', 'divdc3', 'powisf2', 'powidf2',
        'addvsi3', 'addvdi3', 'subvsi3', 'subvdi3', 'mulvsi3', 'mulvdi3',
        'negvsi2', 'negvdi2', 'absvsi2', 'absvdi2', 'memcpy', 'memmove', 'memset', 'memcmp'])
    parser.add_argument('--link-probe', action='store_true', help='link five original arithmetic helpers from an archive and execute direct copies')
    parser.add_argument('--source-file', default='libgcc/libgcc2.c',
                        help='C file inside the pinned GCC tree, e.g. libgcc/fp-bit.c')
    parser.add_argument('--extra-define', action='append', default=[],
                        help='additional -DNAME for the target cc1, e.g. FLOAT for fp-bit.c single precision')
    args = parser.parse_args()
    store, build, target, diagnostic = (p.resolve() for p in
        (args.store, args.cc1_work/'gcc', args.target_source/'gcc', args.diagnostic))
    archive = store/NAME
    assert digest(archive, 'sha512') == SHA512
    source = store/('gcc-'+VERSION)
    prior = json.loads((diagnostic/'evidence.json').read_text())
    elf = diagnostic/'gcc-diagnostic.elf'
    assert digest(elf) == prior['elf_sha256']
    qemu = Path(json.loads((diagnostic/'command.json').read_text())[0])
    assert digest(qemu) == prior['qemu_sha256']
    compiler = json.loads((args.cc1_work/'cc1.json').read_text())
    assert digest(build/'cc1') == compiler['sha256']
    abi_header = target/'config/copyspace/copyspace.h'
    assert digest(abi_header) == compiler['build_profile']['target_sources_sha256']['gcc/config/copyspace/copyspace.h']
    linked = json.loads((diagnostic/'link-inputs.json').read_text())
    assert linked[str(build/'libbackend.a')] == digest(build/'libbackend.a'), 'diagnostic uses a different backend'
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    generated = root/'generated'
    generated.mkdir()
    # The moxie-derived bare-metal target has no extra libgcc tm definitions.
    with tarfile.open(archive, 'r|xz') as package:
        for member in package:
            if member.name == 'gcc-'+VERSION+'/libgcc/mkheader.sh':
                assert package.extractfile(member).read() == (source/'libgcc/mkheader.sh').read_bytes()
                break
        else:
            raise AssertionError('missing original mkheader.sh')
    command = ['sh', str(source/'libgcc/mkheader.sh')]
    (root/'mkheader-command.json').write_text(json.dumps(command)+'\n')
    result = subprocess.run(command, env={**os.environ, 'DEFINES': '', 'HEADERS': ''},
                            capture_output=True, check=True)
    (generated/'libgcc_tm.h').write_bytes(result.stdout)
    if args.source_file in ('libgcc/libgcc2.c', 'libgcc/fp-bit.c'):
        assert (build/'tconfig.h').is_file(), 'generate the normal GCC tconfig.h first'
    include = [generated, build, target, source/'libgcc', source/'include', source/'gcc/ginclude']
    flags = ['-nostdinc', '-Dinhibit_libc', '-DIN_GCC', '-DIN_LIBGCC2', '-fbuilding-libgcc',
             '-fno-stack-protector', '-ffreestanding', '-O2']
    if args.source_file == 'libgcc/memmove.c':
        # Original public-domain source assigns const void * to char *.
        flags += ['-Wno-discarded-qualifiers']
    original = (source/args.source_file)
    if not original.resolve().is_relative_to(source.resolve()) or not original.is_file():
        parser.error('--source-file must name a file inside the pinned GCC tree')
    summary = []
    verified_originals = {}
    for unit in args.unit or ['muldi3', 'udivdi3', 'divdi3', 'umoddi3', 'moddi3', 'clz']:
        folder = root/unit
        folder.mkdir()
        options = flags+['-D'+name for name in args.extra_define]+['-DL_'+unit]
        dependency = ['gcc', '-M']+options+['-I'+str(p) for p in include]+[str(original)]
        (folder/'dependency-command.json').write_text(json.dumps(dependency)+'\n')
        selected = subprocess.run(dependency, capture_output=True, timeout=120)
        (folder/'dependency.stdout').write_bytes(selected.stdout)
        (folder/'dependency.stderr').write_bytes(selected.stderr)
        assert selected.returncode == 0, selected.stderr

        def virtual(path):
            path = Path(os.path.abspath(path))
            for prefix, label in [(generated, 'generated'), (build, 'build'), (target, 'target'), (source, 'source')]:
                if path.is_relative_to(prefix):
                    return label+'/'+path.relative_to(prefix).as_posix()
            raise ValueError('unrecorded dependency: '+str(path))

        paths = [Path(p) for p in shlex.split(selected.stdout.decode().replace('\\\n', ' '))[1:]]
        files = {virtual(p): p.read_bytes() for p in paths}
        # Standalone memory sources need only stddef.h. Carry the verified
        # compiler ABI header as an unused input anchor for package validation.
        files.setdefault(virtual(abi_header), abi_header.read_bytes())
        wanted = {}
        for path in paths:
            real = path.resolve()
            if not real.is_relative_to(source):
                continue
            name = 'gcc-'+VERSION+'/'+real.relative_to(source).as_posix()
            data = files[virtual(path)]
            if name in verified_originals:
                assert verified_originals[name] == hashlib.sha256(data).hexdigest()
            else:
                wanted[name] = data
        if wanted:
            with tarfile.open(archive, 'r|xz') as package:
                for member in package:
                    if member.name in wanted:
                        data = wanted.pop(member.name)
                        assert package.extractfile(member).read() == data, 'changed original GCC file: '+member.name
                        verified_originals[member.name] = hashlib.sha256(data).hexdigest()
                    if not wanted:
                        break
            assert not wanted
        for name, data in files.items():
            dest = folder/'inputs'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        argv = ['cc1', '--space-result=result.s', '-quiet']+options+[
            '-I'+virtual(p/'x')[:-2] for p in include]+['-o', 'result.s', virtual(original)]
        incoming = pack(argv, files)
        (folder/'job.bin').write_bytes(incoming)
        command = [str(qemu), '-strace', str(elf)]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=180)
        (folder/'response.bin').write_bytes(compiled.stdout)
        (folder/'syscalls.txt').write_bytes(compiled.stderr)
        code, stdout, stderr, assembly = decode(compiled.stdout)
        (folder/'assembly.s').write_bytes(assembly)
        record = {'unit': unit, 'code': code, 'process_exit': compiled.returncode,
                  'stdout': stdout.decode(errors='replace'), 'stderr': stderr.decode(errors='replace'),
                  'assembly_bytes': len(assembly), 'assembly_sha256': hashlib.sha256(assembly).hexdigest(),
                  'job_sha256': digest(folder/'job.bin'),
                  'files_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
        (folder/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
        summary.append(record)
        print(unit, 'exit', code, 'assembly', len(assembly), stderr.decode(errors='replace'), flush=True)
    probe_evidence = None
    if args.link_probe:
        assert {r['unit'] for r in summary} >= {'muldi3', 'udivdi3', 'divdi3', 'umoddi3', 'moddi3', 'clz'}
        assert all(r['code'] == r['process_exit'] == 0 for r in summary)
        probe = root/'probe'
        probe.mkdir()
        members = []
        for record in summary:
            path = probe/(record['unit']+'.s')
            shutil.copyfile(root/record['unit']/'assembly.s', path)
            members.append(str(path))
        command = ['ar', 'rcSD', str(probe/'libgcc.a')]+members
        (probe/'archive-command.json').write_text(json.dumps(command)+'\n')
        subprocess.run(command, capture_output=True, check=True)
        rng = random.Random(0xc0f13264)
        cases = [(0, 1), (1, 1), (0xffffffffffffffff, 1), (0xffffffffffffffff, 0xffffffff),
                 (0x100000000, 0x10000), (0x8000000000000000, 3), (0x8000000000000000, 0xffffffff),
                 (0xffffffff, 0x100000000), (0x8000000000000000, 0x8000000000000000),
                 (0xffffffffffffffff, 0xffffffffffffffff)]
        cases += [(rng.getrandbits(64), rng.getrandbits(64) or 1) for _ in range(50)]
        mask = (1 << 64)-1
        records = []
        for a, b in cases:
            sa, sb = (a if a < 1 << 63 else a-(1 << 64)), (b if b < 1 << 63 else b-(1 << 64))
            quotient = (abs(sa)//abs(sb)) * (-1 if (sa < 0) != (sb < 0) else 1)
            values = [a, b, (a*b)&mask, a//b, a%b, quotient&mask, (sa-quotient*sb)&mask]
            records.append('{'+','.join(hex(v)+'ULL' for v in values)+'}')
        text = ('typedef __UINT64_TYPE__ u64; typedef __INT64_TYPE__ s64;\n'
                'struct record { u64 a,b,expected[5]; };\n'
                'static const struct record cases[]={'+','.join(records)+'};\n')
        expressions = ['a*b', 'a/b', 'a%b', '(u64)((s64)a/(s64)b)', '(u64)((s64)a%(s64)b)']
        for i, expression in enumerate(expressions):
            text += ('static __attribute__((__noinline__,__noipa__)) u64 calc'+str(i)+
                     '(u64 a,u64 b) { return '+expression+'; }\n')
        text += 'unsigned value(void) { unsigned passed=0; for(unsigned i=0;i<'+str(len(cases))+';i++) {\n'
        for i in range(5):
            text += f'passed += calc{i}(cases[i].a,cases[i].b)==cases[i].expected[{i}];\n'
        text += '} return passed; }\n'
        data = text.encode()
        (probe/'main.c').write_bytes(data)
        incoming = pack(['cc1', '--space-program=result.s', '--space-entry=value', '--space-memory=65536',
                         '--space-library=libgcc.a', '-quiet', '-O2', '-ffreestanding', '-fno-builtin', '-nostdinc',
                         '-o', 'result.s', 'main.c'], {'main.c': data, 'libgcc.a': (probe/'libgcc.a').read_bytes()})
        (probe/'job.bin').write_bytes(incoming)
        command = [str(qemu), '-strace', str(elf)]
        (probe/'command.json').write_text(json.dumps(command)+'\n')
        compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=300)
        (probe/'response.bin').write_bytes(compiled.stdout)
        (probe/'syscalls.txt').write_bytes(compiled.stderr)
        code, stdout, stderr, image = decode(compiled.stdout)
        assert compiled.returncode == code == 0 and not stdout and not stderr, (compiled.returncode, stderr)
        (probe/'image.bin').write_bytes(image)
        command = [str(ROOT/'build/bin/space-256m'), '--ticks', '10000000', '--core', str(probe/'image.bin'),
                   '--trace-channels', str(probe/'direct.trace')]
        (probe/'direct-command.json').write_text(json.dumps(command)+'\n')
        direct = subprocess.run(command, capture_output=True, timeout=300, check=True)
        (probe/'direct.out').write_bytes(direct.stdout)
        assert not direct.stderr and direct.stdout == struct.pack('<I', len(cases)*5), direct.stdout
        assert (probe/'direct.trace').read_bytes().endswith(b' idle\n')
        probe_evidence = {'cases': len(cases), 'operations': 5, 'direct_result': len(cases)*5,
                          'archive_sha256': digest(probe/'libgcc.a'), 'job_sha256': digest(probe/'job.bin'),
                          'image_sha256': digest(probe/'image.bin'), 'image_bytes': len(image)}
        print('Original libgcc archive: direct arithmetic checks', len(cases)*5, flush=True)
    evidence = {'scope': __doc__, 'gcc_archive_sha512': SHA512, 'elf_sha256': digest(elf),
                'qemu_sha256': digest(qemu), 'original_files_verified': verified_originals, 'units': summary, 'link_probe': probe_evidence}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    assert all(r['code'] == r['process_exit'] == 0 and not r['stderr'] and not r['stdout'] and
               r['assembly_bytes'] for r in summary)


if __name__ == '__main__':
    main()
