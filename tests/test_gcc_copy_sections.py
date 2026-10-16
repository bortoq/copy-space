"""Exercise growing section/fragment tables and allocation failure cleanup.

Assembler fixtures are lowered natively and with ASan/UBSan. Result images
execute as direct copies. This is not a Linux build or GCC-in-Space proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def probe(values):
    code = b'.text\n.global value\nvalue:\ncopy.ldi.l $r0,5381\ncopy.ldi.l $r5,33\ncopy.ldi.l $r1,0\n'
    expected = 5381
    for i, words in enumerate(values):
        code += f'copy.ldi.l $r2,begin{i}\ncopy.ldi.l $r3,{len(words)}\n.Lloop{i}:\n'.encode()
        code += b'copy.ld.l $r4,($r2)\ncopy.mul $r0,$r5\ncopy.xor $r0,$r4\n'
        code += f'copy.inc $r2,4\ncopy.dec $r3,1\ncopy.cmp $r3,$r1\ncopy.branch.ne .Lloop{i}\n'.encode()
        for value in words:
            expected = ((expected * 33) ^ value) & 0xffffffff
    return code + b'copy.ret\n', expected


def cases():
    for count in (1, 8, 15, 16, 17, 31, 33, 65, 257, 300):
        # Every section contributes one word, including zero-filled NOBITS.
        values = [0 if i % 3 == 2 else (i * 0x1020304 + 7) & 0xffffffff for i in range(count)]
        code, expected = probe([values])
        for i, value in enumerate(values):
            kind = ('.data', '.rodata', '.bss')[i % 3]
            code += f'.section {kind}.test{i},"aw"\n.balign 4\n'.encode()
            if i == 0:
                code += b'begin0:\n'
            code += b'.zero 4\n' if kind == '.bss' else f'.long {value}\n'.encode()
        yield f'sections-{count}', code, expected, False
    for count in (128, 129, 300):
        words = [[(i * (17 + j) + 3 + j) & 0xffffffff for i in range(count)] for j in range(2)]
        code, expected = probe(words)
        for i in range(count):
            for j in range(2):
                code += f'.pushsection .data.stream{j},"aw"\n'.encode()
                if i == 0:
                    code += f'begin{j}:\n'.encode()
                code += f'.long {words[j][i]}\n.popsection\n'.encode()
        yield f'fragments-{count*2}', code, expected, False
    for count in (33, 257):
        code = b'.global value\n.section .init.text.test0,"ax"\nvalue:\ncopy.ldi.l $r0,71\n'
        for i in range(1, count):
            code += f'.section .init.text.test{i},"ax"\ncopy.nop\n'.encode()
        yield f'code-sections-{count}', code+b'copy.ret\n', 71, False
    # Separate input units have distinct local symbols and share section names.
    code, expected = probe([[i + 1 for i in range(40)]])
    first = code + b''.join(f'.section .data.unit{i},"aw"\n'.encode() +
                           (b'begin0:\n' if i == 0 else b'') + f'.long {i+1}\n'.encode()
                           for i in range(40))
    other = b''.join(f'.section .data.other{i},"aw"\n.long {500+i}\n'.encode() for i in range(40))
    yield 'objects-80-sections', first + b'\0' + other, expected, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, help='old linker with identical fixture/configuration')
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    sources = ['tests/fixtures/gcc/copy_link.c', 'runtime/gcc/copy_link.c',
               'runtime/gcc/copy_link.h', 'runtime/gcc/copy_emit.c', 'runtime/gcc/copy_emit.h']
    for name in sources:
        target = root/'sources'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    shutil.copyfile(__file__, root/'run.py')
    wrapper = root/'fail_malloc.c'
    wrapper.write_text('#include <stdlib.h>\n#include <stddef.h>\n'
        'void *__real_malloc(size_t);\n'
        'void *__wrap_malloc(size_t n) { static unsigned long calls;\n'
        ' const char *fail=getenv("CS_FAIL_MALLOC");\n'
        ' if (fail && ++calls==strtoul(fail,0,10)) return NULL;\n'
        ' return __real_malloc(n); }\n')
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
    tools = {}
    for sanitized in (False, True):
        for objects in (False, True):
            name = ('objects' if objects else 'program') + ('-sanitize' if sanitized else '')
            output = root/name
            command = ['gcc', '-O1' if sanitized else '-O2', '-g', '-Wall', '-Wextra', '-Werror',
                       '-DCS_COPY_PROGRAM', '-DCS_COPY_LABEL_CAPACITY=128',
                       '-DCS_COPY_IMAGE_BYTES=1048576', '-DCS_COPY_ASSEMBLY_BYTES=131072',
                       '-I'+str(root/'sources/runtime/gcc')]
            if sanitized:
                command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
            if objects:
                command += ['-DCS_COPY_OBJECTS', '-DCS_COPY_OBJECT_ALLOC']
            command += [str(root/'sources'/name) for name in sources if name.endswith('.c')]
            command += [str(wrapper), '-Wl,--wrap=malloc', '-o', str(output)]
            (root/(output.name+'-command.json')).write_text(json.dumps(command)+'\n')
            compiled = subprocess.run(command, capture_output=True, timeout=120)
            assert compiled.returncode == 0, compiled.stderr
            tools[sanitized, objects] = output
    evidence = {'scope': __doc__, 'cases': [], 'allocation_rejections': 0, 'invalid_sections': [],
                'source_sha256': {name: hashlib.sha256((root/'sources'/name).read_bytes()).hexdigest() for name in sources}}
    if args.baseline:
        evidence['baseline_sha256'] = hashlib.sha256(args.baseline.read_bytes()).hexdigest()
    for name, assembly, expected, objects in cases():
        folder = root/name
        folder.mkdir()
        (folder/'input.s').write_bytes(assembly)
        images = []
        for sanitized in (False, True):
            linked = subprocess.run([str(tools[sanitized, objects])], input=assembly,
                                    capture_output=True, env=env, timeout=30)
            assert linked.returncode == 0 and not linked.stderr, (name, linked.returncode, linked.stderr)
            images.append(linked.stdout)
        assert images[0] == images[1], name
        (folder/'image.bin').write_bytes(images[0])
        command = [str(ROOT/'build/bin/space'), '--ticks', '1000000', '--core', str(folder/'image.bin'),
                   '--trace-channels', str(folder/'trace.txt')]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        direct = subprocess.run(command, capture_output=True, timeout=60)
        (folder/'out.bin').write_bytes(direct.stdout)
        assert direct.returncode == 0 and not direct.stderr and direct.stdout == struct.pack('<I', expected), name
        assert (folder/'trace.txt').read_bytes().endswith(b' idle\n'), name
        same_baseline = args.baseline and name in ('sections-1', 'sections-8', 'sections-15', 'fragments-256')
        if same_baseline:
            old = subprocess.run([str(args.baseline.resolve())], input=assembly, capture_output=True, timeout=30)
            assert old.returncode == 0 and not old.stderr and old.stdout == images[0], name
        evidence['cases'].append({'name': name, 'expected': expected, 'matches_baseline': bool(same_baseline),
                                  'image_sha256': hashlib.sha256(images[0]).hexdigest()})
    base = next(assembly for name, assembly, _, _ in cases() if name == 'sections-300')
    for name, suffix in [
        ('section-name', b'.section .data.'+b'x'*64+b',"aw"\n'),
        ('section-kind', b'.section .custom,"aw"\n.long 1\n.section .custom,"ax"\n'),
        ('section-stack', b'.pushsection .data.stack,"aw"\n'*17)]:
        folder = root/name
        folder.mkdir()
        (folder/'input.s').write_bytes(base+suffix)
        failed = subprocess.run([str(tools[True, False])], input=base+suffix,
                                capture_output=True, env=env, timeout=30)
        (folder/'stderr.txt').write_bytes(failed.stderr)
        assert failed.returncode == 2 and not failed.stdout, (name, failed.stderr)
        assert b'Sanitizer' not in failed.stderr and b'runtime error:' not in failed.stderr, failed.stderr
        evidence['invalid_sections'].append(name)
    # Every malloc failure until the first successful full run must clean up.
    # This includes growth of tables after old allocations and object rewriting.
    for name, assembly, _, objects in cases():
        if name not in ('fragments-600', 'objects-80-sections'):
            continue
        folder = root/(name+'-failures')
        folder.mkdir()
        for index in range(1, 100):
            failed = subprocess.run([str(tools[True, objects])], input=assembly, capture_output=True,
                env=dict(env, CS_FAIL_MALLOC=str(index)), timeout=30)
            if failed.returncode == 0:
                assert not failed.stderr
                break
            (folder/f'{index}.stderr').write_bytes(failed.stderr)
            assert failed.returncode == 2 and not failed.stdout, (name, index, failed.stderr)
            assert b'Sanitizer' not in failed.stderr and b'runtime error:' not in failed.stderr, failed.stderr
            evidence['allocation_rejections'] += 1
        else:
            raise AssertionError('allocation failure sequence did not reach success')
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK sections/fragments:', len(evidence['cases']), 'direct cases;',
          evidence['allocation_rejections'], 'allocation failures; native/sanitized exact')


if __name__ == '__main__':
    main()
