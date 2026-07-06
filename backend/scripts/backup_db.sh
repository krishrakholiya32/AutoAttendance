#!/bin/bash
# Full logical backup of the AutoAttendance production database.
# Run before any migration or schema-touching change. Keeps the last 10 backups.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
DB_NAME="${DB_NAME:-autoattendance}"
DB_USER="${DB_USER:-autoattendance}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUT_FILE="$BACKUP_DIR/autoattendance_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"
pg_dump -Fc -U "$DB_USER" -h localhost "$DB_NAME" > "$OUT_FILE"
echo "Backup written: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"

# Keep only the last 10 backups
ls -1t "$BACKUP_DIR"/autoattendance_*.dump 2>/dev/null | tail -n +11 | xargs -r rm -f
