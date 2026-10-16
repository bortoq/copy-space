"""Compile a Linux atomic/bitops probe with the actual copyspace GCC.

The fixture exercises the copyspace asm/atomic.h, asm/cmpxchg.h and UP
atomic bitops through <linux/atomic.h> and <linux/bitops.h>. The host
dependency scan only selects files for GCCJOB1; QEMU runs the compiler
and the guest linker, results execute as direct copies. The __sync_*
helpers come from the installed runtime with --installed, or from the
fixture compiled by the same target GCC. This is not GCC-in-Space evidence.
"""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import struct
import subprocess
import sys
import tarfile
from pathlib import Path

from test_gcc_linux_units import pack
from test_gcc_copy_output import decode
ROOT = Path(__file__).resolve().parents[1]

EXPECTED = 62


def digest(path):
    with path.open('rb') as s:
        return hashlib.file_digest(s, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-root', type=Path, required=True)
    parser.add_argument('--build-root', type=Path, required=True)
    parser.add_argument('--linux-archive', type=Path, required=True,
                        help='pinned original linux-6.12.tar.xz; verify every Linux input')
    parser.add_argument('--diagnostic', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--installed', action='store_true')
    parser.add_argument('--image', type=Path)
    args = parser.parse_args()
    if args.installed != bool(args.image):
        parser.error('--installed and --image require each other')
    archive = args.linux_archive.resolve()
    archive_sha256 = 'b1a2562be56e42afb3f8489d4c2a7ac472ac23098f1ef1c1e40da601f54625eb'
    assert digest(archive) == archive_sha256, 'changed pinned Linux 6.12 archive'
    linux, build = args.linux_root.resolve(), args.build_root.resolve()
    diagnostic = args.diagnostic.resolve()
    original = json.loads((diagnostic/'evidence.json').read_text())
    elf = diagnostic/'gcc-diagnostic.elf'
    command = json.loads((diagnostic/'command.json').read_text())
    assert digest(elf) == original['elf_sha256'], 'changed diagnostic GCC'
    qemu = Path(command[0])
    assert digest(qemu) == original['qemu_sha256'], 'changed diagnostic QEMU'
    installed_hash = None
    if args.installed:
        image = args.image.resolve()
        manifest = json.loads((image/'image.json').read_text())
        assert digest(image/'gcc-space.elf') == manifest['elf_sha256'] == original['original_elf_sha256']
        assert manifest['target_library']['default']
        installed_hash = digest(image/'target-libgcc.a')
        assert installed_hash == manifest['target_library']['archive_sha256']
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    port = root/'port'
    shutil.copytree(ROOT/'runtime/linux/arch/copyspace/include', port/'include')
    (port/'config.h').write_text('#include <linux/kconfig.h>\n'
        '#undef CONFIG_GENERIC_BUG\n'
        '#undef CONFIG_GENERIC_BUG_RELATIVE_POINTERS\n'
        '#undef CONFIG_DEBUG_BUGVERBOSE\n'
        '#undef CONFIG_GENERIC_ATOMIC64\n')
    shutil.copyfile(ROOT/'tests/fixtures/gcc/linux_atomic_probe.c', port/'probe.c')
    toolchain = ROOT/'tmp/rv32i-toolchain/root/usr/bin/riscv64-unknown-elf-gcc'
    assert toolchain.is_file(), 'missing riscv dep-scan toolchain'
    scan = [str(toolchain), '-I'+str(port/'include'), '-D__copyspace__=1',
            '-D__COPYSPACE_LITTLE_ENDIAN__=1', '-nostdinc',
            '-I'+str(linux/'arch/riscv/include'), '-I./arch/riscv/include/generated',
            '-I'+str(linux/'include'), '-I./include',
            '-I'+str(linux/'arch/riscv/include/uapi'), '-I./arch/riscv/include/generated/uapi',
            '-I'+str(linux/'include/uapi'), '-I./include/generated/uapi',
            '-include', str(linux/'include/linux/compiler-version.h'),
            '-include', str(linux/'include/linux/kconfig.h'),
            '-include', str(linux/'include/linux/compiler_types.h'),
            '-D__KERNEL__', '-DCONFIG_PAGE_OFFSET=0x80200000',
            '-std=gnu11', '-ffreestanding', '-fno-common', '-fno-stack-protector',
            '-Werror=implicit-function-declaration', '-Werror=implicit-int',
            '-nostdinc', '-include', str(port/'config.h'), '-M', str(port/'probe.c')]
    (root/'dependency-command.json').write_text(json.dumps(scan, indent=2)+'\n')
    dependencies = subprocess.run(scan, cwd=build, capture_output=True, timeout=120)
    (root/'dependency.stdout').write_bytes(dependencies.stdout)
    (root/'dependency.stderr').write_bytes(dependencies.stderr)
    assert dependencies.returncode == 0, dependencies.stderr

    def virtual(path):
        path = Path(path)
        if not path.is_absolute():
            path = build/path
        path = Path(os.path.abspath(path))
        for prefix, name in [(port, 'port'), (linux, 'linux'), (build, 'build')]:
            if path.is_relative_to(prefix):
                return name+'/'+path.relative_to(prefix).as_posix()
        raise ValueError('dependency outside recorded roots: '+str(path))

    files = {}
    for name in shlex.split(dependencies.stdout.decode().replace('\\\n', ' '))[1:]:
        path = Path(name)
        if not path.is_absolute():
            path = build/path
        files[virtual(path)] = path.read_bytes()
    files['port/config.h'] = (port/'config.h').read_bytes()
    assert len(files) <= 1024, 'too many guest files'
    wanted = {'linux-6.12/'+name[6:]: name for name in files if name.startswith('linux/')}
    with tarfile.open(archive, 'r|xz') as package:
        for member in package:
            if member.name in wanted:
                name = wanted.pop(member.name)
                assert package.extractfile(member).read() == files[name], 'changed Linux source: '+name
            if not wanted:
                break
    assert not wanted, 'Linux dependency absent from pinned archive'
    for name, data in files.items():
        dest = root/'inputs'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    common = ['-Iport/include', '-Ilinux/arch/riscv/include', '-Ibuild/arch/riscv/include/generated',
              '-Ilinux/include', '-Ibuild/include', '-Ilinux/arch/riscv/include/uapi',
              '-Ibuild/arch/riscv/include/generated/uapi', '-Ilinux/include/uapi',
              '-Ibuild/include/generated/uapi', '-D__KERNEL__', '-DCONFIG_PAGE_OFFSET=0x80200000']
    run = [str(qemu), '-strace', str(elf)]
    (root/'command.json').write_text(json.dumps(run)+'\n')
    # 1. Compile the probe to copy assembly.
    argv = (['cc1', '--space-result=result.s', '-quiet', '-O2', '-std=gnu11', '-ffreestanding',
             '-fno-builtin', '-fno-common', '-fno-strict-aliasing', '-fno-stack-protector',
             '-Werror=implicit-function-declaration', '-Werror=implicit-int', '-nostdinc']
            + common + ['-include', 'port/config.h', '-o', 'result.s', 'port/probe.c'])
    (root/'probe-argv.json').write_text(json.dumps(argv, indent=2)+'\n')
    incoming = pack(argv, files)
    (root/'probe.job').write_bytes(incoming)
    compiled = subprocess.run(run, input=incoming, capture_output=True, timeout=180)
    (root/'probe-response.bin').write_bytes(compiled.stdout)
    status, stdout, stderr, probe_asm = decode(compiled.stdout)
    assert compiled.returncode == status == 0 and not stdout and not stderr and probe_asm, stderr
    (root/'probe.s').write_bytes(probe_asm)
    # 2. Compile the __sync_* helpers with the same compiler.
    helper_asm = b''
    if not args.installed:
        sync_src = (ROOT/'tests/fixtures/gcc/sync_up.c').read_bytes()
        (root/'sync_up.c').write_bytes(sync_src)
        argv2 = ['cc1', '--space-result=result.s', '-quiet', '-O2', '-ffreestanding', '-fno-builtin',
                 '-nostdinc', '-o', 'result.s', 'sync_up.c']
        (root/'sync-argv.json').write_text(json.dumps(argv2, indent=2)+'\n')
        compiled2 = subprocess.run(run, input=pack(argv2, {'sync_up.c': sync_src}),
                                   capture_output=True, timeout=180)
        (root/'sync-response.bin').write_bytes(compiled2.stdout)
        status2, stdout2, stderr2, helper_asm = decode(compiled2.stdout)
        assert compiled2.returncode == status2 == 0 and not stdout2 and not stderr2 and helper_asm, stderr2
        (root/'sync_up.s').write_bytes(helper_asm)
    # 3. Link probe + helper in the guest and execute direct copies.
    object_option = [] if args.installed else ['--space-object=port/sync_up.s']
    argv3 = (['cc1', '--space-program=result.s', '--space-entry=value', '--space-memory=65536']+
             object_option+['-quiet', '-O2', '-std=gnu11', '-ffreestanding',
              '-fno-builtin', '-fno-common', '-fno-strict-aliasing', '-fno-stack-protector',
              '-Werror=implicit-function-declaration', '-Werror=implicit-int', '-nostdinc']
             + common + ['-include', 'port/config.h', '-o', 'result.s', 'port/probe.c'])
    linked_files = dict(files)
    if not args.installed:
        linked_files['port/sync_up.s'] = helper_asm
    (root/'link-argv.json').write_text(json.dumps(argv3, indent=2)+'\n')
    incoming = pack(argv3, linked_files)
    (root/'link.job').write_bytes(incoming)
    linked = subprocess.run(run, input=incoming, capture_output=True, timeout=300)
    (root/'link-response.bin').write_bytes(linked.stdout)
    status3, stdout3, stderr3, image = decode(linked.stdout)
    assert linked.returncode == status3 == 0 and not stdout3 and not stderr3 and image, stderr3
    (root/'image.bin').write_bytes(image)
    emulator = ROOT/'build/bin/space-256m'
    direct = subprocess.run([str(emulator), '--ticks', '10000000', '--core', str(root/'image.bin'),
                             '--trace-channels', str(root/'direct.trace')],
                            capture_output=True, timeout=300)
    (root/'direct.out').write_bytes(direct.stdout)
    assert direct.returncode == 0, direct.stderr[:300]
    assert direct.stdout == struct.pack('<I', EXPECTED) and not direct.stderr, direct.stdout
    assert (root/'direct.trace').read_bytes()[-6:] == b' idle\n'
    evidence = {'scope': __doc__, 'linux_archive_sha256': archive_sha256,
                'elf_sha256': original['elf_sha256'], 'qemu_sha256': original['qemu_sha256'],
                'guest_files': len(files), 'probe_bytes': len(probe_asm),
                'helper_bytes': len(helper_asm), 'direct_result': EXPECTED,
                'installed_runtime': args.installed, 'installed_archive_sha256': installed_hash,
                'input_contains_assembly': any(name.endswith(('.s', '.S', '.a', '.o')) for name in linked_files),
                'image_sha256': digest(root/'image.bin')}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(f'OK Linux atomics: {len(files)} guest files; direct OUT={EXPECTED}; QEMU diagnostic only')


if __name__ == '__main__':
    main()
