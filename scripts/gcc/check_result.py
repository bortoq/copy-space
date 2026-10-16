"""Execute a completed Space GCC job's frozen result as direct copies.

This also works when the original runner finished GCC but exhausted its
direct execution limit. Compiler execution and its artifacts are preserved.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_direct(root, destination, manifest, *, expected=None, trap=False,
                 ticks=100000, timeout=120):
    if (expected is None) == (not trap):
        raise ValueError('require exactly one expected result or trap')
    if ticks < 1 or timeout <= 0:
        raise ValueError('execution limits must be positive')
    if expected is not None and not 0 <= expected <= 0xffffffff:
        raise ValueError('expected result must fit uint32')
    result = root/'result.bin'
    assert result.stat().st_size == manifest['copy_program_bytes'], 'unexpected direct image size'
    destination.mkdir(parents=True, exist_ok=False)
    command = [str(root/'emulator'), '--ticks', str(ticks), '--core', str(result),
               '--trace-channels', str(destination/'trace.txt')]
    (destination/'command.json').write_text(json.dumps(command)+'\n')
    checked = subprocess.run(command, capture_output=True, timeout=timeout)
    (destination/'out.bin').write_bytes(checked.stdout)
    (destination/'stderr.txt').write_bytes(checked.stderr)
    assert checked.returncode == 0 and not checked.stderr, checked.stderr
    assert (destination/'trace.txt').read_bytes().endswith(b' idle\n'), 'direct image did not terminate'
    assert checked.stdout == (b'' if trap else struct.pack('<I', expected)), 'unexpected direct OUT'
    return {'direct_output_hex': checked.stdout.hex(), 'direct_stop': 'idle',
            'direct_ticks': ticks, 'result_sha256': digest(result),
            'emulator_sha256': digest(root/'emulator')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True, help='completed run_job.py artifacts')
    parser.add_argument('--artifacts', type=Path, required=True, help='new directory for direct verification')
    expected = parser.add_mutually_exclusive_group(required=True)
    expected.add_argument('--expect-result', type=lambda text: int(text, 0))
    expected.add_argument('--expect-trap', action='store_true')
    parser.add_argument('--ticks', type=int, default=10000000)
    parser.add_argument('--timeout', type=float, default=300)
    args = parser.parse_args()
    root = args.run.resolve()
    evidence = json.loads((root/'evidence.json').read_text())
    manifest = json.loads((root/'image.json').read_text())
    configuration = json.loads((root/'configuration.json').read_text())
    assert evidence['guest_status'] == 10 and evidence['guest_exit'] == 0, 'GCC did not finish successfully'
    assert digest(root/'image.json') == evidence['image_manifest_sha256'], 'changed image manifest'
    assert manifest['stream_sha256'] == evidence['stream_sha256'] == configuration['stream_sha256']
    for name, key in [('job.bin', 'job_sha256'), ('in.bin', 'input_sha256'),
                      ('emulator', 'emulator_sha256')]:
        assert digest(root/name) == evidence[key] == configuration[key], 'changed frozen '+name
    assert digest(root/'result.bin') == evidence['result_sha256'], 'changed result'
    packet = (root/'space/program.in').read_bytes()
    stdout, stderr, result = ((root/name).read_bytes() for name in ('stdout.bin', 'stderr.bin', 'result.bin'))
    header = b'GCCOUT1\0'+struct.pack('<IIII', 0, len(stdout), len(stderr), len(result))
    assert len(stdout)+len(stderr) <= 16*1024*1024 and packet == header+stdout+stderr+result, 'changed GCCOUT1 response'
    destination = args.artifacts.resolve()
    checked = check_direct(root, destination, manifest, expected=args.expect_result,
                           trap=args.expect_trap, ticks=args.ticks, timeout=args.timeout)
    checked.update(scope=__doc__, run=str(root), run_evidence_sha256=digest(root/'evidence.json'),
                   job_sha256=evidence['job_sha256'], stream_sha256=manifest['stream_sha256'])
    (destination/'evidence.json').write_text(json.dumps(checked, indent=2)+'\n')
    print('OK frozen GCC result: direct OUT', checked['direct_output_hex'], '; idle', flush=True)


if __name__ == '__main__':
    main()
