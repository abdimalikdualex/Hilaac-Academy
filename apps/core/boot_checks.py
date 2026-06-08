"""Log critical production misconfiguration at startup."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def check_database_persistence():
    from django.conf import settings

    engine = settings.DATABASES["default"]["ENGINE"]
    on_render = bool(os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_HOSTNAME"))
    using_sqlite = "sqlite" in engine

    if not using_sqlite:
        return

    data_dir = Path(getattr(settings, "DATA_DIR", settings.BASE_DIR))

    if on_render:
        if data_dir.as_posix() == settings.BASE_DIR.as_posix():
            logger.critical(
                "RENDER + SQLite in app directory: data will be LOST on every deploy. "
                "Attach a Render persistent disk at /app/data and set PERSISTENT_DATA_DIR=/app/data."
            )
            return

        try:
            probe = data_dir / ".write_probe"
            probe.touch()
            probe.unlink()
        except OSError:
            logger.critical(
                "Persistent data directory is not writable: %s. "
                "Add a Render disk mounted at /app/data.",
                data_dir,
            )
            return

        db_path = Path(settings.DATABASES["default"]["NAME"])
        logger.info(
            "SQLite persistence enabled — database at %s (survives redeploys when disk is attached).",
            db_path,
        )
        return

    logger.warning(
        "Using SQLite — fine for local dev; production on Render uses a persistent disk at /app/data."
    )
