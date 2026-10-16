"""Package verified target runtime assembly units into a reproducible ar library.

This preparation tool verifies pinned GCC and explicit project source bytes. It
only packages existing guest results; it never compiles or lowers their code.
The catalog covers the listed core runtime units, not all of upstream libgcc.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tarfile
from pathlib import Path

from fetch import VERSION, NAME, SHA512
from job_format import unpack_job
ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT/'runtime/gcc/target/libgcc.json'
ABI = {'word_bits': 32, 'pointer_bits': 32, 'byte_order': 'little'}
FORMAT = 'copyspace-target-library-v1'
PROJECT_FORMAT = 'copyspace-target-library-v2'
PROJECT_SOURCES = {'runtime/gcc/target/sync_up.c'}


def embedded_assembly(filename, size):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', filename) or not 8 <= size <= 0xffffffff:
        raise ValueError('invalid embedded target archive')
    return ('.section .rodata.cs_gcc_default_archive,"a",@progbits\n.balign 4\n'
            '.global cs_gcc_default_archive_size\ncs_gcc_default_archive_size:\n.long '+str(size)+'\n'
            '.global cs_gcc_default_archive\ncs_gcc_default_archive:\n.incbin "'+filename+'"\n'
            '.section .note.GNU-stack,"",@progbits\n').encode()


def digest(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def catalog_units(path=CATALOG):
    catalog = json.loads(path.read_text())
    if catalog['format'] != 'copyspace-libgcc-catalog-v1':
        raise ValueError('unsupported libgcc catalog')
    result = {}
    for group in catalog['groups']:
        origin = group.get('origin', 'gcc')
        if (origin not in ('gcc', 'project') or
                (origin == 'project' and group['source'] not in PROJECT_SOURCES) or
                (origin == 'gcc' and group['source'] in PROJECT_SOURCES)):
            raise ValueError('unsupported runtime source origin')
        for unit in group['units']:
            if not re.fullmatch(r'[A-Za-z0-9_]+', unit) or unit in result:
                raise ValueError('duplicate or invalid catalog unit: '+unit)
            result[unit] = group
    return result


def compiler_arguments(group, unit):
    source = ('project/' if group.get('origin') == 'project' else 'source/')+group['source']
    argv = ['cc1', '--space-result=result.s', '-quiet', '-nostdinc', '-Dinhibit_libc',
        '-DIN_GCC', '-DIN_LIBGCC2', '-fbuilding-libgcc', '-fno-stack-protector', '-ffreestanding', '-O2']
    argv += group.get('options', [])
    argv += ['-D'+name for name in group['defines']]+['-DL_'+unit]
    return argv+['-Igenerated', '-Ibuild', '-Itarget', '-Isource/libgcc', '-Isource/include',
                 '-Isource/gcc/ginclude', '-o', 'result.s', source]


def load_library(root, target_header=None):
    root = Path(root)
    manifest = json.loads((root/'library.json').read_text())
    if (manifest.get('format') not in (FORMAT, PROJECT_FORMAT) or manifest.get('gcc_version') != VERSION or
            manifest.get('gcc_archive_sha512') != SHA512 or manifest.get('abi') != ABI or
            manifest.get('target') != 'copyspace-unknown-elf'):
        raise ValueError('incompatible target library')
    if target_header is not None and manifest['target_header_sha256'] != target_header:
        raise ValueError('target library was built with a different target header')
    if digest(root/'catalog.json') != manifest['catalog_sha256']:
        raise ValueError('changed target library catalog')
    licenses=manifest.get('licenses_sha256', {})
    if (licenses or manifest['format'] == PROJECT_FORMAT) and set(licenses) != {'COPYING3', 'COPYING.RUNTIME'}:
        raise ValueError('invalid target library license inventory')
    for name, expected_hash in licenses.items():
        if digest(root/name) != expected_hash:
            raise ValueError('changed upstream license: '+name)
    expected = catalog_units(root/'catalog.json')
    project_sources = {group['source'] for group in expected.values() if group.get('origin') == 'project'}
    if bool(project_sources) != (manifest['format'] == PROJECT_FORMAT):
        raise ValueError('incompatible project runtime provenance format')
    project_inputs = manifest.get('project_inputs_sha256', {})
    if set(project_inputs) != project_sources:
        raise ValueError('invalid project runtime source inventory')
    for name, signature in project_inputs.items():
        if digest(root/'project-sources'/name) != signature:
            raise ValueError('changed project runtime source: '+name)
    project_licenses = manifest.get('project_licenses_sha256', {})
    if set(project_licenses) != ({'PROJECT-LICENSE'} if project_sources else set()):
        raise ValueError('invalid project runtime license inventory')
    for name, signature in project_licenses.items():
        if digest(root/name) != signature:
            raise ValueError('changed project runtime license')
    if [m['unit'] for m in manifest['members']] != list(expected):
        raise ValueError('missing, duplicated or reordered library members')
    for member in manifest['members']:
        if member.get('origin', 'gcc') != expected[member['unit']].get('origin', 'gcc'):
            raise ValueError('inconsistent runtime member origin')
        if digest(root/'members'/(member['unit']+'.s')) != member['assembly_sha256']:
            raise ValueError('changed target library member: '+member['unit'])
    archive = root/'libgcc.a'
    if digest(archive) != manifest['archive_sha256']:
        raise ValueError('changed target archive')
    return archive, manifest


def package(runs, store, root, ar='ar'):
    expected = catalog_units()
    provided, originals, target_headers, project_inputs = {}, {}, set(), {}
    for run in runs:
        run = Path(run).resolve()
        receipt = json.loads((run/'evidence.json').read_text())
        if receipt.get('gcc_archive_sha512') != SHA512:
            raise ValueError('producer has no pinned GCC provenance: '+str(run))
        for record in receipt['units']:
            unit = record['unit']
            if unit not in expected:
                continue
            group = expected[unit]
            folder = run/unit
            if (record['code'] or record['process_exit'] or record['stdout'] or record['stderr'] or
                    not record['assembly_bytes']):
                raise ValueError('failed compiler unit: '+unit)
            assembly = (folder/'assembly.s').read_bytes()
            if len(assembly) != record['assembly_bytes'] or digest(folder/'assembly.s') != record['assembly_sha256']:
                raise ValueError('changed compiler output: '+unit)
            incoming = (folder/'job.bin').read_bytes()
            if hashlib.sha256(incoming).hexdigest() != record['job_sha256']:
                raise ValueError('changed compiler job: '+unit)
            argv, files = unpack_job(incoming)
            canonical = compiler_arguments(group, unit)
            if argv != canonical or json.loads((folder/'evidence.json').read_text()) != record:
                raise ValueError('inconsistent compiler recipe or receipt: '+unit)
            defines = {a[2:] for a in argv if a.startswith('-D')}
            wanted = {'inhibit_libc', 'IN_GCC', 'IN_LIBGCC2', 'L_'+unit, *group['defines']}
            if (defines != wanted or argv[-1] != canonical[-1] or
                    not {'-nostdinc', '-fbuilding-libgcc', '-ffreestanding', '-O2'} <= set(argv)):
                raise ValueError('unexpected compilation options: '+unit)
            if set(files) != set(record['files_sha256']):
                raise ValueError('changed job filesystem: '+unit)
            if group.get('origin') == 'project':
                source_name = 'project/'+group['source']
                if set(files) != {source_name, 'target/config/copyspace/copyspace.h'}:
                    raise ValueError('unexpected project runtime inputs: '+unit)
                if files[source_name] != (ROOT/group['source']).read_bytes():
                    raise ValueError('changed project runtime input: '+unit)
                project_inputs[group['source']] = files[source_name]
            for name, data in files.items():
                if hashlib.sha256(data).hexdigest() != record['files_sha256'][name]:
                    raise ValueError('changed compiler input: '+name)
                if (folder/'inputs'/name).read_bytes() != data:
                    raise ValueError('changed frozen input: '+name)
                original = None
                if name.startswith('source/'):
                    original = name[7:]
                elif name.startswith('target/') and not name.startswith('target/config/copyspace/'):
                    original = 'gcc/'+name[7:]
                if original is not None:
                    if original in originals and originals[original] != data:
                        raise ValueError('conflicting original source: '+original)
                    originals[original] = data
            target_headers.add(record['files_sha256']['target/config/copyspace/copyspace.h'])
            response = (folder/'response.bin').read_bytes()
            if (response[:8] != b'GCCOUT1\0' or len(response) != 24+len(assembly) or
                    struct.unpack_from('<IIII', response, 8) != (0, 0, 0, len(assembly)) or
                    response[24:] != assembly):
                raise ValueError('compiler response and assembly disagree: '+unit)
            command = json.loads((folder/'command.json').read_text())
            if digest(Path(command[0])) != receipt['qemu_sha256'] or digest(Path(command[-1])) != receipt['elf_sha256']:
                raise ValueError('changed recorded producer executable: '+unit)
            if unit in provided and provided[unit]['record']['assembly_sha256'] != record['assembly_sha256']:
                raise ValueError('conflicting duplicate unit: '+unit)
            if unit not in provided:
                provided[unit] = {'folder': folder, 'record': record, 'assembly': assembly,
                                  'elf_sha256': receipt['elf_sha256'], 'producer': str(run)}
    missing = set(expected)-set(provided)
    if missing:
        raise ValueError('missing catalog units: '+', '.join(sorted(missing)))
    if len(target_headers) != 1:
        raise ValueError('mixed target configurations')
    archive = Path(store).resolve()/NAME
    if digest(archive, 'sha512') != SHA512:
        raise ValueError('changed pinned GCC archive')
    wanted = {'gcc-'+VERSION+'/'+name: data for name, data in originals.items()}
    verified = {}
    licenses = {}
    with tarfile.open(archive, 'r|xz') as source:
        for member in source:
            if member.name in ['gcc-'+VERSION+'/'+name for name in ('COPYING3', 'COPYING.RUNTIME')]:
                licenses[Path(member.name).name] = source.extractfile(member).read()
            if member.name in wanted:
                data = wanted.pop(member.name)
                if source.extractfile(member).read() != data:
                    raise ValueError('changed original source: '+member.name)
                verified[member.name] = hashlib.sha256(data).hexdigest()
            if not wanted and len(licenses)==2:
                break
    if wanted or len(licenses)!=2:
        raise ValueError('original inputs missing from pinned GCC archive')
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'package.py')
    shutil.copyfile(CATALOG, root/'catalog.json')
    for name, data in licenses.items():
        (root/name).write_bytes(data)
    project_licenses = {}
    if project_inputs:
        project_licenses['PROJECT-LICENSE'] = (ROOT/'LICENSE').read_bytes()
        (root/'PROJECT-LICENSE').write_bytes(project_licenses['PROJECT-LICENSE'])
        for name, data in project_inputs.items():
            dest = root/'project-sources'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    members = root/'members'
    members.mkdir()
    entries = []
    for unit in expected:
        provider = provided[unit]
        record = provider['record']
        dest = members/(unit+'.s')
        dest.write_bytes(provider['assembly'])
        dest.chmod(0o644)
        provenance = root/'provenance'/unit
        provenance.mkdir(parents=True)
        for name in ['job.bin', 'response.bin', 'command.json', 'evidence.json']:
            shutil.copyfile(provider['folder']/name, provenance/name)
        if digest(provenance/'job.bin') != record['job_sha256']:
            raise ValueError('producer job changed during packaging: '+unit)
        entries.append({'unit': unit, 'origin': expected[unit].get('origin', 'gcc'),
                        'assembly_sha256': record['assembly_sha256'],
                        'job_sha256': record['job_sha256'], 'producer': provider['producer'],
                        'compiler_elf_sha256': provider['elf_sha256']})
    command = [ar, 'rcSD', str(root/'libgcc.a')]+[str(members/(unit+'.s')) for unit in expected]
    (root/'archive-command.json').write_text(json.dumps(command)+'\n')
    subprocess.run(command, check=True, capture_output=True)
    manifest = {'format': PROJECT_FORMAT if project_inputs else FORMAT, 'gcc_version': VERSION, 'gcc_archive_sha512': SHA512,
        'target': 'copyspace-unknown-elf', 'abi': ABI, 'target_header_sha256': target_headers.pop(),
        'catalog_sha256': digest(root/'catalog.json'), 'archive_sha256': digest(root/'libgcc.a'),
        'members': entries, 'original_inputs_sha256': verified,
        'licenses_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in licenses.items()},
        'project_inputs_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in project_inputs.items()},
        'project_licenses_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in project_licenses.items()},
        'scope': 'Listed core libgcc units and explicitly identified project runtime; compiler execution was diagnosed in QEMU. '
                 'Packaging only, not full upstream libgcc or proof of Space compilation.'}
    (root/'library.json').write_text(json.dumps(manifest, indent=2)+'\n')
    load_library(root)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit-run', type=Path, action='append', required=True)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    manifest = package(args.unit_run, args.store, args.artifacts)
    print('Packaged', len(manifest['members']), 'target runtime units:', manifest['archive_sha256'])


if __name__ == '__main__':
    main()
