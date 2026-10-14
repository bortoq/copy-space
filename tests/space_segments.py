"""Continue primitive space execution from full snapshots and logical file cursors."""
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from space_trace_audit import audit_trace


def execute_segments(emulator, folder, data_file, *, space_bytes, layer_bytes,
                     ticks, timeout, compression="zstd", initial_core=None, max_parts=512,
                     resume=False):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    def signature(path):
        with Path(path).open("rb") as source:
            digest = hashlib.sha256()
            while block := source.read(1024*1024):
                digest.update(block)
        return digest.hexdigest()

    configuration = {"input_sha256": signature(data_file),
                     "emulator_sha256": signature(emulator),
                     "initial_core_sha256": signature(initial_core) if initial_core else None,
                     "space_bytes": space_bytes, "layer_bytes": layer_bytes,
                     "ticks": ticks, "compression": compression}
    metadata = folder / "execution.json"
    if resume:
        assert json.loads(metadata.read_text()) == configuration, "changed execution input/configuration"
        parts = json.loads((folder / "segments.json").read_text())
        assert parts and parts[-1]["stop"] == "limit", "no resumable checkpoint"
        previous = folder / f"part-{parts[-1]['part']:04d}"
        core = previous / "space.bin"
        if parts[-1]["dump_file"].endswith(".gz"):
            with gzip.open(previous / parts[-1]["dump_file"], "rb") as source, core.open("wb") as target:
                shutil.copyfileobj(source, target, 1024*1024)
        assert signature(core) == parts[-1]["dump_sha256"], "changed checkpoint"
        input_offset = parts[-1]["input_after"]
        assert (folder / "program.in").stat().st_size == parts[-1]["output_after"], "changed output length"
    else:
        assert not metadata.exists() and not (folder / "segments.json").exists(), "use a new folder or resume=True"
        metadata.write_text(json.dumps(configuration, indent=2)+"\n")
        core, input_offset, parts = initial_core, 0, []
    total_copies = sum(entry["copy_events"] for entry in parts)
    total_channels = sum(entry["channel_events"] for entry in parts)
    first = parts[-1]["part"]+1 if parts else 0
    with Path(data_file).open("rb") as incoming, (folder / "program.in").open("r+b" if resume else "wb") as output:
        output.seek(0, os.SEEK_END)
        for index in range(first, first+max_parts):
            part = folder / f"part-{index:04d}"
            if resume and part.exists():
                # Preserve the interrupted attempt; only completed checkpoints
                # are used to restore memory and channel cursors.
                attempt = 0
                while part.with_name(part.name+f".interrupted-{attempt}").exists():
                    attempt += 1
                part.rename(part.with_name(part.name+f".interrupted-{attempt}"))
            part.mkdir()
            dump, fifo = part / "space.bin", part / "trace.fifo"
            trace = part / ("trace.txt.zst" if compression == "zstd" else "trace.txt.gz")
            fifo.unlink(missing_ok=True)
            os.mkfifo(fifo)
            keepalive = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
            errors = []

            def compress():
                try:
                    with fifo.open("rb", buffering=0) as source:
                        if compression == "gzip":
                            with gzip.open(trace, "wb", compresslevel=1) as target:
                                shutil.copyfileobj(source, target, 1024*1024)
                        else:
                            with trace.open("wb") as target, subprocess.Popen(
                                    ["zstd", "-q", "-1", "-c"], stdin=subprocess.PIPE,
                                    stdout=target, stderr=subprocess.PIPE) as encoder:
                                try:
                                    shutil.copyfileobj(source, encoder.stdin, 1024*1024)
                                finally:
                                    encoder.stdin.close()
                                error = encoder.stderr.read()
                                assert encoder.wait() == 0, error
                except Exception as error:
                    errors.append(error)

            worker = threading.Thread(target=compress, daemon=True)
            worker.start()
            command = [str(emulator), "--ticks", str(ticks), "--trace", str(fifo),
                       "--dump-space", str(dump)]
            if core is not None:
                command += ["--core", str(core)]
            (part / "args.json").write_text(json.dumps(command, indent=2)+"\n")
            incoming.seek(input_offset)
            output_before = output.tell()
            try:
                with (part / "stderr.txt").open("wb") as error_output:
                    result = subprocess.run(command, stdin=incoming, stdout=output,
                                            stderr=error_output, timeout=timeout)
            finally:
                os.close(keepalive)
                worker.join(timeout=30)
                fifo.unlink()
            assert not worker.is_alive() and not errors, errors
            assert result.returncode == 0 and not (part / "stderr.txt").read_bytes()
            raw = dump.read_bytes()
            assert len(raw) == space_bytes
            cursor = {}
            copies, channels, last = audit_trace(trace, cursor)
            idle = raw[:layer_bytes] == bytes(layer_bytes)
            assert last.endswith(b" idle\n" if idle else b" limit\n"), last
            assert output.tell()-output_before == cursor.get(2, 0), "OUT cursor differs from events"
            next_offset = input_offset+cursor.get(1, 0)
            assert next_offset <= Path(data_file).stat().st_size
            entry = {"part": index, "trace_file": str(trace.relative_to(folder)),
                     "dump_file": "space.bin", "input_file": str(Path(data_file).resolve()),
                     "input_before": input_offset, "input_after": next_offset,
                     "output_before": output_before, "output_after": output.tell(),
                     "copy_events": copies, "channel_events": channels,
                     "stop": "idle" if idle else "limit", "dump_sha256": hashlib.sha256(raw).hexdigest()}
            (part / "evidence.json").write_text(json.dumps(entry, indent=2)+"\n")
            parts.append(entry)
            # The previous snapshot has been consumed by this process. Keep it
            # losslessly compressed, rather than retaining another whole space.
            if index and initial_core != core:
                with Path(core).open("rb") as source, gzip.open(str(core)+".gz", "wb", compresslevel=1) as target:
                    shutil.copyfileobj(source, target, 1024*1024)
                with gzip.open(str(core)+".gz", "rb") as source:
                    digest = hashlib.sha256()
                    while block := source.read(1024*1024):
                        digest.update(block)
                assert digest.hexdigest() == parts[-2]["dump_sha256"]
                Path(core).unlink()
                parts[-2]["dump_file"] = "space.bin.gz"
                Path(core).with_name("evidence.json").write_text(json.dumps(parts[-2], indent=2)+"\n")
            input_offset, core = next_offset, dump
            total_copies += copies
            total_channels += channels
            (folder / "segments.json").write_text(json.dumps(parts, indent=2)+"\n")
            print(f"OK space segment {index}: {entry['stop']}, IN={input_offset}, OUT={output.tell()}, copies={copies}", flush=True)
            if idle:
                shutil.copyfile(dump, folder / "space.bin")
                return {"copy_events": total_copies, "channel_events": total_channels,
                        "seconds": time.monotonic()-started,
                        "trace_files": [entry["trace_file"] for entry in parts], "parts": len(parts)}
    raise AssertionError("space exceeded the segment limit")
