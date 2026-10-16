"""Verify independent direct-result checks against a completed Space job."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--expected', type=lambda text: int(text, 0), required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    fixture = root/'fixture'
    (fixture/'space').mkdir(parents=True)
    for name in ('evidence.json', 'configuration.json', 'image.json', 'job.bin', 'in.bin',
                 'emulator', 'result.bin', 'stdout.bin', 'stderr.bin', 'space/program.in'):
        shutil.copyfile(args.fixture/name, fixture/name)
    (fixture/'emulator').chmod(0o755)
    command = [sys.executable, str(ROOT/'scripts/gcc/check_result.py'), '--run', str(fixture),
               '--expect-result', str(args.expected)]

    def run(name, extra=()):
        argv = command+['--artifacts', str(root/name)]+list(extra)
        (root/(name+'-command.json')).write_text(json.dumps(argv)+'\n')
        result = subprocess.run(argv, capture_output=True, timeout=300)
        (root/(name+'.stdout')).write_bytes(result.stdout)
        (root/(name+'.stderr')).write_bytes(result.stderr)
        return result

    original = (fixture/'evidence.json').read_bytes()
    passed = run('success')
    assert passed.returncode == 0, passed.stderr
    checked = json.loads((root/'success/evidence.json').read_text())
    assert checked['direct_stop'] == 'idle'
    assert checked['direct_output_hex'] == args.expected.to_bytes(4, 'little').hex()
    rejected = []
    for name, extra, message in [
            ('limit', ['--ticks', '1'], b'direct image did not terminate'),
            ('wrong-output', ['--expect-result', str(args.expected ^ 1)], b'unexpected direct OUT')]:
        failed = run(name, extra)
        assert failed.returncode and message in failed.stderr, failed.stderr
        assert not (root/name/'evidence.json').exists()
        rejected.append(name)
    for name in ('result.bin', 'emulator', 'job.bin', 'in.bin', 'space/program.in'):
        path = fixture/name
        with path.open('r+b') as stream:
            byte = stream.read(1)
            stream.seek(0)
            stream.write(bytes([byte[0] ^ 1]))
        case = 'changed-'+name.replace('/', '-')
        try:
            failed = run(case)
            assert failed.returncode and b'changed' in failed.stderr, failed.stderr
            assert not (root/case).exists(), 'changed inputs reached execution'
        finally:
            with path.open('r+b') as stream:
                stream.write(byte)
        rejected.append(case)
    assert (fixture/'evidence.json').read_bytes() == original, 'compiler evidence changed'
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'rejected': rejected,
        'direct': checked, 'compiler_evidence_preserved': True}, indent=2)+'\n')
    print('OK direct result: successful execution, limit/output rejection and five changed-artifact rejections')


if __name__ == '__main__':
    main()
