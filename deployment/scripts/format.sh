#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../backend"
echo "Formatting code..."
python -m ruff format app/ "$@"
echo "Format complete."
