"""Audit complete compressed observer traces without retaining them in RAM."""
import gzip


def audit_trace(path):
    copies, channels, pending, last = 0, 0, b"", b""
    with gzip.open(path, "rb") as trace:
        while block := trace.read(8*1024*1024):
            data = pending+block
            end = data.rfind(b"\n")
            if end < 0:
                pending = data
                continue
            complete, pending = data[:end+1], data[end+1:]
            copies += complete.count(b"\ncopy ")+complete.startswith(b"copy ")
            channels += complete.count(b"\nchannel ")+complete.startswith(b"channel ")
            last = complete[complete.rfind(b"\n", 0, len(complete)-1)+1:]
    assert not pending, "incomplete final trace record"
    return copies, channels, last
