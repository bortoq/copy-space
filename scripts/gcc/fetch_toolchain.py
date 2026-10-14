"""Extract pinned preparation tools without changing system packages."""
import argparse
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

PACKAGES = [
    ("g/gcc-riscv64-unknown-elf", "gcc-riscv64-unknown-elf_12.2.0-14+deb12u1+11+b2_amd64.deb",
     "6117b2328a58059977e04e9938fffa2016cc88a2dc0ca70d1efeeea0c7b4dace"),
    ("b/binutils-riscv64-unknown-elf", "binutils-riscv64-unknown-elf_2.40-2+4+b1_amd64.deb",
     "e3b54bd849891b1afb83b9751efe671e35d6267ce791ea9b01205b616276021c"),
]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    store, root = args.store.resolve(), args.root.resolve()
    store.mkdir(parents=True, exist_ok=True)
    if root.exists():
        raise ValueError("toolchain root already exists; inspect before retrying")
    records = []
    for directory, name, expected in PACKAGES:
        path = store/name
        url = "https://deb.debian.org/debian/pool/main/"+directory+"/"+name
        if not path.is_file():
            partial = path.with_suffix(".deb.part")
            with urllib.request.urlopen(url, timeout=60) as source, partial.open("wb") as target:
                while block := source.read(1024*1024):
                    target.write(block)
            if sha256(partial) != expected:
                raise ValueError("download checksum mismatch: "+name)
            partial.rename(path)
        if sha256(path) != expected:
            raise ValueError("cached checksum mismatch: "+name)
        records.append({"file": name, "url": url, "sha256": expected,
                        "bytes": path.stat().st_size})
    root.mkdir(parents=True)
    for row in records:
        subprocess.run(["dpkg-deb", "--extract", str(store/row["file"]), str(root)], check=True)
    compiler = root/"usr/bin/riscv64-unknown-elf-gcc"
    result = subprocess.run([str(compiler), "--version"], capture_output=True, check=True)
    (root/"preparation-toolchain.json").write_text(json.dumps({
        "packages": records, "compiler": str(compiler), "version": result.stdout.decode(),
        "checksum_sources": ["https://packages.debian.org/bookworm/amd64/"+p+"/download"
                             for p in ("gcc-riscv64-unknown-elf", "binutils-riscv64-unknown-elf")],
        "scope": "image preparation only; not guest GCC execution"}, indent=2)+"\n")
    print(result.stdout.decode(), end="", flush=True)


if __name__ == "__main__":
    main()
