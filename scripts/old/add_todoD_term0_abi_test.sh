#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_term0_abi_test"
mkdir -p "$bakdir"

need_file() { [ -f "$1" ] || { echo "FAIL: missing $1" >&2; exit 1; }; }
backup() { cp -a "$1" "$bakdir/$(echo "$1" | tr '/ ' '__')"; }

[ -d src ] && [ -d scripts ] || { echo "FAIL: run from project root" >&2; exit 1; }

TDD="scripts/tdd"
RUNALL="$TDD/run_all.sh"
TEST="$TDD/test_term0_desc_abi.sh"

need_file "$RUNALL"
backup "$RUNALL"

if [ -f "$TEST" ]; then
  echo "SKIP: $TEST already exists"
else
  cat >"$TEST" <<'EOF'
#!/bin/sh
set -eu

# file: scripts/tdd/test_term0_desc_abi.sh
# date: 2026-05-05
# purpose: verify TERM0 device descriptor ABI via ART[65..66] (BUS_BASE, TERM0_DESC)

# Prefer mkimage_meta.sh (it already knows how to build std7_fixed images).
if [ ! -f scripts/mkimage_meta.sh ]; then
  echo "FAIL: missing scripts/mkimage_meta.sh" >&2
  exit 1
fi

mkdir -p tmp
stamp="tmp/.tdd_term0_stamp"
: >"$stamp"

log="tmp/tdd_term0_mkimage.log"
# Capture both stdout/stderr; we need ART(byte)=... which mkimage prints to stderr.
( sh scripts/mkimage_meta.sh small ) >"$log" 2>&1 || {
  echo "FAIL: mkimage_meta.sh small failed; log follows:" >&2
  tail -n 200 "$log" >&2 || true
  exit 1
}

art_byte="$(sed -n 's/^ART(byte)=//p' "$log" | tail -n 1)"
if [ -z "$art_byte" ]; then
  echo "FAIL: cannot find ART(byte)=... in mkimage log (tmp/tdd_term0_mkimage.log)" >&2
  tail -n 200 "$log" >&2 || true
  exit 1
fi

# Find newest .bin produced after stamp (mkimage_meta typically produces exactly one).
space_bin="$(find tmp -maxdepth 1 -type f -name '*.bin' -newer "$stamp" -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR==1{print $2}')"
if [ -z "$space_bin" ]; then
  echo "FAIL: cannot find new tmp/*.bin produced by mkimage_meta.sh (after stamp)" >&2
  echo "Log:" >&2
  tail -n 200 "$log" >&2 || true
  echo "tmp listing:" >&2
  ls -la tmp >&2 || true
  exit 1
fi

python3 - "$space_bin" "$art_byte" <<'PY'
import sys, math

space_path = sys.argv[1]
art_byte   = int(sys.argv[2])

data = open(space_path, "rb").read()
space_bytes = len(data)
space_bits = space_bytes * 8

# derive addr_bits like VM does: bits_needed -> round up to multiple of 8
bits_needed = (space_bits - 1).bit_length()
addr_bits = ((bits_needed + 7) // 8) * 8
addr_bytes = addr_bits // 8

def need(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)

need(addr_bits in (8,16,24,32,40,48,56,64), f"suspicious addr_bits={addr_bits}")
need(art_byte >= 0 and art_byte < space_bytes, f"ART(byte) out of range: {art_byte}")

def read_art(i: int) -> int:
    off = art_byte + i*addr_bytes
    need(off + addr_bytes <= space_bytes, f"ART[{i}] out of range (off={off})")
    return int.from_bytes(data[off:off+addr_bytes], "big")

BUS_BASE   = read_art(65)
TERM0_DESC = read_art(66)

need(BUS_BASE != 0, "ART[65] BUS_BASE is 0")
need(TERM0_DESC != 0, "ART[66] TERM0_DESC is 0")
need(BUS_BASE % 8 == 0, "BUS_BASE not byte-aligned (bitaddr%8!=0)")
need(TERM0_DESC % 8 == 0, "TERM0_DESC not byte-aligned (bitaddr%8!=0)")
need(BUS_BASE < space_bits, "BUS_BASE outside space")
need(TERM0_DESC < space_bits, "TERM0_DESC outside space")
need(TERM0_DESC >= BUS_BASE, "TERM0_DESC < BUS_BASE (unexpected)")

desc_off = TERM0_DESC // 8
need(desc_off + 64 <= space_bytes, "TERM0_DESC near end of space (need >=64 bytes)")

def u8(off): return data[off]
def u16be(off): return int.from_bytes(data[off:off+2], "big")
def u32be(off): return int.from_bytes(data[off:off+4], "big")
def u64be(off): return int.from_bytes(data[off:off+8], "big")

magic = data[desc_off:desc_off+4]
need(magic == b"CDEV", f"bad descriptor magic {magic!r} (expected b'CDEV')")

ver = u16be(desc_off+4)
typ = u16be(desc_off+6)
dev_id = u64be(desc_off+8)
pcnt = u8(desc_off+16)

need(ver == 1, f"unexpected descriptor version={ver}")
need(typ == 1, f"unexpected dev_type={typ} (expected 1 TERM)")
need(pcnt == 3, f"unexpected port_count={pcnt} (expected 3)")
need(dev_id != 0, "device_id is 0 (unexpected)")

# ports start at byte 20, each record 8 bytes
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
    need(chan_base < space_bits, f"port[{i}] chan_base outside space")
    need(chan_base >= BUS_BASE, f"port[{i}] chan_base < BUS_BASE (unexpected)")

    ch_off = chan_base // 8
    need(ch_off + 4 <= space_bytes, f"port[{i}] chan header out of range")
    ch_magic = data[ch_off:ch_off+4]
    need(ch_magic == b"CHN1", f"port[{i}] bad channel magic {ch_magic!r} (expected b'CHN1')")

print("OK: term0 descriptor ABI")
PY
EOF
  chmod +x "$TEST"
  echo "OK: created $TEST"
fi

# add to run_all.sh if missing
if grep -q "test_term0_desc_abi.sh" "$RUNALL"; then
  echo "OK: already in $RUNALL"
else
  backup "$RUNALL"
  # Insert near other tests, before final summary/exit
  # We append at the end to be safe.
  printf '\n%s\n' 'sh scripts/tdd/test_term0_desc_abi.sh' >>"$RUNALL"
  echo "OK: appended to $RUNALL"
fi

echo "DONE: backups in $bakdir"
echo "Next: make tdd"
