"""Execute copies exceeding the default label, jump and call capacities."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--assembly', type=Path)
    parser.add_argument('--expected-result', type=int, default=43)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    paths = ['tests/fixtures/gcc/copy_link.c'] + ['runtime/gcc/'+name for name in
             ('copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]
    hashes = {}
    for name in paths:
        dest = root/'sources'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dest)
        hashes[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    sources = [str(root/'sources'/name) for name in paths if name.endswith('.c')]

    def build(name, limits):
        command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-DCS_COPY_PROGRAM',
                   '-DCS_COPY_RESULT_ADDRESS_BITS=31', '-DCS_COPY_IMAGE_BYTES=8388608',
                   '-DCS_COPY_ASSEMBLY_BYTES=65536', '-I'+str(root/'sources/runtime/gcc')]
        command += ['-DCS_COPY_'+key+'_CAPACITY='+str(value) for key, value in limits.items()]
        command += sources + ['-o', str(root/name)]
        (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
        subprocess.run(command, check=True, capture_output=True)
        return root/name

    default = build('default', {})
    limits = {'LABEL': 128, 'JUMP': 512, 'CALL': 64}
    expanded = build('expanded', limits)
    isolated = {key: build('limit-'+key, {k: v for k, v in limits.items() if k != key})
                for key in limits}
    cases = [
        (b'value:\ncopy.jmpa end\n'+b''.join(('unused%d:\n'%i).encode() for i in range(40))+
         b'end:\ncopy.ret\n', 3),
        (b'value:\ncopy.cmp $r0,$r0\n'+b''.join(('copy.branch.eq .L%d\n.L%d:\n'%(i, i)).encode() for i in range(80))+
         b'copy.ret\n', 3),
        (b'value:\n'+b'copy.jsra helper\n'*40+b'copy.ret\nhelper:\ncopy.inc $r0,1\ncopy.ret\n', 43)]
    if args.assembly:
        cases.append((args.assembly.read_bytes(), args.expected_result))
    evidence = []
    for index, (assembly, expected) in enumerate(cases):
        folder = root/str(index)
        folder.mkdir()
        (folder/'input.s').write_bytes(assembly)
        # Each capacity is tested independently, with the other two expanded.
        for key in limits:
            result = subprocess.run([str(isolated[key])], input=assembly, capture_output=True)
            (folder/('limit-'+key+'.json')).write_text(json.dumps({'exit': result.returncode}))
            if index == {'LABEL': 0, 'JUMP': 1, 'CALL': 2}[key]:
                assert result.returncode == 2 and not result.stdout, (index, key)
        rejected = subprocess.run([str(default)], input=assembly, capture_output=True)
        assert rejected.returncode == 2 and not rejected.stdout
        image = subprocess.run([str(expanded)], input=assembly, capture_output=True, check=True).stdout
        assert len(image) == 8388608
        (folder/'image.bin').write_bytes(image)
        command = [str(ROOT/'build/bin/space-256m'), '--ticks', '100000',
                   '--core', str(folder/'image.bin'), '--trace', str(folder/'trace.txt')]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        run = subprocess.run(command, capture_output=True, check=True, timeout=120)
        (folder/'out.bin').write_bytes(run.stdout)
        assert not run.stderr and run.stdout == struct.pack('<I', expected), (index, run.stdout)
        with (folder/'trace.txt').open('rb') as trace:
            trace.seek(max(0, (folder/'trace.txt').stat().st_size-80))
            assert trace.read().endswith(b' idle\n')
        evidence.append({'case': index, 'result': expected,
                         'image_sha256': hashlib.sha256(image).hexdigest()})
    (root/'evidence.json').write_text(json.dumps({'source_sha256': hashes, 'cases': evidence,
        'scope': 'Native linker preparation; generated copies execute in Space. Not GCC in Space.'}, indent=2)+'\n')
    print('OK configurable capacities:', len(cases), 'direct programs')


if __name__ == '__main__':
    main()
