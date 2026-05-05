#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_fix_tdd_term0_desc_abi_poolcells"
mkdir -p "$bakdir"

T="scripts/tdd/test_term0_desc_abi.sh"
[ -f "$T" ] || { echo "FAIL: missing $T" >&2; exit 1; }
cp -a "$T" "$bakdir/test_term0_desc_abi.sh.bak"

cat >"$T" <<'EOF'
#!/bin/sh
set -eu

# file: scripts/tdd/test_term0_desc_abi.sh
# date: 2026-05-05
# purpose: verify TERM0 device descriptor ABI via ART[65..66]
# note: POSIX sh (dash) compatible

[ -f scripts/mkimage_meta.sh ] || { echo "FAIL: missing scripts/mkimage_meta.sh" >&2; exit 1; }

mkdir -p tmp
stamp="tmp/.tdd_term0_stamp"
: >"$stamp"

log_meta="tmp/tdd_term0_meta.log"
log_run="tmp/tdd_term0_run.log"

# mkimage_meta.sh requires: --out and --pool-cells
# Choose a small-ish pool; std7_fixed words are fixed-address, so this should be safe.
POOL_CELLS="${POOL_CELLS:-1024}"

( sh scripts/mkimage_meta.sh --out tmp/tdd_term0 --pool-cells "$POOL_CELLS" ) >"$log_meta" 2>&1 || {
  echo "FAIL: mkimage_meta.sh failed; log follows:" >&2
  tail -n 200 "$log_meta" >&2 || true
  exit 1
}

# Find a generated meta runner newer than stamp
meta="$(python3 - "$stamp" <<'PY'
import os, sys
stamp = sys.argv[1]
st = os.stat(stamp).st_mtime
cands=[]
for name in os.listdir("tmp"):
    if not name.endswith(".meta"):
        continue
    p=os.path.join("tmp", name)
    s=os.stat(p)
    if s.st_mtime <= st:
        continue
    cands.append((s.st_size, s.st_mtime, p))
cands.sort(reverse=True)
print(cands[0][2] if cands else "")
PY
)"
if [ -z "$meta" ]; then
  echo "FAIL: no tmp/*.meta produced by mkimage_meta.sh" >&2
  tail -n 200 "$log_meta" >&2 || true
  ls -la tmp >&2 || true
  exit 1
fi

( sh "$meta" ) >"$log_run" 2>&1 || {
  echo "FAIL: meta runner failed: $meta; log follows:" >&2
  tail -n 200 "$log_run" >&2 || true
  exit 1
}

# Find ART(byte)=... in tmp/*.log
art_byte="$(grep -h '^ART(byte)=' tmp/*.log 2>/dev/null | tail -n 1 | sed 's/^ART(byte)=//')"
if [ -z "$art_byte" ]; then
  echo "FAIL: cannot find ART(byte)=... in tmp/*.log" >&2
  echo "meta log tail:" >&2
  tail -n 80 "$log_meta" >&2 || true
  echo "run log tail:" >&2
  tail -n 120 "$log_run" >&2 || true
  ls -la tmp >&2 || true
  exit 1
fi

# Find produced .bin newer than stamp (pick largest)
space_bin="$(python3 - "$stamp" <<'PY'
import os, sys
stamp = sys.argv[1]
st = os.stat(stamp).st_mtime
cands=[]
for name in os.listdir("tmp"):
    if not name.endswith(".bin"):
        continue
    p=os.path.join("tmp", name)
    s=os.stat(p)
    if s.st_mtime <= st:
        continue
    cands.append((s.st_size, s.st_mtime, p))
cands.sort(reverse=True)
print(cands[0][2] if cands else "")
PY
)"
if [ -z "$space_bin" ]; then
  echo "FAIL: cannot find tmp/*.bin produced after stamp" >&2
  tail -n 120 "$log_run" >&2 || true
  ls -la tmp >&2 || true
  exit 1
fi

python3 - "$space_bin" "$art_byte" <<'PY'
import sys

space_path = sys.argv[1]
art_byte   = int(sys.argv[2])

data = open(space_path, "rb").read()
space_bytes = len(data)
space_bits = space_bytes * 8

bits_needed = (space_bits - 1).bit_length()
addr_bits = ((bits_needed + 7) // 8) * 8
addr_bytes = addr_bits // 8

def need(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)

need(0 <= art_byte < space_bytes, f"ART(byte) out of range: {art_byte}")
need(1 <= addr_bytes <= 8, f"unexpected addr_bytes={addr_bytes}")

def read_art(i: int) -> int:
    off = art_byte + i*addr_bytes
    need(off + addr_bytes <= space_bytes, f"ART[{i}] out of range")
    return int.from_bytes(data[off:off+addr_bytes], "big")

BUS_BASE   = read_art(65)
TERM0_DESC = read_art(66)

need(BUS_BASE != 0, "ART[65] BUS_BASE is 0")
need(TERM0_DESC != 0, "ART[66] TERM0_DESC is 0")
need(BUS_BASE % 8 == 0, "BUS_BASE not byte-aligned")
need(TERM0_DESC % 8 == 0, "TERM0_DESC not byte-aligned")
need(BUS_BASE < space_bits, "BUS_BASE outside space")
need(TERM0_DESC < space_bits, "TERM0_DESC outside space")

desc_off = TERM0_DESC // 8
need(desc_off + 64 <= space_bytes, "TERM0_DESC near end of space (need >=64 bytes)")

def u8(off): return data[off]
def u16be(off): return int.from_bytes(data[off:off+2], "big")
def u64be(off): return int.from_bytes(data[off:off+8], "big")

magic = data[desc_off:desc_off+4]
need(magic == b"CDEV", f"bad descriptor magic {magic!r}")

ver = u16be(desc_off+4)
typ = u16be(desc_off+6)
dev_id = u64be(desc_off+8)
pcnt = u8(desc_off+16)

need(ver == 1, f"unexpected descriptor version={ver}")
need(typ == 1, f"unexpected dev_type={typ}")
need(pcnt == 3, f"unexpected port_count={pcnt}")
need(dev_id != 0, "device_id is 0")

PORTS_BASE = desc_off + 20
for i in range(3):
    rec = PORTS_BASE + i*8
    port_id = u8(rec+0)
    proto   = u8(rec+1)
    flags   = u16be(rec+2)
    chan_base = int.from_bytes(data[rec+4:rec+4+addr_bytes], "big")

    need(port_id == i, f"port[{i}] port_id={port_id} expected {i}")
    need(proto == 1, f"port[{i}] proto={proto} expected 1 (CHN1)")
    need(flags == 0, f"port[{i}] flags={flags} expected 0")
    need(chan_base != 0, f"port[{i}] chan_base is 0")
    need(chan_base % 8 == 0, f"port[{i}] chan_base not byte-aligned")

    ch_off = chan_base // 8
    need(ch_off + 4 <= space_bytes, f"port[{i}] channel header out of range")
    ch_magic = data[ch_off:ch_off+4]
    need(ch_magic == b"CHN1", f"port[{i}] bad channel magic {ch_magic!r}")

print("OK: term0 descriptor ABI")
PY
EOF

chmod +x "$T"
echo "OK: fixed $T (backup in $bakdir)"
EOF

chmod +x scripts/fix_tdd_term0_desc_abi_needs_poolcells.sh
echo "OK: wrote scripts/fix_tdd_term0_desc_abi_needs_poolcells.sh"
