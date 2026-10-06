#!/usr/bin/env bash
# Side-by-side: ty vs Taskless over the same files. Defaults to examples/.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run scripts/compare.py "$@"
