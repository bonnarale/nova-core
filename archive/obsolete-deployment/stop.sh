#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Stopping NOVA CORE..."
docker compose -f deployment/docker/docker-compose.yml down
echo "Stopped."
