"""Persistent local storage for SQLite and uploads across Render redeploys."""
import logging
import os
import shutil
from pathlib import Path

from decouple import config

logger = logging.getLogger(__name__)

# Render Docker services: attach a persistent disk at this path in the dashboard.
DEFAULT_RENDER_DATA_DIR = "/app/data"


def resolve_data_dir(base_dir: Path) -> Path:
    explicit = config("PERSISTENT_DATA_DIR", default="").strip()
    if explicit:
        return Path(explicit)
    if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
        return Path(DEFAULT_RENDER_DATA_DIR)
    return base_dir


def ensure_data_dirs(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "media").mkdir(parents=True, exist_ok=True)
    return data_dir


def migrate_legacy_sqlite(data_dir: Path, base_dir: Path) -> None:
    """Copy a database from the ephemeral app directory on first boot."""
    target = data_dir / "db.sqlite3"
    if target.exists():
        return
    legacy = base_dir / "db.sqlite3"
    if not legacy.exists():
        return
    shutil.copy2(legacy, target)
    logger.info("Migrated SQLite database to persistent storage at %s", target)


def configure_sqlite(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.execute("PRAGMA foreign_keys=ON;")
