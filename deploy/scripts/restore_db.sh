#!/usr/bin/env bash
# Restore a PostgreSQL backup created by backup_db.sh / backup_weekly.sh.
# Usage: restore_db.sh /path/to/hilaac_db_YYYYMMDD.dump.gz
set -euo pipefail

APP_DIR="${APP_DIR:-/home/hilaac/hilaac-academy}"
DUMP="${1:-}"

if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
  echo "Usage: $0 <backup-file.dump[.gz]>" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
[ -f "$APP_DIR/.env" ] && . "$APP_DIR/.env"
set +a

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL not set; aborting." >&2
  exit 1
fi

echo "WARNING: this overwrites the current database. Press Ctrl+C to cancel."
sleep 5

TMP="$DUMP"
if [[ "$DUMP" == *.gz ]]; then
  TMP="$(mktemp)"
  gunzip -c "$DUMP" > "$TMP"
fi

# --clean drops existing objects first; --if-exists avoids errors on first restore.
pg_restore --clean --if-exists --no-owner --dbname "$DATABASE_URL" "$TMP"
echo "Restore complete from $DUMP"
