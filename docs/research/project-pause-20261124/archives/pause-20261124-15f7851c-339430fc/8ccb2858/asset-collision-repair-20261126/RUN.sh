#!/usr/bin/env bash
set -euo pipefail
repair_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec /usr/bin/python3 "$repair_dir/handover.py" "$@"
