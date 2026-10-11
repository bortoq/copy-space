#!/bin/sh
set -eu

mkdir -p tmp

layer_bin="tmp/proof_first_layer_out.bin"
out_bin="tmp/proof_first_layer_out.out"
space_out_bin="tmp/proof_first_layer_out.space.out"

build/bin/assembler < modules/proof_first_layer_out.copy > "$layer_bin"
printf '\003' >> "$layer_bin"

build/bin/space_image_proof \
  --in "$layer_bin" \
  --out "$out_bin" \
  --ticks 3

got_hex="$(xxd -p "$out_bin" | tr -d '\n')"
[ "$got_hex" = "03" ] || {
  echo "FAIL: expected OUT=03 got=${got_hex:-<empty>}" >&2
  exit 1
}

build/bin/space < "$layer_bin" > "$space_out_bin"
space_hex="$(xxd -p "$space_out_bin" | tr -d '\n')"
[ "$space_hex" = "03" ] || {
  echo "FAIL: expected space OUT=03 got=${space_hex:-<empty>}" >&2
  exit 1
}

echo "OK first layer load: proof OUT=$got_hex, space OUT=$space_hex"
