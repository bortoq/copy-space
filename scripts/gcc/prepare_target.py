"""Prepare a separate copyspace GCC target; original GCC sources stay intact."""
import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path
from fetch import VERSION, NAME, SHA512, digest


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("unexpected GCC source: " + repr(old))
    return text.replace(old, new, 1)


def derive(name, text):
    text = text.replace("moxie", "copyspace").replace("MOXIE", "COPYSPACE").replace("Moxie", "Copyspace")
    if name == "moxie.h":
        text = replace_once(text, "#define GCC_COPYSPACE_H", "#define GCC_COPYSPACE_H\n#define TARGET_DEFAULT MASK_LITTLE_ENDIAN")
    if name == "moxie.md":
        # No branch displacement measured in the original CPU's instruction bytes.
        start = text.index("  if (get_attr_length (insn) == 2)")
        end = text.index("\n}", start)
        text = text[:start] + '  return "copy.branch.<CC>\\\\t%l0";' + text[end:]
        text = text.replace('"nop")', '"copy.nop")').replace('"ret")', '"copy.ret")')
        text = re.sub(r"(?<![\w.])([a-z]+(?:\.[a-z]+)?)(?=\\\\t)", r"copy.\1", text)
        text = text.replace('"<mul>', '"copy.<mul>')
    if name == "moxie.cc":
        for function, body in [
            ("copyspace_asm_trampoline_template", '(void)f; sorry ("copyspace nested-function trampolines are not implemented");'),
            ("copyspace_trampoline_init", '(void)m_tramp; (void)fndecl; (void)chain_value; sorry ("copyspace nested-function trampolines are not implemented");'),
        ]:
            start = text.index("\n{", text.index("\n" + function + " ("))
            end = text.index("\n}", start)
            text = text[:start] + "\n{\n  " + body + text[end:]
        start = text.index("\n{", text.index("\ncopyspace_option_override (")) + 2
        text = text[:start] + '\n  if (!TARGET_LITTLE_ENDIAN) sorry ("copyspace requires little-endian data");' + text[start:]
    return text


def overlay(destination, original, skip):
    destination.mkdir()
    for entry in original.iterdir():
        if entry.name not in skip:
            (destination / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    store = args.store.resolve()
    archive = store / NAME
    if digest(archive, "sha512") != SHA512:
        raise ValueError("GCC archive differs from pinned release")
    original = store / ("gcc-" + VERSION)
    names = ["config.sub", "gcc/config.gcc"]
    target_names = ["moxie.h", "moxie.cc", "moxie.md", "moxie-protos.h", "moxie.opt",
                    "constraints.md", "predicates.md", "t-moxie"]
    names += ["gcc/config/moxie/" + name for name in target_names]
    source = {}
    prefix="gcc-"+VERSION+"/"
    wanted={prefix+name:name for name in names}
    with tarfile.open(archive, "r|xz") as package:
        for member in package:
            if member.name not in wanted:
                continue
            name=wanted[member.name]
            source[name]=package.extractfile(member).read()
            if (original/name).read_bytes()!=source[name]:
                raise ValueError("extracted GCC source changed: "+name)
            if len(source)==len(names):
                break
    if len(source)!=len(names):
        raise ValueError("missing target inputs in pinned archive")
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    tree = root / "source"
    overlay(tree, original, {"config.sub", "gcc"})
    overlay(tree / "gcc", original / "gcc", {"config.gcc", "config"})
    overlay(tree / "gcc/config", original / "gcc/config", {"copyspace"})
    target = tree / "gcc/config/copyspace"
    target.mkdir()
    for name in target_names:
        (target / name.replace("moxie", "copyspace")).write_text(derive(name, source["gcc/config/moxie/" + name].decode()))
    config = source["gcc/config.gcc"].decode()
    config = replace_once(config, "moxie*)\tcpu_type=moxie", "copyspace*)\tcpu_type=copyspace\n\t;;\nmoxie*)\tcpu_type=moxie")
    config = replace_once(config, "moxie-*-elf)", 'copyspace-*-elf)\n\tgas=yes\n\tgnu_ld=yes\n\ttm_file="dbxelf.h elfos.h newlib-stdint.h ${tm_file}"\n\ttmake_file="${tmake_file} copyspace/t-copyspace"\n\t;;\nmoxie-*-elf)')
    (tree / "gcc/config.gcc").write_text(config)
    (tree / "config.sub").write_text(replace_once(source["config.sub"].decode(), "| moxie \\", "| copyspace | moxie \\"))
    (tree / "config.sub").chmod(0o755)
    files = [tree / "gcc/config.gcc", tree / "config.sub"] + list(target.iterdir())
    manifest = {"scope": "copyspace target source prototype; guest template lowering still required",
                "target": "copyspace-unknown-elf", "gcc_archive_sha512": SHA512,
                "original_source_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in source.items()},
                "generated_source_sha256": {str(p.relative_to(tree)): digest(p, "sha256") for p in files},
                "original_source": str(original)}
    (root / "target.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared", manifest["target"], "in", tree)


if __name__ == "__main__":
    main()
