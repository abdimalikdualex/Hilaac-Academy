import os
from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

from apps.core.persistence import ensure_data_dirs, resolve_data_dir  # noqa: E402

DATA_DIR = ensure_data_dirs(resolve_data_dir(BASE_DIR))

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key-change-me")
DEBUG = config("DEBUG", default=True, cast=bool)

# Render.com sets RENDER_EXTERNAL_HOSTNAME automatically (e.g. hilaac-academy.onrender.com)
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
ALLOWED_HOSTS = list(config("ALLOWED_HOSTS", default="localhost,127.0.0.1,.onrender.com", cast=Csv()))
for _host in (RENDER_EXTERNAL_HOSTNAME, ".onrender.com"):
    if _host and _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "cloudinary",
    "cloudinary_storage",
    "django_htmx",
    "django_celery_beat",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.courses",
    "apps.learning",
    "apps.assessments",
    "apps.payments",
    "apps.certificates",
    "apps.library",
    "apps.notifications",
    "apps.cms",
    "apps.analytics",
    "apps.admin_portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.UserLocaleMiddleware",
    "apps.core.middleware.RoleAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.core.middleware.EmailVerificationMiddleware",
]

ROOT_URLCONF = "hilaac_academy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "apps.core.context_processors.site_settings",
                "apps.notifications.context_processors.unread_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "hilaac_academy.wsgi.application"

USE_SQLITE = config("USE_SQLITE", default=False, cast=bool)
_on_render = bool(RENDER_EXTERNAL_HOSTNAME or os.environ.get("RENDER"))
# Render injects DATABASE_URL when a Postgres instance is linked to the web service.
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("DATABASE_INTERNAL_URL")
    or config("DATABASE_URL", default="")
)

if DATABASE_URL and not USE_SQLITE:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif USE_SQLITE or _on_render:
    # SQLite on a Render persistent disk (PERSISTENT_DATA_DIR=/app/data) survives redeploys.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "db.sqlite3",
            "OPTIONS": {"timeout": 30},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
            "NAME": config("DB_NAME", default="hilaac_academy"),
            "USER": config("DB_USER", default="hilaac"),
            "PASSWORD": config("DB_PASSWORD", default="hilaac_secret"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.CaseInsensitiveUsernameBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.HilaacPasswordValidator"},
]

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("so", "Af-Soomaali"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_L10N = True
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

if DEBUG:
    # Serve new assets immediately from static/ without collectstatic.
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    WHITENOISE_USE_FINDERS = True
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(DATA_DIR / "media")))

# Serve sensitive media (videos, certificates, payment proofs) only after an auth
# check. Enable on the VPS so Nginx blocks direct /media/ access to these folders
# and Django streams them via X-Accel-Redirect. Left off in dev (Django serves media).
USE_X_ACCEL_REDIRECT = config("USE_X_ACCEL_REDIRECT", default=False, cast=bool)
X_ACCEL_INTERNAL_PREFIX = "/_protected/"

# Allow large video uploads in admin (default 2.5MB is too small)
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

_REDIS_URL = config("REDIS_URL", default="") or config("CELERY_BROKER_URL", default="")
if _REDIS_URL and not config("USE_LOC_MEM_CACHE", default=False, cast=bool):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
            "KEY_PREFIX": "hilaac",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0

# Auth redirects
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "cms:home"

# Email
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@hilaacacademy.com")
# Set True only after SMTP is configured (EMAIL_HOST, etc.)
REQUIRE_EMAIL_VERIFICATION = config("REQUIRE_EMAIL_VERIFICATION", default=False, cast=bool)

# Site
SITE_URL = config(
    "SITE_URL",
    default=f"https://{RENDER_EXTERNAL_HOSTNAME}" if RENDER_EXTERNAL_HOSTNAME else "http://localhost:8000",
)
WHATSAPP_SUPPORT_NUMBER = config("WHATSAPP_SUPPORT_NUMBER", default="+254722156718")

CSRF_TRUSTED_ORIGINS = list(config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv()))
if RENDER_EXTERNAL_HOSTNAME:
    _render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)

# Render terminates TLS at the proxy; Django must trust X-Forwarded-Proto.
if RENDER_EXTERNAL_HOSTNAME or not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cloudinary
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
}

if config("CLOUDINARY_CLOUD_NAME", default=""):
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Run tasks inline when Redis/worker is unavailable (local dev default).
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=DEBUG, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = True

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Payments
MPESA_CONSUMER_KEY = config("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = config("MPESA_CONSUMER_SECRET", default="")
MPESA_SHORTCODE = config("MPESA_SHORTCODE", default="")
MPESA_PASSKEY = config("MPESA_PASSKEY", default="")
MPESA_CALLBACK_URL = config("MPESA_CALLBACK_URL", default="")
MPESA_ENV = config("MPESA_ENV", default="sandbox")

EVC_PLUS_MERCHANT_ID = config("EVC_PLUS_MERCHANT_ID", default="")
EVC_PLUS_API_KEY = config("EVC_PLUS_API_KEY", default="")

# Sessions
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=60 * 60 * 24 * 14, cast=int)  # 14 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = config("SESSION_EXPIRE_AT_BROWSER_CLOSE", default=False, cast=bool)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # required for JS-driven forms; protected by SameSite
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Security (production)
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Logging — write app, security, and error logs to separate files under LOGS_DIR.
_logs_configured = Path(config("LOGS_DIR", default=str(DATA_DIR / "logs")))
try:
    _logs_configured.mkdir(parents=True, exist_ok=True)
    LOGS_DIR = _logs_configured
except OSError:
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {process:d} {message}",
            "style": "{",
        },
        "simple": {"format": "{asctime} {levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "app.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "error.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "level": "ERROR",
            "formatter": "verbose",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "security.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "audit_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "audit.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 30,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "app_file", "error_file"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console", "app_file", "error_file"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["security_file", "console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["error_file", "console"], "level": "ERROR", "propagate": False},
        "hilaac.audit": {"handlers": ["audit_file", "console"], "level": "INFO", "propagate": False},
    },
}
