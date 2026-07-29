#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Starting NOVA CORE..."
docker compose -f deployment/docker/docker-compose.yml up -d backend
echo "Started."
