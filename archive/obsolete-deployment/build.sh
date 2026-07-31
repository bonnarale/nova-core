#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "Building NOVA CORE..."
docker build -f deployment/docker/Dockerfile -t nova-core:latest .
echo "Build complete."
