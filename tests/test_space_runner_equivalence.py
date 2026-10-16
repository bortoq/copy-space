"""Replay a frozen GCC checkpoint with its original and current copy runners.

Compare the complete Space, OUT, channel events, copy count and stop reason.
The benchmark executes only generic copy/channel primitives; no guest ISA is
decoded here. CPU and wall times are observations, not correctness gates.
"""
import argparse
import gzip
import hashlib
import json
import resource
import shutil
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-run', type=Path, required=True)
    parser.add_argument('--checkpoint-index', type=int, default=0)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--ticks', type=int, default=1000000)
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    if args.ticks < 1 or args.repetitions < 1 or args.checkpoint_index < 0:
        parser.error('positive limits and nonnegative checkpoint index required')
    source = args.baseline_run.resolve()
    configuration = json.loads((source/'configuration.json').read_text())
    execution = json.loads((source/'space/execution.json').read_text())
    parts = json.loads((source/'space/segments.json').read_text())
    checkpoint = next(part for part in parts if part['part'] == args.checkpoint_index)
    assert checkpoint['stop'] == 'limit', 'require an active completed checkpoint'
    # Old compressed checkpoints are immutable while the source run continues.
    snapshot = source/'space'/f"part-{checkpoint['part']:04d}"/checkpoint['dump_file']
    assert snapshot.suffix == '.gz', 'choose a completed compressed checkpoint'
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    for name, key in [('emulator', 'emulator_sha256'), ('in.bin', 'input_sha256')]:
        shutil.copyfile(source/name, root/name)
        assert digest(root/name) == configuration[key] == execution[key], 'changed frozen '+name
    (root/'emulator').chmod(0o755)
    initial = root/'initial.core'
    with gzip.open(snapshot, 'rb') as incoming, initial.open('wb') as target:
        size = 0
        while chunk := incoming.read(1024*1024):
            if any(chunk):
                target.seek(size)
                target.write(chunk)
            size += len(chunk)
        target.truncate(size)
    assert size == execution['space_bytes'] and digest(initial) == checkpoint['dump_sha256']
    paths = [Path('src')/name for name in
             ('space_main.c', 'space_run.c', 'core.c', 'space_trace.c', 'space.c', 'bitcopy.c')]
    paths += [path.relative_to(ROOT) for path in (ROOT/'src').glob('*.h')]
    for path in paths:
        destination = root/'sources'/path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/path, destination)
    candidate = root/'candidate'
    command = ['gcc', '-O2', '-g', '-std=c99', '-Wall', '-Wextra', '-Werror',
               '-I'+str(root/'sources/src'), '-DVM_SPACE_BYTES='+str(size)]
    command += [str(root/'sources'/path) for path in paths if path.suffix == '.c']
    command += ['-o', str(candidate)]
    (root/'compile.json').write_text(json.dumps(command, indent=2)+'\n')
    compiled = subprocess.run(command, capture_output=True)
    (root/'compile.stdout').write_bytes(compiled.stdout)
    (root/'compile.stderr').write_bytes(compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    results, expected = [], None
    for repetition in range(args.repetitions):
        # Alternate order so background work is less likely to bias one runner.
        for name in (('baseline', 'candidate') if repetition % 2 == 0 else ('candidate', 'baseline')):
            folder = root/f'{repetition}-{name}'
            folder.mkdir()
            emulator = root/'emulator' if name == 'baseline' else candidate
            command = [str(emulator), '--ticks', str(args.ticks), '--core', str(initial),
                       '--trace-channels', str(folder/'trace.txt'), '--dump-space', str(folder/'space.bin')]
            (folder/'command.json').write_text(json.dumps(command)+'\n')
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            started = time.monotonic()
            with (root/'in.bin').open('rb') as incoming:
                incoming.seek(checkpoint['input_after'])
                completed = subprocess.run(command, stdin=incoming, capture_output=True, timeout=300)
            wall = time.monotonic()-started
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu = after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime
            (folder/'out.bin').write_bytes(completed.stdout)
            (folder/'stderr.txt').write_bytes(completed.stderr)
            assert completed.returncode == 0 and not completed.stderr, completed.stderr
            assert (folder/'space.bin').stat().st_size == size
            actual = {file: digest(folder/file) for file in ('space.bin', 'out.bin', 'trace.txt')}
            if expected is None:
                expected = actual
            assert actual == expected, (name, repetition, actual, expected)
            record = {'runner': name, 'repetition': repetition, 'wall_seconds': wall,
                      'cpu_seconds': cpu, 'sha256': actual}
            results.append(record)
            (folder/'evidence.json').write_text(json.dumps(record, indent=2)+'\n')
            # All complete dumps have the same verified hash; retain one copy.
            if name != 'baseline' or repetition:
                (folder/'space.bin').unlink()
            print(name, repetition, f'CPU {cpu:.3f}s; wall {wall:.3f}s; exact state/OUT/events', flush=True)
    median = {name: statistics.median(record['cpu_seconds'] for record in results if record['runner'] == name)
              for name in ('baseline', 'candidate')}
    evidence = {'scope': __doc__, 'source_run': str(source), 'checkpoint': checkpoint,
                'ticks': args.ticks, 'repetitions': args.repetitions, 'space_bytes': size,
                'baseline_sha256': digest(root/'emulator'), 'candidate_sha256': digest(candidate),
                'source_sha256': {str(path): digest(root/'sources'/path) for path in paths},
                'median_cpu_seconds': median, 'cpu_speedup': median['baseline']/median['candidate'],
                'results': results}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK exact checkpoint replay; observed CPU speedup', evidence['cpu_speedup'], flush=True)


if __name__ == '__main__':
    main()
