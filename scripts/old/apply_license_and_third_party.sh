#!/bin/sh
set -eu

ts="$(date +%Y%m%d_%H%M%S)"
bakdir="bak/cleanup_${ts}_license_third_party"
mkdir -p "$bakdir"

backup() {
  f="$1"
  if [ -f "$f" ]; then
    cp -a "$f" "$bakdir/$(echo "$f" | tr '/ ' '__').bak"
  fi
}

backup LICENSE
backup THIRD_PARTY.md
backup doc/readme.md

# --- LICENSE (MIT) ---
if [ -f LICENSE ]; then
  echo "SKIP: LICENSE already exists" >&2
else
  cat > LICENSE <<'LIC'
MIT License

Copyright (c) 2026 Dmitri Bortoq

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LIC
  echo "OK: wrote LICENSE (MIT)" >&2
fi

# --- THIRD_PARTY.md ---
cat > THIRD_PARTY.md <<'TP'
# THIRD_PARTY.md — third-party code and licenses — 2026-05-05

This repository is intended to be MIT-licensed (see `LICENSE`).

## Third-party code
At the time of writing (2026-05-05), the project aims to contain **no copied third-party source code**.

If third-party code is added in the future, it must be:
- explicitly listed here (file paths + source URL + license),
- compatible with the repository license and intended usage.
TP
echo "OK: wrote THIRD_PARTY.md" >&2

# --- doc/readme.md: add License section (neutral) ---
if grep -q "^## License" doc/readme.md 2>/dev/null; then
  echo "SKIP: doc/readme.md already has License section" >&2
else
  # Append a small section at the end.
  cat >> doc/readme.md <<'MD'

## License
- License: MIT (see `LICENSE`).
- Third-party notes: see `THIRD_PARTY.md`.
MD
  echo "OK: appended License section to doc/readme.md" >&2
fi

echo "DONE (backups in $bakdir)" >&2
