#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from copyspace.v0.validate import main
if __name__ == "__main__":
    raise SystemExit(main())
