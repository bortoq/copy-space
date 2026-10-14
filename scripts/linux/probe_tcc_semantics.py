"""Host-only GNU C diagnostics for choosing a Linux bootstrap compiler."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from probe_tcc_units import prepare_start


CASES = {
    "anonymous-records": "struct S{union{struct{int x,y;};struct{int a,b;};};};int probe(void){struct S s={.a=3,.b=4};return s.x+s.y;}",
    "packed-aligned": "struct __attribute__((packed,aligned(8))) S{char c;int x;};_Static_assert(sizeof(struct S)==8,\"size\");_Static_assert(__alignof__(struct S)==8,\"align\");int probe(void){struct S s={1,6};return s.c+s.x;}",
    "generic-typeof": "int probe(void){const volatile unsigned long x=7;typeof(_Generic(x,unsigned long:(unsigned long)0,default:(int)0)) y=x;return __builtin_types_compatible_p(typeof(y),unsigned long)*y;}",
    "statement-expression": "int probe(void){int n=0;return ({typeof(n) x=7;n=x;n;});}",
    "auto-type": "int probe(void){int n=0;return ({__auto_type p=&n;*p=7;*p;});}",
    "compound-literal": "struct S{int a,b;};int probe(void){struct S *p=&(struct S){.a=3,.b=4};return p->a+p->b;}",
    "range-designator": "int a[8]={[0 ... 7]=7};int probe(void){return a[3];}",
    "flexible-static-tail": "struct S{int n;int a[];};static struct S s={2,{3,4}};int probe(void){return s.a[0]+s.a[1];}",
    "bitfields-wide": "struct S{unsigned long long a:40;unsigned b:3;};int probe(void){struct S s={0x123456789aULL,7};return (s.a==0x123456789aULL)?s.b:0;}",
    "packed-enum": "enum E{A=0,B=7} __attribute__((packed));_Static_assert(sizeof(enum E)==1,\"packed enum size\");int probe(void){enum E x=B;return x;}",
    "wide-arithmetic": "volatile unsigned long long a=0x1234567812345678ULL,b=0x12345;int probe(void){return (a/b==0x100005af8a05ULL && a%b==0x741f)?7:0;}",
    "computed-goto": "int probe(void){void *p=&&done;goto *p;return 0;done:return 7;}",
    "choose-expression": "int probe(void){return __builtin_choose_expr(__builtin_types_compatible_p(int,int),7,0);}",
    "constant-p": "int probe(void){return 7*__builtin_constant_p(7);}",
    "expect": "int probe(void){volatile int x=7;return __builtin_expect(x,0);}",
    "bswap32": "int probe(void){return __builtin_bswap32(0x07000000u);}",
    "bswap64": "int probe(void){return __builtin_bswap64(0x0700000000000000ULL);}",
    "bit-counts": "int probe(void){volatile unsigned x=8;return (__builtin_clz(x)==28 && __builtin_ctz(x)==3 && __builtin_ffs(x)==4)?7:0;}",
    "object-size": "int probe(void){char a[7];return __builtin_object_size(a,0);}",
    "dynamic-object-size": "int probe(void){char a[7];return __builtin_dynamic_object_size(a,0);}",
    "cleanup-return": "static int result;static void clean(int *p){result+=*p;}static void f(void){int x __attribute__((cleanup(clean)))=7;}int probe(void){f();return result;}",
    "cleanup-goto": "static int result;static void clean(int *p){result+=*p;}int probe(void){{int x __attribute__((cleanup(clean)))=7;goto done;}done:return result;}",
    "alias": "int original(void){return 7;}int other(void) __attribute__((alias(\"original\")));int probe(void){return other();}",
    "asm-goto": "int probe(void){__asm__ goto(\"jmp %l0\"::::done);return 0;done:return 7;}",
    "volatile-read-once": "int probe(void){volatile int x=7;return *(volatile typeof(x) *)&x;}",
    "inline-immediate": "static inline __attribute__((always_inline)) int f(int x){int y;__asm__(\"movl %1,%0\":\"=r\"(y):\"i\"(x));return y;}int probe(void){return f(7);}",
    "inline-symbol": "static inline __attribute__((always_inline)) int must_inline(int x){return x+1;}int probe(void){return must_inline(6);}",
    "gnu-inline": "extern inline __attribute__((gnu_inline)) int f(int x){return x+1;}int probe(void){return f(6);}",
    "compiletime-assert-inline": "extern void fail(void) __attribute__((error(\"invalid value\")));static inline __attribute__((always_inline)) int f(int x){if(x!=7)fail();return x;}int probe(void){return f(7);}",
    "error-called": "extern void fail(void) __attribute__((error(\"invalid value\")));int probe(void){fail();return 7;}",
}

SUPPORT = r'''
void *memset(void *p,int v,unsigned n){unsigned char *q=p;for(unsigned i=0;i<n;i++)q[i]=v;return p;}
void *memcpy(void *p,const void *s,unsigned n){unsigned char *q=p;const unsigned char *r=s;for(unsigned i=0;i<n;i++)q[i]=r[i];return p;}
#if defined(__GNUC__) && !defined(__TINYC__)
/* Host GCC has no installed i386 libgcc; keep these helpers explicit. */
unsigned long long __udivdi3(unsigned long long n,unsigned long long d){
unsigned long long q=0,r=0;for(int i=63;i>=0;i--){unsigned carry=r>>63;
r=(r<<1)|((n>>i)&1);if(carry||r>=d){r-=d;q|=1ULL<<i;}}return q;}
unsigned long long __umoddi3(unsigned long long n,unsigned long long d){return n-d*__udivdi3(n,d);}
#endif
'''


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(folder, label, args, *, timeout=60):
    started = time.monotonic()
    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout)
        record = {"args": args, "returncode": result.returncode}
        stdout, stderr = result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        record = {"args": args, "returncode": None, "timeout": timeout}
        stdout, stderr = error.stdout or b"", error.stderr or b""
    record["seconds"] = time.monotonic()-started
    (folder/(label+".stdout")).write_bytes(stdout)
    (folder/(label+".stderr")).write_bytes(stderr)
    (folder/(label+".json")).write_text(json.dumps(record, indent=2)+"\n")
    return record, stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--tcc", type=Path, required=True)
    parser.add_argument("--tcc-runtime", type=Path, required=True)
    parser.add_argument("--gcc", default="gcc")
    args = parser.parse_args()
    root = args.artifacts.resolve()
    root.mkdir(parents=True, exist_ok=False)
    startup = prepare_start(root, "shared")
    summary = {"execution": "host i386 diagnostic; not Space execution",
               "tcc_sha256": digest(args.tcc), "cases": {}}
    for name, body in CASES.items():
        folder = root/name
        folder.mkdir()
        source = folder/"source.c"
        source.write_text(body+"\n"+SUPPORT)
        outcome = {"source_sha256": digest(source)}
        for compiler in ("gcc", "tcc-strict", "tcc-relaxed"):
            is_gcc = compiler == "gcc"
            executable = folder/compiler
            command = ([args.gcc, "-m32", "-fno-pie", "-no-pie",
                        "-fno-stack-protector", "-Wl,-e,_start"] if is_gcc else [str(args.tcc.resolve())])
            command += ["-std=gnu11", "-O2", "-g", "-ffreestanding", "-nostdlib", "-Wall"]
            if compiler != "tcc-relaxed":
                command += ["-Werror"]
            if compiler == "tcc-strict":
                command += ["-Wunsupported"]
            command += [str(source), str(startup)]
            if not is_gcc:
                command += [str(args.tcc_runtime.resolve())]
            command += ["-o", str(executable)]
            built, _ = run(folder, compiler+"-compile", command)
            result = {"compile": built}
            if built["returncode"] == 0:
                executed, output = run(folder, compiler+"-run", [str(executable)])
                assert executed["returncode"] == 0 and len(output) == 4, (name, compiler, executed, output)
                result.update({"run": executed, "output_hex": output.hex(),
                               "executable_sha256": digest(executable)})
                run(folder, compiler+"-symbols", ["nm", str(executable)])
                run(folder, compiler+"-assembly", ["objdump", "-d", str(executable)])
            outcome[compiler] = result
        gcc = outcome["gcc"]
        assert (gcc["compile"]["returncode"] != 0 if name == "error-called" else
                gcc["compile"]["returncode"] == 0 and gcc["run"]["returncode"] == 0
                and gcc["output_hex"] == "07000000"), (name, gcc)
        summary["cases"][name] = outcome
        (root/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
        print(name, *(compiler+":"+str(outcome[compiler]["compile"]["returncode"])+
              ":"+outcome[compiler].get("output_hex", "-") for compiler in
              ("gcc", "tcc-strict", "tcc-relaxed")), flush=True)


if __name__ == "__main__":
    main()
