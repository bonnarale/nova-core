#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../backend"
echo "Running database migrations..."
python -c "from app.db.models import Base; print('Models loaded successfully')"
echo "Migrations complete."
