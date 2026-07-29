#!/usr/bin/env bash
set -euo pipefail
# NOVA CORE Deployment Health Check
# Usage: healthcheck.sh [endpoint] [expected_status]
ENDPOINT="${1:-http://localhost:8000/health}"
EXPECTED="${2:-200}"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT" 2>/dev/null || echo "000")
if [ "$STATUS" = "$EXPECTED" ]; then
    echo "OK: $ENDPOINT returned $STATUS"
    exit 0
else
    echo "FAIL: $ENDPOINT returned $STATUS (expected $EXPECTED)"
    exit 1
fi
