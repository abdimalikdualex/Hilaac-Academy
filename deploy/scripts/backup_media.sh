#!/usr/bin/env bash
# Daily media backup (incremental tar). Retains daily archives for 30 days.
set -euo pipefail

MEDIA_DIR="${MEDIA_DIR:-/home/hilaac/media}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/hilaac/backups}"
DAILY_DIR="$BACKUP_ROOT/daily/media"
RETENTION_DAYS=30

mkdir -p "$DAILY_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$DAILY_DIR/hilaac_media_${STAMP}.tar.gz"

if [ ! -d "$MEDIA_DIR" ]; then
  echo "Media dir $MEDIA_DIR not found; aborting." >&2
  exit 1
fi

tar -czf "$OUT" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"
echo "Media backup written: $OUT"

find "$DAILY_DIR" -name "hilaac_media_*.tar.gz" -mtime +$RETENTION_DAYS -delete
echo "Pruned media backups older than ${RETENTION_DAYS} days."
