# Hilaac Academy — Hostinger VPS Deployment Guide

Production deployment for **Ubuntu 24.04 LTS** using **Nginx + Gunicorn + PostgreSQL + Redis + Celery**.

## Architecture

```
Internet → Nginx (HTTPS, gzip, static/media, security headers)
             ├── /static/      → served directly (collectstatic)
             ├── /media/       → public uploads (thumbnails, profiles…)
             ├── /_protected/  → internal only (videos, certificates) via X-Accel-Redirect
             └── /             → Gunicorn (unix socket) → Django
                                   ├── PostgreSQL (all platform data)
                                   ├── Redis (cache + Celery broker)
                                   └── Celery worker + beat (background jobs)
```

## What's in `deploy/`

| Path | Purpose |
|------|---------|
| `nginx/hilaac_academy.conf` | Nginx site: HTTPS, gzip, static/media, protected media, security headers |
| `gunicorn/gunicorn.conf.py` | Gunicorn settings (workers, timeout, socket) |
| `systemd/hilaac-gunicorn.{socket,service}` | App server units |
| `systemd/hilaac-celery.service` | Celery worker |
| `systemd/hilaac-celerybeat.service` | Celery scheduler |
| `scripts/setup_server.sh` | One-time VPS provisioning |
| `scripts/deploy.sh` | Pull + migrate + collectstatic + restart |
| `scripts/backup_db.sh` | Daily PostgreSQL backup (30-day retention) |
| `scripts/backup_media.sh` | Daily media backup (30-day retention) |
| `scripts/backup_weekly.sh` | Weekly full backup (12 weeks / 12 months) |
| `scripts/restore_db.sh` | Restore a database backup |
| `scripts/hilaac-backups.cron` | Backup schedule |

---

## 1. First-time setup (automated)

SSH into the VPS as a sudo user, then:

```bash
git clone https://github.com/abdimalikdualex/Hilaac-Academy.git /tmp/hilaac-bootstrap
sudo REPO_URL=https://github.com/abdimalikdualex/Hilaac-Academy.git \
     bash /tmp/hilaac-bootstrap/deploy/scripts/setup_server.sh
```

This installs packages, creates the `hilaac` user, PostgreSQL DB, virtualenv, systemd
services, Nginx site, firewall, and the backup cron. It writes a starter `.env`.

Then:

```bash
sudo nano /home/hilaac/hilaac-academy/.env   # set ADMIN_PASSWORD, EMAIL_*, domain
# Point DNS A records (@ and www) to the server IP, then:
sudo certbot --nginx -d hilaacacademy.com -d www.hilaacacademy.com
sudo systemctl restart hilaac-gunicorn
```

---

## 2. First-time setup (manual outline)

If you prefer step-by-step, `setup_server.sh` documents every command. Key points:

- **DB:** create role + database, set `DATABASE_URL` in `.env`.
- **Env:** copy `.env.production.example` → `.env`, fill secrets. Set
  `MEDIA_ROOT=/home/hilaac/media` and `LOGS_DIR=/home/hilaac/logs` so data lives
  **outside** the git checkout and survives `git pull`/redeploys.
- **Services:** copy `deploy/systemd/*` to `/etc/systemd/system/`, `daemon-reload`,
  enable + start.
- **Nginx:** symlink `deploy/nginx/hilaac_academy.conf` into `sites-enabled`, test, reload.

---

## 3. Routine deployments

```bash
sudo -u hilaac /home/hilaac/hilaac-academy/deploy/scripts/deploy.sh
```

Equivalent to the required manual flow:

```bash
git pull origin main
pip install -r requirements/production.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart hilaac-gunicorn
systemctl reload nginx
```

Migrations run automatically on every deploy, so the schema stays current.

---

## 4. Data persistence (no data loss on deploy)

- **Database:** PostgreSQL is a separate service; `git pull` and code redeploys never
  touch it. Deletes are permanent only via the app (recycle bin / soft delete) — they
  do **not** reappear because seeding is one-time and guarded.
- **Media:** stored at `/home/hilaac/media` (outside the repo). Code updates don't
  remove it.
- **Restores:** only from backups via `restore_db.sh`.

---

## 5. Backups

Installed via `hilaac-backups.cron`:

| Backup | Schedule | Retention |
|--------|----------|-----------|
| Database | daily 02:00 | 30 days |
| Media | daily 02:30 | 30 days |
| Full (db+media+env) | weekly Sun 03:00 | 12 weeks |
| Monthly copy | 1st of month | 12 months |

Backups live in `/home/hilaac/backups`. **Copy them off-server** (e.g. `rclone` to
object storage) for disaster recovery.

Restore a database:

```bash
/home/hilaac/hilaac-academy/deploy/scripts/restore_db.sh \
    /home/hilaac/backups/daily/db/hilaac_db_YYYYMMDD_HHMMSS.dump.gz
```

---

## 6. Security checklist

- HTTPS enforced (`SECURE_SSL_REDIRECT`) + HSTS (1 year, preload).
- Secure, HttpOnly, SameSite cookies; CSRF protection on all forms.
- Security headers at both Django and Nginx layers.
- Rate limiting on login (10/5min) and registration (5/10min); blocks logged to `security.log`.
- Role isolation enforced by `RoleAccessMiddleware` (students/instructors/admin cannot
  cross boundaries; wrong-role access returns 403).
- **Direct media access blocked:** videos, certificate PDFs, payment screenshots and
  assignment submissions are `internal` in Nginx and only released by Django after an
  enrollment/ownership check (`apps/core/protected_media.py`). Free preview lessons stay public.
- Firewall (ufw) allows only SSH + HTTP/HTTPS.

Verify Django's own checks:

```bash
python manage.py check --deploy
```

---

## 7. Logs & monitoring

Written under `LOGS_DIR` (`/home/hilaac/logs`), rotated automatically:

- `app.log` — general application logs
- `error.log` — errors / 500s
- `security.log` — auth + rate-limit events
- `audit.log` — logins, payments, uploads, course actions, admin changes

Service logs: `journalctl -u hilaac-gunicorn -f` (and `hilaac-celery`, `hilaac-celerybeat`).

---

## 8. Performance

- Redis caching (set `REDIS_URL`); versioned cache keys with auto-invalidation.
- WhiteNoise compressed static storage + Nginx caching of `/static/`.
- Gzip for text assets; long-lived cache headers for static.
- Query optimization + indexes already in models; responsive/WebP images via the
  imaging pipeline.

---

## 9. Future integrations

- **Payments:** M-Pesa, Airtel, Zaad, EVC Plus, Sahal, Premier, Visa/Mastercard — add
  credentials to `.env`; provider scaffolding is in `apps/payments`.
- **Mobile app:** DRF API under `/api/` (session auth today; add token/JWT auth for mobile).
