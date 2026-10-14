"""Try TCC's own preprocessor with an explicit identification-only Linux patch."""
import argparse
import difflib
import json
import shlex
from pathlib import Path
from probe_tcc_kernel_macros import CASES
from probe_tcc_units import digest, link_probe, run


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
    overlay = root/"overlay/linux"
    overlay.mkdir(parents=True)
    original = args.linux/"include/linux/compiler_types.h"
    text = original.read_text()
    needle = "#ifdef __clang__\n#include <linux/compiler-clang.h>"
    assert text.count(needle) == 1
    replacement = "#if defined(__TINYC__)\n#include <linux/compiler-tcc.h>\n#elif defined(__clang__)\n#include <linux/compiler-clang.h>"
    changed = text.replace(needle, replacement)
    (root/"compiler_types.original.h").write_bytes(original.read_bytes())
    (overlay/"compiler_types.h").write_text(changed)
    (root/"identification.patch").write_text("".join(difflib.unified_diff(text.splitlines(True), changed.splitlines(True), fromfile="include/linux/compiler_types.h", tofile="overlay/linux/compiler_types.h")))
    (overlay/"compiler-tcc.h").write_text('/* Diagnostic identity only. No capabilities or replacement macros. */\n#ifndef __LINUX_COMPILER_TYPES_H\n#error "include compiler_types.h first"\n#endif\n#ifndef __TINYC__\n#error "TCC required"\n#endif\n')
    summary = {"scope": "host diagnostic; TCC own preprocessor with identification-only overlay and GCC-generated control configuration; not a working kernel backend", "original_compiler_types_sha256": digest(original), "patch_sha256": digest(root/"identification.patch"), "cases": {}}
    for arch in ("x86", "riscv"):
        build = getattr(args, arch+"_build").resolve()
        saved = shlex.split((build/"lib/.ctype.o.cmd").read_text().splitlines()[0].split(":=", 1)[1])
        includes = ["-I"+str(overlay.parent)]
        index = 0
        while index < len(saved):
            word = saved[index]
            if word == "-include":
                filename = saved[index+1]
                if filename.endswith("/linux/compiler_types.h"):
                    filename = str(overlay/"compiler_types.h")
                includes += [word, filename]
                index += 1
            elif word.startswith(("-I", "-D")):
                includes.append(word)
            index += 1
        for name, body in CASES.items():
            folder = root/(arch+"-"+name)
            folder.mkdir()
            source = folder/"source.c"
            source.write_text(body)
            command = [str(args.tcc.resolve()), "-std=gnu11", "-O2", "-g"]+includes
            pp = run(folder, "tcc-preprocess", command+["-E", str(source), "-o", str(folder/"source.i")], build)
            record = run(folder, "tcc-compile", command+["-c", str(source), "-o", str(folder/"tcc.o")], build)
            row = {"source_sha256": digest(source), "preprocess": pp, "compile": record}
            if (folder/"source.i").is_file():
                row["preprocessed_sha256"] = digest(folder/"source.i")
            if (folder/"tcc.o").is_file():
                row["object_sha256"] = digest(folder/"tcc.o")
                run(folder, "tcc-undefined", ["nm", "-u", str(folder/"tcc.o")], build)
                if arch == "x86" and name == "build-bug-valid":
                    row["executable"] = link_probe(folder, "tcc", folder/"tcc.o")
            summary["cases"][folder.name] = row
            (root/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
            print(folder.name, "TCC preprocess", pp["returncode"], "compile", record["returncode"], flush=True)


if __name__ == "__main__":
    main()
