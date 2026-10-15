"""Probe original Linux C and headers with the actual copyspace GCC in QEMU.

The host dependency scan only selects files for GCCJOB1. Its preprocessed
output is never compiler input. This is an architecture-fragment diagnostic,
not GCC execution in Space, a complete Linux port, or a kernel build.
"""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import struct
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pack(argv, files):
    directories = sorted({str(Path(name).parent) for name in files if '/' in name})
    packet = b'\0CCFILES1' + struct.pack('<III', len(files), 0, len(directories))
    for directory in directories:
        data = directory.encode()
        packet += struct.pack('<I', len(data)) + data
    for name, data in files.items():
        encoded = name.encode()
        packet += struct.pack('<II', len(encoded), len(data)) + encoded + data
    job = b'GCCJOB1\0' + struct.pack('<II', len(argv), len(packet))
    for argument in argv:
        data = argument.encode()
        job += struct.pack('<I', len(data)) + data
    return job + packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-root', type=Path, required=True)
    parser.add_argument('--build-root', type=Path, required=True)
    parser.add_argument('--linux-archive', type=Path, required=True,
                        help='pinned original linux-6.12.tar.xz; verify every Linux input')
    parser.add_argument('--diagnostic', type=Path, required=True,
                        help='directory produced by scripts/gcc/diagnose_guest.py')
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--unit', choices=['string', 'ctype', 'sort', 'rbtree', 'bug'], default='string')
    parser.add_argument('--entry-probe', action='store_true',
                        help='compile ctype/sort/string with direct execution entries')
    args = parser.parse_args()
    if args.entry_probe and args.unit not in ('ctype', 'sort', 'string'):
        parser.error('--entry-probe requires ctype, sort or string')
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
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, root/'run.py')
    shutil.copyfile(build/'.config', root/'original.config')
    kbuild = build/'lib'/('.'+('string' if args.unit == 'bug' else args.unit)+'.o.cmd')
    shutil.copyfile(kbuild, root/'kbuild.cmd')
    words = shlex.split(kbuild.read_text().splitlines()[0].split(':=', 1)[1])
    source = linux/'lib'/(('string' if args.unit == 'bug' else args.unit)+'.c')
    assert words[-1] == str(source), 'unexpected Kbuild source'
    # The probe keeps the RISC-V scaffold's other headers explicitly. This
    # initial architecture fragment has fatal BUG, but no generic bug tables.
    port = root/'port'
    shutil.copytree(ROOT/'runtime/linux/arch/copyspace/include', port/'include')
    header = port/'include/asm/bug.h'
    config = port/'config.h'
    config.write_text('/* Initial copyspace BUG configuration for this probe. */\n'
        '#include <linux/kconfig.h>\n'
        '#undef CONFIG_GENERIC_BUG\n'
        '#undef CONFIG_GENERIC_BUG_RELATIVE_POINTERS\n'
        '#undef CONFIG_DEBUG_BUGVERBOSE\n')
    if args.unit == 'bug' or args.entry_probe:
        source = port/'probe.c'
        shutil.copyfile(ROOT/'tests/fixtures/gcc'/('linux_'+args.unit+'.c'), source)
        words[-1] = str(source)
    if args.entry_probe:
        words[1:1] = ['-I'+str(linux)]
        if args.unit == 'string':
            shutil.copyfile(ROOT/'runtime/gcc/target/muldi3.c', port/'muldi3.c')
    collector = []
    skip = False
    for word in words:
        if skip:
            skip = False
        elif word == '-o':
            skip = True
        elif word == '-c' or word.startswith('-Wp,-MMD,'):
            continue
        else:
            collector.append(word)
    collector[1:1] = ['-I'+str(port/'include'), '-D__copyspace__=1',
                      '-D__COPYSPACE_LITTLE_ENDIAN__=1']
    collector += ['-include', str(config), '-M']
    (root/'dependency-command.json').write_text(json.dumps(collector, indent=2)+'\n')
    dependencies = subprocess.run(collector, cwd=build, capture_output=True, timeout=120)
    (root/'dependency.stdout').write_bytes(dependencies.stdout)
    (root/'dependency.stderr').write_bytes(dependencies.stderr)
    assert dependencies.returncode == 0, dependencies.stderr

    def virtual(path):
        path = Path(path)
        if not path.is_absolute():
            path = build/path
        # Keep lexical paths: generated headers can be symlinks into Linux.
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
    files['port/config.h'] = config.read_bytes()
    assert files[virtual(source)] == source.read_bytes()
    if args.unit in ('bug', 'string'):
        assert files['port/include/asm/bug.h'] == header.read_bytes()
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

    options = ['-Iport/include']
    i = 1
    while i < len(words):
        word = words[i]
        if word == '-include':
            options += [word, virtual(words[i+1])]
            i += 2
            continue
        if word.startswith('-I'):
            options.append('-I'+virtual(word[2:]))
        elif word.startswith('-D'):
            options.append(word)
        i += 1
    argv = ['cc1', '--space-result=result.s', '-quiet', '-O2', '-std=gnu11',
            '-ffreestanding', '-fno-builtin', '-fno-common', '-fno-strict-aliasing',
            '-fno-stack-protector', '-Werror=implicit-function-declaration',
            '-Werror=implicit-int', '-nostdinc'] + options + [
            '-include', 'port/config.h', '-o', 'result.s', virtual(source)]
    (root/'argv.json').write_text(json.dumps(argv, indent=2)+'\n')
    job = pack(argv, files)
    assert len(argv) <= 256 and len(job) <= 16*1024*1024
    (root/'job.bin').write_bytes(job)
    run = [str(qemu), '-strace', str(elf)]
    (root/'command.json').write_text(json.dumps(run, indent=2)+'\n')
    result = subprocess.run(run, input=job, capture_output=True, timeout=180)
    (root/'out.bin').write_bytes(result.stdout)
    (root/'syscalls.txt').write_bytes(result.stderr)
    packet = result.stdout
    assert len(packet) >= 24 and packet[:8] == b'GCCOUT1\0', packet[:80]
    status, outsize, errsize, size = struct.unpack_from('<IIII', packet, 8)
    assert result.returncode == status and len(packet) == 24+outsize+errsize+size
    (root/'stdout.bin').write_bytes(packet[24:24+outsize])
    (root/'stderr.bin').write_bytes(packet[24+outsize:24+outsize+errsize])
    assembly = packet[24+outsize+errsize:]
    (root/'result.s').write_bytes(assembly)
    evidence = {'scope': __doc__, 'unit': virtual(source),
        'linux_archive_sha256': archive_sha256,
        'elf_sha256': original['elf_sha256'], 'qemu_sha256': original['qemu_sha256'],
        'original_config_sha256': digest(root/'original.config'),
        'inputs_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        'job_sha256': digest(root/'job.bin'), 'exit': status, 'assembly_bytes': size,
        'assembly_sha256': digest(root/'result.s')}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    assert status == 0, (root/'stderr.bin').read_bytes()
    assert not outsize and size
    rejections = []
    if args.unit == 'bug':
        rejections = [
            ('generic-bug', [], b'\n#define CONFIG_GENERIC_BUG 1\n', None,
             b'copyspace does not yet support CONFIG_GENERIC_BUG'),
            ('wrong-target', ['-U__copyspace__'], b'', None,
             b'copyspace asm/bug.h requires the copyspace GCC target')]
    elif args.unit == 'string' and args.entry_probe:
        rejections = [
            ('smp', [], b'\n#define CONFIG_SMP 1\n', 'barrier.h',
             b'copyspace SMP ordering is not implemented'),
            ('mmu', [], b'\n#define CONFIG_MMU 1\n', 'page.h',
             b'copyspace page tables are not implemented'),
            ('64bit', [], b'\n#define CONFIG_64BIT 1\n', 'page.h',
             b'copyspace requires a 32-bit kernel configuration'),
            ('page-size', [], b'\n#undef CONFIG_PAGE_SHIFT\n#define CONFIG_PAGE_SHIFT 16\n', 'page.h',
             b'copyspace requires 4096-byte logical pages'),
            ('fault-recovery', [], b'\n#define CONFIG_DCACHE_WORD_ACCESS 1\n', 'word-at-a-time.h',
             b'copyspace fault-recovering word access is not implemented'),
            ('endian', ['-U__COPYSPACE_LITTLE_ENDIAN__'], b'', 'byteorder.h',
             b'copyspace requires its little-endian GCC target')]
    if rejections:
        rejected = []
        for name, flags, configuration, include, message in rejections:
            folder = root/name
            folder.mkdir()
            bad_files, bad_argv = dict(files), argv[:]
            bad_files['port/config.h'] += configuration
            bad_argv[2:2] = flags
            if include:
                bad_files['port/probe.c'] = ('#include <asm/'+include+'>\n').encode()
            bad_job = pack(bad_argv, bad_files)
            (folder/'job.bin').write_bytes(bad_job)
            failed = subprocess.run(run, input=bad_job, capture_output=True, timeout=180)
            (folder/'out.bin').write_bytes(failed.stdout)
            (folder/'syscalls.txt').write_bytes(failed.stderr)
            assert failed.returncode and failed.stdout[:8] == b'GCCOUT1\0'
            status, outsize, errsize, size = struct.unpack_from('<IIII', failed.stdout, 8)
            assert status == failed.returncode and not size and not outsize
            assert len(failed.stdout) == 24+errsize and message in failed.stdout[24:]
            rejected.append({'case': name, 'exit': status, 'job_sha256': digest(folder/'job.bin')})
        evidence['rejected_cases'] = rejected
    if args.unit == 'bug':
        check_direct(root, assembly, evidence, [('value', 7), ('fatal', None), ('conditional_trap', None),
                            ('condition_once', 5), ('warning_once', 21), ('warning_return', 101)])
    elif args.entry_probe:
        cases = {'ctype': [('value', 65)], 'sort': [('value', 204)],
                 'string': [('value', 207), ('fatal', None), ('warning_once', 1),
                            ('multiplication', 8), ('bit_operations', 32),
                            ('argument_home', 11), ('variadic', 15),
                            ('stack_arguments', 52), ('variadic_call', 42)]}
        check_direct(root, assembly, evidence, cases[args.unit], large=args.unit == 'string')
    print('OK actual copyspace GCC:', 'BUG fixture with original Linux headers' if args.unit == 'bug' else 'original Linux '+args.unit,
          ';', len(files), 'guest files;', len(assembly), 'assembly bytes; QEMU diagnostic only')


def check_direct(root, assembly, evidence, cases, large=False):
    """Execute generated code as direct copies; GCC itself ran in QEMU."""
    harness = root/'direct.c'
    harness.write_text('''#include "copy_link.h"
#include <stdio.h>
static unsigned char image[8388608];
static char assembly[131072];
int main(int argc,char **argv) {
    size_t n=fread(assembly,1,sizeof(assembly),stdin);
    unsigned arguments[]={3,4,5,6,7,8}; struct cs_copy_link_error error;
    if(argc!=2 || n==sizeof(assembly)) return 1;
    if(cs_copy_link_program_memory(image,sizeof(image),31,65536,assembly,n,
                                  argv[1],arguments,6,&error)) {
        fprintf(stderr,"%zu: %s\\n",error.line,error.message);return 2;
    }
    return fwrite(image,1,sizeof(image),stdout)==sizeof(image) ? 0 : 3;
}
''')
    paths = ['runtime/gcc/'+name for name in ('copy_link.c', 'copy_link.h', 'copy_emit.c', 'copy_emit.h')]
    for name in paths:
        dest = root/'sources'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dest)
    capacities = {'LABEL': 1024, 'JUMP': 2048, 'CALL': 256, 'SYMBOL': 256, 'RELOCATION': 256} if large else {
                  'LABEL': 256, 'JUMP': 1024, 'CALL': 128, 'SYMBOL': 128, 'RELOCATION': 128}
    command = ['gcc', '-O2', '-Wall', '-Wextra', '-Werror',
               '-I'+str(root/'sources/runtime/gcc')] + [
               '-DCS_COPY_'+key+'_CAPACITY='+str(value) for key, value in capacities.items()] + [str(harness)]
    command += [str(root/'sources'/name) for name in paths if name.endswith('.c')]
    command += ['-o', str(root/'direct-linker')]
    (root/'direct-link-command.json').write_text(json.dumps(command, indent=2)+'\n')
    subprocess.run(command, capture_output=True, check=True)
    results = []
    for entry, expected in cases:
        folder = root/entry
        folder.mkdir()
        link_command = [str(root/'direct-linker'), entry]
        (folder/'link-command.json').write_text(json.dumps(link_command)+'\n')
        linked = subprocess.run(link_command, input=assembly,
                                capture_output=True, timeout=60)
        (folder/'link.stderr').write_bytes(linked.stderr)
        assert linked.returncode == 0, linked.stderr
        assert not linked.stderr and len(linked.stdout) == 8388608
        (folder/'image.bin').write_bytes(linked.stdout)
        command = [str(ROOT/'build/bin/space-256m'), '--ticks', '1000000' if large else '100000', '--core',
                   str(folder/'image.bin'), '--trace', str(folder/'trace.txt')]
        (folder/'command.json').write_text(json.dumps(command)+'\n')
        checked = subprocess.run(command, capture_output=True, check=True, timeout=120)
        (folder/'out.bin').write_bytes(checked.stdout)
        assert not checked.stderr and checked.stdout == (b'' if expected is None else struct.pack('<I', expected))
        with (folder/'trace.txt').open('rb') as trace:
            trace.seek(max(0, (folder/'trace.txt').stat().st_size-80))
            assert trace.read().endswith(b' idle\n')
        results.append({'entry': entry, 'expected': expected, 'image_sha256': digest(folder/'image.bin')})
    evidence['direct_cases'] = results
    evidence['linker_sources_sha256'] = {name: digest(root/'sources'/name) for name in paths}
    (root/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
