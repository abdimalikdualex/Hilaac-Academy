#!/usr/bin/env bash
# Safe deploy/update for Hilaac Academy — never deletes database or media data.
# - PostgreSQL lives outside this git repo (/home/hilaac/…)
# - Media uploads live in MEDIA_ROOT (outside the repo)
# - seed_data is NEVER run here (courses/users are never auto-restored)
# - ensure_admin only creates a missing admin; it never resets passwords
set -euo pipefail

APP_DIR="${APP_DIR:-/home/hilaac/hilaac-academy}"
VENV="${VENV:-$APP_DIR/venv}"
BRANCH="${DEPLOY_BRANCH:-main}"
MEDIA_ROOT="${MEDIA_ROOT:-/home/hilaac/media}"

cd "$APP_DIR"

echo "==> Safe deploy — your database and uploads are preserved."
echo "    (Only code is updated; no seed/reset commands run.)"

echo "==> Pre-deploy database backup..."
if [ -x "$APP_DIR/deploy/scripts/backup_db.sh" ]; then
    bash "$APP_DIR/deploy/scripts/backup_db.sh" || echo "    Backup skipped or failed (deploy continues)."
fi

echo "==> Pulling latest code ($BRANCH)..."
git fetch --all --prune
git reset --hard "origin/$BRANCH"

echo "==> Installing dependencies..."
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r requirements/production.txt

echo "==> Running database migrations (schema only — no data wipe)..."
"$VENV/bin/python" manage.py migrate --noinput
if ! "$VENV/bin/python" manage.py migrate --check; then
  echo "ERROR: Unapplied migrations remain. Site may show 500 errors until migrate completes."
  exit 1
fi

echo "==> Ensuring super admin exists (create only — never resets password)..."
"$VENV/bin/python" manage.py ensure_admin || true

echo "==> Collecting static files..."
"$VENV/bin/python" manage.py collectstatic --noinput

echo "==> Ensuring Nginx can read static/media..."
chmod o+x "$(dirname "$APP_DIR")" 2>/dev/null || true
chmod -R o+rX "$APP_DIR/staticfiles" 2>/dev/null || true
chmod -R o+rX "$MEDIA_ROOT" 2>/dev/null || true

echo "==> Restarting services..."
sudo systemctl restart hilaac-gunicorn
sudo systemctl restart hilaac-celery
sudo systemctl restart hilaac-celerybeat
sudo systemctl reload nginx

echo "==> Deploy complete — all user/course/payment data retained."
"$VENV/bin/python" manage.py check --deploy || true
