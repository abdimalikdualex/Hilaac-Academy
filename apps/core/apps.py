from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self):
        from apps.cms.models import FAQ, SiteStatistic, Testimonial
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
            Testimonial,
            SiteStatistic,
            LibraryResource,
            ExchangeRate,
        ):
            register_cache_sync(model)
        connect_cache_signals()
