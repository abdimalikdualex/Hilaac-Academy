#!/bin/sh
set -e

DATA_DIR="${PERSISTENT_DATA_DIR:-/app/data}"
mkdir -p "$DATA_DIR/media"

if [ ! -f "$DATA_DIR/db.sqlite3" ] && [ -f "/app/db.sqlite3" ]; then
  echo "Migrating database to persistent storage at $DATA_DIR..."
  cp /app/db.sqlite3 "$DATA_DIR/db.sqlite3"
fi

python manage.py migrate --noinput
python manage.py ensure_admin

if [ "$SEED_INITIAL_DATA" = "true" ]; then
  python manage.py seed_data --demo
fi

WORKERS="${GUNICORN_WORKERS:-1}"
exec gunicorn hilaac_academy.wsgi:application --bind 0.0.0.0:8000 --workers "$WORKERS"
