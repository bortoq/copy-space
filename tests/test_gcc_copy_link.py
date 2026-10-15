"""Lower copy assembly inside Space, then execute its output without RV32I."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts/rv32i"))
from build import build
from space_segments import execute_segments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts",type=Path,required=True)
    parser.add_argument("--compiler",required=True)
    parser.add_argument("--newlib",type=Path,required=True)
    parser.add_argument("--assembly",type=Path,help="use an existing GCC-produced assembler file for guest lowering")
    parser.add_argument("--native-only",action="store_true",help="check direct images without building the guest assembler")
    parser.add_argument("--guest-case",type=int,default=0,help="fixture index to lower inside Space")
    parser.add_argument("--result-space-bytes",type=int,choices=[2097152,67108864,268435456],default=2097152)
    parser.add_argument("--expected-result",type=lambda s:int(s,0),default=2,
                        help="independent unsigned 32-bit result for --assembly (arguments 3,4)")
    args=parser.parse_args()
    if not 0<=args.expected_result<=0xffffffff:
        raise ValueError("expected result must be an unsigned 32-bit value")
    address_bits=(args.result_space_bytes*8).bit_length()-1
    result_emulator=ROOT/"build/bin"/{2097152:"space",67108864:"space-64m",268435456:"space-256m"}[args.result_space_bytes]
    profile_flag=f"-DCS_COPY_RESULT_ADDRESS_BITS={address_bits}"
    root=args.artifacts.resolve();root.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/"tests/fixtures/gcc/copy_link.c"]+[ROOT/"runtime/gcc"/name for name in
        ("copy_link.c","copy_link.h","copy_emit.c","copy_emit.h")]
    hashes={}
    for source in paths:
        destination=root/"sources"/source.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(source.read_bytes())
        hashes[str(source.relative_to(ROOT))]=hashlib.sha256(destination.read_bytes()).hexdigest()
    sources=[root/"sources"/source.relative_to(ROOT) for source in paths if source.suffix==".c"]
    include="-I"+str(root/"sources/runtime/gcc")
    native=root/"native"
    command=["gcc","-O2","-Wall","-Wextra","-Werror",include,profile_flag]+[str(s) for s in sources]+["-o",str(native)]
    (root/"native-command.json").write_text(json.dumps(command)+"\n")
    subprocess.run(command,check=True,capture_output=True)
    # These are assembler fixtures, not a claim of actual GCC output yet.
    prefix=b'.file "test.c"\n.text\n.p2align 1\n.global value\n.type value,@function\nvalue:\n'
    suffix=b'copy.ret\n.size value,.-value\n.ident "assembler test fixture"\n'
    cases=[(b'copy.add $r0,$r1\ncopy.ldi.l $r2,5\ncopy.xor $r0,$r2\n',2),
           (b'copy.add $r0,$r1\ncopy.sub $r0,$r1\n',3),
           (b'copy.or $r0,$r1\ncopy.and $r0,$r1\n',4),
           (b'copy.ldi.l $r0,0xffffffff\ncopy.inc $r0,1\ncopy.dec $r0,--5\n',0xfffffffb),
           (b'copy.ldi.l $r2,010\ncopy.mov $r0,$r2\n',8)]
    cases.extend([(b'copy.jmpa .Ldone\n.Lskip:\ncopy.ldi.l $r0,99\ncopy.ret\n.Ldone:\ncopy.add $r0,$r1\n',7),
                  (b'copy.jmpa .Llast\n.Lfirst:\ncopy.add $r0,$r1\ncopy.ret\n.Llast:\ncopy.jmpa .Lfirst\n.Lunused:\n',7),
                  (b'copy.add $r0,$r1\n.Lalias:\ncopy.xor $r0,$r1\n',3)])
    cases=[(body,value,suffix) for body,value in cases]
    cases.append((b'copy.ret\n.Lunreachable:\ncopy.ldi.l $r0,99\n',3,b'.size value,.-value\n'))
    for operation in (b'ashl',b'lshr',b'ashr'):
        for value in (0,3,0x80000000,0xffffffff):
            for count in (0,1,4,31,32,63):
                shift=count&31
                if operation==b'ashl': result=(value<<shift)&0xffffffff
                elif operation==b'lshr': result=value>>shift
                else:
                    signed=value if value<0x80000000 else value-0x100000000
                    result=(signed>>shift)&0xffffffff
                body=f'copy.ldi.l $r0,{value}\ncopy.ldi.l $r1,{count}\n'.encode()
                cases.append((body+b'copy.'+operation+b' $r0,$r1\n',result,suffix))
        cases.append((b'copy.ldi.l $r0,31\ncopy.'+operation+b' $r0,$r0\n',
                      0x80000000 if operation==b'ashl' else 0,suffix))
    for operation in (b'neg',b'not'):
        for value in (0,1,0x80000000,0xffffffff):
            expected_value=(-value if operation==b'neg' else ~value)&0xffffffff
            for register in (b'$r0',b'$r2'):
                body=b'copy.ldi.l '+register+b','+str(value).encode()+b'\n'
                body+=b'copy.'+operation+b' $r0,'+register+b'\n'
                cases.append((body,expected_value,suffix))
    values=(0,1,0x7fffffff,0x80000000,0xffffffff,0xaaaaaaaa)
    for left in values:
        for right in values:
            signed_left=left if left<0x80000000 else left-0x100000000
            signed_right=right if right<0x80000000 else right-0x100000000
            conditions={"eq":left==right,"ne":left!=right,
                "lt":signed_left<signed_right,"ge":signed_left>=signed_right,
                "le":signed_left<=signed_right,"gt":signed_left>signed_right,
                "ltu":left<right,"geu":left>=right,"leu":left<=right,"gtu":left>right}
            for condition,taken in conditions.items():
                body=f'copy.ldi.l $r2,{left}\ncopy.ldi.l $r3,{right}\ncopy.cmp $r2,$r3\n'.encode()
                body+=f'copy.ldi.l $r0,11\ncopy.branch.{condition} .Lyes\n'.encode()
                body+=b'copy.ldi.l $r0,22\ncopy.ret\n.Lyes:\ncopy.ldi.l $r0,33\n'
                cases.append((body,33 if taken else 22,suffix))
    cases.append((b'copy.ldi.l $r2,0\ncopy.ldi.l $r3,4\n.Lloop:\n'
                  b'copy.inc $r2,1\ncopy.cmp $r2,$r3\ncopy.branch.ltu .Lloop\n'
                  b'copy.mov $r0,$r2\n',4,suffix))
    for left in values:
        for right in values:
            body=f'copy.ldi.l $r0,{left}\ncopy.ldi.l $r1,{right}\ncopy.mul $r0,$r1\n'.encode()
            cases.append((body,(left*right)&0xffffffff,suffix))
        body=f'copy.ldi.l $r0,{left}\ncopy.mul $r0,$r0\n'.encode()
        cases.append((body,(left*left)&0xffffffff,suffix))
    cases.append((b'copy.cmp $r0,$r1\ncopy.mul $r0,$r1\ncopy.branch.ltu .Ldone\n'
                  b'copy.inc $r0,100\n.Ldone:\n',12,suffix))
    cases.append((b'copy.mul $r0,$r1\ncopy.mul $r0,$r1\n',48,suffix))
    for operation in ("udiv","umod","div","mod"):
        for left in values:
            for right in values:
                if not right: quotient,residue=0xffffffff,left
                elif operation.startswith("u"): quotient,residue=divmod(left,right)
                else:
                    a=left if left<0x80000000 else left-0x100000000
                    b=right if right<0x80000000 else right-0x100000000
                    quotient=abs(a)//abs(b)
                    if (a<0)!=(b<0): quotient=-quotient
                    residue=a-quotient*b
                result=residue if operation.endswith("mod") else quotient
                body=f'copy.ldi.l $r0,{left}\ncopy.ldi.l $r1,{right}\ncopy.{operation} $r0,$r1\n'.encode()
                cases.append((body,result&0xffffffff,suffix))
        cases.append((f'copy.ldi.l $r0,3\ncopy.{operation} $r0,$r0\n'.encode(),
                      0 if operation.endswith("mod") else 1,suffix))
    cases.append((b'copy.cmp $r0,$r1\ncopy.udiv $r0,$r1\ncopy.branch.ltu .Ldone\n'
                  b'copy.inc $r0,100\n.Ldone:\n',0,suffix))
    for value in (0,0x89abcdef,0xffffffff):
        setup=f'copy.ldi.l $r2,16\ncopy.ldi.l $r0,{value}\ncopy.st.l ($r2),$r0\n'.encode()
        for width,bits in ((b'b',8),(b's',16),(b'l',32)):
            body=setup+b'copy.ldi.l $r0,0xffffffff\ncopy.ld.'+width+b' $r0,($r2)\n'
            cases.append((body,value&((1<<bits)-1),suffix))
        for offset in range(4):
            body=setup+f'copy.ldo.b $r0,{offset}($r2)\n'.encode()
            cases.append((body,(value>>(offset*8))&255,suffix))
        cases.append((setup+b'copy.ldo.s $r0,1($r2)\n',(value>>8)&65535,suffix))
    cases.extend([
        (b'copy.ldi.l $r0,0x12345678\ncopy.sta.l 16,$r0\ncopy.ldi.l $r1,255\n'
         b'copy.sta.b 17,$r1\ncopy.lda.l $r0,16\n',0x1234ff78,suffix),
        (b'copy.sto.l -4($sp),$r0\ncopy.ldo.l $r0,-4($sp)\n',3,suffix),
        (b'copy.sto.b -1($fp),$r1\ncopy.ldo.b $r0,-1($fp)\n',4,suffix),
        (b'copy.ldi.l $r2,17\ncopy.ldi.l $r0,0x89abcdef\ncopy.st.l ($r2),$r0\n'
         b'copy.ld.l $r2,($r2)\ncopy.mov $r0,$r2\n',0x89abcdef,suffix),
        (b'copy.cmp $r0,$r1\ncopy.ldi.l $r2,16\ncopy.st.l ($r2),$r0\n'
         b'copy.ld.l $r0,($r2)\ncopy.branch.ltu .Ldone\ncopy.inc $r0,100\n.Ldone:\n',3,suffix)])
    for operation in (b'ld',b'st'):
        for width,last in ((b'b',8191),(b's',8190),(b'l',8188)):
            for address in (last+1,0xffffffff):
                body=f'copy.ldi.l $r2,{address}\n'.encode()
                operands=b'$r0,($r2)' if operation==b'ld' else b'($r2),$r0'
                cases.append((body+b'copy.'+operation+b'.'+width+b' '+operands+b'\n',None,suffix))
    narrow_values=(0,0x7f,0x80,0xff,0x7fff,0x8000,0xffff,0x89abcdef,0xffffffff)
    for width,bits in (('b',8),('s',16)):
        mask=(1<<bits)-1
        for value in narrow_values:
            truncated=value&mask
            cases.append((f'copy.ldi.{width} $r0,{value}\n'.encode(),truncated,suffix))
            for kind in ('zex','sex'):
                extended=truncated
                if kind=='sex' and truncated&(1<<(bits-1)): extended=truncated-(1<<bits)
                for register in ('$r0','$r2'):
                    body=f'copy.ldi.l {register},{value}\ncopy.{kind}.{width} $r0,{register}\n'.encode()
                    cases.append((body,extended&0xffffffff,suffix))
        cases.append((f'copy.ldi.{width} $r0,-1\ncopy.sex.{width} $r0,$r0\n'.encode(),0xffffffff,suffix))
        body=f'copy.ldi.l $r2,16\ncopy.ldi.{width} $r0,{1<<(bits-1)}\n'.encode()
        body+=f'copy.st.{width} ($r2),$r0\ncopy.ld.{width} $r0,($r2)\ncopy.sex.{width} $r0,$r0\n'.encode()
        cases.append((body,(1<<(bits-1))- (1<<bits) &0xffffffff,suffix))
    cases.extend([
        (b'copy.push $sp,$r0\ncopy.ldi.l $r0,99\ncopy.pop $sp,$r0\n',3,suffix),
        (b'copy.push $sp,$sp\ncopy.pop $sp,$r0\n',8192,suffix),
        (b'copy.push $sp,$r0\ncopy.pop $sp,$r1\ncopy.mov $r0,$sp\n',8192,suffix),
        (b'copy.push $sp,$r0\ncopy.push $sp,$r1\ncopy.pop $sp,$r2\ncopy.pop $sp,$r0\ncopy.sub $r0,$r2\n',0xffffffff,suffix),
        (b'copy.ldi.l $r2,20\ncopy.push $r2,$r0\ncopy.pop $r2,$r2\ncopy.mov $r0,$r2\n',3,suffix),
        (b'copy.cmp $r0,$r1\ncopy.push $sp,$r1\ncopy.pop $sp,$r2\ncopy.branch.ltu .Ldone\n'
         b'copy.ldi.l $r0,100\n.Ldone:\n',3,suffix),
        (b'copy.ldi.l $sp,0\ncopy.push $sp,$r0\n',None,suffix),
        (b'copy.ldi.l $sp,2\ncopy.push $sp,$r0\n',None,suffix),
        (b'copy.pop $sp,$r0\n',None,suffix),
        (b'copy.ldi.l $sp,8190\ncopy.pop $sp,$r0\n',None,suffix)])
    cases.extend([
        (b'copy.trap\n', None, b''),
        (b'copy.cmp $r0,$r1\ncopy.branch.eq .Lbad\ncopy.add $r0,$r1\n'
         b'copy.ret\n.Lbad:\ncopy.trap\n', 7, b''),
        (b'copy.cmp $r0,$r0\ncopy.branch.eq .Lbad\ncopy.ret\n.Lbad:\ncopy.trap\n', None, b'')])
    results=[]
    for index,(body,value,tail) in enumerate(cases):
        folder=root/str(index);folder.mkdir()
        assembly=prefix+body+tail
        (folder/"input.s").write_bytes(assembly)
        result=subprocess.run([str(native)],input=assembly,capture_output=True,check=True)
        assert len(result.stdout)==65536
        (folder/"image.bin").write_bytes(result.stdout)
        command=[str(result_emulator),"--ticks","100000","--core",str(folder/"image.bin"),"--trace",str(folder/"trace.txt")]
        (folder/"command.json").write_text(json.dumps(command)+"\n")
        checked=subprocess.run(command,capture_output=True,check=True,timeout=10)
        (folder/"out.bin").write_bytes(checked.stdout)
        assert checked.stdout==(b"" if value is None else struct.pack("<I",value)),checked.stdout
        assert not checked.stderr and (folder/"trace.txt").read_bytes().endswith(b' idle\n')
        results.append({"image_sha256":hashlib.sha256(result.stdout).hexdigest(),"output_hex":checked.stdout.hex()})
        if index==args.guest_case: incoming,expected,expected_value=assembly,result.stdout,value
    if not 0<=args.guest_case<len(cases):
        raise ValueError("guest case index outside fixture list")
    bad_bodies=[b'copy.mul.x $r0,$r1\n',b'copy.mov $r99,$r0\n',b'copy.ldi.l $r0,4294967296\n',
                b'copy.ldi.l $r0,08\n',b'copy.jmpa elsewhere\n']
    invalid=[prefix+s+suffix for s in bad_bodies]+[b'.data\nvalue:\ncopy.ret\n',
        prefix+b'copy.add $r0,$r1\n',prefix+b'other:\ncopy.ret\n',
        prefix+b'copy.ret\ncopy.add $r0,$r1\n',prefix+b'copy.ret\x00\n']
    invalid.extend([prefix+b'copy.jmpa .Lmissing\n'+suffix,
                    prefix+b'.Ldup:\n.Ldup:\n'+suffix])
    invalid.extend([prefix+b'copy.branch.eq .Lyes\n.Lyes:\n'+suffix,
                    prefix+b'copy.cmp $r0,$r1\ncopy.branch.zz .Lyes\n.Lyes:\n'+suffix,
                    prefix+b'copy.cmp $r0,$r1\ncopy.branch.eq .Lmissing\n'+suffix,
                    prefix+b'copy.udiv $r0,$r1\ncopy.branch.eq .Lyes\n.Lyes:\n'+suffix])
    for index,assembly in enumerate(invalid):
        (root/f"invalid-{index}.s").write_bytes(assembly)
        result=subprocess.run([str(native)],input=assembly,capture_output=True)
        assert result.returncode==2 and not result.stdout,(index,result.returncode)
    if args.native_only:
        (root/"evidence.json").write_text(json.dumps({"source_sha256":hashes,
            "result_space_bytes":args.result_space_bytes,
            "native_direct_cases":results,"rejected_cases":len(invalid)},indent=2)+"\n")
        print(f"OK {len(results)} direct images and {len(invalid)} rejected inputs")
        return
    if args.assembly:
        incoming=args.assembly.read_bytes()
        (root/"gcc-input.s").write_bytes(incoming)
        result=subprocess.run([str(native)],input=incoming,capture_output=True,check=True)
        expected=result.stdout
        expected_value=args.expected_result
        assert len(expected)==65536
    prefix=args.newlib.resolve()/"riscv64-unknown-elf"
    manifest=build(sources,root/"linker.stream",compiler=args.compiler,stream=True,optimization="-O2",
        extra_cflags=[include,profile_flag,"-isystem",str(prefix/"include"),"-DCS_RUNTIME_EXTERNAL_MEMORY"],
        extra_libraries=["-Wl,--start-group",str(prefix/"lib/libc.a"),"-lgcc","-Wl,--end-group"])
    (root/"in.bin").write_bytes((root/"linker.stream").read_bytes()+incoming)
    execution=execute_segments(ROOT/"build/bin/space",root/"linker",root/"in.bin",
        space_bytes=manifest["space_bytes"],layer_bytes=manifest["layer_bits"]//8,
        ticks=100000,timeout=300,compression="zstd")
    output=(root/"linker/program.in").read_bytes();assert output==expected
    raw=(root/"linker/space.bin").read_bytes()
    def word(at):return sum(((raw[(at+i)//8]>>(7-(at+i)%8))&1)<<i for i in range(32))
    assert word(132128)==10 and word(132160)==0
    direct=root/"guest-result";direct.mkdir();(direct/"image.bin").write_bytes(output)
    command=[str(result_emulator),"--core",str(direct/"image.bin"),"--trace",str(direct/"trace.txt")]
    (direct/"command.json").write_text(json.dumps(command)+"\n")
    checked=subprocess.run(command,capture_output=True,check=True,timeout=10)
    (direct/"out.bin").write_bytes(checked.stdout);assert checked.stdout==struct.pack("<I",expected_value)
    (root/"evidence.json").write_text(json.dumps({"scope":"guest leaf assembler; compiler execution must be verified separately",
        "source_sha256":hashes,"native_direct_cases":results,"rejected_cases":len(invalid),
        "guest_case":args.guest_case,"assembly_sha256":hashlib.sha256(incoming).hexdigest(),
        "result_space_bytes":args.result_space_bytes,
        "guest_link_execution":execution,"guest_exit":word(132160),
        "guest_image_sha256":hashlib.sha256(output).hexdigest(),"direct_output_hex":checked.stdout.hex()},indent=2)+"\n")
    print(f"OK guest copy assembler generated direct image; result {expected_value:#x} without RV32I")


if __name__=="__main__":main()
