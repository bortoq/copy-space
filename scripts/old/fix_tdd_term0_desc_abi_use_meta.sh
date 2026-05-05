#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_fix_term0_abi_use_meta"
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
# method: use scripts/mkimage_meta.sh (requires --out/--pool-cells/--meta)

[ -f scripts/mkimage_meta.sh ] || { echo "FAIL: missing scripts/mkimage_meta.sh" >&2; exit 1; }

mkdir -p tmp

OUT="tmp/tdd_term0_space.bin"
META="tmp/tdd_term0.meta"
LOG="tmp/tdd_term0.meta.log"

POOL_CELLS="${POOL_CELLS:-1024}"

# mkimage_meta runs mkimage and writes META + LOG
sh scripts/mkimage_meta.sh --out "$OUT" --pool-cells "$POOL_CELLS" --meta "$META" --log "$LOG"

# Load meta variables (OUT_PATH, ART_BYTE, etc.)
# meta file is simple KEY=VALUE so '.' is ok
. "$META"

if [ -z "${OUT_PATH:-}" ]; then
  echo "FAIL: META missing OUT_PATH" >&2
  tail -n 80 "$META" >&2 || true
  exit 1
fi
if [ -z "${ART_BYTE:-}" ]; then
  echo "FAIL: META missing ART_BYTE" >&2
  tail -n 80 "$META" >&2 || true
  exit 1
fi

python3 - "$OUT_PATH" "$ART_BYTE" <<'PY'
import sys

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

need(0 <= art_byte < space_bytes, f"ART_BYTE out of range: {art_byte}")
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
need(typ == 1, f"unexpected dev_type={typ} (expected 1 TERM)")
need(pcnt == 3, f"unexpected port_count={pcnt} (expected 3)")
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
    need(chan_base < space_bits, f"port[{i}] chan_base outside space")

    ch_off = chan_base // 8
    need(ch_off + 4 <= space_bytes, f"port[{i}] channel header out of range")
    ch_magic = data[ch_off:ch_off+4]
    need(ch_magic == b"CHN1", f"port[{i}] bad channel magic {ch_magic!r}")

print("OK: term0 descriptor ABI")
PY
EOF

chmod +x "$T"
echo "OK: fixed $T (backup in $bakdir)"
