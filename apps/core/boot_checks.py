"""Log critical production misconfiguration at startup."""
import logging
import os

logger = logging.getLogger(__name__)


def check_database_persistence():
    from django.conf import settings

    engine = settings.DATABASES["default"]["ENGINE"]
    on_render = bool(os.environ.get("RENDER"))
    using_sqlite = "sqlite" in engine

    if on_render and using_sqlite:
        logger.critical(
            "RENDER + SQLite: course and user data will be LOST on every deploy. "
            "Link a Render PostgreSQL database and set DATABASE_URL."
        )
    elif using_sqlite:
        logger.warning(
            "Using SQLite — fine for local dev; use PostgreSQL in production for persistent data."
        )
