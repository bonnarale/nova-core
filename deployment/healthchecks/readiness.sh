#!/usr/bin/env bash
set -euo pipefail
# Readiness check — verifies all dependencies are available
check_endpoint() {
    local name="$1" url="$2"
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "OK: $name"
    else
        echo "FAIL: $name (status=$STATUS)"
        return 1
    fi
}

check_endpoint "backend" "http://localhost:8000/health"
check_endpoint "deployment/readiness" "http://localhost:8000/api/v1/deployment/readiness"
