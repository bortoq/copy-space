"""Compile explicitly catalogued project runtime C with the real guest GCC.

Only boot preparation and diagnostic QEMU execution happen on the host.
The project C bytes and ABI anchor travel unchanged through GCCJOB1.
Upstream GCC provenance is kept separate by package_target_library.py.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path

from fetch import SHA512
from job_format import pack_job, unpack_job
from package_target_library import ROOT, catalog_units, compiler_arguments, load_library


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--base-library', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    image, diagnostic, library = (p.resolve() for p in (args.image, args.diagnostic, args.base_library))
    _, base = load_library(library)
    manifest = json.loads((image/'image.json').read_text())
    prior = json.loads((diagnostic/'evidence.json').read_text())
    command = json.loads((diagnostic/'command.json').read_text())
    assert digest(image/'gcc-space.elf') == manifest['elf_sha256'] == prior['original_elf_sha256']
    assert digest(Path(command[0])) == prior['qemu_sha256']
    assert digest(Path(command[-1])) == prior['elf_sha256']
    first = base['members'][0]
    job = library/'provenance'/first['unit']/'job.bin'
    assert digest(job) == first['job_sha256']
    _, files = unpack_job(job.read_bytes())
    anchor = 'target/config/copyspace/copyspace.h'
    header = files[anchor]
    assert hashlib.sha256(header).hexdigest() == base['target_header_sha256'] == manifest['target_sources_sha256']['gcc/config/copyspace/copyspace.h']
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    units = []
    project = {}
    for unit, group in catalog_units().items():
        if group.get('origin') != 'project':
            continue
        folder = root/unit
        folder.mkdir()
        source_name = 'project/'+group['source']
        data = (ROOT/group['source']).read_bytes()
        project[group['source']] = hashlib.sha256(data).hexdigest()
        files = {source_name: data, anchor: header}
        for name, content in files.items():
            target = folder/'inputs'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        incoming = pack_job(compiler_arguments(group, unit), files)
        (folder/'job.bin').write_bytes(incoming)
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        compiled = subprocess.run(command, input=incoming, capture_output=True, timeout=300)
        (folder/'response.bin').write_bytes(compiled.stdout)
        (folder/'syscalls.txt').write_bytes(compiled.stderr)
        packet = compiled.stdout
        assert packet[:8] == b'GCCOUT1\0' and len(packet) >= 24
        code, outsize, errsize, size = struct.unpack_from('<IIII', packet, 8)
        assert len(packet) == 24+outsize+errsize+size
        out, err, assembly = packet[24:24+outsize], packet[24+outsize:24+outsize+errsize], packet[24+outsize+errsize:]
        (folder/'assembly.s').write_bytes(assembly)
        record = {'unit': unit, 'code': code, 'process_exit': compiled.returncode,
            'stdout': out.decode(errors='replace'), 'stderr': err.decode(errors='replace'),
            'assembly_bytes': size, 'assembly_sha256': hashlib.sha256(assembly).hexdigest(),
            'job_sha256': digest(folder/'job.bin'),
            'files_sha256': {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}
        (folder/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
        assert code == compiled.returncode == 0 and not out and not err and size, record
        operation, width = unit[5:-1], unit[-1]
        exports = ([f'__sync_bool_compare_and_swap_{width}', f'__sync_val_compare_and_swap_{width}',
                    f'__sync_lock_test_and_set_{width}'] if operation == 'cas' else
                   [f'__sync_fetch_and_{operation}_{width}', f'__sync_{operation}_and_fetch_{width}'])
        for name in exports:
            assert re.search(rb'(?m)^'+name.encode()+rb':\s*$', assembly), 'missing '+name
        units.append(record)
        print(unit, size, 'assembly bytes', flush=True)
    evidence = {'scope': __doc__, 'gcc_archive_sha512': SHA512, 'units': units,
        'elf_sha256': prior['elf_sha256'], 'qemu_sha256': prior['qemu_sha256'],
        'project_sources_sha256': project, 'target_header_sha256': base['target_header_sha256']}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
