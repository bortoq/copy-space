#!/bin/sh
set -eu
python3 - <<'PY'
import os, sys
bad=[]
for root,_,files in os.walk("src"):
  for n in files:
    try: n.encode("ascii")
    except UnicodeEncodeError:
      bad.append(os.path.join(root,n))
if bad:
  print("Non-ASCII filenames:\n" + "\n".join(bad))
  sys.exit(1)
print("OK: all filenames ASCII")
PY