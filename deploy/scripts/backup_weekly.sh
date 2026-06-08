#!/usr/bin/env bash
# Weekly full backup: database + media + .env, bundled together.
# Retention: weekly 12 weeks (84d), monthly 12 months (kept on day 01).
set -euo pipefail

APP_DIR="${APP_DIR:-/home/hilaac/hilaac-academy}"
MEDIA_DIR="${MEDIA_DIR:-/home/hilaac/media}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/hilaac/backups}"
WEEKLY_DIR="$BACKUP_ROOT/weekly"
MONTHLY_DIR="$BACKUP_ROOT/monthly"
WEEKLY_RETENTION_DAYS=84      # 12 weeks
MONTHLY_RETENTION_DAYS=366    # 12 months

set -a
# shellcheck disable=SC1091
[ -f "$APP_DIR/.env" ] && . "$APP_DIR/.env"
set +a

mkdir -p "$WEEKLY_DIR" "$MONTHLY_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Database
if [ -n "${DATABASE_URL:-}" ]; then
  pg_dump "$DATABASE_URL" -Fc -f "$WORK/database.dump"
fi

# Media
[ -d "$MEDIA_DIR" ] && tar -czf "$WORK/media.tar.gz" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"

# Config (without committing secrets to git, but kept in encrypted-at-rest backups)
[ -f "$APP_DIR/.env" ] && cp "$APP_DIR/.env" "$WORK/env.backup"

BUNDLE="$WEEKLY_DIR/hilaac_full_${STAMP}.tar.gz"
tar -czf "$BUNDLE" -C "$WORK" .
echo "Weekly full backup written: $BUNDLE"

# Keep a monthly copy on the 1st of the month
if [ "$(date +%d)" = "01" ]; then
  cp "$BUNDLE" "$MONTHLY_DIR/hilaac_full_${STAMP}.tar.gz"
  echo "Monthly copy stored."
fi

find "$WEEKLY_DIR" -name "hilaac_full_*.tar.gz" -mtime +$WEEKLY_RETENTION_DAYS -delete
find "$MONTHLY_DIR" -name "hilaac_full_*.tar.gz" -mtime +$MONTHLY_RETENTION_DAYS -delete
echo "Pruned old weekly/monthly backups."
