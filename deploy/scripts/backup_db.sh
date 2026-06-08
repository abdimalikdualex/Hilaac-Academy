#!/usr/bin/env bash
# Daily PostgreSQL backup. Retains daily dumps for 30 days.
set -euo pipefail

APP_DIR="${APP_DIR:-/home/hilaac/hilaac-academy}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/hilaac/backups}"
DAILY_DIR="$BACKUP_ROOT/daily/db"
RETENTION_DAYS=30

# Load DATABASE_URL from the app .env
set -a
# shellcheck disable=SC1091
[ -f "$APP_DIR/.env" ] && . "$APP_DIR/.env"
set +a

mkdir -p "$DAILY_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$DAILY_DIR/hilaac_db_${STAMP}.dump"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL not set; aborting." >&2
  exit 1
fi

# Custom format (-Fc) supports parallel, selective restore via pg_restore.
pg_dump "$DATABASE_URL" -Fc -f "$OUT"
gzip -f "$OUT"
echo "Database backup written: ${OUT}.gz"

# Retention: delete daily db dumps older than RETENTION_DAYS
find "$DAILY_DIR" -name "hilaac_db_*.dump.gz" -mtime +$RETENTION_DAYS -delete
echo "Pruned db backups older than ${RETENTION_DAYS} days."
