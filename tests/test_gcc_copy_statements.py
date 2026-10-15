"""Prove assembly statement parsing with direct and separate copy execution."""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--ctype-assembly', type=Path, required=True)
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
    flags = ['-O2', '-Wall', '-Wextra', '-Werror', '-DCS_COPY_PROGRAM',
             '-DCS_COPY_RESULT_ADDRESS_BITS=31', '-DCS_COPY_IMAGE_BYTES=2097152',
             '-DCS_COPY_MEMORY_BYTES=65536', '-DCS_COPY_ASSEMBLY_BYTES=131072',
             '-DCS_COPY_OBJECT_TEXT_BYTES=262144', '-I'+str(root/'sources/runtime/gcc')]
    allocation_checks = root/'allocation_checks.c'
    allocation_checks.write_text('''#include <stdlib.h>
static unsigned active;
extern void *__real_malloc(size_t);
extern void __real_free(void *);
void *__wrap_malloc(size_t n) {
    if (getenv("CS_COPY_TEST_FAIL_ALLOC")) return NULL;
    void *p=__real_malloc(n); if(p) ++active; return p;
}
void __wrap_free(void *p) {
    if(p) { if(!active) abort(); --active; } __real_free(p);
}
__attribute__((destructor)) static void check(void) { if(active) abort(); }
''')

    def build(name, objects=False, sanitize=False):
        command = ['gcc']+flags
        if objects:
            command += ['-DCS_COPY_OBJECTS']
        if sanitize:
            command += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-fno-pie', '-no-pie']
        command += sources+[str(allocation_checks), '-Wl,--wrap=malloc', '-Wl,--wrap=free',
                            '-o', str(root/name)]
        (root/(name+'-command.json')).write_text(json.dumps(command)+'\n')
        subprocess.run(command, check=True, capture_output=True)
        return root/name

    cases = [
        (b'.data; text: .ascii "A;#:\\"Z"; .text; value: copy.lda.b $r0,text+4; copy.ret # ; invalid\n', 34),
        (b'.data; text: .ascii "\\\\"; .text; value: copy.lda.b $r0,text; copy.ret', 92),
        (b'.data; text: .ascii "'+b'A'*20000+b'Z"; .text; value: copy.lda.b $r0,text+20000; copy.ret\n', 90),
        (b';;# ignored ; nonsense\n.text; value: copy.jmpa .Lnext; .Lnext: copy.ret\n', 3),
        (args.ctype_assembly.read_bytes()+b'\n.text; value: '
         b'copy.ldi.l $r2,__export_symbol__ctype+4; copy.ld.l $r2,($r2); '
         b'copy.ldo.b $r0,65($r2); copy.ret\n', 65),
        (b'value: copy.jmpa 1f; .Ldead: copy.ldi.l $r0,99; 1: copy.inc $r0,2; '
         b'copy.jmpa 1f; 1: copy.inc $r0,3; copy.ret\n', 8),
        (b'value: copy.ldi.l $r1,0; copy.ldi.l $r2,0; 1: copy.inc $r1,2; '
         b'copy.dec $r0,1; copy.cmp $r0,$r2; copy.branch.ne 1b; '
         b'copy.mov $r0,$r1; copy.ret\n', 6),
        (b'value: copy.cmp $r0,$r1; 1: copy.branch.ltu 2f; copy.ldi.l $r0,99; '
         b'copy.ret; 2: copy.ldi.l $r0,7; copy.ret\n', 7),
        (b'.data; pointer: .long 1f+1; 1: .byte 4,9; .text; value: '
         b'copy.lda.l $r2,pointer; copy.ld.b $r0,($r2); copy.ret\n', 9),
        (b'value: copy.jmpa 4294967295f; 4294967295: copy.ldi.l $r0,11; copy.ret\n', 11),
        (b'.data; 1: .long 15; pointer: .long 1b; .text; value: '
         b'copy.lda.l $r2,pointer; copy.ld.l $r0,($r2); copy.ret\n', 15),
        (b'.data; text: .ascii "1f;1b#1:"; .text; value: '
         b'copy.lda.b $r0,text; copy.ret\n', 49),
        (b'value: copy.jmpa 1f; .L.__cA0.N0: copy.ldi.l $r0,99; '
         b'1: copy.ldi.l $r0,13; copy.ret\n', 13),
        (b'value: copy.trap\n', None),
        (b'value: copy.cmp $r0,$r1; copy.branch.eq .Lbad; copy.add $r0,$r1; '
         b'copy.ret; .Lbad: copy.trap\n', 7),
        (b'value: copy.cmp $r0,$r0; copy.branch.eq .Lbad; copy.ret; .Lbad: copy.trap\n', None),
        (b'value: copy.jsra helper; copy.ret; helper: copy.trap\n', None),
        (b'value: copy.jmpa 1f; 1: copy.trap\n', None)]
    evidence = []
    for objects in (False, True):
        folder = root/('objects' if objects else 'program')
        folder.mkdir()
        native = build(folder.name+'-native', objects=objects)
        sanitizer = build(folder.name+'-sanitized', objects=objects, sanitize=True)
        failing = b'value: copy.ret\n'
        if objects:
            failing += b'\0unused: copy.ret\n'
        rejected = subprocess.run([str(native)], input=failing, capture_output=True,
                                  env={**os.environ, 'CS_COPY_TEST_FAIL_ALLOC': '1'})
        assert rejected.returncode == 2 and not rejected.stdout and b'out of memory' in rejected.stderr
        for index, (assembly, expected) in enumerate(cases):
            case = folder/str(index)
            case.mkdir()
            incoming = assembly
            if objects:
                # Force the scanner and rewriter for multiple units, including scoped local labels.
                incoming += b'\0.text; .global unused; unused: copy.jmpa 1f; 1: copy.ret\n'
                incoming = b'.global value; '+incoming
            (case/'input.s').write_bytes(incoming)
            run = subprocess.run([str(native)], input=incoming, capture_output=True, check=True)
            assert not run.stderr and len(run.stdout) == 2097152
            image = run.stdout
            (case/'image.bin').write_bytes(image)
            checked = subprocess.run([str(sanitizer)], input=incoming, capture_output=True,
                                     env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}, timeout=60)
            assert checked.returncode == 0 and not checked.stderr and checked.stdout == image
            command = [str(ROOT/'build/bin/space-256m'), '--ticks', '10000',
                       '--core', str(case/'image.bin'), '--trace', str(case/'trace.txt')]
            (case/'command.json').write_text(json.dumps(command)+'\n')
            result = subprocess.run(command, capture_output=True, check=True, timeout=60)
            (case/'out.bin').write_bytes(result.stdout)
            assert not result.stderr and result.stdout == (b'' if expected is None else struct.pack('<I', expected))
            with (case/'trace.txt').open('rb') as trace:
                trace.seek(max(0, (case/'trace.txt').stat().st_size-80))
                assert trace.read().endswith(b' idle\n')
            evidence.append({'mode': folder.name, 'case': index, 'result': expected,
                             'image_sha256': hashlib.sha256(image).hexdigest()})
        invalid = b'# first line\n.text; value: copy.unsupported $r0,$r1; copy.ret\n'
        if objects:
            invalid += b'\0.text; unused: copy.ret\n'
        rejected = subprocess.run([str(native)], input=invalid, capture_output=True)
        assert rejected.returncode == 2 and not rejected.stdout
        if not objects:
            assert rejected.stderr.startswith(b'2: '), rejected.stderr
        for invalid in [b'.data; text: .ascii "unterminated; # :\n',
                        b'.data; text: .ascii "escaped\\"\n',
                        b'value: copy.jmpa 1f; copy.ret\n',
                        b'value: copy.jmpa 1b; copy.ret\n',
                        b'value: 4294967296: copy.ret\n']:
            if objects:
                invalid += b'\0.text; value: copy.ret\n'
            rejected = subprocess.run([str(native)], input=invalid, capture_output=True)
            assert rejected.returncode == 2 and not rejected.stdout
        if objects:
            for invalid in [b'.global value; value: copy.jmpa 1f\0 1: copy.ret\n',
                            b'1: copy.ret\0.global value; value: copy.jmpa 1b\n']:
                rejected = subprocess.run([str(native)], input=invalid, capture_output=True)
                assert rejected.returncode == 2 and not rejected.stdout
    (root/'evidence.json').write_text(json.dumps({'source_sha256': hashes, 'cases': evidence,
        'scope': 'Native linker preparation, direct copies in Space; ctype assembly from diagnostic GCC. '
                 'Not Linux or compiler execution in Space.'}, indent=2)+'\n')
    print('OK assembly statements:', len(evidence), 'direct results, separate inputs, ASan/UBSan and errors')


if __name__ == '__main__':
    main()
