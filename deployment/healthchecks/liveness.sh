#!/usr/bin/env bash
set -euo pipefail
# Liveness check — verifies the process is alive
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/deployment/liveness" 2>/dev/null || echo "000")
if [ "$STATUS" = "200" ]; then
    exit 0
else
    exit 1
fi
