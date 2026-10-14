"""Fetch pinned GCC sources for image preparation; never compile user C."""
import argparse
import hashlib
import json
import tarfile
import urllib.request
from pathlib import Path

VERSION = "12.5.0"
NAME = "gcc-"+VERSION+".tar.xz"
BASE = "https://gcc.gnu.org/pub/gcc/releases/gcc-"+VERSION+"/"
SHA512 = "c76020e4c844b53485502cb8a4e295221c9d37487d66c9f4559031fb14c85de20602e6387310005386cb0ef25e55067d2cfef141423bb445f3b77e7456a23533"


def digest(path, algorithm):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def archive_filter(member, destination):
    # Python 3.11's data_filter checks symlinks relative to the extraction
    # root, not their containing directory. Validate their actual target.
    if member.issym():
        base, name = Path(destination).resolve(), Path(member.name)
        if name.is_absolute() or ".." in name.parts or Path(member.linkname).is_absolute():
            raise ValueError("unsafe archive link: "+member.name)
        (base/name).resolve().relative_to(base)
        (base/name.parent/member.linkname).resolve().relative_to(base)
        return member.replace(uid=None, gid=None, uname=None, gname=None, mode=None)
    return tarfile.data_filter(member, destination)


def fetch(store, *, extract=False):
    store = store.resolve()
    store.mkdir(parents=True, exist_ok=True)
    target = store/NAME
    checksums = urllib.request.urlopen(BASE+"sha512.sum", timeout=60).read()
    published = next(line.split()[0].decode() for line in checksums.splitlines()
                     if line.split()[-1].decode().lstrip("*") == NAME)
    if published != SHA512:
        raise ValueError("published GCC checksum differs from pinned checksum")
    (store/("gcc-"+VERSION+".sha512.sum")).write_bytes(checksums)
    if not target.is_file():
        partial = target.with_suffix(target.suffix+".part")
        with urllib.request.urlopen(BASE+NAME, timeout=90) as response, partial.open("wb") as output:
            while True:
                block = response.read(1024*1024)
                if not block:
                    break
                output.write(block)
        if digest(partial, "sha512") != SHA512:
            raise ValueError("downloaded GCC archive checksum mismatch")
        partial.rename(target)
    if digest(target, "sha512") != SHA512:
        raise ValueError("cached GCC archive checksum mismatch")
    receipt = {"version": VERSION, "url": BASE+NAME,
               "official_checksums_url": BASE+"sha512.sum", "bytes": target.stat().st_size,
               "sha512": SHA512, "sha256": digest(target, "sha256")}
    folder = store/("gcc-"+VERSION)
    marker = store/("gcc-"+VERSION+"-extraction.json")
    if extract:
        if folder.exists() and not marker.is_file():
            raise ValueError("partial source extraction exists; inspect it before retrying")
        if not marker.is_file():
            # Preserve the complete archive. Testsuites are extracted later
            # when needed; they dominate small-file I/O on the data disk.
            skipped, count = 0, 0
            with tarfile.open(target, "r:xz") as archive:
                for member in archive:
                    if "testsuite" in Path(member.name).parts and not member.name.endswith(".in"):
                        skipped += 1
                        continue
                    archive.extract(member, store, filter=archive_filter)
                    count += 1
            marker.write_text(json.dumps({"archive_sha512": SHA512,
                "extracted_members": count, "skipped_testsuite_members": skipped}, indent=2)+"\n")
        if json.loads(marker.read_text())["archive_sha512"] != SHA512:
            raise ValueError("source extraction is from another GCC archive")
        receipt["source_directory"] = str(folder)
    (store/("gcc-"+VERSION+"-archive.json")).write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()
    print(json.dumps(fetch(args.store, extract=args.extract), indent=2), flush=True)


if __name__ == "__main__":
    main()
