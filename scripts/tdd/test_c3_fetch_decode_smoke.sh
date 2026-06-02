#!/bin/sh
set -eu

sh scripts/tdd/test_c3_layout.sh
sh scripts/tdd/test_c3_fetch_only.sh
sh scripts/tdd/test_c3_decode_known_unknown.sh

echo "OK c3 fetch+decode smoke"
