"""Pack original C files for IN; the guest resolves and preprocesses includes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

MAGIC = b"\0CCFILES1"


def name_bytes(name, *, root=False):
    encoded = name.encode("utf-8")
    if (len(encoded)>4096 or b"\0" in encoded or
        (not encoded and not root) or
        (encoded and any(part in (b"", b".", b"..") for part in encoded.split(b"/")))):
        raise ValueError("file names and include roots must be canonical relative POSIX paths")
    return encoded


def pack_files(files, roots, main=0):
    if not 1<=len(files)<=1024 or not 0<=main<len(files) or len(roots)>32:
        raise ValueError("invalid CCFILES1 file/root counts or main index")
    result=bytearray(MAGIC+struct.pack("<III",len(files),main,len(roots)))
    for root in roots:
        name=name_bytes(root,root=True)
        result.extend(struct.pack("<I",len(name))+name)
    offsets=[]; seen=set()
    for name,content in files:
        encoded=name_bytes(name)
        if encoded in seen:
            raise ValueError("duplicate file name: "+name)
        seen.add(encoded)
        if len(content)>0xffffffff:
            raise ValueError("file exceeds CCFILES1 length range")
        result.extend(struct.pack("<II",len(encoded),len(content))+encoded)
        offsets.append(len(result))
        result.extend(content)
    return bytes(result), offsets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--image", type=Path, default=Path("build/copy-c/compiler.stream"))
    parser.add_argument("-o", "--output", type=Path, default=Path("build/copy-c/job.in"))
    parser.add_argument("--bundle", action="store_true", help="send a CCFILES1 bundle even without extra files")
    parser.add_argument("--main-name", help="main file name in the bundle (default: source basename)")
    parser.add_argument("--file", action="append", default=[], metavar="NAME=PATH", help="add unmodified file bytes")
    parser.add_argument("-I", "--include-dir", action="append", metavar="NAME", help="guest search root; default: bundle root")
    args = parser.parse_args()
    paths=[(args.main_name if args.main_name is not None else args.source.name,args.source)]
    for entry in args.file:
        name,separator,path=entry.partition("=")
        if not separator or not path:
            parser.error("--file requires NAME=PATH")
        paths.append((name,Path(path)))
    sidecar=args.output.with_name(args.output.name+".json")
    protected={path.resolve() for _,path in paths}
    protected.update((args.image.resolve(),args.image.with_name(args.image.name+".json").resolve()))
    if args.output.resolve() in protected or sidecar.resolve() in protected:
        parser.error("output and metadata must not overwrite source, header or compiler")
    source, image = args.source.read_bytes(), args.image.read_bytes()
    bundle=args.bundle or args.main_name is not None or bool(args.file) or args.include_dir is not None
    roots=args.include_dir if args.include_dir is not None else [""]
    files=[(paths[0][0],source)]+[(name,path.read_bytes()) for name,path in paths[1:]]
    try:
        payload,offsets=pack_files(files,roots) if bundle else (source,[0])
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image+b"CC-RUN\n"+payload)
    metadata={
        "compiler": str(args.image.resolve()), "source": str(args.source.resolve()),
        "source_bytes": len(source), "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_offset": len(image)+len(b"CC-RUN\n")+offsets[0],
        "job_bytes": args.output.stat().st_size,
    }
    if bundle:
        metadata.update(input_format="CCFILES1",include_roots=roots,files=[{
            "name":name,"path":str(path.resolve()),"bytes":len(content),
            "sha256":hashlib.sha256(content).hexdigest(),
            "offset":len(image)+len(b"CC-RUN\n")+offset,
        } for (name,path),(_,content),offset in zip(paths,files,offsets)])
    sidecar.write_text(json.dumps(metadata,indent=2)+"\n")


if __name__ == "__main__":
    main()
