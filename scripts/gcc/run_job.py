"""Run an existing GCCJOB1 through actual GCC and copy lowering inside Space.

The host concatenates the prepared boot image and the unchanged input job,
services primitive Space channels, and saves the GCCOUT1 response. It does
not preprocess or compile the job's C or interpret generated instructions.
"""
import argparse
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path
from check_result import check_direct

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tests'))
from space_segments import execute_segments


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--job', type=Path, help='required for a fresh run; inherited on a checkpoint fork')
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--emulator', type=Path)
    continuation = parser.add_mutually_exclusive_group()
    continuation.add_argument('--resume', action='store_true')
    continuation.add_argument('--checkpoint-from', type=Path,
                              help='fork a frozen run into new artifacts, optionally using a new emulator')
    parser.add_argument('--segment-ticks', type=int, default=10000000)
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--max-parts', type=int, default=512)
    parser.add_argument('--direct-ticks', type=int, default=100000,
                        help='tick limit for the resulting direct program')
    parser.add_argument('--direct-timeout', type=float, default=120,
                        help='wall time limit for direct execution in seconds')
    expected = parser.add_mutually_exclusive_group()
    expected.add_argument('--expect-result', type=lambda text: int(text, 0),
                          help='also execute the resulting direct image and check uint32 OUT')
    expected.add_argument('--expect-trap', action='store_true',
                          help='also execute the resulting direct image; require idle without OUT')
    args = parser.parse_args()
    if (args.segment_ticks < 1 or args.max_parts < 1 or args.timeout <= 0
            or args.direct_ticks < 1 or args.direct_timeout <= 0):
        parser.error('execution limits must be positive')
    if args.expect_result is not None and not 0 <= args.expect_result <= 0xffffffff:
        parser.error('--expect-result must fit uint32')
    if not args.resume and not args.checkpoint_from and not args.job:
        parser.error('a fresh run requires --job')
    if args.resume and args.emulator:
        parser.error('resume uses the frozen emulator')
    image = args.image.resolve()
    manifest = json.loads((image/'image.json').read_text())
    assert manifest.get('framed_output'), 'GCCOUT1 image required'
    assert digest(image/'gcc.stream') == manifest['stream_sha256'], 'changed image'
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=args.resume)
    configuration = {'stream_sha256': manifest['stream_sha256'],
        'segment_ticks': args.segment_ticks, 'expect_result': args.expect_result,
        'expect_trap': args.expect_trap}
    origin = args.checkpoint_from.resolve() if args.checkpoint_from else None
    if origin:
        assert origin != root, 'checkpoint fork requires a new artifacts directory'
        assert json.loads((origin/'image.json').read_text()) == manifest, 'changed checkpoint image manifest'
        recorded = json.loads((origin/'configuration.json').read_text())
        assert all(recorded[k] == value for k, value in configuration.items()), 'changed checkpoint configuration'
        for name, key in [('job.bin', 'job_sha256'), ('in.bin', 'input_sha256'), ('emulator', 'emulator_sha256')]:
            assert digest(origin/name) == recorded[key], 'changed checkpoint '+name
        if args.job:
            assert digest(args.job) == recorded['job_sha256'], 'changed checkpoint job'
    if args.resume:
        assert json.loads((root/'image.json').read_text()) == manifest, 'changed image manifest'
        recorded = json.loads((root/'configuration.json').read_text())
        assert all(recorded[k] == value for k, value in configuration.items()), 'changed run configuration'
        if args.job:
            assert digest(args.job) == recorded['job_sha256'], 'changed job'
        configuration = recorded
    else:
        job = (args.job if args.job else origin/'job.bin').read_bytes()
        assert 16 <= len(job) <= 16*1024*1024 and job[:8] == b'GCCJOB1\0', 'expected GCCJOB1'
        (root/'job.bin').write_bytes(job)
        profiles = {2097152: 'space', 67108864: 'space-64m', 268435456: 'space-256m'}
        emulator = args.emulator.resolve() if args.emulator else ROOT/'build/bin'/profiles[manifest['space_bytes']]
        shutil.copyfile(emulator, root/'emulator')
        (root/'emulator').chmod(0o755)
        shutil.copyfile(__file__, root/'run.py')
        shutil.copyfile(image/'image.json', root/'image.json')
        with (root/'in.bin').open('wb') as target, (image/'gcc.stream').open('rb') as source:
            shutil.copyfileobj(source, target, 1024*1024)
            target.write(job)
        configuration.update(job_sha256=digest(root/'job.bin'), input_sha256=digest(root/'in.bin'),
                             emulator_sha256=digest(root/'emulator'))
        if origin:
            assert configuration['input_sha256'] == recorded['input_sha256'], 'changed checkpoint input'
            configuration['forked_from'] = str(origin)
        (root/'configuration.json').write_text(json.dumps(configuration, indent=2)+'\n')
    for name, key in [('job.bin', 'job_sha256'), ('in.bin', 'input_sha256'), ('emulator', 'emulator_sha256')]:
        assert digest(root/name) == configuration[key], 'changed frozen '+name
    execution = execute_segments(root/'emulator', root/'space', root/'in.bin',
        space_bytes=manifest['space_bytes'], layer_bytes=manifest['layer_bits']//8,
        ticks=args.segment_ticks, timeout=args.timeout, compression='zstd',
        max_parts=args.max_parts, channels_only=True, resume=args.resume,
        fork_from=origin/'space' if origin else None)
    raw = (root/'space/space.bin').read_bytes()

    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))

    assert word(132128) == 10, 'GCC did not terminate'
    assert raw[:manifest['layer_bits']//8] == bytes(manifest['layer_bits']//8), 'Space is not idle'
    packet = (root/'space/program.in').read_bytes()
    assert len(packet) >= 24 and packet[:8] == b'GCCOUT1\0', 'missing GCCOUT1'
    status, outsize, errsize, size = struct.unpack_from('<IIII', packet, 8)
    assert status == word(132160) and len(packet) == 24+outsize+errsize+size
    assert outsize+errsize <= 16*1024*1024 and (not status or not size)
    (root/'stdout.bin').write_bytes(packet[24:24+outsize])
    (root/'stderr.bin').write_bytes(packet[24+outsize:24+outsize+errsize])
    result = packet[24+outsize+errsize:]
    (root/'result.bin').write_bytes(result)
    evidence = {'scope': 'Guest image and unchanged GCCJOB1 executed through primitive Space; '
                 'GCC identity is recorded in image.json.',
        'original_cc1_sha256': manifest.get('original_cc1_sha256'),
        'image_manifest_sha256': digest(root/'image.json'), **configuration, 'guest_status': word(132128),
        'guest_exit': status, 'stdout_bytes': outsize, 'stderr_bytes': errsize,
        'result_bytes': size, 'result_sha256': digest(root/'result.bin'), **execution}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    if status:
        raise SystemExit(status)
    if args.expect_result is not None or args.expect_trap:
        checked = check_direct(root, root/'direct', manifest, expected=args.expect_result,
                               trap=args.expect_trap, ticks=args.direct_ticks, timeout=args.direct_timeout)
        evidence.update(checked)
        (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK framed job inside Space: exit', status, '; result bytes', size, flush=True)


if __name__ == '__main__':
    main()
