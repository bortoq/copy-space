"""Host-only diagnostics using original Linux compiler and data-layout macros."""
import argparse
import json
import shlex
from pathlib import Path
from probe_tcc_units import digest, link_probe, run


CASES = {
    "build-bug-valid": '#include <linux/build_bug.h>\nstatic __always_inline int checked(int value){BUILD_BUG_ON(value!=7);return value;}\nint probe(void){return checked(7);}\n',
    "build-bug-invalid": '#include <linux/build_bug.h>\nstatic __always_inline int checked(int value){BUILD_BUG_ON(value!=7);return value;}\nint probe(void){return checked(8);}\n',
    "rw-hint": '#include <linux/rw_hint.h>\nint probe(void){return sizeof(enum rw_hint)*7;}\n',
    "minmax": '#include <linux/minmax.h>\nvolatile int a=3,b=4;\nint probe(void){return min(a,b)+4;}\n',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--x86-build", type=Path, required=True)
    parser.add_argument("--riscv-build", type=Path, required=True)
    parser.add_argument("--tcc", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    summary = {"scope": "host diagnostic of original Linux 6.12 macros after GCC preprocessing; not a kernel or Space build", "cases": {}}
    for arch in ("x86", "riscv"):
        build = getattr(args, arch+"_build").resolve()
        command_file = build/"lib/.ctype.o.cmd"
        command = shlex.split(command_file.read_text().splitlines()[0].split(":=", 1)[1])
        original = next(word for word in command if word.endswith("/lib/ctype.c"))
        for name, text in CASES.items():
            label = arch+"-"+name
            folder = root/label
            folder.mkdir()
            source, pp = folder/"source.c", folder/"source.i"
            source.write_text(text)
            changed = command[:]
            changed[changed.index(original)] = str(source)
            preprocess = []
            skip = False
            for word in changed:
                if skip:
                    skip = False
                elif word == "-o":
                    skip = True
                elif word == "-c" or word.startswith("-Wp,-MMD,"):
                    continue
                else:
                    preprocess.append(word)
            record = run(folder, "gcc-preprocess", preprocess+["-E", "-o", str(pp)], build)
            assert record["returncode"] == 0, label
            changed[changed.index(str(source))] = str(pp)
            changed[changed.index("-o")+1] = str(folder/"gcc.o")
            gcc = run(folder, "gcc-compile", changed, build)
            assert (gcc["returncode"] != 0 if name == "build-bug-invalid" else gcc["returncode"] == 0), label
            row = {"source_sha256": digest(source), "preprocessed_sha256": digest(pp), "gcc": gcc}
            if (folder/"gcc.o").is_file():
                run(folder, "gcc-undefined", ["nm", "-u", str(folder/"gcc.o")], build)
                row["gcc_object_sha256"] = digest(folder/"gcc.o")
            tcc = run(folder, "tcc-compile", [str(args.tcc.resolve()), "-std=gnu11", "-O2", "-g", "-c", str(pp), "-o", str(folder/"tcc.o")], build)
            row["tcc"] = tcc
            if (folder/"tcc.o").is_file():
                run(folder, "tcc-undefined", ["nm", "-u", str(folder/"tcc.o")], build)
                run(folder, "tcc-assembly", ["objdump", "-d", str(folder/"tcc.o")], build)
                row["tcc_object_sha256"] = digest(folder/"tcc.o")
            if arch == "x86" and name == "build-bug-valid":
                row["gcc_executable"] = link_probe(folder, "gcc", folder/"gcc.o")
                assert row["gcc_executable"].get("output_hex") == "07000000", row
                if (folder/"tcc.o").is_file():
                    row["tcc_executable"] = link_probe(folder, "tcc", folder/"tcc.o")
            summary["cases"][label] = row
            (root/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
            print(label, "GCC", gcc["returncode"], "TCC", tcc["returncode"], flush=True)


if __name__ == "__main__":
    main()
