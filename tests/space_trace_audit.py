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


def audit_trace(path, channel_bytes=None, *, channels_only=False):
    copies, channels, pending, last = 0, 0, b"", b""
    reported = None
    with open_trace(path) as trace:
        while block := trace.read(8*1024*1024):
            data = pending+block
            end = data.rfind(b"\n")
            if end < 0:
                pending = data
                continue
            complete, pending = data[:end+1], data[end+1:]
            new_copies = complete.count(b"\ncopy ")+complete.startswith(b"copy ")
            new_channels = complete.count(b"\nchannel ")+complete.startswith(b"channel ")
            assert reported is None or not (new_copies or new_channels), "events after counts"
            copies += new_copies
            channels += new_channels
            totals = []
            if channels_only or b"counts " in complete:
                totals = list(re.finditer(rb"(?m)^counts ([0-9]+) ([0-9]+)\n", complete))
                assert len(totals) == len(re.findall(rb"(?m)^counts[^\n]*\n", complete)), "invalid counts"
            if totals:
                assert channels_only, "counts require channel-only mode"
                assert reported is None and len(totals) == 1, "duplicate counts"
                reported = tuple(map(int, totals[0].groups()))
                assert all(value <= 0xffffffffffffffff for value in reported), "counts overflow"
                tail = complete[totals[0].end():]
                assert not re.search(rb"(?m)^(copy|channel) ", tail), "events after counts"
            if channel_bytes is not None:
                for match in re.finditer(rb"(?m)^channel [^\n]+\n", complete):
                    fields = match.group().split()
                    assert len(fields) == 7, "invalid channel record"
                    channel = int(fields[2])
                    channel_bytes[channel] = channel_bytes.get(channel, 0)+(int(fields[5])+7)//8
            last = complete[complete.rfind(b"\n", 0, len(complete)-1)+1:]
    assert not pending, "incomplete final trace record"
    if channels_only:
        assert not copies, "copy records in channel-only trace"
        assert reported is not None, "missing counts"
        assert reported[1] == channels, "channel counts differ"
        assert last.startswith(b"stop "), "missing terminal stop"
        copies = reported[0]
    return copies, channels, last
