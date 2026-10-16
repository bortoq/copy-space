"""Reject forged project runtime receipts without relaxing pinned GCC checks."""
import argparse
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/gcc'))
from job_format import pack_job, unpack_job
from package_target_library import package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producer', type=Path, required=True)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    producer = args.producer.resolve()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    receipt = json.loads((producer/'evidence.json').read_text())
    original = receipt['units'][0]
    unit = original['unit']
    folder = producer/unit
    argv, files = unpack_job((folder/'job.bin').read_bytes())
    source = next(name for name in files if name.startswith('project/'))
    rejected = []

    def reject(name, inputs, destination, message):
        try:
            package(inputs, args.store, destination)
        except ValueError as error:
            assert message in str(error), (name, error)
            assert not destination.exists(), 'rejected package was published'
            rejected.append({'name': name, 'error': str(error)})
        else:
            raise AssertionError('accepted '+name)

    # A real producer passes its unit checks, then correctly needs the GCC units.
    reject('real-project-needs-upstream', [producer], root/'incomplete', 'missing catalog units')
    for name in ('modified-source', 'extra-input', 'wrong-define', 'wrong-path', 'upstream-impersonation', 'wrong-compiler'):
        case = root/name
        forged = case/'producer'
        record, top = copy.deepcopy(original), copy.deepcopy(receipt)
        arguments, contents = argv[:], dict(files)
        if name == 'modified-source':
            contents[source] += b'\n/* unreviewed source change */\n'
            message = 'changed project runtime input'
        elif name == 'extra-input':
            contents['project/extra.c'] = b'int unrecorded;\n'
            message = 'unexpected project runtime inputs'
        elif name == 'wrong-define':
            arguments[arguments.index('-DL_'+unit)] = '-DL_sync_cas8'
            message = 'inconsistent compiler recipe'
        elif name == 'wrong-path':
            arguments[-1] = 'project/other.c'
            contents['project/other.c'] = contents.pop(source)
            message = 'inconsistent compiler recipe'
        elif name == 'upstream-impersonation':
            record['unit'] = 'muldi3'
            message = 'inconsistent compiler recipe'
        else:
            top['elf_sha256'] = '0'*64
            message = 'changed recorded producer executable'
        target = forged/record['unit']
        target.mkdir(parents=True)
        for filename in ('assembly.s', 'response.bin', 'command.json'):
            shutil.copyfile(folder/filename, target/filename)
        incoming = pack_job(arguments, contents)
        (target/'job.bin').write_bytes(incoming)
        record['job_sha256'] = hashlib.sha256(incoming).hexdigest()
        record['files_sha256'] = {key: hashlib.sha256(data).hexdigest() for key, data in contents.items()}
        for path, data in contents.items():
            dest = target/'inputs'/path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        (target/'evidence.json').write_text(json.dumps(record)+'\n')
        top['units'] = [record]
        (forged/'evidence.json').write_text(json.dumps(top)+'\n')
        reject(name, [forged], case/'package', message)
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'rejected': rejected,
        'producer': str(producer)}, indent=2)+'\n')
    print('OK project runtime provenance:', len(rejected), 'rejections', flush=True)


if __name__ == '__main__':
    main()
