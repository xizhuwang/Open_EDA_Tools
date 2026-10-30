#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
bash eda unit-test
bash eda doctor
bash eda test
bash eda run verify --timeout 3600 --jobs 2
python3 scripts/check_physical.py examples/counter/project.json
