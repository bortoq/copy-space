"""Check NOMMU header contracts with native and actual target GCC.

Only linux/types.h and linux/string.h are minimal test interfaces. PFN,
constant and folded-table definitions come from the supplied Linux tree.
Native GCC also checks ILP32 compilation; optional diagnostic GCC produces
an image executed as direct copies. No kernel boot or MMU claim.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 18


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--linux-root', type=Path, required=True)
    p.add_argument('--artifacts', type=Path, required=True)
    p.add_argument('--diagnostic', type=Path)
    args = p.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    port = root/'port'
    shutil.copytree(ROOT/'runtime/linux/arch/copyspace/include', port)
    stubs = root/'interfaces/linux'
    stubs.mkdir(parents=True)
    (stubs/'types.h').write_text('#pragma once\ntypedef unsigned long long u64;\ntypedef unsigned long phys_addr_t;\n')
    (stubs/'string.h').write_text('#pragma once\nvoid *memcpy(void *,const void *,__SIZE_TYPE__);\nvoid *memset(void *,int,__SIZE_TYPE__);\n')
    shutil.copyfile(ROOT/'tests/fixtures/gcc/linux_page_probe.c', root/'probe.c')
    driver = f'extern unsigned value(void); int main(void){{return value()!={EXPECTED};}}\n'
    (root/'driver.c').write_text(driver)
    includes = ['-I'+str(root/'interfaces'), '-I'+str(port), '-I'+str(args.linux_root.resolve()/'include')]
    flags = ['-DCONFIG_FLATMEM=1', '-DCONFIG_PAGE_OFFSET=0x80200000']
    command = ['gcc', '-O2', '-Werror', '-nostdinc',
               '-ffreestanding', '-fno-builtin', '-fno-stack-protector']
    command += includes + flags + [str(root/'probe.c'), str(root/'driver.c'), '-o', str(root/'native')]
    (root/'native-command.json').write_text(json.dumps(command)+'\n')
    subprocess.run(command, capture_output=True, check=True)
    subprocess.run([str(root/'native')], capture_output=True, check=True)
    subprocess.run(['gcc', '-m32', '-O2', '-Werror', '-nostdinc', '-ffreestanding', '-c']+includes+flags+
                   [str(root/'probe.c'), '-o', str(root/'probe-32.o')], capture_output=True, check=True)
    # Assembly users must see constants, not C typedefs or UL suffixes.
    (root/'page.S').write_text('#define __ASSEMBLY__\n#include <asm/page.h>\n.long PAGE_SIZE\n.long ARCH_PFN_OFFSET\n')
    subprocess.run(['gcc', '-m32', '-nostdinc', '-c']+includes+flags+
                   [str(root/'page.S'), '-o', str(root/'page.o')], capture_output=True, check=True)
    for define in ('CONFIG_MMU=1', 'CONFIG_64BIT=1', 'CONFIG_PAGE_SHIFT=13'):
        bad = subprocess.run(['gcc', '-m32', '-nostdinc', '-fsyntax-only']+includes+flags+
                             ['-D'+define, str(root/'probe.c')], capture_output=True)
        assert bad.returncode and b'copyspace' in bad.stderr
    evidence = {'scope': __doc__, 'native_checks': EXPECTED, 'configuration_rejections': 3}
    if args.diagnostic:
        from test_gcc_linux_units import pack
        from test_gcc_copy_output import decode
        import struct
        diag = args.diagnostic.resolve()
        prior = json.loads((diag/'evidence.json').read_text())
        elf = diag/'gcc-diagnostic.elf'
        qemu = Path(json.loads((diag/'command.json').read_text())[0])
        for file, key in ((elf, 'elf_sha256'), (qemu, 'qemu_sha256')):
            with file.open('rb') as s: assert hashlib.file_digest(s, 'sha256').hexdigest() == prior[key]
        # Select raw header bytes through the native preprocessor's dependency scan.
        selected = subprocess.run(['gcc', '-m32', '-nostdinc', '-M']+includes+flags+
                                  [str(root/'probe.c')], capture_output=True, check=True)
        import shlex
        files = {}
        for path in shlex.split(selected.stdout.decode().replace('\\\n', ' '))[1:]:
            path = Path(path)
            for prefix, name in ((root, ''), (args.linux_root.resolve()/'include', 'linux')):
                if path.is_relative_to(prefix):
                    virtual = '/'.join(x for x in (name, path.relative_to(prefix).as_posix()) if x)
                    files[virtual] = path.read_bytes()
                    break
            else:
                raise ValueError('unexpected dependency: '+str(path))
        argv = ['cc1', '--space-program=result.s', '--space-entry=value', '--space-memory=65536',
                '-quiet', '-O2', '-ffreestanding', '-fno-builtin', '-nostdinc',
                '-Iinterfaces', '-Iport', '-Ilinux']+flags+['-o', 'result.s', 'probe.c']
        job = pack(argv, files)
        (root/'job.bin').write_bytes(job)
        compiled = subprocess.run([str(qemu), '-strace', str(elf)], input=job, capture_output=True, timeout=300)
        (root/'response.bin').write_bytes(compiled.stdout)
        status, out, err, image = decode(compiled.stdout)
        assert compiled.returncode == status == 0 and not out and not err and image, err
        (root/'image.bin').write_bytes(image)
        run = subprocess.run([str(ROOT/'build/bin/space-256m'), '--ticks', '10000000', '--core', str(root/'image.bin'),
                              '--trace-channels', str(root/'direct.trace')], capture_output=True, timeout=300)
        (root/'direct.out').write_bytes(run.stdout)
        assert run.returncode == 0 and not run.stderr and run.stdout == struct.pack('<I', EXPECTED), run
        assert (root/'direct.trace').read_bytes().endswith(b' idle\n')
        evidence['direct_checks'] = EXPECTED
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print('OK NOMMU headers:', evidence, flush=True)


if __name__ == '__main__':
    main()
