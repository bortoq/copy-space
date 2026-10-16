"""Check the framed job runner with the frozen guest adapter fixture, not GCC."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True,
                        help='completed gcc-framed-main-integration artifacts')
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    fixture, root = args.fixture.resolve(), args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    image = root/'fixture-image'
    image.mkdir()
    stream = (fixture/'program.stream').read_bytes()
    original = json.loads((fixture/'evidence.json').read_text())
    assert original['scope'] == 'guest newlib operations only; not GCC execution'
    manifest = json.loads((fixture/'program.stream.json').read_text())
    manifest.update(framed_output=True, stream_sha256=hashlib.sha256(stream).hexdigest(),
                    scope='Guest adapter fixture only; not GCC execution')
    (image/'gcc.stream').write_bytes(stream)
    (image/'image.json').write_text(json.dumps(manifest, indent=2)+'\n')
    incoming = (fixture/'in.bin').read_bytes()
    assert incoming.startswith(stream)
    job = incoming[len(stream):]
    (root/'job.bin').write_bytes(job)
    runner = root/'run_job.py'
    shutil.copyfile(ROOT/'scripts/gcc/run_job.py', runner)
    # The script locates shared Space helpers from the repository root.
    command = [sys.executable, str(ROOT/'scripts/gcc/run_job.py'), '--image', str(image),
               '--artifacts', str(root/'run'), '--segment-ticks', '100000']

    def run(name, extra):
        argv = command+extra
        (root/(name+'-command.json')).write_text(json.dumps(argv)+'\n')
        result = subprocess.run(argv, capture_output=True, timeout=180)
        (root/(name+'.stdout')).write_bytes(result.stdout)
        (root/(name+'.stderr')).write_bytes(result.stderr)
        return result

    limited = run('limited', ['--job', str(root/'job.bin'), '--max-parts', '1'])
    assert limited.returncode and b'space exceeded the segment limit' in limited.stderr
    segments = root/'run/space/segments.json'
    checkpoint = segments.read_bytes()
    rejected = []
    for name, relative, message in [
        ('job', 'job.bin', b'changed frozen job.bin'),
        ('input', 'in.bin', b'changed frozen in.bin'),
        ('emulator', 'emulator', b'changed frozen emulator')]:
        path = root/'run'/relative
        data = path.read_bytes()
        try:
            path.write_bytes(data[:-1]+bytes([data[-1]^1]))
            result = run('changed-'+name, ['--resume'])
            assert result.returncode and message in result.stderr
            fork_rejected = run('changed-fork-'+name, ['--artifacts', str(root/('bad-fork-'+name)),
                                '--checkpoint-from', str(root/'run')])
            assert fork_rejected.returncode and ('changed checkpoint '+relative).encode() in fork_rejected.stderr
            assert segments.read_bytes() == checkpoint, 'rejection advanced execution'
        finally:
            path.write_bytes(data)
        rejected.append(name)
    path = image/'image.json'
    data = path.read_bytes()
    try:
        changed = dict(manifest, scope='changed fixture manifest')
        path.write_text(json.dumps(changed)+'\n')
        result = run('changed-manifest', ['--resume'])
        assert result.returncode and b'changed image manifest' in result.stderr
        fork_rejected = run('changed-fork-manifest', ['--artifacts', str(root/'bad-fork-manifest'),
                            '--checkpoint-from', str(root/'run')])
        assert fork_rejected.returncode and b'changed checkpoint image manifest' in fork_rejected.stderr
        assert segments.read_bytes() == checkpoint
    finally:
        path.write_bytes(data)
    rejected.append('manifest')
    fork_rejected = run('changed-fork-expectation', ['--artifacts', str(root/'bad-fork-expectation'),
                        '--checkpoint-from', str(root/'run'), '--expect-result', '17'])
    assert fork_rejected.returncode and b'changed checkpoint configuration' in fork_rejected.stderr
    fork = run('fork', ['--artifacts', str(root/'fork'), '--checkpoint-from', str(root/'run')])
    assert fork.returncode == 0, fork.stderr
    assert segments.read_bytes() == checkpoint, 'fork changed its source checkpoint'
    assert (root/'fork/space/program.in').read_bytes() == bytes.fromhex(original['output_hex'])
    fork_evidence = json.loads((root/'fork/evidence.json').read_text())
    assert fork_evidence['guest_exit'] == 0 and fork_evidence['origin_sha256']
    assert fork_evidence['forked_from'] == str(root/'run')
    assert json.loads((root/'fork/space/origin.json').read_text())['checkpoint_sha256'] == json.loads(checkpoint)[-1]['dump_sha256']
    result = run('resume', ['--resume'])
    assert result.returncode == 0, result.stderr
    assert (root/'run/space/program.in').read_bytes() == bytes.fromhex(original['output_hex'])
    assert (root/'run/stdout.bin').read_bytes() == b'a\0b'
    assert (root/'run/stderr.bin').read_bytes() == b'warn'
    assert (root/'run/result.bin').read_bytes() == b'copy'
    evidence = json.loads((root/'run/evidence.json').read_text())
    assert evidence['guest_exit'] == 0 and evidence['original_cc1_sha256'] is None
    assert len(json.loads(segments.read_text())) > 1
    (root/'evidence.json').write_text(json.dumps({'scope': __doc__, 'rejected_changes': rejected,
        'fork_rejected_changes': rejected+['expectation'],
        'runner_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(),
        'output_hex': original['output_hex'], 'copy_events': evidence['copy_events'],
        'fork_copy_events': fork_evidence['copy_events'], 'fork_source_preserved': True}, indent=2)+'\n')
    print('OK framed runner fixture: limit/resume/fork, four resume and five fork rejections; exact response; not GCC')


if __name__ == '__main__':
    main()
