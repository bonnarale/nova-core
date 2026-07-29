#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../backend"
echo "Running linter..."
python -m ruff check app/ "$@"
echo "Lint complete."
