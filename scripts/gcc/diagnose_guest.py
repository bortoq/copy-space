"""Diagnose the guest cc1 with QEMU; this is not Space execution evidence."""
import argparse
import hashlib
import json
import struct
import subprocess
import time
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--qemu", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    image = args.image.resolve()
    manifest = json.loads((image / "image.json").read_text())
    if not manifest.get("framed_output"):
        raise ValueError("a GCCOUT1 image is required")
    if digest(image / "gcc-space.elf") != manifest["elf_sha256"]:
        raise ValueError("original guest ELF changed")
    for name, expected in manifest["runtime_sources"].items():
        if digest(image / "sources" / name) != expected:
            raise ValueError("frozen runtime source changed: " + name)
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    job = root / "job.bin"
    job.write_bytes(args.job.read_bytes())
    if job.read_bytes()[:8] != b"GCCJOB1\0":
        raise ValueError("expected guest job packet, not Space boot stream")
    script = root / "diagnostic.ld"
    source = (image / "sources/runtime/gcc/link.ld").read_text()
    if source.count(". = 0;") != 1:
        raise ValueError("unexpected original linker script")
    script.write_text(source.replace(". = 0;", ". = 0x10000;", 1))
    link = json.loads((image / "link.json").read_text())
    argv = link["argv"]
    elf = root / "gcc-diagnostic.elf"
    argv[argv.index("-o") + 1] = str(elf)
    argv[argv.index("-T") + 1] = str(script)
    argv = [f"-Wl,-Map={root}/diagnostic.map" if a.startswith("-Wl,-Map=") else a for a in argv]
    inputs = {}
    for argument in argv:
        if argument.endswith((".o", ".a")):
            path = Path(argument)
            if not path.is_absolute():
                path = Path(link["cwd"]) / path
            inputs[str(path.resolve())] = digest(path)
    (root / "link-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    (root / "link.json").write_text(json.dumps({"argv": argv, "cwd": link["cwd"]}, indent=2) + "\n")
    with (root / "link.stdout").open("wb") as out, (root / "link.stderr").open("wb") as err:
        linked = subprocess.run(argv, cwd=link["cwd"], stdout=out, stderr=err, timeout=args.timeout)
    (root / "link.status.json").write_text(json.dumps({"returncode": linked.returncode}) + "\n")
    if linked.returncode:
        raise RuntimeError("diagnostic link failed; see link.stderr")
    qemu = args.qemu.resolve()
    command = [str(qemu), "-strace", str(elf)]
    (root / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    started = time.monotonic()
    evidence = {"scope": "QEMU diagnostic only; relocated guest ELF, not Space execution",
                "original_elf_sha256": manifest["elf_sha256"], "elf_sha256": digest(elf),
                "qemu_sha256": digest(qemu), "job_sha256": digest(job)}
    with job.open("rb") as incoming, (root / "out.bin").open("wb") as out, (root / "syscalls.txt").open("wb") as err:
        try:
            result = subprocess.run(command, stdin=incoming, stdout=out, stderr=err, timeout=args.timeout)
            evidence["returncode"] = result.returncode
        except subprocess.TimeoutExpired:
            evidence["timeout"] = True
    evidence["seconds"] = time.monotonic() - started
    evidence["out_sha256"] = digest(root / "out.bin")
    (root / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    packet = (root / "out.bin").read_bytes()
    if len(packet) < 24 or packet[:8] != b"GCCOUT1\0":
        raise RuntimeError("guest produced no complete GCCOUT1 header; see evidence/syscalls")
    code, outsize, errsize, filesize = struct.unpack_from("<IIII", packet, 8)
    if outsize + errsize > 16 * 1024 * 1024 or len(packet) != 24 + outsize + errsize + filesize:
        raise RuntimeError("invalid GCCOUT1 lengths")
    if evidence.get("returncode") != code or (code and filesize):
        raise RuntimeError("guest exit and response disagree")
    (root / "stdout.bin").write_bytes(packet[24:24 + outsize])
    (root / "stderr.bin").write_bytes(packet[24 + outsize:24 + outsize + errsize])
    (root / "result.bin").write_bytes(packet[24 + outsize + errsize:])
    print(f"Guest diagnostic exit {code}: stdout={outsize}, stderr={errsize}, result={filesize}")
    if code:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
