"""Preparation-only driver: append guest libraries only to link commands."""
import json
import os
import sys
from pathlib import Path


def command(configuration, language, arguments):
    base=configuration[language]
    # Configure queries and dependency/preprocessor/assembler invocations
    # must not acquire object files or libraries as extra inputs.
    compile_only=any(arg in ("-c","-S","-E","-M","-MM","-fsyntax-only") for arg in arguments)
    query=any(arg in ("--version","-V","-qversion") or arg.startswith(("-print-","-dump"))
              for arg in arguments)
    query=query or (arguments==["-v"])
    libraries=[] if compile_only or query else configuration["libraries"]
    return base+arguments+libraries


def main():
    configuration=json.loads(Path(sys.argv[1]).read_text())
    argv=command(configuration,sys.argv[2],sys.argv[3:])
    os.execv(argv[0],argv)


if __name__=="__main__":
    main()
