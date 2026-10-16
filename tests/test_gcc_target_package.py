"""Check target-library receipts, malformed inputs and GCCJOB1 compatibility."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from job_format import pack_job, unpack_job
from package_target_library import package, load_library, embedded_assembly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--unit-run', type=Path, required=True)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    library = args.library.resolve()
    archive, manifest = load_library(library)
    command = ['ar', 't', str(archive)]
    assert subprocess.run(command, capture_output=True, check=True).stdout.decode().splitlines() == [
        m['unit']+'.s' for m in manifest['members']]
    for member in manifest['members']:
        data = subprocess.run(['ar', 'p', str(archive), member['unit']+'.s'], capture_output=True, check=True).stdout
        assert data == (library/'members'/(member['unit']+'.s')).read_bytes()
    failures = []

    def reject(name, action, text=None):
        try:
            action()
        except ValueError as error:
            if text:
                assert text in str(error), (name, error)
            failures.append({'name': name, 'error': str(error)})
        else:
            raise AssertionError('accepted '+name)

    def clone(name, overrides):
        folder = root/name
        folder.mkdir()
        for p in library.iterdir():
            if p.name not in overrides:
                (folder/p.name).symlink_to(p, target_is_directory=p.is_dir())
        for name, data in overrides.items():
            (folder/name).write_bytes(data)
        return folder

    damaged = clone('bad-archive', {'libgcc.a': archive.read_bytes()+b'x'})
    reject('archive checksum', lambda: load_library(damaged), 'changed target archive')
    damaged = clone('bad-catalog', {'catalog.json': (library/'catalog.json').read_bytes()+b'\n'})
    reject('catalog checksum', lambda: load_library(damaged), 'changed target library catalog')
    for name, key, value in [('abi', 'abi', {}), ('member-list', 'members', manifest['members'][:-1])]:
        modified = {**manifest, key: value}
        damaged = clone('bad-'+name, {'library.json': json.dumps(modified).encode()})
        reject(name, lambda: load_library(damaged))
    reject('target header', lambda: load_library(library, '0'*64), 'different target header')
    if manifest.get('licenses_sha256'):
        damaged = clone('bad-license', {'COPYING.RUNTIME': (library/'COPYING.RUNTIME').read_bytes()+b'\n'})
        reject('license checksum', lambda: load_library(damaged), 'changed upstream license')
    if manifest.get('project_inputs_sha256'):
        modified = {**manifest, 'project_inputs_sha256': {}}
        damaged = clone('bad-project-inventory', {'library.json': json.dumps(modified).encode()})
        reject('project source inventory', lambda: load_library(damaged), 'project runtime source inventory')
        damaged = clone('bad-project-source', {})
        (damaged/'project-sources').unlink()
        shutil.copytree(library/'project-sources', damaged/'project-sources')
        name = next(iter(manifest['project_inputs_sha256']))
        path = damaged/'project-sources'/name
        path.write_bytes(path.read_bytes()+b'\n')
        reject('project source checksum', lambda: load_library(damaged), 'changed project runtime source')
        damaged = clone('bad-project-license', {'PROJECT-LICENSE': (library/'PROJECT-LICENSE').read_bytes()+b'\n'})
        reject('project license checksum', lambda: load_library(damaged), 'changed project runtime license')
        modified = {**manifest, 'project_licenses_sha256': {}}
        damaged = clone('missing-project-license', {'library.json': json.dumps(modified).encode()})
        reject('project license inventory', lambda: load_library(damaged), 'project runtime license inventory')
        modified = {**manifest, 'licenses_sha256': {}}
        damaged = clone('missing-gcc-licenses', {'library.json': json.dumps(modified).encode()})
        reject('GCC license inventory', lambda: load_library(damaged), 'license inventory')
        modified = {**manifest, 'format': 'copyspace-target-library-v1'}
        damaged = clone('downgraded-project-format', {'library.json': json.dumps(modified).encode()})
        reject('project provenance downgrade', lambda: load_library(damaged), 'project runtime provenance format')
        entries = [dict(member) for member in manifest['members']]
        entries[-1]['origin'] = 'gcc'
        modified = {**manifest, 'members': entries}
        damaged = clone('bad-project-origin', {'library.json': json.dumps(modified).encode()})
        reject('project origin', lambda: load_library(damaged), 'member origin')
        catalog = json.loads((library/'catalog.json').read_text())
        for group in catalog['groups']:
            if group.get('origin') == 'project':
                group['origin'] = 'gcc'
        raw_catalog = json.dumps(catalog).encode()
        modified = {**manifest, 'catalog_sha256': hashlib.sha256(raw_catalog).hexdigest()}
        damaged = clone('bad-project-catalog-origin', {
            'catalog.json': raw_catalog, 'library.json': json.dumps(modified).encode()})
        reject('project catalog origin', lambda: load_library(damaged), 'unsupported runtime source origin')
    damaged = clone('bad-member', {})
    (damaged/'members').unlink()
    (damaged/'members').mkdir()
    first = manifest['members'][0]['unit']+'.s'
    for p in (library/'members').iterdir():
        if p.name == first:
            (damaged/'members'/p.name).write_bytes(p.read_bytes()+b'\n')
        else:
            (damaged/'members'/p.name).symlink_to(p)
    reject('member checksum', lambda: load_library(damaged), 'changed target library member')

    producer = args.unit_run.resolve()
    receipt = json.loads((producer/'evidence.json').read_text())
    record = receipt['units'][0]
    unit = record['unit']
    job = (producer/unit/'job.bin').read_bytes()
    argv, files = unpack_job(job)
    assert pack_job(argv, files) == job
    for n, payload in enumerate([b'', job[:-1], job+b'x', b'badmagic'+job[8:]]):
        reject('truncated/magic '+str(n), lambda payload=payload: unpack_job(payload))
    for count in (0, 257):
        reject('argc '+str(count), lambda count=count: unpack_job(job[:8]+struct.pack('<I', count)+job[12:]))
    simple = pack_job(['cc1'], {'main.c': b'int x;\n'})
    reject('argument NUL', lambda: unpack_job(simple[:20]+b'\0'+simple[21:]))
    for argc, filemap in [([], {'x': b''}), ([''], {'x': b''}), (['cc1'], {}), (['cc1'], {'../x': b''}),
                        (['cc1', 'x'*4097], {'x': b''})]:
        reject('encoder validation '+str(len(failures)), lambda argc=argc, filemap=filemap: pack_job(argc, filemap))
    valid = pack_job(['cc1', ''], {'nested/main.c': b'', 'library.a': b'\0binary'})
    assert unpack_job(valid) == (['cc1', ''], {'nested/main.c': b'', 'library.a': b'\0binary'})
    reject('assembly filename', lambda: embedded_assembly('../archive', 8))
    reject('missing units', lambda: package([producer], args.store, root/'missing-output'), 'missing catalog units')
    assert not (root/'missing-output').exists()

    def altered_run(name, assembly=None, incoming=None):
        folder = root/name
        folder.mkdir()
        modified = json.loads(json.dumps(receipt))
        changed = modified['units'][0]
        for p in producer.iterdir():
            if p.name not in (unit, 'evidence.json'):
                (folder/p.name).symlink_to(p, target_is_directory=p.is_dir())
        child = folder/unit
        child.mkdir()
        for p in (producer/unit).iterdir():
            if p.name not in ('assembly.s', 'job.bin', 'response.bin', 'evidence.json'):
                (child/p.name).symlink_to(p, target_is_directory=p.is_dir())
        a = (producer/unit/'assembly.s').read_bytes() if assembly is None else assembly
        j = job if incoming is None else incoming
        (child/'assembly.s').write_bytes(a)
        (child/'job.bin').write_bytes(j)
        changed['assembly_sha256'] = hashlib.sha256(a).hexdigest()
        changed['assembly_bytes'] = len(a)
        changed['job_sha256'] = hashlib.sha256(j).hexdigest()
        (child/'response.bin').write_bytes(b'GCCOUT1\0'+struct.pack('<IIII', 0, 0, 0, len(a))+a)
        (child/'evidence.json').write_text(json.dumps(changed))
        (folder/'evidence.json').write_text(json.dumps(modified))
        return folder

    changed = altered_run('changed-recipe', incoming=pack_job([a for a in argv if a != '-fbuilding-libgcc'], files))
    reject('compiler recipe', lambda: package([changed], args.store, root/'recipe-output'), 'recipe')
    changed = altered_run('conflicting-producer', assembly=(producer/unit/'assembly.s').read_bytes()+b'\n')
    reject('conflicting duplicate', lambda: package([producer, changed], args.store, root/'duplicate-output'), 'conflicting duplicate')
    assert not (root/'recipe-output').exists() and not (root/'duplicate-output').exists()
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'units': len(manifest['members']),
        'archive_sha256': manifest['archive_sha256'], 'rejected': failures,
        'producer_packet_roundtrip': True, 'all_archive_members_exact': True}, indent=2)+'\n')
    print('OK target package:', len(manifest['members']), 'exact members;', len(failures), 'rejections')


if __name__ == '__main__':
    main()
