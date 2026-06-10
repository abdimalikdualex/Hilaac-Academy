from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self):
        from django.db.backends.signals import connection_created

        from apps.core.boot_checks import check_database_persistence
        from apps.core.persistence import configure_sqlite

        check_database_persistence()
        connection_created.connect(configure_sqlite, dispatch_uid="hilaac_sqlite_wal")

        from apps.cms.models import (
            Announcement,
            FAQ,
            PartnerSchool,
            PlatformIntroductionVideo,
            SiteStatistic,
            Testimonial,
        )
        from apps.core.models import SiteSettings
        from apps.core.signals import connect_cache_signals, register_cache_sync
        from apps.courses.models import Language, Lesson, Level, Module
        from apps.library.models import LibraryResource
        from apps.payments.models import ExchangeRate

        for model in (
            SiteSettings,
            Level,
            Module,
            Lesson,
            Language,
            FAQ,
            Announcement,
            PlatformIntroductionVideo,
            PartnerSchool,
            Testimonial,
            SiteStatistic,
            LibraryResource,
            ExchangeRate,
        ):
            register_cache_sync(model)
        connect_cache_signals()
