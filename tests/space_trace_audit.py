"""Audit complete compressed observer traces without retaining them in RAM."""
import gzip
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_trace(path):
    path = Path(path)
    if path.suffix != ".zst":
        with gzip.open(path, "rb") as stream:
            yield stream
        return
    with subprocess.Popen(["zstd", "-q", "-d", "-c", "--", str(path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as decoder:
        try:
            yield decoder.stdout
        finally:
            decoder.stdout.close()
            error = decoder.stderr.read()
            status = decoder.wait()
            if status:
                raise ValueError("invalid zstd trace: "+error.decode(errors="replace"))


def audit_trace(path, channel_bytes=None):
    copies, channels, pending, last = 0, 0, b"", b""
    with open_trace(path) as trace:
        while block := trace.read(8*1024*1024):
            data = pending+block
            end = data.rfind(b"\n")
            if end < 0:
                pending = data
                continue
            complete, pending = data[:end+1], data[end+1:]
            copies += complete.count(b"\ncopy ")+complete.startswith(b"copy ")
            channels += complete.count(b"\nchannel ")+complete.startswith(b"channel ")
            if channel_bytes is not None:
                for match in re.finditer(rb"(?m)^channel [^\n]+\n", complete):
                    fields = match.group().split()
                    assert len(fields) == 7, "invalid channel record"
                    channel = int(fields[2])
                    channel_bytes[channel] = channel_bytes.get(channel, 0)+(int(fields[5])+7)//8
            last = complete[complete.rfind(b"\n", 0, len(complete)-1)+1:]
    assert not pending, "incomplete final trace record"
    return copies, channels, last
