"""Run a copy-space image, forwarding streams and returning the guest exit code."""
import argparse
from contextlib import ExitStack
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "modules"))
from rv32i import EXIT_CODE, LAYER_BITS, SPACE_BYTES, STATUS


def word(raw, address):
    return sum(((raw[(address+i)//8] >> (7-(address+i)%8)) & 1) << i for i in range(32))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--space", type=Path, default=ROOT / "build/bin/space")
    parser.add_argument("--stream", action="store_true", help="send the packet and guest input to the standard core through IN")
    parser.add_argument("--ticks", type=int)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--dump-space", type=Path)
    parser.add_argument("--in", dest="input_path", type=Path)
    parser.add_argument("--out", dest="output_path", type=Path)
    args = parser.parse_args()
    if args.ticks is not None and args.ticks < 0:
        parser.error("ticks must not be negative")
    try:
        with tempfile.TemporaryDirectory(prefix="rv32i-run-") as directory, ExitStack() as files:
            dump = args.dump_space or Path(directory) / "space.bin"
            command = [str(args.space), "--dump-space", str(dump)]
            if not args.stream:
                command += ["--core", str(args.image)]
            if args.ticks is not None:
                command += ["--ticks", str(args.ticks)]
            if args.trace:
                command += ["--trace", str(args.trace)]
            descriptors = []
            for path, output in [(args.input_path, False), (args.output_path, True)]:
                if path is None:
                    descriptors.append(None)
                else:
                    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC if output else os.O_RDONLY
                    descriptor = os.open(path, flags, 0o666)
                    files.callback(os.close, descriptor)
                    descriptors.append(descriptor)
            # Direct file descriptors: no host-side buffering or guest execution.
            forwarding_errors = []
            if args.stream:
                # Feed the fixed packet first, then relay live guest input. No
                # program decoding or space state changes happen in this relay.
                packet = files.enter_context(args.image.open("rb", buffering=0))
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=descriptors[1])

                def forward():
                    try:
                        for source in (packet.fileno(), descriptors[0] if descriptors[0] is not None else 0):
                            while True:
                                chunk = os.read(source, 65536)
                                if not chunk:
                                    break
                                remaining = memoryview(chunk)
                                while remaining:
                                    remaining = remaining[os.write(process.stdin.fileno(), remaining):]
                    except BrokenPipeError:
                        pass
                    except OSError as error:
                        forwarding_errors.append(error)
                    finally:
                        process.stdin.close()

                feeder = threading.Thread(target=forward, daemon=True)
                feeder.start()
                process.wait()
                result = process
            else:
                result = subprocess.run(command, stdin=descriptors[0], stdout=descriptors[1])
            if forwarding_errors:
                raise forwarding_errors[0]
            if result.returncode:
                return 125
            raw = dump.read_bytes()
            if len(raw) != SPACE_BYTES or raw[:LAYER_BITS//8] != bytes(LAYER_BITS//8):
                print("RV32I did not complete (possibly tick limit)", file=sys.stderr)
                return 125
            status = word(raw, STATUS)
            if status != 10:
                print(f"RV32I stopped with status {status}", file=sys.stderr)
                return 125
            return word(raw, EXIT_CODE) & 255
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 125


if __name__ == "__main__":
    sys.exit(main())
