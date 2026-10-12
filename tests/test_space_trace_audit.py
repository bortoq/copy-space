"""Check lossless gzip/zstd trace storage, event audit and corrupt-file rejection."""
import gzip
import shutil
import subprocess
import tempfile
from pathlib import Path

from space_trace_audit import audit_trace, open_trace


def check():
    with tempfile.TemporaryDirectory(prefix="copy-space-trace-") as directory:
        root = Path(directory)
        data = b"".join(
            f"copy {i} 3 32 151552 8388608\nchannel {i} 1 8 0 8 0\n".encode()
            for i in range(150000)) + b"stop 150000 idle\n"
        compressed = [("gz", gzip.compress(data, compresslevel=1))]
        if shutil.which("zstd"):
            encoded = subprocess.run(["zstd", "-q", "-1", "-c"], input=data,
                                     capture_output=True, check=True)
            compressed.append(("zst", encoded.stdout))
        for extension, encoded in compressed:
            path = root / ("trace.txt."+extension)
            path.write_bytes(encoded)
            with open_trace(path) as stream:
                assert stream.read() == data, "compression changed raw trace bytes"
            cursor = {}
            assert audit_trace(path, cursor) == (150000, 150000, b"stop 150000 idle\n")
            assert cursor == {1: 150000}
            path.write_bytes(encoded[:-5])
            try:
                audit_trace(path)
            except (ValueError, EOFError, OSError, AssertionError):
                pass
            else:
                raise AssertionError("corrupt compressed trace was accepted")
            print("OK raw trace "+extension+": lossless, exact events, corruption rejected")


if __name__ == "__main__":
    check()
