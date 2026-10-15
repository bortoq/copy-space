"""Compare full and channel-only observers against the same complete Space state."""
import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'modules'))
from rv32i import Image, Layout
from space_trace_audit import audit_trace
from space_segments import execute_segments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source_paths = [Path('src') / name for name in ('space_main.c', 'space_run.c', 'core.c', 'space_trace.c', 'space.c', 'bitcopy.c')]
    source_paths += [p.relative_to(ROOT) for p in (ROOT / 'src').glob('*.h')]
    for path in source_paths:
        dest = root / 'sources' / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / path).read_bytes())
    hashes = {str(p): hashlib.sha256((root / 'sources' / p).read_bytes()).hexdigest() for p in source_paths}
    program = b''.join(word.to_bytes(4, 'little') for word in (
        0x73, 0x00100513, 0x04000893, 0x73, 0x00000513, 0x03f00893, 0x73,
        0x00100513, 0x04000893, 0x73, 0x00000513, 0x05d00893, 0x73))
    incoming = b'ABCDEFGHIJKLMNOPunused input!'
    (root / 'input.bin').write_bytes(incoming)
    evidence = []
    for size in (2097152, 67108864, 268435456):
        folder = root / str(size)
        folder.mkdir()
        compiler = ['gcc', '-O2', '-g', '-std=c99', '-Wall', '-Wextra', '-Werror', '-I' + str(root / 'sources/src'), '-DVM_SPACE_BYTES=' + str(size)]
        compiler += [str(root / 'sources' / p) for p in source_paths if p.suffix == '.c'] + ['-o', str(folder / 'space')]
        (folder / 'compile.json').write_text(json.dumps(compiler) + '\n')
        subprocess.run(compiler, check=True, capture_output=True)
        baseline = ROOT / 'build/bin' / {2097152:'space',67108864:'space-64m',268435456:'space-256m'}[size]
        shutil.copyfile(baseline, folder / 'baseline-space')
        (folder / 'baseline-space').chmod(0o755)
        image, manifest = Image(io=True, memory_bytes=65536, layout=Layout(size)).build().encode(program, registers={10: 0, 11: 4096, 12: 8, 17: 63})
        # Sparse preparation avoids writing the zero part of the initial image.
        with (folder / 'initial.core').open('wb') as f:
            for at in range(0, len(image), 1048576):
                block = image[at:at+1048576]
                if block != bytes(len(block)):
                    f.seek(at)
                    f.write(block)
            f.truncate(len(image))
        del image
        results = []
        full_state = None
        full_trace = None
        for name, reduced in (('baseline',False),('full',False),('channels',True)):
            mode = folder / name
            mode.mkdir()
            executable = folder / ('baseline-space' if name == 'baseline' else 'space')
            command = [str(executable), '--core', str(folder / 'initial.core'), '--trace-channels' if reduced else '--trace', str(mode / 'trace.txt'), '--dump-space', str(mode / 'space.bin')]
            (mode / 'command.json').write_text(json.dumps(command) + '\n')
            started = time.monotonic()
            result = subprocess.run(command, input=incoming, capture_output=True, timeout=60)
            elapsed = time.monotonic() - started
            (mode / 'out.bin').write_bytes(result.stdout)
            assert result.returncode == 0 and not result.stderr and result.stdout == incoming[:16]
            raw = (mode / 'space.bin').read_bytes()
            assert len(raw) == size
            if name != 'baseline':
                assert raw == full_state
            else:
                full_state = raw
            trace = (mode / 'trace.txt').read_bytes()
            if name == 'baseline':
                full_trace = trace
            elif name == 'full':
                assert trace == full_trace
            with gzip.open(mode / 'trace.txt.gz', 'wb') as f:
                f.write(trace)
            (mode / 'trace.txt').unlink()
            with gzip.open(mode / 'space.bin.gz', 'wb', compresslevel=1) as f:
                f.write(raw)
            (mode / 'space.bin').unlink()
            cursor = {}
            copies, channels, last = audit_trace(mode / 'trace.txt.gz', cursor, channels_only=reduced)
            assert last.endswith(b' idle\n') and cursor == {1: 16, 2: 16}
            results.append({'mode': name, 'emulator_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(), 'copy_events': copies, 'channel_events': channels,
                            'trace_bytes': len(trace), 'snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'seconds': elapsed})
        assert len({r['copy_events'] for r in results}) == 1
        assert len({r['channel_events'] for r in results}) == 1
        assert results[2]['trace_bytes'] < results[1]['trace_bytes']
        if size == 2097152:
            segmented = execute_segments(folder / 'space', folder / 'resumed', root / 'input.bin',
                space_bytes=size, layer_bytes=manifest['layer_bits']//8, ticks=10, timeout=30,
                initial_core=folder / 'initial.core', channels_only=True, compression='gzip')
            assert (folder / 'resumed/space.bin').read_bytes() == full_state
            assert (folder / 'resumed/program.in').read_bytes() == incoming[:16]
            assert segmented['copy_events'] == results[0]['copy_events']
            seed = folder / 'fork-source'
            try:
                execute_segments(folder/'baseline-space', seed, root/'input.bin', space_bytes=size,
                    layer_bytes=manifest['layer_bits']//8, ticks=10, timeout=30, max_parts=5,
                    initial_core=folder/'initial.core', compression='gzip')
            except AssertionError as error:
                assert str(error) == 'space exceeded the segment limit'
            else:
                raise AssertionError('fork source unexpectedly completed')
            assert (seed/'program.in').read_bytes() == incoming[:8]
            with (seed/'program.in').open('ab') as f:
                f.write(b'unverified partial output')
            fork = folder / 'fork-channels'
            try:
                execute_segments(folder/'space', fork, root/'input.bin', space_bytes=size,
                    layer_bytes=manifest['layer_bits']//8, ticks=20, timeout=30, max_parts=1,
                    fork_from=seed, channels_only=True, compression='gzip')
            except AssertionError as error:
                assert str(error) == 'space exceeded the segment limit'
            else:
                raise AssertionError('fork phase unexpectedly completed')
            assert (fork/'program.in').read_bytes() == incoming[:8]
            origin_path = fork/'origin.json'
            origin_saved = origin_path.read_bytes()
            origin_path.write_bytes(origin_saved+b' ')
            try:
                execute_segments(folder/'space', fork, root/'input.bin', space_bytes=size,
                    layer_bytes=manifest['layer_bits']//8, ticks=20, timeout=30,
                    resume=True, channels_only=True, compression='gzip')
            except AssertionError as error:
                assert str(error) == 'changed execution input/configuration'
            else:
                raise AssertionError('changed origin metadata accepted')
            finally:
                origin_path.write_bytes(origin_saved)
            forked = execute_segments(folder/'space', fork, root/'input.bin', space_bytes=size,
                layer_bytes=manifest['layer_bits']//8, ticks=20, timeout=30,
                resume=True, channels_only=True, compression='gzip')
            assert (fork/'program.in').read_bytes() == incoming[:16]
            assert (fork/'space.bin').read_bytes() == full_state
            assert forked['copy_events'] == results[0]['copy_events']
            assert forked['channel_events'] == results[0]['channel_events']
            assert (seed/'program.in').read_bytes() == incoming[:8]+b'unverified partial output'
            metadata = seed/'segments.json'
            saved = metadata.read_bytes()
            damaged = json.loads(saved)
            damaged[-1]['dump_sha256'] = '0'*64
            metadata.write_text(json.dumps(damaged))
            try:
                try:
                    execute_segments(folder/'space', folder/'fork-bad-checkpoint', root/'input.bin',
                        space_bytes=size, layer_bytes=manifest['layer_bits']//8, ticks=20,
                        timeout=30, fork_from=seed, channels_only=True, compression='gzip')
                except AssertionError as error:
                    assert str(error) == 'changed fork checkpoint'
                else:
                    raise AssertionError('damaged fork checkpoint accepted')
            finally:
                metadata.write_bytes(saved)
            changed_input = root/'changed-input.bin'
            changed_input.write_bytes(incoming+b'changed')
            for name, data, layout_size, layer in (
                ('input', changed_input, size, manifest['layer_bits']//8),
                ('space', root/'input.bin', size*2, manifest['layer_bits']//8),
                ('layer', root/'input.bin', size, manifest['layer_bits']//8+1)):
                try:
                    execute_segments(folder/'space', folder/('fork-bad-'+name), data,
                        space_bytes=layout_size, layer_bytes=layer, ticks=20,
                        timeout=30, fork_from=seed, channels_only=True, compression='gzip')
                except AssertionError as error:
                    assert str(error) == 'changed fork input/layout'
                else:
                    raise AssertionError(('changed fork input/layout accepted', name))
            evidence.append({'fork_test': forked, 'unverified_output_excluded': True,
                             'changed_checkpoint_rejected': True, 'changed_origin_rejected': True,
                             'changed_input_and_layout_rejected': True})
        evidence.append({'space_bytes': size, 'runs': results})
        print('OK observers:', size, results[0]['copy_events'], 'copies;', results[1]['trace_bytes'], '->', results[2]['trace_bytes'], 'trace bytes', flush=True)
        del full_state, raw
    # Refuse mixed CLI modes before creating either trace file.
    for options in (['--trace', str(root/'bad-full'), '--trace-channels', str(root/'bad-channels')],
                    ['--trace-channels', str(root/'bad-channels'), '--trace', str(root/'bad-full')]):
        result = subprocess.run([str(root/'2097152/space')] + options, capture_output=True)
        assert result.returncode == 1 and b'choose one trace mode' in result.stderr
        assert not (root/'bad-full').exists() and not (root/'bad-channels').exists()
    corrupt = [b'stop 0 idle\n', b'counts 1 1\nstop 0 idle\n', b'counts -1 0\nstop 0 idle\n',
               b'counts 1 0\ncounts 1 0\nstop 0 idle\n', b'counts 1 0\ncopy 0 3 1 2 3\nstop 1 idle\n',
               b'counts 1 0\nchannel 0 1 8 0 8 0\nstop 1 idle\n', b'counts 18446744073709551616 0\nstop 0 idle\n']
    for i, trace in enumerate(corrupt):
        path = root / f'invalid-{i}.gz'
        with gzip.open(path, 'wb') as f:
            f.write(trace)
        try:
            audit_trace(path, channels_only=True)
        except AssertionError:
            pass
        else:
            raise AssertionError(('invalid channel-only trace accepted', i))
    (root / 'evidence.json').write_text(json.dumps({'source_sha256': hashes, 'profiles': evidence, 'rejected_traces': len(corrupt)}, indent=2) + '\n')


if __name__ == '__main__':
    main()
