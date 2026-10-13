"""Losslessly retain full completed target dumps and observer logs."""
import gzip
import hashlib
import json
import os
from pathlib import Path


def archive_target(folder):
    folder = Path(folder)
    assert (folder / "trace.txt").read_bytes().splitlines()[-1].endswith(b" idle")
    for filename, metadata in (("space.bin", "dump-archive.json"),
                               ("trace.txt", "trace-archive.json")):
        source = folder / filename
        target = source.with_name(source.name+".gz")
        pending = source.with_name(source.name+".gz.pending")
        record = folder / metadata
        assert not target.exists() and not pending.exists() and not record.exists()
        original = source.read_bytes()
        signature = hashlib.sha256(original).hexdigest()
        with gzip.open(pending, "wb", compresslevel=1) as output:
            output.write(original)
        with gzip.open(pending, "rb") as incoming:
            restored = incoming.read()
        assert len(restored) == len(original) and hashlib.sha256(restored).hexdigest() == signature
        assert source.read_bytes() == original
        pending.rename(target)
        proof = {"original_file": source.name, "original_bytes": len(original),
                 "original_sha256": signature, "archive_file": target.name,
                 "archive_bytes": target.stat().st_size,
                 "archive_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        with record.open("w") as output:
            json.dump(proof, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        source.unlink()
