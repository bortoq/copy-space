"""Execute direct copy programs with explicitly sized data/stack memory."""
import argparse
import gzip
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
    parser.add_argument('--assembly', type=Path, action='append')
    parser.add_argument('--expected-result', type=lambda s: int(s, 0), default=7)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    paths = ['tests/fixtures/gcc/copy_link.c'] + ['runtime/gcc/'+name for name in
        ('copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]
    for name in paths:
        dest = root/'sources'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dest)
    sources = [str(root/'sources'/name) for name in paths if name.endswith('.c')]

    def build(name, bits, memory=None, objects=False, image_bytes=2097152):
        command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-DCS_COPY_PROGRAM',
            '-DCS_COPY_RESULT_ADDRESS_BITS='+str(bits), '-DCS_COPY_IMAGE_BYTES='+str(image_bytes),
            '-I'+str(root/'sources/runtime/gcc')]
        if memory is not None:
            command += ['-DCS_COPY_MEMORY_BYTES='+str(memory)]
        if objects:
            command += ['-DCS_COPY_OBJECTS']
        command += sources+['-o', str(root/name)]
        (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
        subprocess.run(command, check=True, capture_output=True)
        return root/name

    memory = 1048576
    frame = (b'value:\ncopy.ldi.l $r2,131072\ncopy.sub $sp,$r2\n'
        b'copy.st.b ($sp),$r0\ncopy.mov $r3,$sp\ncopy.ldi.l $r2,131071\n'
        b'copy.add $r3,$r2\ncopy.st.b ($r3),$r1\ncopy.ld.b $r0,($sp)\n'
        b'copy.ld.b $r1,($r3)\ncopy.jsra helper\ncopy.ret\n'
        b'helper:\ncopy.add $r0,$r1\ncopy.ret\n')
    cases = [(b'value:\ncopy.mov $r0,$sp\ncopy.ret\n', memory-36),
        (b'value:\ncopy.jsra helper\ncopy.ret\nhelper:\ncopy.mov $r0,$sp\ncopy.ret\n', memory-48),
        (frame, 7),
        (b'value:\ncopy.ldi.l $r2,131071\ncopy.st.l ($r2),$r0\ncopy.ld.l $r0,($r2)\ncopy.ret\n', 3),
        (f'value:\ncopy.ldi.l $r2,{memory-1}\ncopy.st.b ($r2),$r0\ncopy.ld.b $r0,($r2)\ncopy.ret\n'.encode(), 3),
        (f'value:\ncopy.ldi.l $r2,{memory-4}\ncopy.st.l ($r2),$r0\ncopy.ld.l $r0,($r2)\ncopy.ret\n'.encode(), 3),
        (f'value:\ncopy.ldi.l $r2,{memory-3}\ncopy.ld.l $r0,($r2)\ncopy.ret\n'.encode(), None),
        (f'value:\ncopy.ldi.l $r2,{memory}\ncopy.ld.b $r0,($r2)\ncopy.ret\n'.encode(), None),
        (b'value:\ncopy.ldi.l $r2,4294967295\ncopy.ld.b $r0,($r2)\ncopy.ret\n', None),
        (b'value:\ncopy.ldi.l $r2,4294967295\ncopy.ldo.b $r0,1($r2)\ncopy.ret\n', 0)]
    cases += [
        (b'.bss\nlarge:\n.zero 131072\n.text\nvalue:\ncopy.lda.l $r0,large+131068\ncopy.ret\n', 0),
        (b'.data\narray:\n.zero 70000\n.byte 17\n.rodata\nother:\n.byte 34\n.data\n.byte 51\n.text\nvalue:\ncopy.lda.s $r0,array+70000\ncopy.ret\n', 0x3311),
        (b'.data\npointer:\n.long tail\n.zero 131072\n.rodata\ntail:\n.long 12345\n.text\nvalue:\ncopy.lda.l $r2,pointer\ncopy.ld.l $r0,($r2)\ncopy.ret\n', 12345),
        (b'.comm huge,196608,65536\n.text\nvalue:\ncopy.sta.l huge+196604,$r1\ncopy.lda.l $r0,huge+196604\ncopy.ret\n', 4),
        (b'.data\n.p2align 16\naligned:\n.long 7\n.text\nvalue:\ncopy.ldi.l $r0,aligned\ncopy.ret\n', 65536),
        (b'.bss\nexact:\n.zero 524032\n.text\nvalue:\ncopy.lda.l $r0,exact+524028\ncopy.ret\n', 0),
        (b''.join(b'.data\n.zero 1\n' if i%2==0 else b'.bss\n.zero 1\n' for i in range(256))+b'.text\nvalue:\ncopy.ret\n', 3),
        (b'.data\narray:\n'+b'.byte 1\n'*900+b'.text\nvalue:\ncopy.lda.b $r0,array+899\ncopy.ret\n', 1)]
    for assembly in args.assembly or []:
        cases.append((assembly.read_bytes(), args.expected_result))
    invalid_sections = [
        b'.bss\n.zero 524033\n.text\nvalue:\ncopy.ret\n',
        b'.data\n.byte 1\n.bss\n.balign 524288\n.zero 1\n.text\nvalue:\ncopy.ret\n',
        b'.data\n.p2align 20\n.long 0\n.text\nvalue:\ncopy.ret\n',
        b'.data\n.zero 4294967295\n.text\nvalue:\ncopy.ret\n',
        b''.join(b'.data\n.zero 1\n' if i%2==0 else b'.bss\n.zero 1\n' for i in range(257))+b'.text\nvalue:\ncopy.ret\n']
    evidence = []
    for bits, emulator in [(24, 'space'), (31, 'space-256m')]:
        native = build('native-'+str(bits), bits, memory)
        for index, assembly in enumerate(invalid_sections):
            (root/f'invalid-section-{index}.s').write_bytes(assembly)
            invalid = subprocess.run([str(native)], input=assembly, capture_output=True)
            assert invalid.returncode == 2 and not invalid.stdout
        for i, (assembly, expected) in enumerate(cases):
            folder = root/str(bits)/str(i)
            folder.mkdir(parents=True)
            (folder/'input.s').write_bytes(assembly)
            linked = subprocess.run([str(native)], input=assembly, capture_output=True, check=True)
            assert not linked.stderr and len(linked.stdout) == 2097152
            (folder/'image.bin').write_bytes(linked.stdout)
            command = [str(ROOT/'build/bin'/emulator), '--ticks', '10000', '--core', str(folder/'image.bin'),
                '--trace', str(folder/'trace.txt')]
            if i < 3:
                command += ['--dump-space', str(folder/'space.bin')]
            (folder/'command.json').write_text(json.dumps(command)+'\n')
            run = subprocess.run(command, capture_output=True, check=True, timeout=120)
            (folder/'out.bin').write_bytes(run.stdout)
            assert not run.stderr and run.stdout == (b'' if expected is None else struct.pack('<I', expected)), (bits, i, run.stdout.hex(), expected)
            with (folder/'trace.txt').open('rb') as log:
                log.seek(max(0, (folder/'trace.txt').stat().st_size-80))
                assert log.read().endswith(b' idle\n')
            if i < 3:
                raw = (folder/'space.bin').read_bytes()
                def word(at):
                    return sum(((raw[(at+j)//8] >> (7-(at+j)%8)) & 1) << j for j in range(32))
                assert word(32768) == word(32800) == memory
                with gzip.open(folder/'space.bin.gz', 'wb', compresslevel=1) as out:
                    out.write(raw)
                (folder/'space.bin').unlink()
            evidence.append({'address_bits': bits, 'case': i, 'expected': expected,
                'image_sha256': hashlib.sha256(linked.stdout).hexdigest()})
        # Existing ABI and new explicit 8192-byte mode produce identical images.
        old, explicit = build('default-'+str(bits), bits), build('small-'+str(bits), bits, 8192)
        for assembly, _ in cases:
            a = subprocess.run([str(old)], input=assembly, capture_output=True)
            b = subprocess.run([str(explicit)], input=assembly, capture_output=True)
            assert (a.returncode, a.stdout, a.stderr) == (b.returncode, b.stdout, b.stderr)
        obj = build('objects-'+str(bits), bits, memory, objects=True)
        pieces = frame.split(b'helper:\n')
        units = b'.global value\n'+pieces[0]+b'\0.global helper\nhelper:\n'+pieces[1]
        linked = subprocess.run([str(obj)], input=units, capture_output=True, check=True)
        # The resulting program must execute too; names can change code addresses.
        folder = root/str(bits)/'objects';folder.mkdir()
        (folder/'input.s').write_bytes(units);(folder/'image.bin').write_bytes(linked.stdout)
        command = [str(ROOT/'build/bin'/emulator), '--ticks', '10000', '--core', str(folder/'image.bin'), '--trace', str(folder/'trace.txt')]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        run = subprocess.run(command, capture_output=True, check=True, timeout=120)
        (folder/'out.bin').write_bytes(run.stdout)
        assert not run.stderr and run.stdout == struct.pack('<I', 7)
        # The one-object delegation also forwards the selected memory size.
        single = subprocess.run([str(obj)], input=frame, capture_output=True, check=True)
        direct = subprocess.run([str(native)], input=frame, capture_output=True, check=True)
        assert single.stdout == direct.stdout
        print('OK memory:', bits, 'bits;', len(cases), 'programs, two units and default ABI', flush=True)
    # Highest data-address bit available in the 256 MiB Space profile.
    large_memory = 134217728
    exe = build('native-maximum-memory', 31, large_memory, image_bytes=268435456)
    folder = root/'maximum-memory';folder.mkdir()
    assembly = (f'.data\nmaximum:\n.zero {large_memory//2-257}\n.byte 173\n.text\n'
        f'value:\ncopy.lda.b $r0,maximum+{large_memory//2-257}\ncopy.ldi.l $r2,{large_memory-4}\n'
        'copy.st.l ($r2),$r0\ncopy.ld.l $r0,($r2)\ncopy.ret\n').encode()
    (folder/'input.s').write_bytes(assembly)
    with (folder/'image.bin').open('wb') as out:
        linked = subprocess.run([str(exe)], input=assembly, stdout=out, stderr=subprocess.PIPE, check=True)
    assert not linked.stderr
    command = [str(ROOT/'build/bin/space-256m'), '--ticks', '10000', '--core', str(folder/'image.bin'),
        '--trace', str(folder/'trace.txt'), '--dump-space', str(folder/'space.bin')]
    (folder/'command.json').write_text(json.dumps(command)+'\n')
    run = subprocess.run(command, capture_output=True, check=True, timeout=120)
    (folder/'out.bin').write_bytes(run.stdout)
    assert not run.stderr and run.stdout == struct.pack('<I', 173)
    raw = (folder/'space.bin').read_bytes()
    def large_word(at):
        return sum(((raw[(at+j)//8] >> (7-(at+j)%8)) & 1) << j for j in range(32))
    assert large_word(32768) == large_word(32800) == large_memory
    for name in ('space.bin', 'image.bin'):
        with (folder/name).open('rb') as inp, gzip.open(folder/(name+'.gz'), 'wb', compresslevel=1) as out:
            shutil.copyfileobj(inp, out, 1048576)
        (folder/name).unlink()
    print('OK maximum memory: 128 MiB, 64 MiB global boundary, SP/FP restored, high-address word', flush=True)
    for value in (0, 4096, 8193, 65535, 2097152, 4194304, 2147483648):
        exe = build('invalid-'+str(value), 24, value)
        run = subprocess.run([str(exe)], input=b'value:\ncopy.ret\n', capture_output=True)
        assert run.returncode == 2 and not run.stdout
    exe = build('invalid-alignment', 24, memory, image_bytes=2097152+8192)
    run = subprocess.run([str(exe)], input=frame, capture_output=True)
    assert run.returncode == 2 and not run.stdout
    (root/'evidence.json').write_text(json.dumps({'memory_bytes': memory, 'cases': evidence,
        'rejected_memory_configurations': 8, 'rejected_sections': len(invalid_sections),
        'default_images_equal': True, 'maximum_memory_bytes': large_memory,
        'maximum_global_end': large_memory//2, 'maximum_result': 173,
        'source_sha256': {name: hashlib.sha256((root/'sources'/name).read_bytes()).hexdigest() for name in paths}}, indent=2)+'\n')


if __name__ == '__main__':
    main()
