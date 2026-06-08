#!/usr/bin/env bash
# Zero-fuss deploy/update for Hilaac Academy on the VPS.
# Run as the hilaac user from the project directory:  ./deploy/scripts/deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/home/hilaac/hilaac-academy}"
VENV="${VENV:-$APP_DIR/venv}"
BRANCH="${DEPLOY_BRANCH:-main}"

cd "$APP_DIR"

echo "==> Pulling latest code ($BRANCH)..."
git fetch --all --prune
git reset --hard "origin/$BRANCH"

echo "==> Installing dependencies..."
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r requirements/production.txt

echo "==> Running database migrations..."
"$VENV/bin/python" manage.py migrate --noinput

echo "==> Ensuring super admin exists..."
"$VENV/bin/python" manage.py ensure_admin || true

echo "==> Collecting static files..."
"$VENV/bin/python" manage.py collectstatic --noinput

echo "==> Restarting services..."
sudo systemctl restart hilaac-gunicorn
sudo systemctl restart hilaac-celery
sudo systemctl restart hilaac-celerybeat
sudo systemctl reload nginx

echo "==> Deploy complete."
"$VENV/bin/python" manage.py check --deploy || true
