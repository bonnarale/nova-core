#!/usr/bin/env sh
set -eu

docker compose ps
docker compose exec backend python -m app.healthcheck

