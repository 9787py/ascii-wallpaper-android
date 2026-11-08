#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"
python3 sync_core.py --check
buildozer android debug
