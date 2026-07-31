#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../backend"
echo "Running tests..."
python -m pytest ../tests/backend/ -v --tb=short "$@"
echo "Tests complete."
