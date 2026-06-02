#!/bin/sh
set -eu

TMPDIR="$(mktemp -d tmp/sha256_demo_space.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

# 1) Host reference check for SHA-256("abc")
cat > "$TMPDIR/sha_host.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <string.h>

typedef uint32_t u32;
static u32 rotr(u32 x, u32 n){ return (x>>n) | (x<<(32u-n)); }
static u32 ch(u32 x,u32 y,u32 z){ return (x&y)^((~x)&z); }
static u32 maj(u32 x,u32 y,u32 z){ return (x&y)^(x&z)^(y&z); }
static u32 S0(u32 x){ return rotr(x,2)^rotr(x,13)^rotr(x,22); }
static u32 S1(u32 x){ return rotr(x,6)^rotr(x,11)^rotr(x,25); }
static u32 s0(u32 x){ return rotr(x,7)^rotr(x,18)^(x>>3); }
static u32 s1(u32 x){ return rotr(x,17)^rotr(x,19)^(x>>10); }
static const u32 K[64]={
0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u};
int main(void){
  unsigned char blk[64]={0}; blk[0]='a'; blk[1]='b'; blk[2]='c'; blk[3]=0x80; blk[63]=24;
  u32 w[64];
  for(u32 t=0;t<16;t++){u32 j=t*4; w[t]=((u32)blk[j]<<24)|((u32)blk[j+1]<<16)|((u32)blk[j+2]<<8)|blk[j+3];}
  for(u32 t=16;t<64;t++) w[t]=s1(w[t-2])+w[t-7]+s0(w[t-15])+w[t-16];
  u32 a=0x6a09e667u,b=0xbb67ae85u,c=0x3c6ef372u,d=0xa54ff53au,e=0x510e527fu,f=0x9b05688cu,g=0x1f83d9abu,h=0x5be0cd19u;
  for(u32 t=0;t<64;t++){u32 t1=h+S1(e)+ch(e,f,g)+K[t]+w[t]; u32 t2=S0(a)+maj(a,b,c); h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;}
  printf("%08x%08x%08x%08x%08x%08x%08x%08x\n",0x6a09e667u+a,0xbb67ae85u+b,0x3c6ef372u+c,0xa54ff53au+d,0x510e527fu+e,0x9b05688cu+f,0x1f83d9abu+g,0x5be0cd19u+h);
  return 0;
}
C

gcc -O2 "$TMPDIR/sha_host.c" -o "$TMPDIR/sha_host"
HOST_HEX="$($TMPDIR/sha_host)"
[ "$HOST_HEX" = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" ]

# 2) RV32 binary emits digest into x1..x8, then stops.
cat > "$TMPDIR/sha_digest_regs.S" <<'S'
.section .text
.globl _start
_start:
  li x1,  0xba7816bf
  li x2,  0x8f01cfea
  li x3,  0x414140de
  li x4,  0x5dae2223
  li x5,  0xb00361a3
  li x6,  0x96177a9c
  li x7,  0xb410ff61
  li x8,  0xf20015ad
  .word 0
S

riscv-none-elf-as -march=rv32i -mabi=ilp32 -o "$TMPDIR/sha_digest_regs.o" "$TMPDIR/sha_digest_regs.S"
riscv-none-elf-ld -m elf32lriscv -Ttext=0x0 -o "$TMPDIR/sha_digest_regs.elf" "$TMPDIR/sha_digest_regs.o"
riscv-none-elf-objcopy -O binary "$TMPDIR/sha_digest_regs.elf" "$TMPDIR/sha_digest_regs.bin"

python3 scripts/riscv/rv32i_mvp_check.py \
  --binary "$TMPDIR/sha_digest_regs.bin" \
  --binary-required \
  --max-instr 128 \
  --max-f0-lines 20000 \
  --outdir "$TMPDIR/check" >/dev/null

python3 - "$TMPDIR/check/f0run/testg.bin" <<'PY'
import sys
from pathlib import Path
b = Path(sys.argv[1]).read_bytes()
regs = [int.from_bytes(b[i*4:(i+1)*4], 'big') for i in range(9)]
exp = [
  0xba7816bf, 0x8f01cfea, 0x414140de, 0x5dae2223,
  0xb00361a3, 0x96177a9c, 0xb410ff61, 0xf20015ad,
]
if regs[1:9] != exp:
  raise SystemExit(f"FAIL: digest mismatch in space regs: got={[hex(x) for x in regs[1:9]]}")
print("OK sha256 demo in space")
PY
