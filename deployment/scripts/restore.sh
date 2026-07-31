#!/usr/bin/env bash
set -euo pipefail
BACKUP_FILE="${1:?Usage: restore.sh <backup_file>}"

echo "Restoring from $BACKUP_FILE..."
if [[ "$BACKUP_FILE" == *.sql ]]; then
    psql -h localhost -U nova nova < "$BACKUP_FILE"
fi
echo "Restore complete."
