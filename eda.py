#!/usr/bin/env python3
"""Native local EDA workbench. All tool invocations use argv, never shell=True."""
from edaworkbench.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
