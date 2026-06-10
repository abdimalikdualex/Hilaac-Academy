#!/usr/bin/env bash
# Reset Super Admin login (run on the VPS when locked out).
# Usage: sudo -u hilaac bash deploy/scripts/reset_admin.sh YourNewPassword
set -euo pipefail

APP_DIR="${APP_DIR:-/home/hilaac/hilaac-academy}"
PASSWORD="${1:-}"

if [ -z "$PASSWORD" ]; then
  echo "Usage: $0 <new-password>"
  echo "Example: sudo -u hilaac bash deploy/scripts/reset_admin.sh MySecurePass123"
  exit 1
fi

cd "$APP_DIR"
"$APP_DIR/venv/bin/python" manage.py ensure_admin --reset --username admin --password "$PASSWORD"
echo "Done. Log in at /accounts/login/ with username: admin"
echo "You will be redirected to /admin-portal/ (not /admin/)."
