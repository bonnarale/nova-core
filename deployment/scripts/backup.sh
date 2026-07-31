#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL..."
if command -v pg_dump &>/dev/null; then
    pg_dump -h localhost -U nova nova > "$BACKUP_DIR/postgres_$TIMESTAMP.sql"
fi

echo "Backing up configuration..."
cp -r deployment/environments "$BACKUP_DIR/env_$TIMESTAMP" 2>/dev/null || true

echo "Backup complete: $BACKUP_DIR"
