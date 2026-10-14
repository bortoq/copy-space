"""Compare compiler front ends on frozen GCC-preprocessed Linux units.

This is a host diagnostic. RISC-V units fed to i386 TCC check language
acceptance only; RISC-V assembly failures are architecture limitations.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
import time
from pathlib import Path


UNITS = {
    "x86": ["lib/ctype", "lib/string", "lib/sort", "lib/rbtree", "lib/vsprintf",
            "lib/xarray", "lib/maple_tree", "init/main", "kernel/fork",
            "kernel/sched/core", "mm/page_alloc"],
    "riscv": ["mm/nommu", "lib/ctype", "lib/string", "lib/sort", "lib/rbtree",
              "init/main"],
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(folder, label, command, cwd):
    started = time.monotonic()
    try:
        p = subprocess.run(command, cwd=cwd, capture_output=True, timeout=120)
        record = {"returncode": p.returncode}
        stdout, stderr = p.stdout, p.stderr
    except subprocess.TimeoutExpired as error:
        record = {"returncode": None, "timeout": 120}
        stdout, stderr = error.stdout or b"", error.stderr or b""
    record.update({"args": command, "cwd": str(cwd), "seconds": time.monotonic()-started})
    (folder/(label+".stdout")).write_bytes(stdout)
    (folder/(label+".stderr")).write_bytes(stderr)
    (folder/(label+".json")).write_text(json.dumps(record, indent=2)+"\n")
    return record


def prepare_start(folder, label):
    """Use one independently compiled host startup for both C compilers."""
    source = folder/(label+"-start.c")
    source.write_text('int probe(void);void _start(void){unsigned value=probe();int result;'
        '__asm__ volatile("int $0x80":"=a"(result):"0"(4),"b"(1),"c"(&value),"d"(4):"memory");'
        '__asm__ volatile("int $0x80"::"a"(1),"b"(result!=4):"memory");for(;;){}}\n')
    start_object = folder/(label+"-start.o")
    base = ["gcc", "-m32", "-O2", "-ffreestanding", "-nostdlib", "-fno-pie",
            "-no-pie", "-fno-stack-protector"]
    compiled = run(folder, label+"-start-compile", base+["-c", str(source), "-o", str(start_object)], folder)
    assert compiled["returncode"] == 0, compiled
    return start_object


def link_probe(folder, label, object_file):
    """Link a no-argument i386 probe with explicit Linux host syscall output."""
    start_object = prepare_start(folder, label)
    base = ["gcc", "-m32", "-O2", "-ffreestanding", "-nostdlib", "-fno-pie",
            "-no-pie", "-fno-stack-protector"]
    output = folder/(label+"-program")
    linked = run(folder, label+"-link", base+[str(start_object), str(object_file), "-Wl,-e,_start", "-o", str(output)], folder)
    result = {"link": linked}
    if linked["returncode"] == 0:
        result["run"] = run(folder, label+"-run", [str(output)], folder)
        result["output_hex"] = (folder/(label+"-run.stdout")).read_bytes().hex()
        result["executable_sha256"] = digest(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--linux", type=Path, required=True)
    parser.add_argument("--x86-build", type=Path, required=True)
    parser.add_argument("--riscv-build", type=Path, required=True)
    parser.add_argument("--tcc", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    summary = {"scope": "host front-end diagnostic on original GCC-preprocessed Linux 6.12; not a TCC kernel build or Space execution",
               "tcc_sha256": digest(args.tcc), "units": {}}
    for arch, units in UNITS.items():
        build = getattr(args, arch+"_build").resolve()
        (root/(arch+".config")).write_bytes((build/".config").read_bytes())
        for unit in units:
            name = arch+"-"+unit.replace("/", "-")
            folder = root/name
            folder.mkdir()
            command_file = build/Path(unit).parent/("."+Path(unit).name+".o.cmd")
            original_source = args.linux/(unit+".c")
            assert command_file.is_file(), command_file
            (folder/"kbuild.cmd").write_bytes(command_file.read_bytes())
            (folder/"source.c").write_bytes(original_source.read_bytes())
            first = command_file.read_text().splitlines()[0].split(":=", 1)[1]
            command = shlex.split(first)
            assert "-c" in command and "-o" in command, command
            assert not any(word in command for word in (";", "&&", "|")), command
            preprocessor = []
            skip = False
            for word in command:
                if skip:
                    skip = False
                elif word == "-o":
                    skip = True
                elif word == "-c" or word.startswith("-Wp,-MMD,"):
                    continue
                else:
                    preprocessor.append(word)
            preprocessed = folder/"source.i"
            pp = run(folder, "gcc-preprocess", preprocessor+["-E", "-o", str(preprocessed)], build)
            assert pp["returncode"] == 0, (name, pp)
            # Keep the real compiler/ABI flags; cpp-output bypasses include flags.
            reference = command[:]
            reference[reference.index("-o")+1] = str(folder/"gcc.o")
            reference[reference.index(str(original_source))] = str(preprocessed)
            reference += ["-x", "none"]
            gcc = run(folder, "gcc-compile", reference, build)
            assert gcc["returncode"] == 0, (name, gcc)
            row = {"source_sha256": digest(original_source),
                   "preprocessed_sha256": digest(preprocessed), "gcc": gcc}
            for mode, flags in (("strict", ["-Werror", "-Wunsupported"]), ("relaxed", [])):
                output = folder/("tcc-"+mode+".o")
                row["tcc-"+mode] = run(folder, "tcc-"+mode,
                    [str(args.tcc.resolve()), "-std=gnu11", "-O2", "-g", "-Wall"]+
                    flags+["-c", str(preprocessed), "-o", str(output)], build)
                if output.is_file():
                    run(folder, "tcc-"+mode+"-undefined", ["nm", "-u", str(output)], build)
                    row["tcc-"+mode]["object_sha256"] = digest(output)
            run(folder, "gcc-undefined", ["nm", "-u", str(folder/"gcc.o")], build)
            row["gcc_object_sha256"] = digest(folder/"gcc.o")
            summary["units"][name] = row
            (root/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
            print(name, "gcc", gcc["returncode"], "tcc-strict", row["tcc-strict"]["returncode"],
                  "tcc-relaxed", row["tcc-relaxed"]["returncode"], flush=True)


if __name__ == "__main__":
    main()
