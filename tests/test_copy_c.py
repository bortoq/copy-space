"""Real Forth C compilation, copy-only target execution and guest raw evidence."""
import argparse
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
from space_segments import execute_segments
from space_archive import archive_target
from copy_c_gnu_cases import valid as gnu_valid, invalid as gnu_invalid, faults as arithmetic_faults
from copy_c_types_cases import valid as types_valid, invalid as types_invalid
from copy_c_array_cases import valid as array_valid, invalid as array_invalid
from copy_c_record_cases import valid as record_valid, invalid as record_invalid
from copy_c_aggregate_value_cases import valid as aggregate_value_valid, invalid as aggregate_value_invalid
from copy_c_aggregate_abi_cases import valid as aggregate_abi_valid, invalid as aggregate_abi_invalid
from copy_c_aggregate_conditional_cases import valid as aggregate_conditional_valid, invalid as aggregate_conditional_invalid
from copy_c_omitted_conditional_cases import valid as omitted_conditional_valid, invalid as omitted_conditional_invalid
from copy_c_omitted_conditional_cases import volatile_reads as omitted_conditional_reads
from copy_c_compound_literal_cases import valid as compound_literal_valid, invalid as compound_literal_invalid
from copy_c_attribute_query_cases import valid as attribute_query_valid, invalid as attribute_query_invalid
from copy_c_expect_cases import valid as expect_valid, invalid as expect_invalid
from copy_c_expect_cases import volatile_reads as expect_volatile_reads
from copy_c_anonymous_cases import valid as anonymous_valid, invalid as anonymous_invalid
from copy_c_anonymous_cases import volatile_reads as anonymous_volatile_reads
from copy_c_identity_cases import valid as identity_valid, invalid as identity_invalid
from copy_c_layout_attribute_cases import valid as layout_valid, invalid as layout_invalid
from copy_c_member_attribute_cases import valid as member_layout_valid, invalid as member_layout_invalid
from copy_c_flexible_cases import valid as flexible_valid, invalid as flexible_invalid
from copy_c_static_flexible_cases import valid as static_flexible_valid
from copy_c_zero_array_cases import valid as zero_array_valid, invalid as zero_array_invalid
from copy_c_builtin_cases import valid as builtin_valid, invalid as builtin_invalid
from copy_c_generic_cases import valid as generic_valid, invalid as generic_invalid
from copy_c_qualifier_cases import valid as qualifier_valid, invalid as qualifier_invalid
from copy_c_qualifier_cases import volatile_reads
from copy_c_typedef_cases import valid as typedef_valid, invalid as typedef_invalid
from copy_c_enum_cases import valid as enum_valid, invalid as enum_invalid
from copy_c_character_cases import valid as character_valid, invalid as character_invalid
from copy_c_string_cases import valid as string_valid, invalid as string_invalid
from copy_c_global_cases import valid as global_valid, invalid as global_invalid
from copy_c_extern_cases import valid as extern_valid, invalid as extern_invalid
from copy_c_static_pointer_cases import valid as static_pointer_valid, invalid as static_pointer_invalid
from copy_c_linkage_cases import valid as linkage_valid, invalid as linkage_invalid
from copy_c_global_aggregate_cases import valid as global_aggregate_valid, invalid as global_aggregate_invalid
from copy_c_designator_cases import valid as designator_valid, invalid as designator_invalid
from copy_c_nested_designator_cases import valid as nested_designator_valid, invalid as nested_designator_invalid
from copy_c_inferred_array_cases import valid as inferred_array_valid, invalid as inferred_array_invalid
from copy_c_range_cases import valid as range_valid, invalid as range_invalid
from copy_c_range_chain_cases import valid as range_chain_valid, invalid as range_chain_invalid
from copy_c_switch_cases import valid as switch_valid, invalid as switch_invalid
from copy_c_goto_cases import valid as goto_valid, invalid as goto_invalid
from copy_c_declarator_cases import valid as declarator_valid, invalid as declarator_invalid
from copy_c_function_type_cases import valid as function_type_valid, invalid as function_type_invalid
from copy_c_function_address_cases import valid as function_address_valid, invalid as function_address_invalid
from copy_c_indirect_cases import valid as indirect_valid, invalid as indirect_invalid, faults as indirect_faults
from copy_c_frame_cases import valid as frame_valid
from copy_c_function_declaration_cases import valid as function_declaration_valid, invalid as function_declaration_invalid
from copy_c_variadic_cases import valid as variadic_valid, invalid as variadic_invalid
from copy_c_long_long_cases import valid as long_long_valid, invalid as long_long_invalid, faults as long_long_faults
from copy_c_long_long_cases import volatile_reads as long_long_volatile_reads
from copy_c_wide_control_cases import valid as wide_control_valid, invalid as wide_control_invalid
from copy_c_wide_control_cases import volatile_reads as wide_control_volatile_reads
from copy_c_local_static_cases import valid as local_static_valid, invalid as local_static_invalid
from copy_c_preprocess_cases import valid as preprocess_valid, invalid as preprocess_invalid
from copy_c_object_macro_cases import valid as object_macro_valid, invalid as object_macro_invalid
from copy_c_function_macro_cases import valid as function_macro_valid, invalid as function_macro_invalid
from copy_c_conditional_cases import valid as conditional_valid, invalid as conditional_invalid
from copy_c_zero_object_cases import valid as zero_object_valid
from copy_c_auto_cases import valid as auto_valid, invalid as auto_invalid
volatile_reads = dict(volatile_reads, **long_long_volatile_reads, **wide_control_volatile_reads)
volatile_reads.update(omitted_conditional_reads)
volatile_reads.update(expect_volatile_reads)
volatile_reads.update(anonymous_volatile_reads)
arithmetic_faults = arithmetic_faults+long_long_faults

ROOT = Path("tmp/space-tests/copy-c")
IMAGE = Path("build/copy-c/compiler.stream")
NATIVE = IMAGE.with_name(IMAGE.name+".build") / "compiler32"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--native-only", action="store_true")
parser.add_argument("--archive-targets", action="store_true", help="losslessly compress completed raw traces and dumps")
parser.add_argument("--target-timeout", type=int, default=60, help="seconds per direct target including raw observer writes")
parser.add_argument("--native-reference", type=Path, help="compare the complete compiler output with a preserved native compiler")
parser.add_argument("--guest-case", action="append", choices=["sum", "control", "loop", "recursive-sum", "pointer-guest", "gnu-integer", "loop-guest", "gnu-expr-guest", "large-source-guest", "types-guest", "arrays-guest", "record-guest", "builtins-guest", "generic-guest", "qualifier-guest", "qualifier-full-guest", "qualifier-error", "typedef-guest", "enum-guest", "char-guest", "string-guest", "string-init-guest", "global-guest", "extern-guest", "static-pointer-guest", "static-init-full-guest", "global-aggregate-guest", "designator-guest", "global-designator-guest", "nested-designator-guest", "inferred-array-guest", "range-guest", "range-chain-guest", "switch-guest", "goto-guest", "declarator-guest", "function-type-guest", "function-address-guest", "indirect-guest", "frame-large-functions", "function-declaration-guest", "variadic-guest", "zero-flex-guest", "syntax-error"])
parser.add_argument("--compiler-space", type=Path, help="emulator binary for the compiler image; targets still use ordinary space")
parser.add_argument("--ticks-per-segment", type=int, default=0, help="save and resume the complete guest state after this many ticks")
parser.add_argument("--resume-segments", action="store_true", help="continue verified checkpoints in the existing artifact folder")
parser.add_argument("--guest-timeout", type=int, default=3600, help="seconds allowed per emulator process")
parser.add_argument("--gcc-reference", action="store_true", help="GNU C reference tests only; never production compilation")
parser.add_argument("--trace-compression", choices=["gzip", "zstd"], default="gzip")
parser.add_argument("--artifacts", type=Path, default=ROOT)
options = parser.parse_args()
if options.ticks_per_segment < 0 or options.guest_timeout <= 0:
    parser.error("ticks must not be negative; guest timeout must be positive")
if options.target_timeout <= 0:
    parser.error("target timeout must be positive")
if options.trace_compression == "zstd" and not shutil.which("zstd"):
    parser.error("zstd is required for --trace-compression zstd")
ROOT = options.artifacts
ROOT.mkdir(parents=True, exist_ok=True)
(ROOT / "compiler.fth").write_bytes(Path("runtime/copy_c/compiler.fth").read_bytes())
source_signature = hashlib.sha256((ROOT / "compiler.fth").read_bytes()).hexdigest()
SOURCE_CAPACITY = 1048576
dictionary = IMAGE.with_name(IMAGE.name+".build") / "dictionary/pfdicdat.h.json"
assert json.loads(dictionary.read_text())["compiler_forth_sha256"] == source_signature, "rebuild stale native compiler"
custom_signature = hashlib.sha256(Path("runtime/pforth/custom.c").read_bytes()).hexdigest()
assert json.loads(dictionary.read_text())["compiler_custom_sha256"] == custom_signature, "rebuild stale compiler runtime"
fold_source = Path("runtime/copy_c/integer64_fold.h").read_bytes()
assert json.loads(dictionary.read_text())["compiler_integer64_fold_sha256"] == hashlib.sha256(fold_source).hexdigest(), "rebuild stale integer64 folding"
(ROOT / "integer64_fold.h").write_bytes(fold_source)
phase2_source = Path("runtime/copy_c/preprocess_phase2.h").read_bytes()
assert json.loads(dictionary.read_text())["compiler_preprocess_phase2_sha256"] == hashlib.sha256(phase2_source).hexdigest(), "rebuild stale preprocessing"
(ROOT / "preprocess_phase2.h").write_bytes(phase2_source)
macros_source = Path("runtime/copy_c/preprocess_macros.h").read_bytes()
assert json.loads(dictionary.read_text())["compiler_preprocess_macros_sha256"] == hashlib.sha256(macros_source).hexdigest(), "rebuild stale macros"
(ROOT / "preprocess_macros.h").write_bytes(macros_source)
condition_source = Path("runtime/copy_c/preprocess_condition.h").read_bytes()
assert json.loads(dictionary.read_text())["compiler_preprocess_condition_sha256"] == hashlib.sha256(condition_source).hexdigest(), "rebuild stale conditions"
(ROOT / "preprocess_condition.h").write_bytes(condition_source)
for name in ("input_files", "preprocess_include", "preprocess_queries"):
    content = Path("runtime/copy_c/"+name+".h").read_bytes()
    assert json.loads(dictionary.read_text())["compiler_"+name+"_sha256"] == hashlib.sha256(content).hexdigest(), "rebuild stale input/include support"
    (ROOT / (name+".h")).write_bytes(content)
reference_runtime = ROOT / "reference_integer64.c"
reference_runtime.write_bytes(Path("tests/fixtures/copy_c/reference_integer64.c").read_bytes())
captured_compiler = ROOT / "compiler32"
captured_compiler.write_bytes(NATIVE.read_bytes())
captured_compiler.chmod(0o755)
NATIVE = captured_compiler


def record(folder, command, data):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "in.bin").write_bytes(data)
    (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")


def compile_native(name, source, error=False):
    folder = ROOT / "native" / name
    command = [str(NATIVE)]
    record(folder, command, b"CC-RUN\n"+source)
    result = subprocess.run(command, input=b"CC-RUN\n"+source, capture_output=True, timeout=10)
    (folder / "program.in").write_bytes(result.stdout)
    (folder / "stderr.txt").write_bytes(result.stderr)
    if options.native_reference:
        reference = subprocess.run([str(options.native_reference)], input=b"CC-RUN\n"+source,
                                   capture_output=True, timeout=10)
        assert (result.returncode, result.stdout, result.stderr) == (reference.returncode, reference.stdout, reference.stderr), name
        (folder / "reference.json").write_text(json.dumps({
            "compiler": str(options.native_reference), "equal": True,
            "output_sha256": hashlib.sha256(reference.stdout).hexdigest(),
        }, indent=2)+"\n")
    assert result.stderr == b"", result.stderr
    if error:
        assert result.returncode == 2 and result.stdout.startswith(b"copy-c error at byte "), (name, result.returncode, len(result.stdout), result.stdout[:120])
    else:
        assert result.returncode == 0 and len(result.stdout) > 37, (name, result)
    return result.stdout


def target(name, packet, expected, *, fault=False, stack_fault=False, pointer_fault=False):
    folder = ROOT / "target" / name
    command = ["build/bin/space", "--ticks", "20000", "--trace", str(folder / "trace.txt"),
               "--dump-space", str(folder / "space.bin")]
    reference_packet = ROOT / "native" / name / "program.in"
    if reference_packet.is_file() and reference_packet.read_bytes() == packet:
        folder.mkdir(parents=True, exist_ok=True)
        incoming = folder / "in.bin"
        incoming.unlink(missing_ok=True)
        incoming.hardlink_to(reference_packet)
        (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
    else:
        record(folder, command, packet)
    result = subprocess.run(command, input=packet, capture_output=True, timeout=options.target_timeout)
    (folder / "result.out").write_bytes(result.stdout)
    (folder / "stderr.txt").write_bytes(result.stderr)
    assert result.returncode == 0 and result.stderr == b"", (name, result)
    want = (b"copy-c: load error\n" if fault else b"copy-c: stack overflow\n" if stack_fault
            else b"copy-c: pointer error\n" if pointer_fault
            else expected if isinstance(expected, bytes) else (expected & 0xffffffff).to_bytes(4, "little"))
    assert result.stdout == want, (name, result.stdout.hex(), want.hex())
    raw = (folder / "space.bin").read_bytes()
    assert len(raw) == 2097152 and raw[:2272] == bytes(2272)
    assert raw[245760//8:262144//8] == bytes(2048), "modified immutable zero interval"
    # The upper MiB is the direct program's call stack. Its pointer is updated
    # by the copy program, and must return to main after balanced calls.
    sp = sum(((raw[(152128+i)//8] >> (7-(152128+i)%8)) & 1) << i for i in range(32))
    if not fault and not pointer_fault:
        assert sp == (16760832 if stack_fault else 8388608), (name, sp)
    if name == "recursive-sum":
        # n has a distinct address in each active recursive invocation.
        assert len({raw[1048576+i*2048:1048576+(i+1)*2048] for i in range(5)}) == 5
    trace = (folder / "trace.txt").read_bytes()
    zeroing = {"frame-large-functions": (9600, 2), "zero-object-repeat": (9600, 2),
               "zero-object-guest": (9600, 1), "zero-object-large": (14400, 1)}
    if name in zeroing:
        width, count = zeroing[name]
        rows = [row.decode().strip() for row in trace.splitlines()
                if (fields := row.split()) and fields[0] == b"copy"
                and int(fields[3]) == width and int(fields[5]) == 245760]
        assert len(rows) == count, (name, rows, count)
        (folder / "zeroing.json").write_text(json.dumps({"source_bit": 245760,
            "width_bits": width, "copies": rows}, indent=2)+"\n")
    if name in volatile_reads:
        # Main reserves a 32-bit return address and a 64-bit result field.
        # Count actual reads of that object's bits, excluding its initialization.
        expectation = volatile_reads[name]
        width = 32
        if isinstance(expectation, tuple) and len(expectation) == 3:
            expected_reads, offset, width = expectation
        else:
            expected_reads, offset = expectation if isinstance(expectation, tuple) else (expectation, 64)
            offset += 32
        reads = sum(line[0] == b"copy" and int(line[3]) == width
                    and int(line[5]) == 8388608+offset
                    for row in trace.splitlines() if (line := row.split()))
        assert reads == expected_reads, (name, reads, expected_reads)
        (folder / "volatile.json").write_text(json.dumps({
            "object_bit_address": 8388608+offset, "reads": reads,
            "expected_reads": expected_reads,
        }, indent=2)+"\n")
    assert trace.splitlines()[-1].endswith(b" idle") and b"copy " in trace
    assert b"channel " in trace
    if name == "carry":
        reads = []
        for line in trace.splitlines():
            fields = line.split()
            if fields[:1] == [b"copy"] and fields[3:5] == [b"2", b"151680"]:
                reads.append(int(fields[5]))
        assert reads == [196614]+[196618]*31, reads
    if options.archive_targets:
        archive_target(folder)
    print(f"OK copy-c target {name}: OUT={result.stdout.hex()}", flush=True)


valid = [
    ("source-max", b"int main(){return 7;}".ljust(SOURCE_CAPACITY), 7),
    ("large-source-guest", b"//"+b"x"*8192+b"\n"+Path("examples/copy_c/gnu_expressions.c").read_bytes(), 7),
    ("sum", b"int f(int a,int b){return a+b;}int main(){return f(1,2);}", 3),
    ("literal-sum", b"int main(){return 1+2;}", 3),
    ("carry", b"int main(){return 0xffffffff+1;}", 0),
    ("sign-wrap", b"int main(){return 2147483647+1;}", 0x80000000),
    ("subtract", b"int main(){return 1-2;}", -1),
    ("unary", b"int main(){return -(-17)+!0;}", 18),
    ("precedence", b"int main(){return 1+2<4==1;}", 1),
    ("truth-high-bit", b"int main(){if(256)return 7;else return 8;}", 7),
    ("false", b"int main(){if(0)return 7;else return 8;}", 8),
    ("if-no-else", b"int main(){int a=2;if(0)a=9;return a;}", 2),
    ("dangling-else", b"int main(){if(1)if(0)return 1;else return 2;return 3;}", 2),
    ("locals", b"int main(){int a=7;int b;b=a+3;return b;}", 10),
    ("nested-call", b"int f(int a,int b){return a-b;}int main(){return f(f(9,2),f(5,1));}", 3),
    ("call-chain", b"int f(int a){return a+1;}int g(int a){return f(a)+f(a+1);}int main(){return g(10);}", 23),
    ("zero-args", b"int f(void){return 13;}int main(void){return f();}", 13),
    ("fallthrough", b"int main(){}", 0),
    ("loop", Path("examples/copy_c/loop.c").read_bytes(), 15),
    ("nested-loop", b"int main(){int i=0;int s=0;while(i<3){int j=0;while(j<2){s=s+1;j=j+1;}i=i+1;}return s;}", 6),
    ("comments", b"/* head */ int main() { // line\nreturn 0XFF + /* inner */ 1; } // tail", 256),
    ("comment-stars", b"/***/int main(){/* * x ** y ***/return 7;}/**/", 7),
    ("comment-empty", b"/**/int main(){return/**/7;}/* tail */", 7),
    ("comment-line-eof", b"int main(){return 7;}//", 7),
    ("comment-line-crlf", b"// ignored\r\nint main(){return 7;}\r\n// tail", 7),
    ("comment-boundaries", b"/* // and / * */int main(){// /* ignored\nreturn 7;}/*/ ***/", 7),
    ("case-sensitive", b"int main(){int A=7;int a=2;return A-a;}", 5),
    ("block-names", b"int main(){int s=0;{int a=1;s=s+a;}{int a=2;s=s+a;}return s;}", 3),
    ("control", b"int f(int a){return a+1;}int main(){int i=0;while(i<2){if(i==0)i=f(i);else i=i+1;}return i;}", 2),
    ("recursive-sum", b"int f(int n){if(n==0)return 0;return n+f(n-1);}int main(){return f(4);}", 10),
    ("recursive-locals", b"int f(int n){int saved=n+7;if(n==0)return saved;int child=f(n-1);return saved+child;}int main(){return f(4);}", 45),
    ("recursive-siblings", b"int f(int n){if(n<2)return n;return f(n-1)+f(n-2);}int main(){return f(6);}", 8),
    ("recursive-nested-args", b"int f(int n){if(n<1)return 0;return f(n-1)+1;}int main(){return f(f(3));}", 3),
    ("stack-last-frame", b"int f(int n){if(n==0)return 0;return f(n-1)+1;}int main(){return f(510);}", 510),
    ("prototype-forward", b"int f(int);int main(){return f(9);}int f(int n){return n+2;}", 11),
    ("prototype-named", b"int f(int old);int f(int value){return value+1;}int main(){return f(4);}", 5),
    ("prototype-unused", b"int absent(int,int);int main(){return 7;}", 7),
    ("prototype-repeated", b"int f(int);int f(int other);int f(int n){return n;}int f(int);int main(){return f(12);}", 12),
    ("prototype-void", b"int f(void);int main(void){return f();}int f(void){return 13;}", 13),
    ("mutual-recursion", b"int odd(int);int even(int n){if(n==0)return 1;return odd(n-1);}int odd(int n){if(n==0)return 0;return even(n-1);}int main(){return even(8)+odd(7);}", 2),
    ("mutual-forward-main", b"int main(void);int f(int);int main(){return f(3);}int f(int n){if(n==0)return 0;return 1+f(n-1);}", 3),
    ("pointer-read", b"int main(){int x=17;int *p=&x;return *p;}", 17),
    ("pointer-write", b"int main(){int x=5;int *p=&x;*p=9;return x;}", 9),
    ("pointer-caller", b"int f(int *p){*p=*p+3;return *p;}int main(){int x=5;f(&x);return x;}", 8),
    ("pointer-return", b"int *f(int *p){return p;}int main(){int x=21;return *f(&x);}", 21),
    ("pointer-forward", b"int *f(int *);int main(){int x=31;return *f(&x);}int *f(int *p){return p;}", 31),
    ("pointer-difference", b"int main(){int x=1;int *p=&x;return (p+1)-p;}", 1),
    ("pointer-negative-difference", b"int main(){int x=1;int *p=&x;return p-(p+1);}", -1),
    ("pointer-integer-add", b"int main(){int x=1;int *p=&x;return (1+p)-p;}", 1),
    ("pointer-equality", b"int main(){int x=0;int *p=&x;if(p==0)return 99;if(0==p)return 98;return p==&x;}", 1),
    ("pointer-null", b"int main(){int *p=0;return !p;}", 1),
    ("pointer-parent-recursion", b"int f(int n,int *p){if(n==0){*p=*p+1;return 0;}int local=n;f(n-1,&local);*p=*p+local;return 0;}int main(){int x=0;f(3,&x);return x;}", 7),
    ("pointer-guest", b"int f(int*p){return *p;}int main(){int x=7;return f(&x);}", 7),
    ("pointer-last-frame", b"int f(int n){if(n==0){int x=19;return *(&x);}return f(n-1);}int main(){return f(510);}", 19),
]
valid += gnu_valid
valid += types_valid
valid += array_valid
valid += record_valid
valid += aggregate_value_valid
valid += aggregate_abi_valid
valid += aggregate_conditional_valid
valid += omitted_conditional_valid
valid += compound_literal_valid
valid += attribute_query_valid
valid += expect_valid
valid += anonymous_valid
valid += identity_valid
valid += layout_valid
valid += member_layout_valid
valid += flexible_valid
valid += static_flexible_valid
valid += zero_array_valid
valid += builtin_valid
valid += generic_valid
valid += qualifier_valid
valid += typedef_valid
valid += enum_valid
valid += character_valid
valid += string_valid
valid += global_valid
valid += extern_valid
valid += static_pointer_valid
valid += linkage_valid
valid += global_aggregate_valid
valid += designator_valid
valid += nested_designator_valid
valid += inferred_array_valid
valid += range_valid
valid += range_chain_valid
valid += switch_valid
valid += goto_valid
valid += declarator_valid
valid += function_type_valid
valid += function_address_valid
valid += indirect_valid
valid += frame_valid
valid += function_declaration_valid
valid += variadic_valid
valid += long_long_valid
valid += wide_control_valid
valid += local_static_valid
valid += preprocess_valid
valid += object_macro_valid
valid += function_macro_valid
valid += conditional_valid
valid += zero_object_valid
valid += auto_valid
for name, expression, expected in [
    ("signed-lt", "0x80000000<0", 0), ("signed-gt", "0xffffffff>0", 1),
    ("signed-ge", "0x80000000>=0x80000000", 1), ("signed-le", "7<=6", 0),
    ("equal", "0xffffffff==(-1)", 1), ("not-equal", "0xffffffff!=0", 1),
    ("false-neq", "7!=7", 0), ("signed-min", "0x80000000<0xffffffff", 1),
]:
    valid.append((name, ("int main(){return "+expression+";}").encode(), expected))

packets = {}
assert len({name for name, _, _ in valid}) == len(valid), "duplicate valid case name"
for name, source, expected in valid:
    packet = compile_native(name, source)
    packets[name] = packet
    target(name, packet, expected)
    if options.gcc_reference and name != "fallthrough":
        folder = ROOT / "gcc" / name
        folder.mkdir(parents=True, exist_ok=True)
        translation = (b"#define main copy_c_test_main\n"+source+b"\n#undef main\n"
                       b"void _start(void){unsigned value=copy_c_test_main();int result;"
                       b"__asm__ volatile(\"int $0x80\":\"=a\"(result):\"0\"(4),\"b\"(1),\"c\"(&value),\"d\"(4):\"memory\");"
                       b"__asm__ volatile(\"int $0x80\"::\"a\"(1),\"b\"(result!=4):\"memory\");for(;;){}}\n")
        (folder / "source.c").write_bytes(translation)
        command = ["gcc", "-m32", "-std=gnu11", "-fwrapv", "-O0", "-ffreestanding", "-nostdlib",
                   "-fno-pie", "-no-pie", "-fno-stack-protector", "-Wl,-e,_start",
                   str(folder / "source.c"), str(reference_runtime), "-o", str(folder / "reference")]
        (folder / "args.json").write_text(json.dumps(command, indent=2)+"\n")
        compiled = subprocess.run(command, capture_output=True, timeout=30)
        assert compiled.returncode == 0, compiled.stderr
        reference = subprocess.run([str(folder / "reference")], capture_output=True, timeout=10)
        (folder / "result.out").write_bytes(reference.stdout)
        assert reference.returncode == 0 and reference.stdout == (expected & 0xffffffff).to_bytes(4, "little"), (name, reference)

invalid = [
    ("missing-main", b"int f(){return 1;}"),
    ("unfinished", b"int main(){return 1;"),
    ("unknown-name", b"int main(){return missing;}"),
    ("duplicate", b"int main(){int a;int a;return 0;}"),
    ("forward-call", b"int main(){return f();}int f(){return 1;}"),
    ("arity", b"int f(int a){return a;}int main(){return f(1,2);}"),
    ("prototype-conflict", b"int f(int);int f(int,int);int main(){return 0;}"),
    ("definition-conflict", b"int f(int);int f(void){return 0;}int main(){return 0;}"),
    ("missing-definition", b"int f(void);int main(){return f();}"),
    ("main-prototype-only", b"int main(void);"),
    ("duplicate-definition", b"int f(){return 1;}int f(){return 2;}int main(){return 0;}"),
    ("unnamed-definition", b"int f(int){return 0;}int main(){return 0;}"),
    ("pointer-int-assignment", b"int main(){int x;int *p=&x;x=p;return 0;}"),
    ("pointer-nonzero-assignment", b"int main(){int *p=123;return 0;}"),
    ("pointer-argument-type", b"int f(int *p){return 0;}int main(){return f(7);}"),
    ("pointer-return-type", b"int f(){int x;return &x;}int main(){return 0;}"),
    ("pointer-param-prototype", b"int f(int*);int f(int);int main(){return 0;}"),
    ("pointer-result-prototype", b"int *f(void);int f(void);int main(){return 0;}"),
    ("pointer-main", b"int *main(){return 0;}"),
    ("pointer-to-pointer", b"int main(){int *p;return &p;}"),
    ("pointer-add-pointers", b"int main(){int x;int *p=&x;return p+p;}"),
    ("pointer-int-subtract", b"int main(){int x;int *p=&x;return 3-p;}"),
    ("pointer-negate", b"int main(){int x;int *p=&x;return -p;}"),
    ("dereference-int", b"int main(){int p=1;return *p;}"),
    ("write-through-int", b"int main(){int p=1;*p=7;return 0;}"),
    ("local-hides-function", b"int f(){return 3;}int main(){int f;return f();}"),
    ("integer-overflow", b"int main(){return 18446744073709551616;}"),
    ("hex-overflow", b"int main(){return 0x10000000000000000;}"),
    ("bad-hex", b"int main(){return 0x;}"),
    ("comment-eof", b"int main(){/* unfinished"),
    ("comment-final-star", b"int main(){return 7;}/* *"),
    ("comment-final-stars", b"int main(){return 7;}/***"),
    ("main-args", b"int main(int a){return a;}"),
    ("reserved-name", b"int main(){int return;return 0;}"),
    ("nul-source", b"int main(){return 0;}\0"),
    ("block-scope", b"int main(){{int a=1;}return a;}"),
    ("source-capacity", b" "*(SOURCE_CAPACITY+1)),
    ("nesting-capacity", b"int main(){return "+b"("*40+b"1"+b")"*40+b";}"),
    ("name-capacity", b"int main(){int "+b"x"*32+b";return 0;}"),
    ("code-capacity", b"volatile int n=0;int main(){"+b"if(n);"*200+b"return n;}"),
]
invalid += gnu_invalid
invalid += types_invalid
invalid += array_invalid
invalid += record_invalid
invalid += aggregate_value_invalid
invalid += aggregate_abi_invalid
invalid += aggregate_conditional_invalid
invalid += omitted_conditional_invalid
invalid += compound_literal_invalid
invalid += attribute_query_invalid
invalid += expect_invalid
invalid += anonymous_invalid
invalid += identity_invalid
invalid += layout_invalid
invalid += member_layout_invalid
invalid += flexible_invalid
invalid += zero_array_invalid
invalid += builtin_invalid
invalid += generic_invalid
invalid += qualifier_invalid
invalid += typedef_invalid
invalid += enum_invalid
invalid += character_invalid
invalid += string_invalid
invalid += global_invalid
invalid += extern_invalid
invalid += static_pointer_invalid
invalid += linkage_invalid
invalid += global_aggregate_invalid
invalid += designator_invalid
invalid += nested_designator_invalid
invalid += inferred_array_invalid
invalid += range_invalid
invalid += range_chain_invalid
invalid += switch_invalid
invalid += goto_invalid
invalid += declarator_invalid
invalid += function_type_invalid
invalid += function_address_invalid
invalid += indirect_invalid
invalid += function_declaration_invalid
invalid += variadic_invalid
invalid += long_long_invalid
invalid += wide_control_invalid
invalid += local_static_invalid
invalid += preprocess_invalid
invalid += object_macro_invalid
invalid += function_macro_invalid
invalid += conditional_invalid
invalid += auto_invalid
assert len({name for name, _ in invalid}) == len(invalid), "duplicate rejected case name"
for name, source in invalid:
    compile_native(name, source, True)
    print(f"OK copy-c rejects {name}", flush=True)
overflow = compile_native("stack-overflow", b"int f(){return f();}int main(){return f();}")
target("stack-overflow", overflow, 0, stack_fault=True)
for name, source in [
    ("null-read", b"int main(){int *p=0;return *p;}"),
    ("null-write", b"int main(){int *p=0;*p=7;return 0;}"),
    ("pointer-range", b"int main(){int *p=0;p=p+1;return *p;}"),
    ("pointer-upper-range", b"int main(){int x=1;int *p=&x;p=p+524288;*p=9;return x;}"),
]:
    target(name, compile_native(name, source), 0, pointer_fault=True)
for name, source, expected in [
    ("types-last-byte", b"int main(){unsigned char*p=(unsigned char*)2097151;*p=171;return *p;}", 171),
    ("types-last-half", b"int main(){unsigned short*p=(unsigned short*)2097150;*p=43981;return *p;}", 43981),
    ("types-odd-byte", b"int main(){unsigned char*p=(unsigned char*)2097137;*p=7;return *p;}", 7),
]:
    # Raw ABI addresses test the space boundary, not defined C objects on GCC.
    target(name, compile_native(name, source), expected)
for name, source in [
    ("types-byte-lower", b"int main(){return *(char*)1048575;}"),
    ("types-byte-upper", b"int main(){return *(char*)2097152;}"),
    ("types-half-align", b"int main(){return *(short*)2097151;}"),
    ("types-pointer-align", b"int main(){int**p=(int**)1048577;return **p;}"),
    ("string-pointer-below", b"int main(){return *(char*)12287;}"),
    ("string-pointer-above", b"int main(){return *(char*)16384;}"),
    ("string-pointer-align", b"int main(){return *(short*)12289;}"),
    ("ll-pointer-upper", b"int main(){return *(long long*)2097148;}"),
    ("ll-pointer-static-upper", b"int main(){return *(long long*)16380;}"),
]:
    target(name, compile_native(name, source), 0, pointer_fault=True)
for name, source in indirect_faults:
    target(name, compile_native(name, source), 0, pointer_fault=True)
main_overflow = compile_native("main-stack-overflow", b"int main(){return main();}")
target("main-stack-overflow", main_overflow, 0, stack_fault=True)
def payload_start(packet):
    for start in range(0, len(packet), 37):
        # First installation records carry zero IN length. The last one
        # orders the payload read; decode independently of compiler helpers.
        at = start*8+71
        bits = sum(((packet[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(23))
        if bits:
            assert bits == (len(packet)-start-37)*8
            return start+37
    raise AssertionError("payload bootstrap missing")


# A forged low address bit in an otherwise valid packet must be rejected
# by the generated copy program, rather than corrupting a neighbouring int.
forged = bytearray(packets["pointer-read"])
constants = payload_start(forged)+(163840-98304)//8
encoded_address = bytes(int(f"{byte:08b}"[::-1], 2) for byte in (1048588).to_bytes(4, "little"))
location = forged.find(encoded_address, constants, constants+2048)
assert location >= constants
forged[location] ^= 0x80
target("pointer-misaligned", bytes(forged), 0, pointer_fault=True)

for cut in (0, 1, 2271):
    target(f"truncated-{cut}", packets["sum"][:payload_start(packets["sum"])+cut], 0, fault=True)
# A large payload crosses the old guard location. The guard must survive
# both a complete load and EOF inside that former location.
large = packets["indirect-many-sites"]
start = payload_start(large)
cuts = ((4128768-98304)//8, (4194304-98304)//8+2271, len(large)-start-1)
for i, cut in enumerate(cuts):
    assert 0 < cut < len(large)-start
    target(f"truncated-large-{i}", large[:start+cut], 0, fault=True)
print(f"OK copy-c native: {len(valid)} valid, {len(invalid)} rejected, stack overflow, pointer boundary/alignment guards, 6 truncated packets", flush=True)
for name, source, expected in arithmetic_faults:
    target(name, compile_native(name, source), expected)
(ROOT / "native-summary.json").write_text(json.dumps({
    "valid": len(valid), "rejected": len(invalid), "arithmetic_faults": len(arithmetic_faults),
    "truncated_packets": 6,
    "gcc_reference": options.gcc_reference,
    "native_reference_sha256": hashlib.sha256(options.native_reference.read_bytes()).hexdigest() if options.native_reference else None,
    "compiler_forth_sha256": hashlib.sha256((ROOT / "compiler.fth").read_bytes()).hexdigest(),
    "native_compiler_sha256": hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
}, indent=2)+"\n")

if options.native_only:
    raise SystemExit(0)


def execute_single(folder, command):
    fifo = folder / "trace.fifo"
    fifo.unlink(missing_ok=True)
    os.mkfifo(fifo)
    keepalive = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    errors = []
    trace_path = folder / ("trace.txt.zst" if options.trace_compression == "zstd" else "trace.txt.gz")

    def compress():
        try:
            with fifo.open("rb", buffering=0) as incoming:
                if options.trace_compression == "gzip":
                    with gzip.open(trace_path, "wb", compresslevel=1) as out:
                        shutil.copyfileobj(incoming, out, 1024*1024)
                else:
                    with trace_path.open("wb") as out, subprocess.Popen(
                            ["zstd", "-q", "-1", "-c"], stdin=subprocess.PIPE,
                            stdout=out, stderr=subprocess.PIPE) as encoder:
                        try:
                            shutil.copyfileobj(incoming, encoder.stdin, 1024*1024)
                        finally:
                            encoder.stdin.close()
                        error = encoder.stderr.read()
                        assert encoder.wait() == 0, error
        except Exception as error:
            errors.append(error)

    compressor = threading.Thread(target=compress, daemon=True)
    compressor.start()
    started = time.monotonic()
    try:
        with (folder / "in.bin").open("rb") as incoming, (folder / "program.in").open("wb") as output, (folder / "stderr.txt").open("wb") as error_output:
            result = subprocess.run(command, stdin=incoming, stdout=output, stderr=error_output,
                                    timeout=options.guest_timeout)
    finally:
        os.close(keepalive)
        compressor.join(timeout=30)
        fifo.unlink()
    assert not compressor.is_alive() and not errors, errors
    assert result.returncode == 0 and (folder / "stderr.txt").read_bytes() == b""
    copies, channels, last = audit_trace(trace_path)
    assert copies > 0 and channels > 0 and last.endswith(b" idle\n")
    return {"copy_events": copies, "channel_events": channels,
            "seconds": time.monotonic()-started, "trace_file": trace_path.name}


def guest(name, source, expected=None):
    folder = ROOT / "guest" / name
    image = IMAGE.read_bytes()
    data = image+b"CC-RUN\n"+source
    assert source not in (IMAGE.with_name(IMAGE.name+".build") / "program.bin").read_bytes()
    image_manifest = json.loads(IMAGE.with_name(IMAGE.name+".json").read_text())
    compiler_space = options.compiler_space or {
        2097152: Path("build/bin/space"), 67108864: Path("build/bin/space-64m"),
    }.get(image_manifest["space_bytes"])
    assert compiler_space is not None, "select --compiler-space for this image layout"
    command = [str(compiler_space), "--trace", str(folder / "trace.fifo"),
               "--dump-space", str(folder / "space.bin")]
    if options.resume_segments:
        assert options.ticks_per_segment > 0, "resume requires --ticks-per-segment"
        assert (folder / "in.bin").read_bytes() == data, "changed guest input"
    else:
        record(folder, command, data)
    compiler_source = Path("runtime/copy_c/compiler.fth").read_bytes()
    assert image_manifest["compiler_forth_sha256"] == hashlib.sha256(compiler_source).hexdigest(), "rebuild stale guest compiler"
    assert image_manifest["compiler_dictionary"]["compiler_custom_sha256"] == custom_signature, "rebuild stale guest compiler runtime"
    (folder / "source.c").write_bytes(source)
    (folder / "compiler.fth").write_bytes(compiler_source)
    (folder / "custom.c").write_bytes(Path("runtime/pforth/custom.c").read_bytes())
    (folder / "compiler.json").write_bytes(IMAGE.with_name(IMAGE.name+".json").read_bytes())
    if options.ticks_per_segment:
        execution = execute_segments(compiler_space, folder, folder / "in.bin",
            space_bytes=image_manifest["space_bytes"], layer_bytes=image_manifest["layer_bits"]//8,
            ticks=options.ticks_per_segment, timeout=options.guest_timeout,
            compression=options.trace_compression, resume=options.resume_segments)
    else:
        execution = execute_single(folder, command)
    output = (folder / "program.in").read_bytes()
    raw = (folder / "space.bin").read_bytes()

    def word(at):
        return sum(((raw[(at+i)//8] >> (7-(at+i)%8)) & 1) << i for i in range(32))

    assert len(raw) == image_manifest["space_bytes"]
    layer_bytes = image_manifest["layer_bits"]//8
    assert raw[:layer_bytes] == bytes(layer_bytes) and word(132128) == 10
    if expected is None:
        assert word(132160) == 2 and output.startswith(b"copy-c error at byte ")
        if name == "qualifier-error":
            assert output.endswith(b"assignment to const object\n"), output
    else:
        assert word(132160) == 0 and output == packets[name]
        target("guest-"+name, output, expected)
    (folder / "evidence.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source).hexdigest(), "output_sha256": hashlib.sha256(output).hexdigest(),
        **execution,
        "guest_exit": word(132160),
        "compiler_forth_sha256": hashlib.sha256(compiler_source).hexdigest(),
        "compiler_image_sha256": hashlib.sha256(image).hexdigest(),
        "trace_compression": options.trace_compression,
    }, indent=2)+"\n")
    print(f"OK copy-c guest {name}: {execution['seconds']:.1f}s, {execution['copy_events']} copies", flush=True)


for name in options.guest_case or ("sum", "pointer-guest", "syntax-error"):
    if name == "syntax-error":
        guest(name, b"int main(){return 1+;}\n")
    elif name == "qualifier-error":
        guest(name, b"int main(){const int x=1;const int*p=&x;*p=7;return x;}")
    else:
        _, source, expected = next(case for case in valid if case[0] == name)
        guest(name, source, expected)
print("OK copy-c guest: selected executions passed; full raw evidence in "+str(ROOT), flush=True)
