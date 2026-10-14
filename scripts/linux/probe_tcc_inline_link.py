"""Check GNU extern-inline linkage and function identity across translation units."""
import argparse
import json
from pathlib import Path
from probe_tcc_semantics import SUPPORT
from probe_tcc_units import digest, prepare_start, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--tcc", type=Path, required=True)
    parser.add_argument("--tcc-runtime", type=Path, required=True)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    startup = prepare_start(root, "shared")
    (root/"inline.h").write_text('typedef int (*fn)(int);\nextern inline __attribute__((gnu_inline)) int f(int x){return x+1;}\n')
    for label in ("a", "b"):
        (root/(label+".c")).write_text('#include "inline.h"\nfn address_'+label+'(void){return f;}\n')
    (root/"definition.c").write_text('typedef int (*fn)(int);fn address_a(void);fn address_b(void);int f(int x){return x+1;}int probe(void){return address_a()==address_b()?7:0;}\n'+SUPPORT)
    summary = {"scope": "host i386 multi-unit diagnostic; not Space execution", "sources": {p.name: digest(p) for p in root.iterdir() if p.suffix in (".h", ".c")}, "modes": {}}
    for mode in ("gcc", "gcc-gnu89", "tcc-default", "tcc-gnu89"):
        folder = root/mode
        folder.mkdir()
        is_gcc = mode.startswith("gcc")
        base = (["gcc", "-m32", "-fno-pie", "-no-pie", "-fno-stack-protector"] if is_gcc else [str(args.tcc.resolve())])
        base += ["-std=gnu11", "-O2", "-g", "-ffreestanding", "-nostdlib"]
        if mode.endswith("gnu89"):
            base += ["-fgnu89-inline"]
        objects = []
        row = {"compile": {}}
        for name in ("a", "b", "definition"):
            obj = folder/(name+".o")
            record = run(folder, name+"-compile", base+["-c", str(root/(name+".c")), "-o", str(obj)], root)
            assert record["returncode"] == 0, (mode, name)
            row["compile"][name] = record
            objects.append(str(obj))
            run(folder, name+"-symbols", ["nm", str(obj)], root)
        output = folder/"program"
        command = base+objects+[str(startup)]
        command += (["-Wl,-e,_start"] if is_gcc else [str(args.tcc_runtime.resolve())])
        command += ["-o", str(output)]
        linked = run(folder, "link", command, root)
        row["link"] = linked
        if linked["returncode"] == 0:
            executed = run(folder, "run", [str(output)], root)
            assert executed["returncode"] == 0 and (folder/"run.stdout").stat().st_size == 4, (mode, executed)
            row.update({"run": executed, "output_hex": (folder/"run.stdout").read_bytes().hex(), "executable_sha256": digest(output)})
        if is_gcc:
            assert linked["returncode"] == 0 and row["run"]["returncode"] == 0 and row["output_hex"] == "07000000", row
        summary["modes"][mode] = row
        (root/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
        print(mode, "link", linked["returncode"], "output", row.get("output_hex", "-"), flush=True)


if __name__ == "__main__":
    main()
