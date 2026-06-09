#!/usr/bin/env bash
# First-time provisioning for Hilaac Academy on Ubuntu 24.04 LTS.
# Run as a sudo-capable user. Idempotent where practical.
set -euo pipefail

APP_USER="${APP_USER:-hilaac}"
APP_HOME="/home/$APP_USER"
APP_DIR="$APP_HOME/hilaac-academy"
REPO_URL="${REPO_URL:-https://github.com/abdimalikdualex/Hilaac-Academy.git}"
DB_NAME="${DB_NAME:-hilaac_academy}"
DB_USER="${DB_USER:-hilaac}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 16)}"

echo "==> Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3 python3-venv python3-dev build-essential \
    postgresql postgresql-contrib libpq-dev \
    redis-server nginx git curl ufw certbot python3-certbot-nginx

echo "==> Creating app user (if missing)..."
id "$APP_USER" &>/dev/null || sudo adduser --disabled-password --gecos "" "$APP_USER"
sudo usermod -aG www-data "$APP_USER"

echo "==> Configuring PostgreSQL database..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'Africa/Nairobi';"

echo "==> Cloning project..."
sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR" 2>/dev/null || \
    (cd "$APP_DIR" && sudo -u "$APP_USER" git pull)

echo "==> Creating virtualenv + installing deps..."
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements/production.txt"

echo "==> Creating data directories..."
sudo -u "$APP_USER" mkdir -p "$APP_HOME/media" "$APP_HOME/backups" "$APP_HOME/logs"

if [ ! -f "$APP_DIR/.env" ]; then
  echo "==> Writing starter .env (EDIT SECRETS BEFORE GOING LIVE)..."
  SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(50))')"
  sudo -u "$APP_USER" tee "$APP_DIR/.env" >/dev/null <<EOF
SECRET_KEY=$SECRET
DEBUG=False
ALLOWED_HOSTS=hilaacacademy.com,www.hilaacacademy.com
CSRF_TRUSTED_ORIGINS=https://hilaacacademy.com,https://www.hilaacacademy.com
SITE_URL=https://hilaacacademy.com
DATABASE_URL=postgres://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False
USE_X_ACCEL_REDIRECT=True
MEDIA_ROOT=$APP_HOME/media
LOGS_DIR=$APP_HOME/logs
GUNICORN_WORKERS=3
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-now
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@hilaacacademy.com
EOF
  echo "    DB password: $DB_PASSWORD"
fi

echo "==> Installing systemd units..."
sudo cp "$APP_DIR"/deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hilaac-gunicorn.service
sudo systemctl enable --now hilaac-celery.service
sudo systemctl enable --now hilaac-celerybeat.service
sudo systemctl enable --now redis-server

echo "==> Installing Nginx site..."
sudo cp "$APP_DIR/deploy/nginx/hilaac_academy.conf" /etc/nginx/sites-available/hilaac_academy
sudo ln -sf /etc/nginx/sites-available/hilaac_academy /etc/nginx/sites-enabled/hilaac_academy
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo "==> Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "==> Running migrations + collectstatic..."
cd "$APP_DIR"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py migrate --noinput
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py collectstatic --noinput
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" manage.py ensure_admin || true

echo "==> Allowing Nginx (www-data) to read static/media..."
sudo chmod o+x "$APP_HOME"
sudo chmod -R o+rX "$APP_DIR/staticfiles" "$APP_HOME/media"

echo "==> Installing backup cron..."
sudo crontab -u "$APP_USER" "$APP_DIR/deploy/scripts/hilaac-backups.cron"

echo ""
echo "Provisioning done. Next steps:"
echo "  1. Edit $APP_DIR/.env (set real ADMIN_PASSWORD, EMAIL_*, domain)."
echo "  2. Point your domain's DNS A record to this server's IP."
echo "  3. Run: sudo certbot --nginx -d hilaacacademy.com -d www.hilaacacademy.com"
echo "  4. Restart: sudo systemctl restart hilaac-gunicorn"
