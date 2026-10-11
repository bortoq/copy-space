"""Concatenate compiler IN stream, its entry command and unmodified C source."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--image", type=Path, default=Path("build/copy-c/compiler.stream"))
    parser.add_argument("-o", "--output", type=Path, default=Path("build/copy-c/job.in"))
    args = parser.parse_args()
    if args.output.resolve() in (args.source.resolve(), args.image.resolve()):
        parser.error("output must not overwrite source or compiler")
    source, image = args.source.read_bytes(), args.image.read_bytes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image+b"CC-RUN\n"+source)
    args.output.with_name(args.output.name+".json").write_text(json.dumps({
        "compiler": str(args.image.resolve()), "source": str(args.source.resolve()),
        "source_bytes": len(source), "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_offset": len(image)+len(b"CC-RUN\n"),
        "job_bytes": args.output.stat().st_size,
    }, indent=2)+"\n")


if __name__ == "__main__":
    main()
