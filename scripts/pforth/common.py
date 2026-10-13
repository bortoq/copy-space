"""Pinned pForth source selection and freestanding port flags."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORT = ROOT / "runtime/pforth"
UPSTREAM = ROOT / "third_party/pforth"
REVISION = "e5617638c3a397c644fe82c6301711867a0ca1bf"


def sources(bootstrap=False):
    names = ["pf_cglue.c", "pf_inner.c", "pf_io.c", "pf_mem.c",
             "pf_text.c", "pf_words.c", "pfcompil.c",
             "paging/pagedmem.c", "paging/lockpage.c", "paging/qadmpage.c"]
    return [UPSTREAM / "csrc" / name for name in names] + [PORT / "clib.c", PORT / "core.c", PORT / "custom.c"] + (
        [UPSTREAM / "csrc/pf_save.c", PORT / "bootstrap/export.c", PORT / "bootstrap/linux32.c"]
        if bootstrap else [PORT / "dictionary.c", PORT / "main.c"])


def flags(bootstrap=False):
    result = ["-I"+str(UPSTREAM / "csrc"), "-I"+str(PORT / "compat"),
              "-I"+str(ROOT / "runtime/rv32i"),
              "-I"+str(PORT / "bootstrap" if bootstrap else PORT),
              "-DPF_NO_STDIO", "-DPF_NO_CLIB", "-DPF_NO_MALLOC", "-DPF_NO_FILEIO",
              "-DPF_USER_INC1=\""+str(PORT / "compat/environment.h")+"\"",
              "-DPF_USER_INC2=\""+str(PORT / "config.h")+"\"",
              "-DPF_MEM_POOL_SIZE="+str(524288 if bootstrap else 65536),
              "-DPF_DEFAULT_HEADER_SIZE=131072", "-DPF_DEFAULT_CODE_SIZE=262144",
              "-fno-builtin", "-fsigned-char", "-ffunction-sections", "-fdata-sections",
              "-Wl,--gc-sections", "-fno-strict-aliasing",
              "-Wno-cast-function-type", "-Wno-unused-function",
              "-Wno-error=sign-compare", "-Wno-error=unused-parameter",
              "-Wno-error=incompatible-pointer-types", "-Wno-error=discarded-qualifiers",
              "-Wno-error=cpp"]
    if not bootstrap:
        result.append("-DPF_NO_INIT")
    return result
